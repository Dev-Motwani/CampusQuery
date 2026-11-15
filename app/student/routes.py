"""
Student and public portal routes for CampusQuery (Phase 5).
Includes:
- Landing page with category highlights and latest circulars
- Authenticated student dashboard with 7 core academic categories
- Public circular feed and keyword search with parameterized filtering
- Paginated results with multi-criteria filters (category, priority, status)
- Comprehensive student notice detail view with academic requirements and milestone timeline
- Read-only student views with strict draft and archived content blocking (Rule E: HTTP 404)
- System healthcheck endpoint
"""
from datetime import datetime, timedelta
from flask import render_template, jsonify, current_app, session, request, redirect, url_for, abort, flash
from werkzeug.exceptions import HTTPException
from sqlalchemy import or_, func, case
from sqlalchemy.exc import OperationalError as SQLAlchemyOperationalError

from app.student import student_bp
from app.database import db, check_mysql_health
from app.auth.utils import login_required, get_current_user
from app.models.notice import Notice
from app.models.category import Category
from app.models.deadline import Deadline
from app.models.notification import Notification
from app.models.office import OfficeInformation
from app.services.deadline_service import (
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_unread_notification_count,
    format_academic_datetime
)


def get_categories_with_counts():
    """
    Retrieves all active categories alongside the count of published notices.
    Safe across MySQL and SQLite.
    """
    try:
        categories = Category.query.filter_by(is_active=True).order_by(Category.name.asc()).all()
        # Aggregate count of published notices grouped by category
        counts_query = (
            db.session.query(Notice.category_id, func.count(Notice.id))
            .filter(Notice.status == "published")
            .group_by(Notice.category_id)
            .all()
        )
        counts_map = dict(counts_query)
        for cat in categories:
            cat.published_notice_count = counts_map.get(cat.id, 0)
        return categories
    except Exception as e:
        current_app.logger.warning(f"Failed to fetch category counts: {e}")
        return []


@student_bp.route("/")
def index():
    """
    Main landing page for CampusQuery.
    Displays search hero, active categories with circular counts,
    latest published notices, and upcoming deadlines.
    """
    try:
        categories = get_categories_with_counts()
        recent_notices = (
            Notice.query.filter_by(status="published")
            .order_by(Notice.published_at.desc())
            .limit(6)
            .all()
        )
        urgent_notices = (
            Notice.query.filter_by(status="published", priority="urgent")
            .order_by(Notice.published_at.desc())
            .limit(3)
            .all()
        )
        upcoming_deadlines = (
            Deadline.query.join(Notice)
            .filter(
                Notice.status == "published",
                Deadline.status.in_(["upcoming", "ongoing", "extended"]),
                Deadline.due_date >= datetime.utcnow()
            )
            .order_by(Deadline.due_date.asc())
            .limit(4)
            .all()
        )
    except (SQLAlchemyOperationalError, Exception) as e:
        current_app.logger.warning(f"Database unavailable on landing page: {e}")
        categories = []
        recent_notices = []
        urgent_notices = []
        upcoming_deadlines = []

    return render_template(
        "student/index.html",
        categories=categories,
        recent_notices=recent_notices,
        urgent_notices=urgent_notices,
        upcoming_deadlines=upcoming_deadlines
    )


@student_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Authenticated student dashboard.
    Displays:
    - Student profile details (name, roll number, email)
    - 7 core academic categories (Scholarships, Admissions, CET, Examinations, Sports, Events, General)
    - Live published notice counts per category
    - Urgent circular alerts
    - Latest published circulars
    - Upcoming milestone deadlines with countdown days
    - Student notifications
    """
    user = get_current_user()

    try:
        categories = get_categories_with_counts()

        notices = (
            Notice.query.filter_by(status="published")
            .order_by(Notice.published_at.desc())
            .limit(8)
            .all()
        )

        urgent_notices = (
            Notice.query.filter_by(status="published", priority="urgent")
            .order_by(Notice.published_at.desc())
            .limit(4)
            .all()
        )

        deadlines = (
            Deadline.query.join(Notice)
            .filter(
                Notice.status == "published",
                Deadline.status.in_(["upcoming", "ongoing", "extended"]),
                Deadline.due_date >= datetime.utcnow()
            )
            .order_by(Deadline.due_date.asc())
            .limit(6)
            .all()
        )

        notifications = (
            Notification.query.filter_by(user_id=user.id)
            .order_by(Notification.created_at.desc())
            .limit(6)
            .all()
            if user else []
        )
        unread_notifications_count = get_unread_notification_count(user.id) if user else 0

        total_published = Notice.query.filter_by(status="published").count()
        urgent_count = Notice.query.filter_by(status="published", priority="urgent").count()
        upcoming_count = len(deadlines)

    except (SQLAlchemyOperationalError, Exception) as e:
        current_app.logger.warning(f"Database error on dashboard: {e}")
        categories = []
        notices = []
        urgent_notices = []
        deadlines = []
        notifications = []
        unread_notifications_count = 0
        total_published = 0
        urgent_count = 0
        upcoming_count = 0

    return render_template(
        "student/dashboard.html",
        user=user,
        categories=categories,
        notices=notices,
        urgent_notices=urgent_notices,
        deadlines=deadlines,
        notifications=notifications,
        unread_notifications_count=unread_notifications_count,
        total_published=total_published,
        urgent_count=urgent_count,
        upcoming_count=upcoming_count
    )


@student_bp.route("/notices")
def list_notices():
    """
    Public and student-accessible circulars directory with search, filtering, and pagination.
    Supports:
    - Parameterized keyword search across title, summary, content, eligibility, required documents
    - Category filtering (by slug or ID)
    - Priority filtering (urgent, high, medium, low)
    - Status/date filtering (upcoming_deadlines, recent, active)
    - Pagination with boundary handling
    - Strictly enforces Notice.status == 'published' (Rule E: drafts & archived hidden)
    """
    # 1. Parse and sanitize query parameters
    raw_q = request.args.get("q", "")
    q = raw_q.strip()[:100]  # sanitize & bound input

    category_slug = request.args.get("category", "").strip().lower()
    priority = request.args.get("priority", "").strip().lower()
    status_filter = request.args.get("status", "").strip().lower()
    sort_by = request.args.get("sort", "newest").strip().lower()

    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    per_page = 9

    # 2. Base query: STRICTLY published notices only
    query = Notice.query.filter(Notice.status == "published")

    # 3. Apply keyword search via parameterized queries
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Notice.title.ilike(search_term),
                Notice.summary.ilike(search_term),
                Notice.content.ilike(search_term),
                Notice.eligibility.ilike(search_term),
                Notice.required_documents.ilike(search_term),
                Notice.submission_instructions.ilike(search_term)
            )
        )

    # 4. Apply category filter
    selected_category = None
    if category_slug and category_slug != "all":
        try:
            selected_category = Category.query.filter_by(slug=category_slug).first()
            if not selected_category and category_slug.isdigit():
                selected_category = db.session.get(Category, int(category_slug))

            if selected_category:
                query = query.filter(Notice.category_id == selected_category.id)
            else:
                # If invalid category provided, return no notices rather than crashing
                query = query.filter(Notice.category_id == -1)
        except Exception as e:
            current_app.logger.warning(f"Error querying category: {e}")
            selected_category = None

    # 5. Apply priority filter
    if priority and priority in ("low", "medium", "high", "urgent"):
        query = query.filter(Notice.priority == priority)

    # 6. Apply status / date filter
    if status_filter == "upcoming_deadlines":
        query = (
            query.join(Notice.deadlines)
            .filter(
                Deadline.due_date >= datetime.utcnow(),
                Deadline.status.in_(["upcoming", "ongoing", "extended"])
            )
            .distinct()
        )
    elif status_filter == "recent":
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        query = query.filter(Notice.published_at >= one_week_ago)
    elif status_filter == "active":
        query = query.filter(
            or_(
                Notice.expires_at == None,  # noqa: E711
                Notice.expires_at >= datetime.utcnow()
            )
        )

    # 7. Apply sorting
    if sort_by == "oldest":
        query = query.order_by(Notice.published_at.asc(), Notice.id.asc())
    elif sort_by == "urgent_first":
        priority_weight = case(
            (Notice.priority == "urgent", 1),
            (Notice.priority == "high", 2),
            (Notice.priority == "medium", 3),
            else_=4
        )
        query = query.order_by(priority_weight, Notice.published_at.desc())
    elif sort_by == "title":
        query = query.order_by(Notice.title.asc())
    else:  # 'newest' default
        query = query.order_by(Notice.published_at.desc(), Notice.id.desc())

    # 8. Execute count and pagination
    try:
        total_count = query.count()
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        if page > total_pages and total_count > 0:
            page = total_pages

        offset = (page - 1) * per_page
        notices = query.offset(offset).limit(per_page).all()
        categories = get_categories_with_counts()
    except (SQLAlchemyOperationalError, Exception) as e:
        current_app.logger.warning(f"Database error in list_notices: {e}")
        total_count = 0
        total_pages = 1
        notices = []
        categories = []

    # Calculate pagination metadata for template rendering
    pagination = {
        "page": page,
        "per_page": per_page,
        "total": total_count,
        "pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_num": page - 1 if page > 1 else None,
        "next_num": page + 1 if page < total_pages else None,
        "iter_pages": [p for p in range(max(1, page - 2), min(total_pages + 1, page + 3))]
    }

    return render_template(
        "student/notices.html",
        notices=notices,
        pagination=pagination,
        categories=categories,
        selected_category=selected_category,
        q=q,
        priority=priority,
        status_filter=status_filter,
        sort_by=sort_by
    )


@student_bp.route("/notices/<int:notice_id>")
def view_notice(notice_id: int):
    """
    Public and student notice detail view.
    Displays:
    - Notice title, summary, and complete instructions
    - Supplied eligibility criteria
    - Required documents checklist
    - Submission instructions
    - Milestone deadlines with countdown badges and status
    - Responsible office information and contact details
    - Associated document attachments
    - Associated flowchart workflows
    - Publication and update timestamps
    - Expired notice warning banner if expired

    CRITICAL SECURITY RULE E:
    Drafts and archived notices MUST NOT be accessible via student views.
    Returns HTTP 404 if notice does not exist or status is not 'published'.
    """
    try:
        notice = db.session.get(Notice, notice_id)
        if not notice or notice.status != "published":
            abort(404)

        # Milestone deadlines sorted chronologically
        deadlines = (
            Deadline.query.filter_by(notice_id=notice.id)
            .order_by(Deadline.due_date.asc())
            .all()
        )

        # Related notices in the same category (published only)
        related_notices = (
            Notice.query.filter(
                Notice.category_id == notice.category_id,
                Notice.id != notice.id,
                Notice.status == "published"
            )
            .order_by(Notice.published_at.desc())
            .limit(3)
            .all()
        )
    except (SQLAlchemyOperationalError, Exception) as e:
        if isinstance(e, HTTPException):
            raise
        current_app.logger.warning(f"Database error loading notice detail: {e}")
        abort(404)

    return render_template(
        "student/notice_detail.html",
        notice=notice,
        deadlines=deadlines,
        related_notices=related_notices
    )


@student_bp.route("/notices/s/<string:slug>")
def view_notice_by_slug(slug: str):
    """
    Slug-based alias route redirecting to the canonical notice detail page.
    Strictly verifies Notice.status == 'published'.
    """
    try:
        notice = Notice.query.filter_by(slug=slug, status="published").first()
        if not notice:
            abort(404)
        return redirect(url_for("student.view_notice", notice_id=notice.id))
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        current_app.logger.warning(f"Database error in view_notice_by_slug: {e}")
        abort(404)


@student_bp.route("/categories/<string:slug>")
def category_notices(slug: str):
    """
    Direct category route redirecting to the circulars feed filtered by category slug.
    Returns HTTP 404 if category does not exist or is inactive.
    """
    try:
        category = Category.query.filter_by(slug=slug, is_active=True).first()
        if not category:
            abort(404)
        return redirect(url_for("student.list_notices", category=category.slug))
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        current_app.logger.warning(f"Database error in category_notices: {e}")
        abort(404)


@student_bp.route("/health")
@student_bp.route("/api/health")
def healthcheck():
    """
    Application health endpoint.
    Reports operational status and database connection state without leaking credentials.
    """
    db_health = check_mysql_health()
    overall_status = "healthy" if db_health["connected"] else "degraded"

    return jsonify({
        "status": overall_status,
        "app": "CampusQuery",
        "version": "1.0.0",
        "environment": current_app.config.get("ENV", "development"),
        "database": {
            "connected": db_health["connected"],
            "name": db_health["database"],
            "message": db_health["message"]
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), 200


# ==============================================================================
# 5. CAMPUS OFFICE DIRECTORY & DETAIL (STUDENT/PUBLIC)
# ==============================================================================
@student_bp.route("/offices")
def list_offices():
    """
    Public and student-accessible campus office directory.
    Lists administrative offices with department, location, hours, and sample indicators.
    """
    try:
        offices = OfficeInformation.query.order_by(OfficeInformation.office_name.asc()).all()
    except (SQLAlchemyOperationalError, Exception) as e:
        current_app.logger.warning(f"Database error loading offices directory: {e}")
        offices = []

    return render_template("student/offices.html", offices=offices)


@student_bp.route("/offices/<int:office_id>")
def view_office(office_id):
    """
    Detailed office profile with operating hours, visit/submission instructions,
    contact details, and linked published circulars.
    """
    office = OfficeInformation.query.get_or_404(office_id)

    # Fetch published notices linked to this office
    published_notices = (
        Notice.query.filter_by(office_id=office.id, status="published")
        .order_by(Notice.published_at.desc())
        .limit(10)
        .all()
    )

    # Fetch active milestone deadlines linked to this office
    active_deadlines = (
        Deadline.query.join(Notice)
        .filter(
            Deadline.office_id == office.id,
            Notice.status == "published",
            Deadline.due_date >= datetime.utcnow()
        )
        .order_by(Deadline.due_date.asc())
        .limit(10)
        .all()
    )

    return render_template(
        "student/office_detail.html",
        office=office,
        published_notices=published_notices,
        active_deadlines=active_deadlines
    )


# ==============================================================================
# 6. IN-DASHBOARD NOTIFICATION CENTER
# ==============================================================================
@student_bp.route("/notifications")
@login_required
def list_notifications():
    """
    Student notification inbox.
    Displays in-dashboard alerts for new circulars, approaching deadlines, and date changes.
    Supports filtering by read/unread state.
    """
    user = get_current_user()
    filter_state = request.args.get("filter", "all").strip().lower()

    query = Notification.query.filter_by(user_id=user.id)
    if filter_state == "unread":
        query = query.filter_by(is_read=False)
    elif filter_state == "read":
        query = query.filter_by(is_read=True)

    notifications = query.order_by(Notification.created_at.desc()).all()
    unread_count = get_unread_notification_count(user.id)

    return render_template(
        "student/notifications.html",
        notifications=notifications,
        unread_count=unread_count,
        filter_state=filter_state
    )


@student_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    """Marks a single notification as read."""
    user = get_current_user()
    success = mark_notification_as_read(notification_id, user.id)

    if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
        return jsonify({"success": success, "notification_id": notification_id}), (200 if success else 404)

    if success:
        flash("Notification marked as read.", "info")
    return redirect(request.referrer or url_for("student.list_notifications"))


@student_bp.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    """Marks all notifications for the authenticated student as read."""
    user = get_current_user()
    marked_count = mark_all_notifications_as_read(user.id)

    if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
        return jsonify({"success": True, "count": marked_count}), 200

    flash(f"All {marked_count} notifications marked as read.", "success")
    return redirect(request.referrer or url_for("student.list_notifications"))


@student_bp.route("/api/notifications/unread-count")
@login_required
def api_unread_count():
    """JSON endpoint for real-time unread badge counts."""
    user = get_current_user()
    count = get_unread_notification_count(user.id) if user else 0
    return jsonify({"unread_count": count}), 200

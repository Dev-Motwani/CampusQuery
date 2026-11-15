"""
Administrator portal routes for CampusQuery (Phase 4).
Comprehensive admin dashboard and academic content management:
- Dashboard metrics: published, draft, archived, expired notices, upcoming deadlines, document counts.
- Notice CRUD with title, short description, full instructions, eligibility, required documents,
  category conditions, submission instructions, office information, creator, and timestamps.
- Notice lifecycle: draft, published, archived with preserved publication and update timestamps.
- Milestone date management: opening dates, last dates, verification dates, event dates, and custom milestones.
- Chronological and structural date validation.
- Category CRUD with deletion protection when notices are attached.
"""
import re
import time
from datetime import datetime
from flask import render_template, jsonify, request, redirect, url_for, flash, current_app
from app.admin import admin_bp
from app.auth.utils import admin_required, get_current_user
from app.models.notice import Notice
from app.models.category import Category
from app.models.deadline import Deadline
from app.models.office import OfficeInformation
from app.models.document import Document
from app.models.notice_document import NoticeDocument
from app.models.user import User
from app.database import db
from app.services.deadline_service import (
    parse_milestone_datetime,
    notify_new_notice_published,
    notify_deadlines_changed,
    process_approaching_deadlines
)
from app.services.document_service import validate_uploaded_file, save_uploaded_document


def slugify(text: str) -> str:
    """Converts a string into a URL-friendly slug."""
    text = re.sub(r'[^\w\s-]', '', (text or '').strip().lower())
    slug = re.sub(r'[-\s]+', '-', text)
    return slug[:180] or "item"


def get_unique_notice_slug(title: str, notice_id: int = None) -> str:
    """Generates an index-safe unique slug for a notice."""
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    query = Notice.query.filter(Notice.slug == slug)
    if notice_id:
        query = query.filter(Notice.id != notice_id)
    while query.first() is not None:
        slug = f"{base_slug[:160]}-{counter}-{int(time.time()) % 10000}"
        counter += 1
        query = Notice.query.filter(Notice.slug == slug)
        if notice_id:
            query = query.filter(Notice.id != notice_id)
    return slug


def get_unique_category_slug(name: str, category_id: int = None) -> str:
    """Generates a unique slug for a category."""
    base_slug = slugify(name)
    slug = base_slug
    counter = 1
    query = Category.query.filter(Category.slug == slug)
    if category_id:
        query = query.filter(Category.id != category_id)
    while query.first() is not None:
        slug = f"{base_slug[:60]}-{counter}"
        counter += 1
        query = Category.query.filter(Category.slug == slug)
        if category_id:
            query = query.filter(Category.id != category_id)
    return slug


def parse_datetime(dt_str: str):
    """Safely parses HTML date or datetime strings."""
    if not dt_str or not dt_str.strip():
        return None
    cleaned = dt_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def get_form_list(key: str):
    """Retrieves list from form data supporting both 'key' and 'key[]'."""
    return request.form.getlist(f"{key}[]") or request.form.getlist(key)


def validate_milestones(milestone_names, milestone_due_dates):
    """
    Validates milestone dates and checks for chronological consistency.
    e.g. An opening/start milestone should not occur after a closing/last-date milestone.
    """
    errors = []
    parsed_milestones = []
    start_date = None
    end_date = None

    for idx, name in enumerate(milestone_names):
        name_clean = name.strip()
        if not name_clean:
            continue
        due_str = milestone_due_dates[idx] if idx < len(milestone_due_dates) else ""
        due_dt = parse_milestone_datetime(due_str, name_clean)
        if not due_dt:
            errors.append(f"Milestone '{name_clean}' must have a valid due date and time.")
            continue

        lower_name = name_clean.lower()
        if any(w in lower_name for w in ("opening", "start", "commencement", "beginning")):
            start_date = (name_clean, due_dt)
        if any(w in lower_name for w in ("last", "closing", "deadline", "end", "cutoff")):
            end_date = (name_clean, due_dt)

        parsed_milestones.append((idx, name_clean, due_dt))

    if start_date and end_date and start_date[1] > end_date[1]:
        errors.append(
            f"Inconsistent milestone dates: '{start_date[0]}' ({start_date[1].strftime('%d-%b-%Y')}) "
            f"cannot be after '{end_date[0]}' ({end_date[1].strftime('%d-%b-%Y')})."
        )

    return errors, parsed_milestones


# ==============================================================================
# 1. ADMIN DASHBOARD (SUMMARIES & METRICS)
# ==============================================================================
@admin_bp.route("/dashboard")
@admin_bp.route("/")
@admin_required
def dashboard():
    """
    Administrator dashboard overview.
    Displays verified database summaries: published, draft, archived, expired notices,
    upcoming deadlines, total documents, active categories, and registered students.
    Every count strictly agrees with actual database records.
    """
    now = datetime.utcnow()
    admin = get_current_user()

    # Exact database record counts (Task 1)
    notices_count = Notice.query.count()
    published_count = Notice.query.filter_by(status="published").count()
    drafts_count = Notice.query.filter_by(status="draft").count()
    archived_count = Notice.query.filter_by(status="archived").count()
    expired_count = Notice.query.filter(Notice.expires_at.isnot(None), Notice.expires_at < now).count()

    upcoming_deadlines_count = Deadline.query.filter(
        Deadline.status == "upcoming",
        Deadline.due_date >= now
    ).count()

    total_deadlines_count = Deadline.query.count()
    documents_count = Document.query.count()
    categories_count = Category.query.count()
    students_count = User.query.filter_by(role="student").count()

    categories = Category.query.order_by(Category.name.asc()).all()
    recent_notices = Notice.query.order_by(Notice.created_at.desc()).limit(8).all()
    upcoming_deadlines = Deadline.query.filter(
        Deadline.due_date >= now
    ).order_by(Deadline.due_date.asc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        admin=admin,
        notices_count=notices_count,
        published_count=published_count,
        drafts_count=drafts_count,
        archived_count=archived_count,
        expired_count=expired_count,
        upcoming_deadlines_count=upcoming_deadlines_count,
        total_deadlines_count=total_deadlines_count,
        documents_count=documents_count,
        categories_count=categories_count,
        students_count=students_count,
        categories=categories,
        recent_notices=recent_notices,
        upcoming_deadlines=upcoming_deadlines
    )


# ==============================================================================
# 2. NOTICE MANAGEMENT (LIST, SEARCH & FILTER)
# ==============================================================================
@admin_bp.route("/notices")
@admin_required
def list_notices():
    """
    Notices management index.
    Filters by publication status (all, published, draft, archived, expired),
    category, and keyword search.
    """
    status_filter = request.args.get("status", "all").strip().lower()
    category_id = request.args.get("category_id", type=int)
    search_query = request.args.get("q", "").strip()
    now = datetime.utcnow()

    query = Notice.query

    if status_filter in ("draft", "published", "archived"):
        query = query.filter(Notice.status == status_filter)
    elif status_filter == "expired":
        query = query.filter(Notice.expires_at.isnot(None), Notice.expires_at < now)

    if category_id:
        query = query.filter(Notice.category_id == category_id)

    if search_query:
        query = query.filter(
            (Notice.title.ilike(f"%{search_query}%")) |
            (Notice.content.ilike(f"%{search_query}%")) |
            (Notice.summary.ilike(f"%{search_query}%")) |
            (Notice.eligibility.ilike(f"%{search_query}%"))
        )

    notices = query.order_by(Notice.created_at.desc()).all()
    categories = Category.query.filter_by(is_active=True).order_by(Category.name.asc()).all()

    return render_template(
        "admin/notices.html",
        notices=notices,
        categories=categories,
        selected_status=status_filter,
        selected_category_id=category_id,
        search_query=search_query
    )


# ==============================================================================
# 3. NOTICE CREATION (NEW WITH ACADEMIC CONTENT & MILESTONES)
# ==============================================================================
@admin_bp.route("/notices/new", methods=["GET"])
@admin_required
def new_notice():
    """Renders the notice creation form with academic fields and milestone presets."""
    categories = Category.query.filter_by(is_active=True).order_by(Category.name.asc()).all()
    offices = OfficeInformation.query.order_by(OfficeInformation.office_name.asc()).all()

    return render_template(
        "admin/notice_form.html",
        notice=None,
        categories=categories,
        offices=offices,
        action_url=url_for("admin.create_notice")
    )


@admin_bp.route("/notices/new", methods=["POST"])
@admin_bp.route("/notice/create", methods=["POST"])
@admin_required
def create_notice():
    """
    Creates a new college circular with comprehensive academic details:
    title, summary, content, eligibility, required documents, submission instructions,
    office information, creator, and multi-milestone deadlines.
    Ensures notice publication status is decoupled from deadline milestone status.
    """
    title = request.form.get("title", "").strip()
    category_id = request.form.get("category_id", type=int)
    content = request.form.get("content", "").strip()
    summary = request.form.get("summary", "").strip() or None
    priority = request.form.get("priority", "medium").strip().lower()
    status = request.form.get("status", "draft").strip().lower()
    office_id = request.form.get("office_id", type=int) or None

    # Academic specific fields (Task 3)
    eligibility = request.form.get("eligibility", "").strip() or None
    required_documents = request.form.get("required_documents", "").strip() or None
    submission_instructions = request.form.get("submission_instructions", "").strip() or None

    expires_at_str = request.form.get("expires_at", "").strip()
    expires_at = parse_datetime(expires_at_str)

    # Server-side validation (Task 7)
    errors = []
    if not title:
        errors.append("Notice title is required.")
    if not category_id or not Category.query.get(category_id):
        errors.append("Please select a valid notice category.")
    if not content:
        errors.append("Notice circular content cannot be empty.")
    if priority not in ("low", "medium", "high", "urgent"):
        priority = "medium"
    if status not in ("draft", "published", "archived"):
        status = "draft"

    # Milestone processing and validation
    milestone_names = get_form_list("milestone_name")
    milestone_due_dates = get_form_list("milestone_due_date")
    milestone_office_ids = get_form_list("milestone_office_id")
    milestone_statuses = get_form_list("milestone_status")
    milestone_instructions = get_form_list("milestone_instructions")

    milestone_errors, parsed_milestones = validate_milestones(milestone_names, milestone_due_dates)
    errors.extend(milestone_errors)

    if errors:
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"error": "Bad Request", "messages": errors}), 400
        for err in errors:
            flash(err, "danger")
        categories = Category.query.filter_by(is_active=True).all()
        offices = OfficeInformation.query.all()
        return render_template(
            "admin/notice_form.html",
            notice=None,
            categories=categories,
            offices=offices,
            action_url=url_for("admin.create_notice")
        ), 400

    admin = get_current_user()
    slug = get_unique_notice_slug(title)

    notice = Notice(
        title=title,
        slug=slug,
        summary=summary,
        content=content,
        category_id=category_id,
        priority=priority,
        status=status,
        eligibility=eligibility,
        required_documents=required_documents,
        submission_instructions=submission_instructions,
        office_id=office_id,
        published_at=datetime.utcnow() if status == "published" else None,
        expires_at=expires_at,
        created_by=admin.id
    )

    try:
        db.session.add(notice)
        db.session.flush()

        for idx, m_name, m_due in parsed_milestones:
            off_id = None
            if idx < len(milestone_office_ids) and milestone_office_ids[idx]:
                try:
                    off_id = int(milestone_office_ids[idx]) or None
                except ValueError:
                    off_id = None

            m_status = milestone_statuses[idx] if idx < len(milestone_statuses) else "upcoming"
            if m_status not in ("upcoming", "ongoing", "extended", "closed"):
                m_status = "upcoming"

            m_instr = milestone_instructions[idx].strip() if idx < len(milestone_instructions) else None

            deadline = Deadline(
                notice_id=notice.id,
                milestone_name=m_name,
                due_date=m_due,
                office_id=off_id,
                status=m_status,
                instructions=m_instr
            )
            db.session.add(deadline)

        # Handle uploaded document attachments (PDF/DOCX)
        uploaded_files = request.files.getlist("document_files")
        if not uploaded_files or (len(uploaded_files) == 1 and not uploaded_files[0].filename):
            single_file = request.files.get("document_file")
            if single_file and single_file.filename:
                uploaded_files = [single_file]
            else:
                uploaded_files = []

        doc_label = request.form.get("document_label", "Supporting Document").strip()
        doc_display_label = request.form.get("document_display_label", "").strip() or None

        for doc_file in uploaded_files:
            if doc_file and doc_file.filename and doc_file.filename.strip():
                is_valid, err_msg, detected_mime, file_bytes = validate_uploaded_file(doc_file)
                if not is_valid:
                    flash(f"Attachment '{doc_file.filename}' rejected: {err_msg}", "warning")
                    continue

                saved_ok, saved_doc, save_msg = save_uploaded_document(
                    file_bytes=file_bytes,
                    original_filename=doc_file.filename,
                    file_type=detected_mime,
                    uploader_id=admin.id,
                    label=doc_label,
                    description=f"Attached to circular: {notice.title}",
                    notice_id=notice.id,
                    display_label=doc_display_label or doc_file.filename
                )
                if not saved_ok:
                    flash(f"Could not save attachment '{doc_file.filename}': {save_msg}", "warning")

        db.session.commit()

        # Phase 6: Broadcast in-dashboard notification if published
        if notice.status == "published":
            try:
                notify_new_notice_published(notice)
            except Exception as e:
                current_app.logger.warning(f"Failed to broadcast notice notification: {e}")

        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({
                "message": "Notice created successfully",
                "notice_id": notice.id,
                "status": notice.status
            }), 201

        flash(f"Notice '{notice.title}' created successfully ({notice.status.capitalize()}).", "success")
        return redirect(url_for("admin.view_notice", notice_id=notice.id))

    except Exception as e:
        db.session.rollback()
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"error": "Internal Server Error", "message": str(e)}), 500
        flash(f"Database error while creating notice: {e}", "danger")
        return redirect(url_for("admin.list_notices"))


# ==============================================================================
# 4. NOTICE DETAIL & PREVIEW
# ==============================================================================
@admin_bp.route("/notices/<int:notice_id>")
@admin_required
def view_notice(notice_id):
    """Renders comprehensive notice preview for administrators."""
    notice = Notice.query.get_or_404(notice_id)
    return render_template("admin/notice_detail.html", notice=notice)


# ==============================================================================
# 5. NOTICE EDITING (UPDATE CORE INFO, ACADEMIC CRITERIA & MILESTONES)
# ==============================================================================
@admin_bp.route("/notices/<int:notice_id>/edit", methods=["GET"])
@admin_required
def edit_notice_view(notice_id):
    """Renders notice edit form pre-populated with notice and deadline details."""
    notice = Notice.query.get_or_404(notice_id)
    categories = Category.query.filter_by(is_active=True).order_by(Category.name.asc()).all()
    offices = OfficeInformation.query.order_by(OfficeInformation.office_name.asc()).all()

    return render_template(
        "admin/notice_form.html",
        notice=notice,
        categories=categories,
        offices=offices,
        action_url=url_for("admin.edit_notice", notice_id=notice.id)
    )


@admin_bp.route("/notices/<int:notice_id>/edit", methods=["POST"])
@admin_required
def edit_notice(notice_id):
    """
    Updates notice fields and synchronizes associated deadline milestones.
    Publication timestamp rule:
    - If notice was draft/archived and transitions to published: published_at is set to now.
    - If notice was already published: original published_at is preserved unless admin checks republish.
    - updated_at is always updated.
    """
    notice = Notice.query.get_or_404(notice_id)

    title = request.form.get("title", "").strip()
    category_id = request.form.get("category_id", type=int)
    content = request.form.get("content", "").strip()
    summary = request.form.get("summary", "").strip() or None
    priority = request.form.get("priority", "medium").strip().lower()
    status = request.form.get("status", notice.status).strip().lower()
    office_id = request.form.get("office_id", type=int) or None

    eligibility = request.form.get("eligibility", "").strip() or None
    required_documents = request.form.get("required_documents", "").strip() or None
    submission_instructions = request.form.get("submission_instructions", "").strip() or None

    expires_at_str = request.form.get("expires_at", "").strip()
    expires_at = parse_datetime(expires_at_str)
    republish = request.form.get("republish") == "1"

    # Validation
    errors = []
    if not title:
        errors.append("Notice title is required.")
    if not category_id or not Category.query.get(category_id):
        errors.append("Please select a valid category.")
    if not content:
        errors.append("Notice circular content cannot be empty.")

    milestone_names = get_form_list("milestone_name")
    milestone_due_dates = get_form_list("milestone_due_date")
    milestone_office_ids = get_form_list("milestone_office_id")
    milestone_statuses = get_form_list("milestone_status")
    milestone_instructions = get_form_list("milestone_instructions")

    milestone_errors, parsed_milestones = validate_milestones(milestone_names, milestone_due_dates)
    errors.extend(milestone_errors)

    if errors:
        for err in errors:
            flash(err, "danger")
        return redirect(url_for("admin.edit_notice_view", notice_id=notice.id))

    # Update title and slug if changed
    if title != notice.title:
        notice.title = title
        notice.slug = get_unique_notice_slug(title, notice_id=notice.id)

    notice.category_id = category_id
    notice.content = content
    notice.summary = summary
    notice.priority = priority if priority in ("low", "medium", "high", "urgent") else notice.priority
    notice.eligibility = eligibility
    notice.required_documents = required_documents
    notice.submission_instructions = submission_instructions
    notice.office_id = office_id
    notice.expires_at = expires_at

    # Publication timestamp rule implementation
    old_status = notice.status
    if status in ("draft", "published", "archived"):
        notice.status = status
        if status == "published":
            if old_status != "published" or not notice.published_at or republish:
                notice.published_at = datetime.utcnow()
        elif status in ("draft", "archived"):
            pass

    notice.updated_at = datetime.utcnow()

    try:
        # Phase 6: Capture previous milestones to detect material date changes
        old_milestones = [(dl.milestone_name, dl.due_date) for dl in notice.deadlines]
        was_published = (old_status == "published")

        # Synchronize deadlines: Replace with validated rows
        Deadline.query.filter_by(notice_id=notice.id).delete()

        for idx, m_name, m_due in parsed_milestones:
            off_id = None
            if idx < len(milestone_office_ids) and milestone_office_ids[idx]:
                try:
                    off_id = int(milestone_office_ids[idx]) or None
                except ValueError:
                    off_id = None

            m_status = milestone_statuses[idx] if idx < len(milestone_statuses) else "upcoming"
            if m_status not in ("upcoming", "ongoing", "extended", "closed"):
                m_status = "upcoming"

            m_instr = milestone_instructions[idx].strip() if idx < len(milestone_instructions) else None

            db.session.add(Deadline(
                notice_id=notice.id,
                milestone_name=m_name,
                due_date=m_due,
                office_id=off_id,
                status=m_status,
                instructions=m_instr
            ))

        # Handle detaching documents marked for removal
        detach_ids = request.form.getlist("detach_document_ids[]")
        for did in detach_ids:
            try:
                doc_id_int = int(did)
                nd_item = NoticeDocument.query.filter_by(notice_id=notice.id, document_id=doc_id_int).first()
                if nd_item:
                    db.session.delete(nd_item)
            except (ValueError, TypeError):
                pass

        # Handle any newly uploaded document attachments (PDF/DOCX)
        uploaded_files = request.files.getlist("document_files")
        if not uploaded_files or (len(uploaded_files) == 1 and not uploaded_files[0].filename):
            single_file = request.files.get("document_file")
            if single_file and single_file.filename:
                uploaded_files = [single_file]
            else:
                uploaded_files = []

        doc_label = request.form.get("document_label", "Supporting Document").strip()
        doc_display_label = request.form.get("document_display_label", "").strip() or None
        admin_user = get_current_user()

        for doc_file in uploaded_files:
            if doc_file and doc_file.filename and doc_file.filename.strip():
                is_valid, err_msg, detected_mime, file_bytes = validate_uploaded_file(doc_file)
                if not is_valid:
                    flash(f"Attachment '{doc_file.filename}' rejected: {err_msg}", "warning")
                    continue

                saved_ok, saved_doc, save_msg = save_uploaded_document(
                    file_bytes=file_bytes,
                    original_filename=doc_file.filename,
                    file_type=detected_mime,
                    uploader_id=admin_user.id if admin_user else 1,
                    label=doc_label,
                    description=f"Attached to circular: {notice.title}",
                    notice_id=notice.id,
                    display_label=doc_display_label or doc_file.filename
                )
                if not saved_ok:
                    flash(f"Could not save attachment '{doc_file.filename}': {save_msg}", "warning")

        db.session.commit()

        # Phase 6: Material deadline change & publication notifications
        if notice.status == "published":
            try:
                if was_published:
                    new_milestones = [(m_name, m_due) for _, m_name, m_due in parsed_milestones]
                    notify_deadlines_changed(notice, old_milestones, new_milestones)
                else:
                    notify_new_notice_published(notice)
            except Exception as e:
                current_app.logger.warning(f"Failed to dispatch deadline notification: {e}")

        flash(f"Notice '{notice.title}' updated successfully.", "success")
        return redirect(url_for("admin.view_notice", notice_id=notice.id))

    except Exception as e:
        db.session.rollback()
        flash(f"Database error while updating notice: {e}", "danger")
        return redirect(url_for("admin.edit_notice_view", notice_id=notice.id))


# ==============================================================================
# 6. PUBLICATION STATE TRANSITIONS
# ==============================================================================
@admin_bp.route("/notices/<int:notice_id>/publish", methods=["POST"])
@admin_required
def publish_notice(notice_id):
    """Transitions a notice to 'published' state with timestamp."""
    notice = Notice.query.get_or_404(notice_id)
    notice.status = "published"
    notice.published_at = datetime.utcnow()
    notice.updated_at = datetime.utcnow()
    db.session.commit()

    # Phase 6: Broadcast in-dashboard notification to active students
    try:
        notify_new_notice_published(notice)
    except Exception as e:
        current_app.logger.warning(f"Failed to broadcast notice on publish: {e}")

    if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
        return jsonify({"message": "Notice published", "notice_id": notice_id, "status": "published"}), 200

    flash(f"Notice '{notice.title}' is now published and visible to students.", "success")
    return redirect(request.referrer or url_for("admin.list_notices"))


@admin_bp.route("/notices/<int:notice_id>/draft", methods=["POST"])
@admin_required
def draft_notice(notice_id):
    """Transitions a notice back to 'draft' state (hidden from students)."""
    notice = Notice.query.get_or_404(notice_id)
    notice.status = "draft"
    notice.updated_at = datetime.utcnow()
    db.session.commit()

    if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
        return jsonify({"message": "Notice returned to draft", "notice_id": notice_id, "status": "draft"}), 200

    flash(f"Notice '{notice.title}' moved back to draft.", "info")
    return redirect(request.referrer or url_for("admin.list_notices"))


@admin_bp.route("/notices/<int:notice_id>/archive", methods=["POST"])
@admin_bp.route("/notice/<int:notice_id>/archive", methods=["POST"])
@admin_required
def archive_notice(notice_id):
    """
    Archives a notice.
    Archived notices are hidden from current student views and AI assistant retrieval.
    """
    notice = Notice.query.get_or_404(notice_id)
    notice.status = "archived"
    notice.updated_at = datetime.utcnow()
    db.session.commit()

    if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
        return jsonify({"message": "Notice archived", "notice_id": notice_id, "status": "archived"}), 200

    flash(f"Notice '{notice.title}' has been archived.", "warning")
    return redirect(request.referrer or url_for("admin.list_notices"))


@admin_bp.route("/notices/<int:notice_id>/delete", methods=["POST"])
@admin_bp.route("/notice/<int:notice_id>/delete", methods=["POST"])
@admin_required
def delete_notice(notice_id):
    """Deletes a notice and cascades deletion of attached deadlines."""
    notice = Notice.query.get_or_404(notice_id)
    title = notice.title
    db.session.delete(notice)
    db.session.commit()

    if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
        return jsonify({"message": "Notice deleted", "notice_id": notice_id}), 200

    flash(f"Notice '{title}' was permanently deleted.", "danger")
    return redirect(url_for("admin.list_notices"))


# ==============================================================================
# 7. CATEGORY MANAGEMENT (CRUD & NOTICE PROTECTION)
# ==============================================================================
@admin_bp.route("/categories")
@admin_required
def list_categories():
    """Renders category management interface."""
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template("admin/categories.html", categories=categories)


@admin_bp.route("/categories/create", methods=["POST"])
@admin_required
def create_category():
    """Creates a new notice category."""
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip() or None
    icon = request.form.get("icon", "bi-bookmark").strip()
    is_active = request.form.get("is_active") == "1"

    if not name:
        flash("Category name is required.", "danger")
        return redirect(url_for("admin.list_categories"))

    if Category.query.filter_by(name=name).first():
        flash(f"A category named '{name}' already exists.", "danger")
        return redirect(url_for("admin.list_categories"))

    slug = get_unique_category_slug(name)
    category = Category(
        name=name,
        slug=slug,
        description=description,
        icon=icon or "bi-bookmark",
        is_active=is_active
    )

    try:
        db.session.add(category)
        db.session.commit()
        flash(f"Category '{category.name}' created successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to create category: {e}", "danger")

    return redirect(url_for("admin.list_categories"))


@admin_bp.route("/categories/<int:category_id>/edit", methods=["POST"])
@admin_required
def edit_category(category_id):
    """Updates an existing category's details."""
    category = Category.query.get_or_404(category_id)
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip() or None
    icon = request.form.get("icon", category.icon).strip()
    is_active = request.form.get("is_active") == "1"

    if not name:
        flash("Category name is required.", "danger")
        return redirect(url_for("admin.list_categories"))

    existing = Category.query.filter(Category.name == name, Category.id != category.id).first()
    if existing:
        flash(f"Another category with the name '{name}' already exists.", "danger")
        return redirect(url_for("admin.list_categories"))

    if name != category.name:
        category.name = name
        category.slug = get_unique_category_slug(name, category_id=category.id)

    category.description = description
    category.icon = icon or "bi-bookmark"
    category.is_active = is_active

    try:
        db.session.commit()
        flash(f"Category '{category.name}' updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update category: {e}", "danger")

    return redirect(url_for("admin.list_categories"))


@admin_bp.route("/categories/<int:category_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_category_active(category_id):
    """Toggles active status of a category."""
    category = Category.query.get_or_404(category_id)
    category.is_active = not category.is_active
    db.session.commit()

    status_str = "active" if category.is_active else "inactive"
    flash(f"Category '{category.name}' is now {status_str}.", "info")
    return redirect(url_for("admin.list_categories"))


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@admin_required
def delete_category(category_id):
    """
    Safely deletes a category.
    Protects against deleting categories that currently have associated notices.
    """
    category = Category.query.get_or_404(category_id)
    notice_count = Notice.query.filter_by(category_id=category.id).count()

    if notice_count > 0:
        flash(
            f"Cannot delete category '{category.name}' because it contains {notice_count} notice(s). "
            f"Please reassign or delete the notices first.",
            "danger"
        )
        return redirect(url_for("admin.list_categories"))

    try:
        name = category.name
        db.session.delete(category)
        db.session.commit()
        flash(f"Category '{name}' deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete category: {e}", "danger")

    return redirect(url_for("admin.list_categories"))


# ==============================================================================
# 8. OFFICE INFORMATION MANAGEMENT (CRUD & SAMPLE STATUS)
# ==============================================================================
@admin_bp.route("/offices")
@admin_required
def list_offices():
    """
    Renders administrative office management interface.
    Lists all offices with locations, hours, contact details, sample data badges,
    and associated notice/deadline counts.
    """
    offices = OfficeInformation.query.order_by(OfficeInformation.office_name.asc()).all()
    return render_template("admin/offices.html", offices=offices)


@admin_bp.route("/offices/create", methods=["POST"])
@admin_required
def create_office():
    """
    Creates a new administrative office record with validation:
    office_name, building_room, contact_person, and contact_email are required.
    Email format is validated. Sample data status is controlled by admin.
    """
    office_name = request.form.get("office_name", "").strip()
    department = request.form.get("department", "").strip() or None
    building_room = request.form.get("building_room", "").strip()
    contact_person = request.form.get("contact_person", "").strip()
    contact_email = request.form.get("contact_email", "").strip().lower()
    contact_phone = request.form.get("contact_phone", "").strip() or None
    office_hours = request.form.get("office_hours", "").strip() or "Mon-Fri 10:00 AM - 04:30 PM"
    visit_instructions = request.form.get("visit_instructions", "").strip() or None
    is_sample = request.form.get("is_sample") == "1"

    errors = []
    if not office_name:
        errors.append("Office name is required.")
    if not building_room:
        errors.append("Building / room location is required.")
    if not contact_person:
        errors.append("Contact person name is required.")
    if not contact_email or "@" not in contact_email or "." not in contact_email.split("@")[-1]:
        errors.append("A valid contact email address is required.")

    if errors:
        for err in errors:
            flash(err, "danger")
        return redirect(url_for("admin.list_offices"))

    office = OfficeInformation(
        office_name=office_name,
        department=department,
        building_room=building_room,
        contact_person=contact_person,
        contact_email=contact_email,
        contact_phone=contact_phone,
        office_hours=office_hours,
        visit_instructions=visit_instructions,
        is_sample=is_sample
    )

    try:
        db.session.add(office)
        db.session.commit()
        flash(f"Office '{office.display_name}' created successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to create office: {e}", "danger")

    return redirect(url_for("admin.list_offices"))


@admin_bp.route("/offices/<int:office_id>/edit", methods=["POST"])
@admin_required
def edit_office(office_id):
    """Updates an existing administrative office record."""
    office = OfficeInformation.query.get_or_404(office_id)

    office_name = request.form.get("office_name", "").strip()
    department = request.form.get("department", "").strip() or None
    building_room = request.form.get("building_room", "").strip()
    contact_person = request.form.get("contact_person", "").strip()
    contact_email = request.form.get("contact_email", "").strip().lower()
    contact_phone = request.form.get("contact_phone", "").strip() or None
    office_hours = request.form.get("office_hours", "").strip() or office.office_hours
    visit_instructions = request.form.get("visit_instructions", "").strip() or None
    is_sample = request.form.get("is_sample") == "1"

    errors = []
    if not office_name:
        errors.append("Office name is required.")
    if not building_room:
        errors.append("Building / room location is required.")
    if not contact_person:
        errors.append("Contact person name is required.")
    if not contact_email or "@" not in contact_email or "." not in contact_email.split("@")[-1]:
        errors.append("A valid contact email address is required.")

    if errors:
        for err in errors:
            flash(err, "danger")
        return redirect(url_for("admin.list_offices"))

    office.office_name = office_name
    office.department = department
    office.building_room = building_room
    office.contact_person = contact_person
    office.contact_email = contact_email
    office.contact_phone = contact_phone
    office.office_hours = office_hours
    office.visit_instructions = visit_instructions
    office.is_sample = is_sample

    try:
        db.session.commit()
        flash(f"Office '{office.display_name}' updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update office: {e}", "danger")

    return redirect(url_for("admin.list_offices"))


@admin_bp.route("/offices/<int:office_id>/delete", methods=["POST"])
@admin_required
def delete_office(office_id):
    """
    Safely deletes an office record.
    Prevents deletion if any deadlines or notices are linked to this office.
    """
    office = OfficeInformation.query.get_or_404(office_id)
    deadline_count = Deadline.query.filter_by(office_id=office.id).count()
    notice_count = Notice.query.filter_by(office_id=office.id).count()

    if deadline_count > 0 or notice_count > 0:
        flash(
            f"Cannot delete office '{office.office_name}' because it is linked to "
            f"{notice_count} notice(s) and {deadline_count} milestone deadline(s). "
            f"Please reassign those items before deleting.",
            "danger"
        )
        return redirect(url_for("admin.list_offices"))

    try:
        name = office.office_name
        db.session.delete(office)
        db.session.commit()
        flash(f"Office '{name}' deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete office: {e}", "danger")

    return redirect(url_for("admin.list_offices"))


# ==============================================================================
# 9. DEADLINE REMINDER ENGINE TRIGGER
# ==============================================================================
@admin_bp.route("/deadlines/check-reminders", methods=["POST"])
@admin_required
def trigger_deadline_reminders():
    """
    Manually or programmatically triggers approaching deadline calculations.
    Scans active deadlines within 7 days, 3 days, and 24 hours / today,
    generating in-dashboard notifications idempotently.
    """
    try:
        results = process_approaching_deadlines()
        total_created = sum(results.values())
        msg = (
            f"Deadline reminder check complete: {total_created} alert(s) generated "
            f"(Today: {results.get('today', 0)}, 1-Day: {results.get('1_day', 0)}, "
            f"3-Day: {results.get('3_day', 0)}, 7-Day: {results.get('7_day', 0)})."
        )
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"message": msg, "results": results, "total_created": total_created}), 200

        flash(msg, "info")
    except Exception as e:
        current_app.logger.error(f"Error checking deadline reminders: {e}")
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"error": "Failed to process deadline reminders", "details": str(e)}), 500
        flash(f"Error checking deadline reminders: {e}", "danger")

    return redirect(request.referrer or url_for("admin.dashboard"))

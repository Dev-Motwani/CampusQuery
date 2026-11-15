"""
CampusQuery Deadline Engine & In-Dashboard Notification Service (Phase 6).

Core Responsibilities:
1. Timezone Strategy:
   - Persistence and internal comparisons strictly use UTC (ISO 8601 / datetime.utcnow).
   - Presentation and academic schedules standardise on Indian Standard Time (IST, UTC+05:30).
2. Date Parsing & Inclusive Closing Rules:
   - Date-only strings ('YYYY-MM-DD') for closing dates expand inclusively to 23:59:59 UTC.
   - Date-only strings for opening milestones default to 00:00:00 UTC.
   - Optional closing times ('HH:MM') are respected when supplied.
3. In-Dashboard Notifications (No external email/SMS):
   - Automatic dispatch on notice publication to all active students.
   - Material deadline change notifications.
   - Scheduled approaching deadline alerts (7 days, 3 days, 24 hours / due today).
   - Strict idempotency: Duplicate alerts are detected and skipped on repeated checks.
   - Publication state security: Draft and archived notices NEVER trigger student alerts.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional, Dict
from sqlalchemy import and_, or_

from app.database import db
from app.models.notice import Notice
from app.models.deadline import Deadline
from app.models.notification import Notification
from app.models.user import User


# ==============================================================================
# 1. TIMEZONE STRATEGY & HELPERS
# ==============================================================================
IST_OFFSET = timedelta(hours=5, minutes=30)
TIMEZONE_DOCUMENTATION = """
CampusQuery Timezone Strategy:
1. Database Storage: All DateTime columns are recorded in coordinated universal time (UTC).
2. Comparisons: Internal milestone comparisons compare UTC against UTC (datetime.utcnow()).
3. Presentation: Displays are converted or labelled clearly in Indian Standard Time (IST, UTC+05:30)
   reflecting the operating hours of Maharashtra college administrative offices.
4. Inclusive Deadlines: Closing dates specified without an explicit time expire at 23:59:59 UTC.
"""


def get_utc_now() -> datetime:
    """Returns current UTC timestamp without timezone info for SQLAlchemy compatibility."""
    return datetime.utcnow()


def utc_to_ist(dt: Optional[datetime]) -> Optional[datetime]:
    """Converts a UTC datetime to Indian Standard Time (UTC+05:30)."""
    if not dt:
        return None
    return dt + IST_OFFSET


def format_academic_datetime(dt: Optional[datetime], show_ist: bool = True) -> str:
    """Formats datetime for academic display."""
    if not dt:
        return "Not Scheduled"
    target = utc_to_ist(dt) if show_ist else dt
    suffix = " IST" if show_ist else " UTC"
    if target.hour == 23 and target.minute == 59:
        return target.strftime("%d %b %Y (End of Day)")
    if target.hour == 0 and target.minute == 0:
        return target.strftime("%d %b %Y (Start of Day)")
    return target.strftime("%d %b %Y at %I:%M %p") + suffix


def parse_milestone_datetime(date_str: str, milestone_name: str = "") -> Optional[datetime]:
    """
    Parses date or datetime input strings with inclusive closing date semantics:
    - If date only ('YYYY-MM-DD'):
      - If name suggests opening: 00:00:00 UTC
      - Otherwise (closing date): 23:59:59 UTC (inclusive end-of-day)
    - If datetime ('YYYY-MM-DDTHH:MM' or 'YYYY-MM-DD HH:MM[:SS]'): parsed directly
    """
    if not date_str or not date_str.strip():
        return None

    cleaned = date_str.strip()
    is_opening = any(w in (milestone_name or "").lower() for w in ["open", "start", "commence", "begin"])

    # 1. Date-only format
    try:
        parsed_date = datetime.strptime(cleaned, "%Y-%m-%d")
        if is_opening:
            return parsed_date.replace(hour=0, minute=0, second=0)
        return parsed_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        pass

    # 2. DateTime formats
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    return None


# ==============================================================================
# 2. IN-DASHBOARD NOTIFICATION GENERATORS
# ==============================================================================
def notify_new_notice_published(notice: Notice) -> int:
    """
    Dispatches in-dashboard alerts to all registered students when a notice is published.
    Strictly verifies Notice.status == 'published'.
    Idempotent: Avoids duplicate notifications if already broadcast.
    Returns: Number of notifications created.
    """
    if not notice or notice.status != "published":
        return 0

    students = User.query.filter_by(role="student", is_active=True).all()
    if not students:
        return 0

    title = f"New Circular: {notice.title[:100]}"
    category_name = notice.category.name if notice.category else "Notice"
    message = f"[{category_name}] {notice.title}. Review academic requirements, documents, and milestone deadlines."

    created_count = 0
    for student in students:
        # Check idempotency: avoid duplicate notification for same notice and user
        existing = Notification.query.filter_by(
            user_id=student.id,
            notice_id=notice.id,
            notification_type="new_notice"
        ).first()

        if not existing:
            notif = Notification(
                user_id=student.id,
                notice_id=notice.id,
                title=title,
                message=message,
                notification_type="new_notice",
                is_read=False,
                created_at=get_utc_now()
            )
            db.session.add(notif)
            created_count += 1

    if created_count > 0:
        db.session.commit()

    return created_count


def notify_deadlines_changed(notice: Notice, old_milestones: List[Tuple[str, datetime]], new_milestones: List[Tuple[str, datetime]]) -> int:
    """
    Detects material changes to published notice deadlines and broadcasts in-dashboard alerts.
    Does NOT notify if notice is draft or archived.
    Avoids duplicate notifications.
    """
    if not notice or notice.status != "published":
        return 0

    # Format sets of (name, due_date_str) to detect material changes
    old_set = {(m[0].strip(), m[1].strftime("%Y-%m-%d %H:%M")) for m in old_milestones if m[1]}
    new_set = {(m[0].strip(), m[1].strftime("%Y-%m-%d %H:%M")) for m in new_milestones if m[1]}

    if old_set == new_set:
        return 0  # No material date change

    students = User.query.filter_by(role="student", is_active=True).all()
    if not students:
        return 0

    title = f"Deadline Update: {notice.title[:90]}"
    message = f"Important: Academic milestones for '{notice.title[:60]}' have been updated by administration. Please check the revised schedule."

    created_count = 0
    now = get_utc_now()
    for student in students:
        notif = Notification(
            user_id=student.id,
            notice_id=notice.id,
            title=title,
            message=message,
            notification_type="deadline_changed",
            is_read=False,
            created_at=now
        )
        db.session.add(notif)
        created_count += 1

    if created_count > 0:
        db.session.commit()

    return created_count


def process_approaching_deadlines(schedule_windows: Tuple[int, ...] = (1, 3, 7)) -> Dict[str, int]:
    """
    Scans published notices for approaching milestones according to documented schedule:
    - 7 days before due date (1-week notice)
    - 3 days before due date (urgent notice)
    - 1 day before due date / due today (24-hour final call)

    Idempotent: Tracks unique alert keys to prevent re-notifying on repeated runs.
    Ignores draft and archived notices.
    Returns: Dict mapping window to count of created notifications.
    """
    now = get_utc_now()
    results = {f"{w}_day": 0 for w in schedule_windows}
    results["today"] = 0

    # Query only milestones of published notices that have not yet expired
    active_deadlines = (
        Deadline.query.join(Notice)
        .filter(
            Notice.status == "published",
            Deadline.due_date >= now
        )
        .all()
    )

    students = User.query.filter_by(role="student", is_active=True).all()
    if not students or not active_deadlines:
        return results

    for dl in active_deadlines:
        delta = dl.due_date - now
        days_left = delta.days
        hours_left = int(delta.total_seconds() // 3600)

        # Determine target alert window
        alert_window = None
        alert_label = None

        if hours_left <= 24:
            alert_window = "today"
            alert_label = "Due Today!"
        elif days_left in schedule_windows:
            alert_window = f"{days_left}_day"
            alert_label = f"Due in {days_left} Days"

        if not alert_window:
            continue

        title = f"{alert_label}: {dl.milestone_name[:70]}"
        message = f"Reminder: '{dl.milestone_name}' for notice '{dl.notice.title[:60]}' is {alert_label.lower()} ({dl.formatted_due_date})."

        for student in students:
            # Check for existing alert in the same window for this student and milestone
            existing = Notification.query.filter(
                Notification.user_id == student.id,
                Notification.notice_id == dl.notice_id,
                Notification.title == title
            ).first()

            if not existing:
                notif = Notification(
                    user_id=student.id,
                    notice_id=dl.notice_id,
                    title=title,
                    message=message,
                    notification_type="deadline_reminder",
                    is_read=False,
                    created_at=now
                )
                db.session.add(notif)
                results[alert_window] += 1

    db.session.commit()
    return results


# ==============================================================================
# 3. NOTIFICATION STATE MANAGEMENT
# ==============================================================================
def mark_notification_as_read(notification_id: int, user_id: int) -> bool:
    """Marks a specific notification as read for the authenticated user."""
    notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notif:
        notif.is_read = True
        db.session.commit()
        return True
    return False


def mark_all_notifications_as_read(user_id: int) -> int:
    """Marks all unread notifications as read for the authenticated user."""
    unread_notifs = Notification.query.filter_by(user_id=user_id, is_read=False).all()
    count = len(unread_notifs)
    for n in unread_notifs:
        n.is_read = True
    if count > 0:
        db.session.commit()
    return count


def get_unread_notification_count(user_id: int) -> int:
    """Returns total unread notification count for the user."""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()

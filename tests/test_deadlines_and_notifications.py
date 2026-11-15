"""
Comprehensive Automated Test Suite for CampusQuery Phase 6:
Deadline Engine, Notifications, and Office Information.

Tests:
1. Multi-milestone creation and inclusive closing date parsing (23:59:59 UTC closing, 00:00:00 UTC opening).
2. Dynamic derived status (effective_status, countdown calculation, and status_badge).
3. Publication state isolation: draft & archived milestones return draft/archived and never alert students.
4. In-dashboard notification broadcast on notice publication (new_notice type).
5. Material deadline change notification dispatch (deadline_changed type).
6. Approaching deadline calculation and idempotent processing (7-day, 3-day, and today alerts).
7. Notification read/unread state management and count APIs.
8. Admin Office Information CRUD with required field and email validation.
9. Office deletion safety protection against deleting offices linked to notices or deadlines.
10. Student / public office directory and detail views with sample data indicators.
"""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.database import db
from app.models.user import User
from app.models.category import Category
from app.models.notice import Notice
from app.models.deadline import Deadline
from app.models.office import OfficeInformation
from app.models.notification import Notification
from app.services.deadline_service import (
    parse_milestone_datetime,
    notify_new_notice_published,
    notify_deadlines_changed,
    process_approaching_deadlines,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_unread_notification_count,
    format_academic_datetime
)
from scripts.seed_demo import seed_demo_data


class DeadlineAndNotificationTestCase(unittest.TestCase):
    """Test suite for Phase 6 deadline engine, notifications, and office information."""

    @classmethod
    def setUpClass(cls):
        """Initializes application in testing mode."""
        cls.app = create_app("testing")
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        """Cleans up test database tables."""
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()

    def setUp(self):
        """Prepares clean seed data and authenticated client before each test."""
        seed_demo_data(self.app, verbose=False)
        self.client = self.app.test_client()

    def tearDown(self):
        """Rolls back open transactions."""
        db.session.rollback()

    def _login_as(self, email, password):
        """Helper to establish an authenticated session."""
        return self.client.post(
            "/auth/login",
            data={"email": email, "password": password},
            follow_redirects=True
        )

    # ==========================================================================
    # 1. TIMEZONE & INCLUSIVE DATE PARSING TESTS
    # ==========================================================================
    def test_inclusive_closing_date_parsing(self):
        """Verifies that date-only closing dates expand to 23:59:59 UTC, opening to 00:00:00 UTC."""
        # Closing milestone
        dt_closing = parse_milestone_datetime("2026-11-15", "Last Date for Online Submission")
        self.assertIsNotNone(dt_closing)
        self.assertEqual(dt_closing.year, 2026)
        self.assertEqual(dt_closing.month, 11)
        self.assertEqual(dt_closing.day, 15)
        self.assertEqual(dt_closing.hour, 23)
        self.assertEqual(dt_closing.minute, 59)
        self.assertEqual(dt_closing.second, 59)

        # Opening milestone
        dt_opening = parse_milestone_datetime("2026-11-01", "Commencement / Opening of Portal")
        self.assertIsNotNone(dt_opening)
        self.assertEqual(dt_opening.hour, 0)
        self.assertEqual(dt_opening.minute, 0)
        self.assertEqual(dt_opening.second, 0)

        # Explicit datetime respects time
        dt_explicit = parse_milestone_datetime("2026-11-20 14:30", "Document Scrutiny Session")
        self.assertIsNotNone(dt_explicit)
        self.assertEqual(dt_explicit.hour, 14)
        self.assertEqual(dt_explicit.minute, 30)

        # Invalid string returns None
        self.assertIsNone(parse_milestone_datetime("invalid-date-string"))
        self.assertIsNone(parse_milestone_datetime(""))

    # ==========================================================================
    # 2. DYNAMIC DERIVED STATUS & COUNTDOWN TESTS
    # ==========================================================================
    def test_derived_effective_status(self):
        """Verifies deadline effective_status derives from dates and publication state."""
        notice = Notice.query.filter_by(status="published").first()
        self.assertIsNotNone(notice)

        # Overdue deadline -> 'closed'
        past_dl = Deadline(
            notice_id=notice.id,
            milestone_name="Past Exam Fee Deadline",
            due_date=datetime.utcnow() - timedelta(days=2),
            status="upcoming"  # Stored status should be overridden
        )
        db.session.add(past_dl)
        db.session.flush()
        self.assertEqual(past_dl.effective_status, "closed")
        self.assertTrue(past_dl.is_overdue)
        self.assertEqual(past_dl.days_remaining, 0)
        self.assertEqual(past_dl.status_badge["label"], "Closed / Expired")

        # Upcoming deadline (5 days ahead)
        future_dl = Deadline(
            notice_id=notice.id,
            milestone_name="Future Submission",
            due_date=datetime.utcnow() + timedelta(days=5),
            status="upcoming"
        )
        db.session.add(future_dl)
        db.session.flush()
        self.assertEqual(future_dl.effective_status, "upcoming")
        self.assertFalse(future_dl.is_overdue)
        self.assertIn(future_dl.days_remaining, (4, 5))
        self.assertIn("left", future_dl.status_badge["label"])

        # Due today (12 hours ahead)
        today_dl = Deadline(
            notice_id=notice.id,
            milestone_name="Due Tonight",
            due_date=datetime.utcnow() + timedelta(hours=12),
            status="upcoming"
        )
        db.session.add(today_dl)
        db.session.flush()
        self.assertTrue(today_dl.is_due_today)
        self.assertEqual(today_dl.status_badge["label"], "Due Today!")

        # Extended deadline
        extended_dl = Deadline(
            notice_id=notice.id,
            milestone_name="Extended Hall Ticket Verification",
            due_date=datetime.utcnow() + timedelta(days=8),
            status="extended"
        )
        db.session.add(extended_dl)
        db.session.flush()
        self.assertEqual(extended_dl.effective_status, "extended")
        self.assertIn("Extended", extended_dl.status_badge["label"])

        # Draft notice deadline -> 'draft'
        draft_notice = Notice.query.filter_by(status="draft").first()
        if draft_notice:
            draft_dl = Deadline(
                notice_id=draft_notice.id,
                milestone_name="Draft Milestone",
                due_date=datetime.utcnow() + timedelta(days=10),
                status="upcoming"
            )
            db.session.add(draft_dl)
            db.session.flush()
            self.assertEqual(draft_dl.effective_status, "draft")

    # ==========================================================================
    # 3. NOTIFICATION BROADCAST ON NOTICE PUBLICATION
    # ==========================================================================
    def test_notice_publication_notification_broadcast(self):
        """Verifies that publishing a notice creates in-dashboard alerts for active students."""
        student_count = User.query.filter_by(role="student", is_active=True).count()
        self.assertGreater(student_count, 0)

        admin = User.query.filter_by(role="admin").first()
        cat = Category.query.first()

        # Create a new notice as draft
        notice = Notice(
            title="Notification Broadcast Test Circular",
            slug="notif-broadcast-test",
            content="Detailed circular content for publication notification test.",
            category_id=cat.id,
            status="draft",
            created_by=admin.id
        )
        db.session.add(notice)
        db.session.commit()

        # No notifications should exist for a draft notice
        count_draft = notify_new_notice_published(notice)
        self.assertEqual(count_draft, 0)

        # Transition to published
        notice.status = "published"
        notice.published_at = datetime.utcnow()
        db.session.commit()

        # Broadcast notifications
        created = notify_new_notice_published(notice)
        self.assertEqual(created, student_count)

        # Verify notification properties
        notif = Notification.query.filter_by(notice_id=notice.id).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.notification_type, "new_notice")
        self.assertFalse(notif.is_read)
        self.assertIn("Notification Broadcast Test Circular", notif.title)

        # Idempotency check: calling again must create 0 duplicates
        dup_count = notify_new_notice_published(notice)
        self.assertEqual(dup_count, 0)

    # ==========================================================================
    # 4. MATERIAL DEADLINE CHANGE NOTIFICATIONS
    # ==========================================================================
    def test_deadline_change_notification(self):
        """Verifies that changing milestone dates on a published notice alerts students."""
        student_count = User.query.filter_by(role="student", is_active=True).count()
        notice = Notice.query.filter_by(status="published").first()
        self.assertIsNotNone(notice)

        now = datetime.utcnow()
        old_milestones = [
            ("Online Form Submission", now + timedelta(days=5)),
            ("Document Verification", now + timedelta(days=7))
        ]
        # Material change: extended dates
        new_milestones = [
            ("Online Form Submission", now + timedelta(days=10)),
            ("Document Verification", now + timedelta(days=12))
        ]

        count = notify_deadlines_changed(notice, old_milestones, new_milestones)
        self.assertEqual(count, student_count)

        notif = Notification.query.filter_by(notice_id=notice.id, notification_type="deadline_changed").first()
        self.assertIsNotNone(notif)
        self.assertIn("Deadline Update", notif.title)

        # Non-material check: same dates must not generate alerts
        no_change_count = notify_deadlines_changed(notice, new_milestones, new_milestones)
        self.assertEqual(no_change_count, 0)

    # ==========================================================================
    # 5. APPROACHING DEADLINE ENGINE & IDEMPOTENCY
    # ==========================================================================
    def test_approaching_deadlines_schedule_and_idempotency(self):
        """Verifies approaching deadline detection within 7d, 3d, and today windows."""
        notice = Notice.query.filter_by(status="published").first()
        now = datetime.utcnow()

        # Add deadlines in specific reminder windows
        dl_7d = Deadline(
            notice_id=notice.id,
            milestone_name="7-Day Milestone Reminder",
            due_date=now + timedelta(days=7, hours=2),
            status="upcoming"
        )
        dl_3d = Deadline(
            notice_id=notice.id,
            milestone_name="3-Day Milestone Reminder",
            due_date=now + timedelta(days=3, hours=2),
            status="upcoming"
        )
        dl_today = Deadline(
            notice_id=notice.id,
            milestone_name="Final Call Due Today",
            due_date=now + timedelta(hours=18),
            status="upcoming"
        )
        db.session.add_all([dl_7d, dl_3d, dl_today])
        db.session.commit()

        # Run approaching deadlines engine
        results1 = process_approaching_deadlines(schedule_windows=(1, 3, 7))
        self.assertGreater(results1["today"], 0)
        self.assertGreater(results1["3_day"], 0)
        self.assertGreater(results1["7_day"], 0)

        # Immediate repeated run must be idempotent (0 new notifications)
        results2 = process_approaching_deadlines(schedule_windows=(1, 3, 7))
        self.assertEqual(results2["today"], 0)
        self.assertEqual(results2["3_day"], 0)
        self.assertEqual(results2["7_day"], 0)

    # ==========================================================================
    # 6. NOTIFICATION READ / UNREAD STATE MANAGEMENT
    # ==========================================================================
    def test_notification_state_management_and_endpoints(self):
        """Verifies read/unread state toggles and student notification endpoints."""
        student = User.query.filter_by(role="student").first()
        self._login_as(student.email, "Student@123")

        # Create test notifications for student
        n1 = Notification(
            user_id=student.id,
            title="Unread Alert 1",
            message="Test unread message 1",
            notification_type="info",
            is_read=False
        )
        n2 = Notification(
            user_id=student.id,
            title="Unread Alert 2",
            message="Test unread message 2",
            notification_type="deadline_reminder",
            is_read=False
        )
        db.session.add_all([n1, n2])
        db.session.commit()

        # Check API unread count
        resp = self.client.get("/api/notifications/unread-count")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreaterEqual(data["unread_count"], 2)

        # Mark single notification as read
        resp_mark = self.client.post(f"/notifications/{n1.id}/read", headers={"Accept": "application/json"})
        self.assertEqual(resp_mark.status_code, 200)
        db.session.refresh(n1)
        self.assertTrue(n1.is_read)

        # Mark all as read
        resp_all = self.client.post("/notifications/mark-all-read", headers={"Accept": "application/json"})
        self.assertEqual(resp_all.status_code, 200)
        db.session.refresh(n2)
        self.assertTrue(n2.is_read)

        # Inbox list view
        resp_inbox = self.client.get("/notifications")
        self.assertEqual(resp_inbox.status_code, 200)
        self.assertIn(b"Notifications", resp_inbox.data)

    # ==========================================================================
    # 7. ADMIN OFFICE INFORMATION CRUD & VALIDATION
    # ==========================================================================
    def test_admin_office_crud_and_validation(self):
        """Verifies admin office management, required validation, and editing."""
        admin = User.query.filter_by(role="admin").first()
        self._login_as(admin.email, "Admin@123")

        # 1. Validation: Missing required fields
        resp_invalid = self.client.post(
            "/admin/offices/create",
            data={
                "office_name": "",  # Empty
                "building_room": "Main Block",
                "contact_person": "Officer",
                "contact_email": "invalid-email"
            },
            follow_redirects=True
        )
        self.assertIn(b"Office name is required", resp_invalid.data)

        # 2. Validation: Invalid email format
        resp_bad_email = self.client.post(
            "/admin/offices/create",
            data={
                "office_name": "Valid Name",
                "building_room": "Main Block",
                "contact_person": "Officer",
                "contact_email": "bademail"
            },
            follow_redirects=True
        )
        self.assertIn(b"valid contact email address is required", resp_bad_email.data)

        # 3. Successful office creation
        resp_create = self.client.post(
            "/admin/offices/create",
            data={
                "office_name": "Grievance Redressal Cell",
                "department": "Student Affairs",
                "building_room": "Administrative Wing, Room 108",
                "contact_person": "Dr. V. K. Deshpande",
                "contact_email": "grievance@campusqueri.edu",
                "contact_phone": "+91 20 2550 0999",
                "office_hours": "Mon-Fri 02:00 PM - 05:00 PM",
                "visit_instructions": "Submit grievance letters in person with student identity verification.",
                "is_sample": "0"
            },
            follow_redirects=True
        )
        self.assertEqual(resp_create.status_code, 200)
        self.assertIn(b"Grievance Redressal Cell", resp_create.data)

        office = OfficeInformation.query.filter_by(office_name="Grievance Redressal Cell").first()
        self.assertIsNotNone(office)
        self.assertFalse(office.is_sample)
        self.assertEqual(office.department, "Student Affairs")

        # 4. Edit office
        resp_edit = self.client.post(
            f"/admin/offices/{office.id}/edit",
            data={
                "office_name": "Central Grievance & Student Welfare Cell",
                "department": "Student Affairs & Welfare",
                "building_room": "Administrative Wing, Room 108-A",
                "contact_person": "Dr. V. K. Deshpande",
                "contact_email": "grievance.desk@campusqueri.edu",
                "contact_phone": "+91 20 2550 0999",
                "office_hours": "Mon-Fri 01:30 PM - 05:00 PM",
                "visit_instructions": "Prior appointment recommended.",
                "is_sample": "1"
            },
            follow_redirects=True
        )
        self.assertEqual(resp_edit.status_code, 200)
        db.session.refresh(office)
        self.assertEqual(office.office_name, "Central Grievance & Student Welfare Cell")
        self.assertTrue(office.is_sample)

    # ==========================================================================
    # 8. OFFICE DELETION PROTECTION
    # ==========================================================================
    def test_office_deletion_safety_protection(self):
        """Verifies that offices linked to milestones or notices cannot be deleted."""
        admin = User.query.filter_by(role="admin").first()
        self._login_as(admin.email, "Admin@123")

        # Find an office linked to seeded deadlines
        office_with_deadlines = OfficeInformation.query.join(Deadline).first()
        self.assertIsNotNone(office_with_deadlines)

        resp_del = self.client.post(
            f"/admin/offices/{office_with_deadlines.id}/delete",
            follow_redirects=True
        )
        self.assertIn(b"Cannot delete office", resp_del.data)
        # Verify office still exists in database
        check = OfficeInformation.query.get(office_with_deadlines.id)
        self.assertIsNotNone(check)

    # ==========================================================================
    # 9. STUDENT / PUBLIC OFFICE DIRECTORY & DETAIL
    # ==========================================================================
    def test_student_office_directory_and_detail(self):
        """Verifies public / student access to campus office directory and detail views."""
        # 1. Directory list
        resp_dir = self.client.get("/offices")
        self.assertEqual(resp_dir.status_code, 200)
        self.assertIn(b"Campus Administrative Offices", resp_dir.data)
        self.assertIn(b"SAMPLE", resp_dir.data)

        # 2. Detail view
        office = OfficeInformation.query.first()
        self.assertIsNotNone(office)
        resp_detail = self.client.get(f"/offices/{office.id}")
        self.assertEqual(resp_detail.status_code, 200)
        self.assertIn(office.office_name.encode("utf-8"), resp_detail.data)
        self.assertIn(office.building_room.encode("utf-8"), resp_detail.data)

        # 3. Nonexistent office returns 404
        resp_404 = self.client.get("/offices/999999")
        self.assertEqual(resp_404.status_code, 404)

    # ==========================================================================
    # 10. ROLE-BASED ACCESS CONTROL FOR PHASE 6 ENDPOINTS
    # ==========================================================================
    def test_phase6_access_control(self):
        """Verifies students cannot access admin office management or reminder triggers."""
        student = User.query.filter_by(role="student").first()
        self._login_as(student.email, "Student@123")

        # Student attempting to access admin offices -> 403
        resp_admin_offices = self.client.get("/admin/offices")
        self.assertEqual(resp_admin_offices.status_code, 403)

        # Student attempting to trigger reminder check -> 403
        resp_reminder = self.client.post("/admin/deadlines/check-reminders")
        self.assertEqual(resp_reminder.status_code, 403)


if __name__ == "__main__":
    unittest.main()

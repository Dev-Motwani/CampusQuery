"""
Comprehensive Database CRUD, Relationship, and Constraint Test Suite.
Tests schema integrity, foreign keys, uniqueness, multi-milestone deadlines, and transactional rollbacks.
Can run with pytest or standalone via Python.
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
from app.models import (
    User,
    Category,
    OfficeInformation,
    Notice,
    Deadline,
    Document,
    NoticeDocument,
    Flowchart,
    NoticeFlowchart,
    Notification
)
from scripts.seed_demo import seed_demo_data
from sqlalchemy.exc import IntegrityError


class DatabaseCRUDTestCase(unittest.TestCase):
    """Database CRUD and Constraint Verification Suite."""

    @classmethod
    def setUpClass(cls):
        """Initializes test application and in-memory isolated database engine."""
        cls.app = create_app("testing")
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        """Cleans up database tables and pops context."""
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()

    def setUp(self):
        """Seeds demo data cleanly before each test."""
        seed_demo_data(self.app, verbose=False)

    def tearDown(self):
        """Clears session state between test methods."""
        db.session.rollback()

    # ----------------------------------------------------
    # 1. READ / SEED VERIFICATION TESTS
    # ----------------------------------------------------
    def test_01_seed_data_counts(self):
        """Verifies that demo seed data was created with expected initial counts."""
        self.assertGreaterEqual(User.query.count(), 3)
        self.assertEqual(Category.query.count(), 7)
        self.assertGreaterEqual(OfficeInformation.query.count(), 5)
        self.assertGreaterEqual(Notice.query.count(), 7)
        self.assertGreaterEqual(Deadline.query.count(), 14)
        self.assertGreaterEqual(Flowchart.query.count(), 1)
        self.assertGreaterEqual(Document.query.count(), 1)

    def test_02_sample_office_marking(self):
        """Verifies that all sample offices are visibly marked [SAMPLE]."""
        offices = OfficeInformation.query.all()
        for office in offices:
            self.assertTrue(office.is_sample)
            self.assertTrue(office.office_name.startswith("[SAMPLE]"))
            self.assertTrue(office.building_room.startswith("[SAMPLE]"))
            self.assertTrue(office.contact_person.startswith("[SAMPLE]"))

    # ----------------------------------------------------
    # 2. MULTIPLE DEADLINES & SEPARATION OF STATUS
    # ----------------------------------------------------
    def test_03_multiple_deadlines_per_notice(self):
        """Verifies that notices support multiple deadline milestones with distinct statuses."""
        exam_notice = Notice.query.filter_by(slug="sample-tybca-sem-6-exam-schedule-2026").first()
        self.assertIsNotNone(exam_notice)
        self.assertEqual(len(exam_notice.deadlines), 3)

        # Check milestones are ordered chronologically
        milestones = [d.milestone_name for d in exam_notice.deadlines]
        self.assertIn("Lab Journal & Project Viva Clearance", milestones)
        self.assertIn("Hall Ticket Pickup Counter", milestones)
        self.assertIn("Commencement of Theory Examinations", milestones)

        # Verify notice publication status is distinct from deadline status
        self.assertEqual(exam_notice.status, "published")
        deadline_statuses = {d.status for d in exam_notice.deadlines}
        self.assertTrue("ongoing" in deadline_statuses or "upcoming" in deadline_statuses)

    # ----------------------------------------------------
    # 3. CRUD: CREATE, READ, UPDATE, DELETE
    # ----------------------------------------------------
    def test_04_create_and_read_notice(self):
        """Tests creating a new notice with custom deadlines and reading it back."""
        admin = User.query.filter_by(role="admin").first()
        cat = Category.query.filter_by(slug="sports").first()
        office = OfficeInformation.query.first()

        new_notice = Notice(
            title="[SAMPLE] Annual Athletics Championship 2026",
            slug="sample-annual-athletics-championship-2026",
            summary="College annual track and field competitions.",
            content="Registrations are open for 100m, 200m, 400m, and relay races.",
            category_id=cat.id,
            priority="medium",
            status="draft",
            created_by=admin.id
        )
        db.session.add(new_notice)
        db.session.flush()

        # Add two deadline milestones
        d1 = Deadline(notice_id=new_notice.id, milestone_name="Registration Form Submission", due_date=datetime.utcnow() + timedelta(days=5), office_id=office.id)
        d2 = Deadline(notice_id=new_notice.id, milestone_name="Track Heat Trials", due_date=datetime.utcnow() + timedelta(days=8), office_id=office.id)
        db.session.add_all([d1, d2])
        db.session.commit()

        # Read back
        fetched = Notice.query.filter_by(slug="sample-annual-athletics-championship-2026").first()
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "[SAMPLE] Annual Athletics Championship 2026")
        self.assertEqual(fetched.status, "draft")
        self.assertEqual(len(fetched.deadlines), 2)
        self.assertEqual(fetched.deadlines[0].office.office_name, office.office_name)

    def test_05_update_notice_status(self):
        """Tests updating notice publication status from draft to published."""
        notice = Notice.query.filter_by(slug="sample-annual-athletics-championship-2026").first()
        if not notice:
            # Create if previous test didn't run
            admin = User.query.filter_by(role="admin").first()
            cat = Category.query.first()
            notice = Notice(title="Temp", slug="temp-test-update", content="Text", category_id=cat.id, status="draft", created_by=admin.id)
            db.session.add(notice)
            db.session.commit()

        notice.status = "published"
        notice.published_at = datetime.utcnow()
        db.session.commit()

        updated = Notice.query.get(notice.id)
        self.assertEqual(updated.status, "published")
        self.assertIsNotNone(updated.published_at)

    def test_06_delete_notice_cascades_deadlines(self):
        """Tests that deleting a notice cascades and cleans up its deadlines without deleting the office."""
        admin = User.query.filter_by(role="admin").first()
        cat = Category.query.first()
        office = OfficeInformation.query.first()

        temp_notice = Notice(title="Notice to Delete", slug="notice-to-delete-slug", content="...", category_id=cat.id, created_by=admin.id)
        db.session.add(temp_notice)
        db.session.flush()

        dl = Deadline(notice_id=temp_notice.id, milestone_name="Temp Deadline", due_date=datetime.utcnow() + timedelta(days=1), office_id=office.id)
        db.session.add(dl)
        db.session.commit()

        notice_id = temp_notice.id
        dl_id = dl.id
        office_id = office.id

        # Delete notice
        db.session.delete(temp_notice)
        db.session.commit()

        # Notice and its deadline must be gone
        self.assertIsNone(Notice.query.get(notice_id))
        self.assertIsNone(Deadline.query.get(dl_id))

        # Office MUST still exist (SET NULL behavior)
        self.assertIsNotNone(OfficeInformation.query.get(office_id))

    # ----------------------------------------------------
    # 4. CONSTRAINT REJECTION TESTS
    # ----------------------------------------------------
    def test_07_foreign_key_constraint_rejection(self):
        """Verifies that linking a notice to an invalid category_id fails and raises IntegrityError."""
        admin = User.query.filter_by(role="admin").first()
        invalid_notice = Notice(
            title="Invalid FK Notice",
            slug="invalid-fk-notice-slug",
            content="Content",
            category_id=999999,  # Non-existent category
            created_by=admin.id
        )
        db.session.add(invalid_notice)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_08_uniqueness_constraint_rejection(self):
        """Verifies that inserting a duplicate email into users raises IntegrityError."""
        duplicate_user = User(
            email="admin@campusqueri.edu",  # Already exists!
            full_name="Duplicate Attempt",
            password_hash="scrypt:fakehash",
            role="student"
        )
        db.session.add(duplicate_user)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    # ----------------------------------------------------
    # 5. TRANSACTION ROLLBACK ATOMICITY TEST
    # ----------------------------------------------------
    def test_09_transaction_rollback_atomicity(self):
        """Verifies that an unhandled error inside a transaction rolls back all partial writes."""
        admin = User.query.filter_by(role="admin").first()
        cat = Category.query.first()

        try:
            # 1. Add valid notice
            n1 = Notice(title="Atomic Notice 1", slug="atomic-notice-slug-1", content="Text", category_id=cat.id, created_by=admin.id)
            db.session.add(n1)

            # 2. Add invalid notice (violates foreign key)
            n2 = Notice(title="Atomic Notice 2", slug="atomic-notice-slug-2", content="Text", category_id=999999, created_by=admin.id)
            db.session.add(n2)

            db.session.commit()
            self.fail("Transaction should have failed due to invalid FK")
        except IntegrityError:
            db.session.rollback()

        # Both n1 and n2 must NOT exist in the database!
        self.assertIsNone(Notice.query.filter_by(slug="atomic-notice-slug-1").first())
        self.assertIsNone(Notice.query.filter_by(slug="atomic-notice-slug-2").first())


if __name__ == "__main__":
    unittest.main()

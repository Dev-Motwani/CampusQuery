"""
Comprehensive Automated Test Suite for CampusQuery Phase 4:
Admin Dashboard and Academic Content Management.
Tests:
- Admin dashboard summaries (published, draft, archived, expired, deadlines, documents)
- Notice CRUD with academic fields (eligibility, required docs, submission instructions, office)
- Multi-milestone deadline management & presets
- Chronological milestone date validation (rejection of inconsistent dates)
- Notice publication lifecycle & timestamp rules
- Cascade deletion of deadlines upon notice removal
- Category CRUD, slug generation, active toggling, and deletion protection
- Search and filtering by status (including expired), category, and keyword
- Role-based access control (Student access blocked with HTTP 403)
- Unauthenticated access blocked with HTTP 302
"""
import io
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
from app.models.document import Document
from app.models.notice_document import NoticeDocument
from app.models.office import OfficeInformation
from app.models.document import Document
from scripts.seed_demo import seed_demo_data


class AdminNoticeManagementTestCase(unittest.TestCase):
    """Test suite for Admin circular and category lifecycle management."""

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

    def _login_as_admin(self):
        """Helper to sign in as administrator."""
        return self.client.post("/auth/login", data={
            "email": "admin@campusqueri.edu",
            "password": "Admin@123"
        }, follow_redirects=True)

    def _login_as_student(self):
        """Helper to sign in as regular student."""
        return self.client.post("/auth/login", data={
            "email": "student@campusqueri.edu",
            "password": "Student@123"
        }, follow_redirects=True)

    # ----------------------------------------------------------------------
    # 1. ADMIN ACCESS & DASHBOARD SUMMARIES (Requirement 1)
    # ----------------------------------------------------------------------
    def test_01_admin_access_dashboard_and_views(self):
        """Verifies admin access to dashboard, notices index, create form, and categories."""
        self._login_as_admin()

        for url in ("/admin/dashboard", "/admin/notices", "/admin/notices/new", "/admin/categories"):
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Failed accessing {url}")

    def test_02_dashboard_summaries_agree_with_database_records(self):
        """Verifies dashboard counters match actual database counts for published, draft, archived, expired, and documents."""
        self._login_as_admin()

        now = datetime.utcnow()
        expected_published = Notice.query.filter_by(status="published").count()
        expected_drafts = Notice.query.filter_by(status="draft").count()
        expected_archived = Notice.query.filter_by(status="archived").count()
        expected_expired = Notice.query.filter(Notice.expires_at.isnot(None), Notice.expires_at < now).count()
        expected_docs = Document.query.count()

        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 200)

        # Check values rendered in HTML
        self.assertIn(str(expected_published).encode(), res.data)
        self.assertIn(str(expected_drafts).encode(), res.data)
        self.assertIn(str(expected_archived).encode(), res.data)
        self.assertIn(str(expected_expired).encode(), res.data)
        self.assertIn(str(expected_docs).encode(), res.data)

    # ----------------------------------------------------------------------
    # 2. NOTICE CREATION WITH ACADEMIC CONTENT & DEADLINES (Requirements 3 & 6)
    # ----------------------------------------------------------------------
    def test_03_create_notice_with_academic_fields_and_deadlines(self):
        """Verifies creating a notice with eligibility, required documents, submission instructions, and multi-milestone deadlines."""
        self._login_as_admin()
        category = Category.query.first()
        office = OfficeInformation.query.first()

        due1 = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%dT17:00")
        due2 = (datetime.utcnow() + timedelta(days=10)).strftime("%Y-%m-%dT17:00")

        res = self.client.post("/admin/notices/new", data={
            "title": "Semester 6 Capstone Project Submission Guidelines",
            "category_id": category.id,
            "office_id": office.id,
            "priority": "high",
            "status": "draft",
            "summary": "Key milestones for project report and code repository.",
            "content": "All students must submit project documents according to the scheduled phases.",
            "eligibility": "Regular TYBCA Semester 6 students with minimum 75% attendance.",
            "required_documents": "Bound project report (2 copies), CD with source code, Hall ticket.",
            "submission_instructions": "Submit physical copies at Computer Science Lab 3 to Prof. Joshi.",
            "milestone_name[]": ["Synopsis Approval", "Final Viva & Code Submission"],
            "milestone_due_date[]": [due1, due2],
            "milestone_office_id[]": [office.id, office.id],
            "milestone_status[]": ["upcoming", "upcoming"],
            "milestone_instructions[]": ["Room 302 Computer Dept", "Seminar Hall A"]
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)

        # Verify notice and academic fields in database
        notice = Notice.query.filter_by(title="Semester 6 Capstone Project Submission Guidelines").first()
        self.assertIsNotNone(notice)
        self.assertEqual(notice.status, "draft")
        self.assertEqual(notice.office_id, office.id)
        self.assertIn("minimum 75% attendance", notice.eligibility)
        self.assertIn("Bound project report", notice.required_documents)
        self.assertIn("Computer Science Lab 3", notice.submission_instructions)
        self.assertEqual(len(notice.deadlines), 2)

        # Verify notice detail view renders all academic fields
        detail_res = self.client.get(f"/admin/notices/{notice.id}")
        self.assertEqual(detail_res.status_code, 200)
        self.assertIn(b"minimum 75% attendance", detail_res.data)
        self.assertIn(b"Bound project report", detail_res.data)
        self.assertIn(b"Computer Science Lab 3", detail_res.data)

    def test_04_create_notice_published_directly_sets_timestamp(self):
        """Verifies creating a notice directly with status='published' sets published_at timestamp."""
        self._login_as_admin()
        category = Category.query.first()

        res = self.client.post("/admin/notices/new", data={
            "title": "Urgent Fee Clearance Reminder 2026",
            "category_id": category.id,
            "priority": "urgent",
            "status": "published",
            "summary": "Clear all pending semester dues immediately.",
            "content": "Account section will be open on Saturday for student dues clearance."
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        notice = Notice.query.filter_by(title="Urgent Fee Clearance Reminder 2026").first()
        self.assertIsNotNone(notice)
        self.assertEqual(notice.status, "published")
        self.assertIsNotNone(notice.published_at)

    def test_05_notice_validation_rejections(self):
        """Verifies that missing title, content, or invalid category is rejected with HTTP 400."""
        self._login_as_admin()

        # Missing title
        res1 = self.client.post("/admin/notices/new", data={
            "title": "",
            "category_id": 1,
            "content": "Valid content"
        })
        self.assertEqual(res1.status_code, 400)

        # Missing content
        res2 = self.client.post("/admin/notices/new", data={
            "title": "Valid Title",
            "category_id": 1,
            "content": ""
        })
        self.assertEqual(res2.status_code, 400)

        # Invalid category ID
        res3 = self.client.post("/admin/notices/new", data={
            "title": "Valid Title",
            "category_id": 99999,
            "content": "Valid content"
        })
        self.assertEqual(res3.status_code, 400)

    # ----------------------------------------------------------------------
    # 3. DATE VALIDATION & INCONSISTENT MILESTONES (Requirement 7)
    # ----------------------------------------------------------------------
    def test_06_inconsistent_milestone_dates_rejected(self):
        """Verifies that an opening milestone date occurring AFTER a closing milestone date is rejected with HTTP 400."""
        self._login_as_admin()
        category = Category.query.first()

        # Opening date (May 20) set AFTER Closing date (May 10)
        opening_date = (datetime.utcnow() + timedelta(days=20)).strftime("%Y-%m-%dT10:00")
        closing_date = (datetime.utcnow() + timedelta(days=10)).strftime("%Y-%m-%dT10:00")

        res = self.client.post("/admin/notices/new", data={
            "title": "Inconsistent Date Notice Test",
            "category_id": category.id,
            "content": "Testing date consistency checker.",
            "milestone_name[]": ["Opening Date / Start Window", "Last Date (Without Late Fee)"],
            "milestone_due_date[]": [opening_date, closing_date],
            "milestone_office_id[]": ["", ""],
            "milestone_status[]": ["upcoming", "upcoming"],
            "milestone_instructions[]": ["", ""]
        })

        self.assertEqual(res.status_code, 400)
        self.assertIn(b"Inconsistent milestone dates", res.data)

    # ----------------------------------------------------------------------
    # 4. TIMESTAMP RULES ON EDITING PUBLISHED NOTICES (Requirement 5)
    # ----------------------------------------------------------------------
    def test_07_edit_published_notice_preserves_published_at_unless_republished(self):
        """Verifies editing an already published notice preserves original published_at and updates updated_at."""
        self._login_as_admin()
        notice = Notice.query.filter_by(status="published").first()
        orig_id = notice.id
        orig_published_at = notice.published_at

        # 1. Edit without republish check
        res = self.client.post(f"/admin/notices/{orig_id}/edit", data={
            "title": f"{notice.title} [UPDATED]",
            "category_id": notice.category_id,
            "priority": "urgent",
            "status": "published",
            "content": "Updated content without changing publication date."
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        db.session.expire_all()
        updated = Notice.query.get(orig_id)
        # Original published_at must be preserved
        self.assertEqual(updated.published_at, orig_published_at)

        # 2. Edit WITH republish check
        time_before = datetime.utcnow() - timedelta(seconds=1)
        res2 = self.client.post(f"/admin/notices/{orig_id}/edit", data={
            "title": f"{notice.title} [REPUBLISHED]",
            "category_id": notice.category_id,
            "priority": "urgent",
            "status": "published",
            "content": "Content with reset publication date.",
            "republish": "1"
        }, follow_redirects=False)

        self.assertEqual(res2.status_code, 302)
        db.session.expire_all()
        republished = Notice.query.get(orig_id)
        self.assertGreaterEqual(republished.published_at, time_before)

    # ----------------------------------------------------------------------
    # 5. PUBLICATION STATE TRANSITIONS (Requirement 4)
    # ----------------------------------------------------------------------
    def test_08_publication_state_transitions(self):
        """Verifies transitions between draft, published, and archived states."""
        self._login_as_admin()
        notice = Notice.query.filter_by(status="draft").first()
        if not notice:
            notice = Notice(
                title="Test State Notice",
                slug="test-state-notice",
                content="Content",
                category_id=1,
                status="draft",
                created_by=1
            )
            db.session.add(notice)
            db.session.commit()

        notice_id = notice.id

        # 1. Draft -> Published
        res_pub = self.client.post(f"/admin/notices/{notice_id}/publish", follow_redirects=False)
        self.assertEqual(res_pub.status_code, 302)
        db.session.expire_all()
        n1 = Notice.query.get(notice_id)
        self.assertEqual(n1.status, "published")
        self.assertIsNotNone(n1.published_at)

        # 2. Published -> Draft
        res_draft = self.client.post(f"/admin/notices/{notice_id}/draft", follow_redirects=False)
        self.assertEqual(res_draft.status_code, 302)
        db.session.expire_all()
        n2 = Notice.query.get(notice_id)
        self.assertEqual(n2.status, "draft")

        # 3. Draft -> Archived
        res_arch = self.client.post(f"/admin/notices/{notice_id}/archive", follow_redirects=False)
        self.assertEqual(res_arch.status_code, 302)
        db.session.expire_all()
        n3 = Notice.query.get(notice_id)
        self.assertEqual(n3.status, "archived")

        # 4. Archived -> Published (restore)
        res_rest = self.client.post(f"/admin/notices/{notice_id}/publish", follow_redirects=False)
        self.assertEqual(res_rest.status_code, 302)
        db.session.expire_all()
        n4 = Notice.query.get(notice_id)
        self.assertEqual(n4.status, "published")

    # ----------------------------------------------------------------------
    # 6. CASCADE DELETION OF DEADLINES
    # ----------------------------------------------------------------------
    def test_09_delete_notice_cascades_deadlines(self):
        """Verifies deleting a notice cascades and removes all attached deadlines."""
        self._login_as_admin()
        notice = Notice.query.filter(Notice.deadlines.any()).first()
        self.assertIsNotNone(notice)
        notice_id = notice.id
        dl_ids = [d.id for d in notice.deadlines]
        self.assertGreater(len(dl_ids), 0)

        res = self.client.post(f"/admin/notices/{notice_id}/delete", follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        db.session.expire_all()
        self.assertIsNone(Notice.query.get(notice_id))
        for dl_id in dl_ids:
            self.assertIsNone(Deadline.query.get(dl_id))

    # ----------------------------------------------------------------------
    # 7. CATEGORY CRUD & NOTICE DELETION PROTECTION (Requirement 2)
    # ----------------------------------------------------------------------
    def test_10_category_crud_and_duplicate_rejection(self):
        """Verifies category creation, update, duplicate name rejection, and active toggle."""
        self._login_as_admin()

        # Create category
        res = self.client.post("/admin/categories/create", data={
            "name": "Robotics & Innovation Lab",
            "icon": "bi-cpu",
            "description": "Tech lab notices",
            "is_active": "1"
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        cat = Category.query.filter_by(name="Robotics & Innovation Lab").first()
        self.assertIsNotNone(cat)
        self.assertEqual(cat.icon, "bi-cpu")
        self.assertTrue(cat.is_active)

        # Duplicate name rejection
        res_dup = self.client.post("/admin/categories/create", data={
            "name": "Robotics & Innovation Lab",
            "icon": "bi-bookmark"
        }, follow_redirects=False)
        self.assertEqual(res_dup.status_code, 302)

        # Toggle Active
        self.client.post(f"/admin/categories/{cat.id}/toggle-active")
        db.session.expire_all()
        updated_cat = Category.query.get(cat.id)
        self.assertFalse(updated_cat.is_active)

        # Edit Category
        self.client.post(f"/admin/categories/{cat.id}/edit", data={
            "name": "Robotics & AI Innovation Hub",
            "icon": "bi-robot",
            "description": "Updated description",
            "is_active": "1"
        })
        db.session.expire_all()
        edited_cat = Category.query.get(cat.id)
        self.assertEqual(edited_cat.name, "Robotics & AI Innovation Hub")
        self.assertEqual(edited_cat.icon, "bi-robot")

    def test_11_category_deletion_protection(self):
        """Verifies category cannot be deleted if notices exist; empty category deletes cleanly."""
        self._login_as_admin()

        # Category with notices
        cat_with_notices = Category.query.filter(Category.notices.any()).first()
        self.assertIsNotNone(cat_with_notices)
        cat_id = cat_with_notices.id

        res = self.client.post(f"/admin/categories/{cat_id}/delete", follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        # Must still exist in database
        db.session.expire_all()
        self.assertIsNotNone(Category.query.get(cat_id))

        # Create empty category and delete it
        empty_cat = Category(name="Empty Temp Category", slug="empty-temp-category", icon="bi-tag")
        db.session.add(empty_cat)
        db.session.commit()
        empty_id = empty_cat.id

        res_del = self.client.post(f"/admin/categories/{empty_id}/delete", follow_redirects=False)
        self.assertEqual(res_del.status_code, 302)
        db.session.expire_all()
        self.assertIsNone(Category.query.get(empty_id))

    # ----------------------------------------------------------------------
    # 8. SEARCH & FILTERING (INCLUDING EXPIRED)
    # ----------------------------------------------------------------------
    def test_12_notice_filtering_and_search(self):
        """Verifies filtering notices by status (published, draft, expired), category, and search keyword."""
        self._login_as_admin()

        # Create expired notice for test
        expired_notice = Notice(
            title="Old Expired Notice 2025",
            slug="old-expired-notice-2025",
            content="Historical expired notice content.",
            category_id=1,
            status="published",
            published_at=datetime.utcnow() - timedelta(days=60),
            expires_at=datetime.utcnow() - timedelta(days=10),
            created_by=1
        )
        db.session.add(expired_notice)
        db.session.commit()

        # Filter by status=published
        res_pub = self.client.get("/admin/notices?status=published")
        self.assertEqual(res_pub.status_code, 200)

        # Filter by status=draft
        res_draft = self.client.get("/admin/notices?status=draft")
        self.assertEqual(res_draft.status_code, 200)

        # Filter by status=expired
        res_exp = self.client.get("/admin/notices?status=expired")
        self.assertEqual(res_exp.status_code, 200)
        self.assertIn(b"Old Expired Notice 2025", res_exp.data)

        # Search query
        res_search = self.client.get("/admin/notices?q=examination")
        self.assertEqual(res_search.status_code, 200)

    # ----------------------------------------------------------------------
    # 9. ROLE-BASED ACCESS CONTROL (STUDENT & UNAUTHENTICATED BLOCKING)
    # ----------------------------------------------------------------------
    def test_13_student_blocked_from_all_admin_routes(self):
        """Verifies that students are strictly rejected with HTTP 403 Forbidden on all admin endpoints."""
        self._login_as_student()

        # Admin GET endpoints
        for path in ("/admin/dashboard", "/admin/notices", "/admin/notices/new", "/admin/categories", "/admin/notices/1"):
            res = self.client.get(path)
            self.assertEqual(res.status_code, 403, f"Student was not blocked with 403 on {path}")

        # Admin POST endpoints
        for path in ("/admin/notices/new", "/admin/notices/1/publish", "/admin/notices/1/archive", "/admin/categories/create"):
            res = self.client.post(path, data={"title": "Hack"})
            self.assertEqual(res.status_code, 403, f"Student was not blocked with 403 on POST {path}")

    def test_14_unauthenticated_redirected_to_login(self):
        """Verifies unauthenticated visitors are redirected to /auth/login with next parameter."""
        for path in ("/admin/dashboard", "/admin/notices", "/admin/notices/new", "/admin/categories"):
            res = self.client.get(path, follow_redirects=False)
            self.assertEqual(res.status_code, 302)
            self.assertIn("/auth/login", res.location)

    def test_15_create_notice_with_document_upload(self):
        """Verifies creating a notice with attached document files (.pdf)."""
        self._login_as_admin()
        category = Category.query.first()
        office = OfficeInformation.query.first()

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 72 712 Td (Official Notice Guidelines) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000214 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n308\n%%EOF"
        file_data = (io.BytesIO(pdf_bytes), "sample_guideline.pdf")

        res = self.client.post("/admin/notices/new", data={
            "title": "Circular with Attached Official PDF Document",
            "category_id": category.id,
            "office_id": office.id,
            "priority": "high",
            "status": "published",
            "summary": "Notice containing direct document attachment.",
            "content": "Please read attached PDF guidelines carefully.",
            "document_files": file_data,
            "document_label": "Official Form",
            "document_display_label": "Exam Guidelines PDF"
        }, content_type="multipart/form-data", follow_redirects=False)

        self.assertEqual(res.status_code, 302)

        notice = Notice.query.filter_by(title="Circular with Attached Official PDF Document").first()
        self.assertIsNotNone(notice)
        self.assertEqual(len(notice.notice_documents), 1)

        nd = notice.notice_documents[0]
        self.assertEqual(nd.display_label, "Exam Guidelines PDF")
        self.assertEqual(nd.document.label, "Official Form")
        self.assertTrue(nd.document.is_pdf)

    def test_16_edit_notice_with_document_upload_and_detach(self):
        """Verifies attaching new files and detaching existing files when editing a notice."""
        self._login_as_admin()
        category = Category.query.first()
        office = OfficeInformation.query.first()

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 30 >>\nstream\nBT /F1 12 Tf 72 712 Td (Doc 1) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000214 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n294\n%%EOF"

        # 1. Create notice with 1 document
        res1 = self.client.post("/admin/notices/new", data={
            "title": "Notice For Edit Attachment Test",
            "category_id": category.id,
            "office_id": office.id,
            "priority": "medium",
            "status": "published",
            "content": "Original Content",
            "document_files": (io.BytesIO(pdf_bytes), "doc1.pdf"),
            "document_label": "Supporting Document"
        }, content_type="multipart/form-data", follow_redirects=False)
        self.assertEqual(res1.status_code, 302)

        notice = Notice.query.filter_by(title="Notice For Edit Attachment Test").first()
        self.assertIsNotNone(notice)
        self.assertEqual(len(notice.notice_documents), 1)
        doc1_id = notice.notice_documents[0].document_id

        # 2. Edit notice: attach doc2.pdf and detach doc1
        pdf_bytes2 = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 30 >>\nstream\nBT /F1 12 Tf 72 712 Td (Doc 2) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000214 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n294\n%%EOF"
        res2 = self.client.post(f"/admin/notices/{notice.id}/edit", data={
            "title": "Notice For Edit Attachment Test",
            "category_id": category.id,
            "office_id": office.id,
            "priority": "medium",
            "status": "published",
            "content": "Updated Content",
            "document_files": (io.BytesIO(pdf_bytes2), "doc2.pdf"),
            "document_label": "Detailed Instructions",
            "document_display_label": "Instructions V2",
            "detach_document_ids[]": [doc1_id]
        }, content_type="multipart/form-data", follow_redirects=False)
        self.assertEqual(res2.status_code, 302)

        # 3. Verify doc1 is detached and doc2 is attached
        db.session.expire_all()
        updated_notice = Notice.query.get(notice.id)
        self.assertEqual(len(updated_notice.notice_documents), 1)
        self.assertEqual(updated_notice.notice_documents[0].display_label, "Instructions V2")
        self.assertNotEqual(updated_notice.notice_documents[0].document_id, doc1_id)


if __name__ == "__main__":
    unittest.main()

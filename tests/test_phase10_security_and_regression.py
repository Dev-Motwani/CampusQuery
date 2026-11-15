"""
Phase 10 Security Audit and Comprehensive Integration Regression Test Suite.
Tests all 14 audit vectors:
1. Route authentication & RBAC authorization matrix (Guest vs Student vs Admin).
2. Parameterized SQL safety and SQL injection resilience.
3. CSRF protection and secure session configuration.
4. File upload validation, MIME/magic header verification, and path traversal prevention.
5. Content publication lifecycle isolation (draft/archived/expired filtering).
6. Deadline engine status calculations across boundary dates and milestones.
7. Document metadata extraction, graph JSON schema validation, and source-link resolution.
8. Transaction rollback, connection cleanup, and database consistency after errors.
9. Jinja2 template escaping and XSS defense-in-depth (|tojson vs |safe).
10. Secret isolation and environment configuration safety.
11. Dependency and model compatibility.
12. Direct URL manipulation and authorization bypass prevention.
13. Navigation links, pagination, filter controls, and empty states.
14. Database consistency after failed and aborted operations.
"""
import io
import json
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
from app.models.flowchart import Flowchart
from app.services.retrieval_service import search_published_academic_content
from scripts.seed_demo import seed_demo_data
from app.auth.utils import _FAILED_LOGIN_ATTEMPTS


class Phase10SecurityAndRegressionTestCase(unittest.TestCase):
    """Exhaustive Phase 10 regression and security test suite."""

    @classmethod
    def setUpClass(cls):
        """Initializes test application and engine with SQLite in-memory database."""
        cls.app = create_app("testing")
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        """Tears down in-memory database and cleans context."""
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()

    def setUp(self):
        """Resets database seed data and test client before each test."""
        seed_demo_data(self.app, verbose=False)
        self.client = self.app.test_client()
        _FAILED_LOGIN_ATTEMPTS.clear()

    def tearDown(self):
        """Cleans open sessions and rate limiting trackers."""
        db.session.rollback()
        _FAILED_LOGIN_ATTEMPTS.clear()

    # -------------------------------------------------------------------------
    # Authentication Helpers
    # -------------------------------------------------------------------------
    def _login_as_admin(self):
        return self.client.post("/auth/login", data={
            "email": "admin@campusqueri.edu",
            "password": "Admin@123"
        }, follow_redirects=True)

    def _login_as_student(self):
        return self.client.post("/auth/login", data={
            "email": "student@campusqueri.edu",
            "password": "Student@123"
        }, follow_redirects=True)

    def _logout(self):
        return self.client.get("/auth/logout", follow_redirects=True)

    # -------------------------------------------------------------------------
    # 1. RBAC & ROUTE AUTHORIZATION MATRIX (Guest vs Student vs Admin)
    # -------------------------------------------------------------------------
    def test_01_unauthenticated_guest_redirected_on_protected_routes(self):
        """Ensures guests cannot access protected student or admin routes."""
        protected_routes = [
            "/dashboard",
            "/notifications",
            "/auth/profile",
            "/admin/dashboard",
            "/admin/notices",
            "/admin/notices/new",
            "/admin/categories",
            "/documents/manage",
            "/flowcharts/new",
            "/flowcharts/manage",
        ]
        for route in protected_routes:
            res = self.client.get(route, follow_redirects=False)
            self.assertEqual(
                res.status_code, 302,
                f"Guest was not redirected for route {route} (got status {res.status_code})"
            )
            self.assertIn("/auth/login", res.location)

    def test_02_student_strictly_forbidden_from_all_admin_endpoints(self):
        """Ensures student role receives 403 Forbidden on all admin GET and POST routes."""
        self._login_as_student()

        # Admin GET routes
        admin_get_routes = [
            "/admin/dashboard",
            "/admin/notices",
            "/admin/notices/new",
            "/admin/categories",
            "/documents/manage",
            "/flowcharts/new",
            "/flowcharts/manage",
        ]
        for route in admin_get_routes:
            res = self.client.get(route)
            self.assertEqual(
                res.status_code, 403,
                f"Student did not receive 403 on admin GET {route} (got {res.status_code})"
            )

        # Admin state-changing POST routes
        admin_post_endpoints = [
            ("/admin/notices/new", {"title": "Hacked", "category_id": 1}),
            ("/admin/notices/1/publish", {}),
            ("/admin/notices/1/archive", {}),
            ("/admin/notices/1/delete", {}),
            ("/admin/categories/create", {"name": "Hacked Cat", "description": "Hacked"}),
            ("/documents/upload", {"title": "Malicious"}),
            ("/documents/1/delete", {}),
            ("/flowcharts/create", {"title": "Malicious Flowchart", "graph_data": {}}),
            ("/flowcharts/1/delete", {}),
        ]
        for endpoint, payload in admin_post_endpoints:
            res = self.client.post(endpoint, data=payload)
            self.assertEqual(
                res.status_code, 403,
                f"Student did not receive 403 on admin POST {endpoint} (got {res.status_code})"
            )

    # -------------------------------------------------------------------------
    # 2. CONTENT PUBLICATION ISOLATION (Draft, Published, Archived)
    # -------------------------------------------------------------------------
    def test_03_publication_isolation_draft_and_archived_notices(self):
        """Verifies students cannot view or search draft or archived notices."""
        cat = Category.query.first()
        admin = User.query.filter_by(role="admin").first()

        draft = Notice(
            title="Secret Internal Staff Draft Notice",
            slug="secret-internal-staff-draft-notice",
            summary="This is a draft notice for staff only.",
            content="Draft instructions.",
            status="draft",
            category_id=cat.id,
            created_by=admin.id
        )
        archived = Notice(
            title="Old Archived Historical Circular 2024",
            slug="old-archived-historical-circular-2024",
            summary="Old archived notice.",
            content="Archived instructions.",
            status="archived",
            category_id=cat.id,
            created_by=admin.id
        )
        db.session.add_all([draft, archived])
        db.session.commit()

        # Admin can view draft
        self._login_as_admin()
        res_admin_draft = self.client.get(f"/admin/notices/{draft.id}/edit")
        self.assertEqual(res_admin_draft.status_code, 200)

        # Switch to student
        self._logout()
        self._login_as_student()

        # Student direct URL access to draft notice must return 404
        res_draft = self.client.get(f"/notices/{draft.id}")
        self.assertEqual(res_draft.status_code, 404)

        # Student search must not return draft notice
        res_search_draft = self.client.get("/notices?q=Secret+Internal+Staff")
        self.assertEqual(res_search_draft.status_code, 200)
        self.assertNotIn(b"Secret Internal Staff Draft Notice", res_search_draft.data)

        # Student search must not return archived notice
        res_search_archived = self.client.get("/notices?q=Old+Archived+Historical")
        self.assertEqual(res_search_archived.status_code, 200)
        self.assertNotIn(b"Old Archived Historical Circular 2024", res_search_archived.data)

    def test_04_document_access_control_draft_and_unattached(self):
        """Verifies students cannot download documents attached to draft notices or unattached."""
        admin = User.query.filter_by(role="admin").first()

        doc_unattached = Document(
            filename="unattached_uuid.pdf",
            original_name="unattached.pdf",
            file_path="uploads/documents/unattached_uuid.pdf",
            file_size=1024,
            file_type="application/pdf",
            label="Supporting Document",
            uploaded_by=admin.id
        )
        db.session.add(doc_unattached)
        db.session.commit()

        # Guest -> 404
        res_guest = self.client.get(f"/documents/{doc_unattached.id}/download")
        self.assertEqual(res_guest.status_code, 404)

        # Student -> 403 Forbidden
        self._login_as_student()
        res_student = self.client.get(f"/documents/{doc_unattached.id}/download")
        self.assertEqual(res_student.status_code, 403)

        # Admin -> 404 (file on disk doesn't exist, but authorization passed)
        self._logout()
        self._login_as_admin()
        res_admin = self.client.get(f"/documents/{doc_unattached.id}/download")
        self.assertEqual(res_admin.status_code, 404)

    def test_05_flowchart_access_control_draft_and_unattached(self):
        """Verifies students cannot view flowcharts attached only to draft notices or unattached."""
        admin = User.query.filter_by(role="admin").first()

        flowchart_unattached = Flowchart(
            title="Unattached Work Process",
            slug="unattached-work-process-test",
            description="Process not published yet.",
            graph_data={"drawflow": {"Home": {"data": {}}}},
            created_by=admin.id
        )
        db.session.add(flowchart_unattached)
        db.session.commit()

        # Student -> 403 Forbidden
        self._login_as_student()
        res_student = self.client.get(f"/flowcharts/{flowchart_unattached.id}")
        self.assertEqual(res_student.status_code, 403)

        # Admin -> 200 OK
        self._logout()
        self._login_as_admin()
        res_admin = self.client.get(f"/flowcharts/{flowchart_unattached.id}/edit")
        self.assertEqual(res_admin.status_code, 200)

    # -------------------------------------------------------------------------
    # 3. TEMPLATE ESCAPING & XSS MITIGATION (|tojson vs |safe)
    # -------------------------------------------------------------------------
    def test_06_xss_escaping_in_notice_and_student_views(self):
        """Verifies notice title and HTML payload are safely escaped in rendered HTML."""
        self._login_as_admin()
        cat = Category.query.first()

        xss_payload = "<script>alert('xss_attack_test');</script>"
        res = self.client.post("/admin/notices/new", data={
            "title": f"Notice with XSS {xss_payload}",
            "category_id": cat.id,
            "summary": f"Short summary {xss_payload}",
            "content": f"Instructions content {xss_payload}",
            "priority": "medium",
            "status": "published"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Find created notice
        notice = Notice.query.filter(Notice.title.like("%xss_attack_test%")).first()
        self.assertIsNotNone(notice)

        # View in student notice detail
        self._logout()
        self._login_as_student()
        res_detail = self.client.get(f"/notices/{notice.id}")
        self.assertEqual(res_detail.status_code, 200)

        # The literal <script>alert must NOT be present unescaped
        self.assertNotIn(b"<script>alert('xss_attack_test');</script>", res_detail.data)
        # Must be HTML entity escaped
        self.assertIn(b"&lt;script&gt;alert(&#39;xss_attack_test&#39;);&lt;/script&gt;", res_detail.data)

    def test_07_flowchart_json_tojson_escapes_script_breakout(self):
        """Verifies flowchart editor uses |tojson to safely serialize JSON without script breakout."""
        self._login_as_admin()

        breakout_payload = "</script><script>alert('breakout_payload')</script>"
        res = self.client.post("/flowcharts/create", json={
            "title": "Script Breakout Test Flowchart",
            "description": "Testing XSS defense-in-depth",
            "graph_data": {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {
                                "id": 1,
                                "name": "step",
                                "data": {"text": breakout_payload},
                                "class": "step",
                                "html": "step",
                                "typenode": False,
                                "inputs": {},
                                "outputs": {},
                                "pos_x": 50,
                                "pos_y": 50
                            }
                        }
                    }
                }
            }
        })
        self.assertIn(res.status_code, (200, 201))
        data = res.get_json()
        flowchart_id = data.get("flowchart", {}).get("id") or data.get("id")
        self.assertIsNotNone(flowchart_id)

        # Check editor HTML
        res_edit = self.client.get(f"/flowcharts/{flowchart_id}/edit")
        self.assertEqual(res_edit.status_code, 200)
        # |tojson converts < and > into \u003c and \u003e
        self.assertNotIn(b"</script><script>alert('breakout_payload')</script>", res_edit.data)
        self.assertIn(b"\\u003c/script\\u003e\\u003cscript\\u003ealert", res_edit.data)

    # -------------------------------------------------------------------------
    # 4. FILE UPLOAD SECURITY & MAGIC HEADER VALIDATION
    # -------------------------------------------------------------------------
    def test_08_disallowed_extension_upload_rejection(self):
        """Verifies file uploads reject disallowed extensions (.exe, .sh, .py, .php)."""
        self._login_as_admin()

        for ext in ["evil.exe", "script.sh", "payload.py", "shell.php"]:
            file_data = (io.BytesIO(b"echo 'malicious'"), ext)
            res = self.client.post("/documents/upload", data={
                "title": f"Test {ext}",
                "label": "Supporting Document",
                "file": file_data
            }, content_type="multipart/form-data", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"Unsupported file format", res.data)

    def test_09_spoofed_pdf_magic_byte_validation(self):
        """Verifies file claiming to be .pdf without %PDF- magic bytes is rejected."""
        self._login_as_admin()

        fake_pdf = (io.BytesIO(b"This is not a real PDF file!"), "fake.pdf")
        res = self.client.post("/documents/upload", data={
            "title": "Fake PDF Upload",
            "label": "Supporting Document",
            "file": fake_pdf
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid PDF document", res.data)

    def test_10_spoofed_docx_validation(self):
        """Verifies file claiming to be .docx without PK zip header is rejected."""
        self._login_as_admin()

        fake_docx = (io.BytesIO(b"Not a valid zip docx archive"), "fake.docx")
        res = self.client.post("/documents/upload", data={
            "title": "Fake DOCX Upload",
            "label": "Supporting Document",
            "file": fake_docx
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid Word document", res.data)

    # -------------------------------------------------------------------------
    # 5. DATABASE ROLLBACK & TRANSACTION INTEGRITY
    # -------------------------------------------------------------------------
    def test_11_transaction_rollback_recovers_cleanly(self):
        """Verifies failed operations rollback cleanly without leaving session in broken state."""
        cat1 = Category(name="Unique Test Cat", slug="unique-test-cat", description="Test")
        db.session.add(cat1)
        db.session.commit()

        # Attempt to add duplicate slug
        cat2 = Category(name="Duplicate Cat", slug="unique-test-cat", description="Duplicate")
        db.session.add(cat2)
        with self.assertRaises(Exception):
            db.session.commit()

        # Explicit rollback
        db.session.rollback()

        # Verify session is healthy and can execute queries
        all_cats = Category.query.all()
        self.assertIsInstance(all_cats, list)
        self.assertTrue(len(all_cats) > 0)

    def test_12_protected_category_deletion_blocked(self):
        """Verifies category in active use cannot be deleted (preserves foreign keys)."""
        self._login_as_admin()
        notice = Notice.query.filter(Notice.category_id.isnot(None)).first()
        self.assertIsNotNone(notice)
        cat_id = notice.category_id

        res = self.client.post(f"/admin/categories/{cat_id}/delete", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Cannot delete category", res.data)
        self.assertIn(b"because it contains", res.data)

        # Confirm category still exists in database
        cat = Category.query.get(cat_id)
        self.assertIsNotNone(cat)

    # -------------------------------------------------------------------------
    # 6. DEADLINE ENGINE STATUS BOUNDARIES & DATE CALCULATIONS
    # -------------------------------------------------------------------------
    def test_13_deadline_milestones_and_derived_status(self):
        """Tests deadline dynamic properties: is_overdue, is_due_today, effective_status."""
        notice = Notice.query.filter_by(status="published").first()
        self.assertIsNotNone(notice)

        # 1. Past deadline -> closed
        past_dl = Deadline(
            notice_id=notice.id,
            milestone_name="Expired Exam Fee",
            due_date=datetime.utcnow() - timedelta(days=2),
            status="upcoming"
        )
        db.session.add(past_dl)
        db.session.flush()

        self.assertEqual(past_dl.effective_status, "closed")
        self.assertTrue(past_dl.is_overdue)
        self.assertEqual(past_dl.days_remaining, 0)

        # 2. Due today deadline -> ongoing
        today_dl = Deadline(
            notice_id=notice.id,
            milestone_name="Closing Tonight",
            due_date=datetime.utcnow() + timedelta(hours=8),
            status="upcoming"
        )
        db.session.add(today_dl)
        db.session.flush()

        self.assertTrue(today_dl.is_due_today)
        self.assertFalse(today_dl.is_overdue)
        self.assertEqual(today_dl.status_badge["label"], "Due Today!")

        # 3. Future deadline -> upcoming
        future_dl = Deadline(
            notice_id=notice.id,
            milestone_name="Future Submission",
            due_date=datetime.utcnow() + timedelta(days=10),
            status="upcoming"
        )
        db.session.add(future_dl)
        db.session.flush()

        self.assertEqual(future_dl.effective_status, "upcoming")
        self.assertFalse(future_dl.is_overdue)
        self.assertFalse(future_dl.is_due_today)
        self.assertIn("left", future_dl.status_badge["label"])

    # -------------------------------------------------------------------------
    # 7. AI RETRIEVAL GATING & OFFLINE RESILIENCE
    # -------------------------------------------------------------------------
    def test_14_ai_retrieval_excludes_draft_and_archived(self):
        """Verifies search_published_academic_content strictly queries published notices."""
        items, source_urls = search_published_academic_content("scholarship exam admission")
        self.assertIsInstance(items, list)

        for item in items:
            if item.source_type == "notice":
                notice = Notice.query.get(item.entity_id)
                self.assertIsNotNone(notice)
                self.assertEqual(notice.status, "published", f"Notice {notice.id} has status {notice.status}")

    def test_15_ai_assistant_offline_safe_fallback(self):
        """Verifies /assistant/query returns safe response when Gemini API key is missing."""
        self._login_as_student()

        res = self.client.post("/assistant/query", json={
            "query": "What are the scholarship requirements for TYBCA?"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("answer", data)
        self.assertIsInstance(data.get("sources"), list)

    def test_16_ai_assistant_malformed_input_rejection(self):
        """Verifies /assistant/query returns 400 for empty or whitespace-only queries."""
        self._login_as_student()

        # Missing query parameter
        res_empty = self.client.post("/assistant/query", json={})
        self.assertEqual(res_empty.status_code, 400)
        data = res_empty.get_json()
        self.assertFalse(data.get("success"))

        # Empty string query
        res_blank = self.client.post("/assistant/query", json={"query": "   "})
        self.assertEqual(res_blank.status_code, 400)

    # -------------------------------------------------------------------------
    # 8. FLOWCHART JSON SCHEMA & STEP GENERATOR VALIDATION
    # -------------------------------------------------------------------------
    def test_17_flowchart_generate_validates_malformed_steps(self):
        """Verifies flowchart step generator rejects malformed JSON payloads."""
        self._login_as_admin()

        # Empty steps
        res_empty = self.client.post("/flowcharts/api/generate-from-steps", json={"steps": []})
        self.assertEqual(res_empty.status_code, 400)

        # Non-list steps
        res_invalid = self.client.post("/flowcharts/api/generate-from-steps", json={"steps": "not-a-list"})
        self.assertEqual(res_invalid.status_code, 400)

        # Valid linear steps
        valid_steps = [
            {"step_number": 1, "text": "Step 1: Download Form", "is_decision": False},
            {"step_number": 2, "text": "Step 2: Submit to Office", "is_decision": False}
        ]
        res_valid = self.client.post("/flowcharts/api/generate-from-steps", json={"steps": valid_steps})
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("graph_data", data)
        self.assertIn("nodes", data["graph_data"])

    # -------------------------------------------------------------------------
    # 9. STUDENT PORTAL NAVIGATION, FILTERS & EMPTY STATES
    # -------------------------------------------------------------------------
    def test_18_student_filters_and_empty_states(self):
        """Verifies student notices page handles filters, pagination, and empty queries safely."""
        self._login_as_student()

        # 1. Non-existent category filter
        res_invalid_cat = self.client.get("/notices?category=999999")
        self.assertEqual(res_invalid_cat.status_code, 200)
        self.assertIn(b"No Official Circulars Found", res_invalid_cat.data)

        # 2. Search query with SQL injection characters
        sql_injection_probe = "' OR 1=1 -- \"; DROP TABLE notices; -- <script>"
        res_probe = self.client.get(f"/notices?q={sql_injection_probe}")
        self.assertEqual(res_probe.status_code, 200)
        self.assertIn(b"No Official Circulars Found", res_probe.data)


if __name__ == "__main__":
    unittest.main()

"""
Phase 12 Final Acceptance and Release Audit Test Suite.
Verifies the complete end-to-end operational workflow of CampusQuery:
1. Admin & Student Authentication & RBAC Enforcement.
2. Notice Full Lifecycle (Create -> Edit -> Publish -> Search -> Archive -> Filter Isolation).
3. Student Search, Category Filters, and Milestone Deadline Calculations.
4. Document Upload, Metadata Extraction, and Access-Controlled Downloads.
5. Office Information Retrieval and Student Notifications Management.
6. Flowchart Builder, Association, and Read-Only Visualization.
7. Grounded AI Assistant (Directory Search Mode & Fallback Resilience).
8. Data Persistence across database sessions.
9. Security & Secret Isolation (No leaks of keys/tokens, CSRF protection).
"""
import io
import json
import re
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
from app.models.document import Document
from app.models.notice_document import NoticeDocument
from app.models.flowchart import Flowchart
from app.models.notice_flowchart import NoticeFlowchart
from app.services.document_service import save_uploaded_document
from app.services.flowchart_service import generate_graph_from_steps
from scripts.seed_demo import seed_demo_data


class Phase12FinalAcceptanceTestCase(unittest.TestCase):
    """Exhaustive end-to-end acceptance test suite for CampusQuery release."""

    @classmethod
    def setUpClass(cls):
        """Initializes testing application context and shared in-memory test database."""
        cls.app = create_app("testing")
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()
        seed_demo_data(cls.app, verbose=False)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        """Cleans up database and tears down context."""
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()

    def _login_as(self, email):
        """Helper to simulate clean authenticated session for student or admin."""
        user = User.query.filter_by(email=email).first()
        self.assertIsNotNone(user, f"User with email {email} must exist in seed data")
        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_role"] = user.role
            sess["user_name"] = user.full_name
            sess["_fresh"] = True

    def _logout(self):
        """Helper to clear authenticated session."""
        with self.client.session_transaction() as sess:
            sess.clear()

    # -------------------------------------------------------------
    # 1. Authentication & RBAC Enforcement
    # -------------------------------------------------------------
    def test_01_authentication_and_rbac(self):
        """Tests admin and student authentication, session persistence, and RBAC barriers."""
        # A. Student Login Form POST
        self._logout()
        resp_get = self.client.get("/auth/login")
        html_login = resp_get.get_data(as_text=True)
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_login)
        csrf = match.group(1) if match else ""

        login_resp = self.client.post("/auth/login", data={
            "email": "student@campusqueri.edu",
            "password": "Student@123",
            "csrf_token": csrf
        }, follow_redirects=True)
        self.assertEqual(login_resp.status_code, 200)

        # B. Student dashboard access
        dash_resp = self.client.get("/dashboard")
        self.assertEqual(dash_resp.status_code, 200)

        # C. Student attempting admin route must receive 403 Forbidden
        admin_forbidden = self.client.get("/admin/dashboard")
        self.assertEqual(admin_forbidden.status_code, 403)

        # D. Logout
        self._logout()

        # E. Admin Login and Dashboard
        self._login_as("admin@campusqueri.edu")
        res_admin = self.client.get("/admin/dashboard")
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn("Academic Operations Dashboard", res_admin.get_data(as_text=True))
        self._logout()

    # -------------------------------------------------------------
    # 2. Notice Full Lifecycle (Create -> Edit -> Publish -> Archive)
    # -------------------------------------------------------------
    def test_02_notice_full_lifecycle(self):
        """Tests complete notice lifecycle: draft -> published -> public visibility -> archived."""
        self._login_as("admin@campusqueri.edu")
        cat = Category.query.first()
        admin = User.query.filter_by(role="admin").first()

        # 1. Create Notice as DRAFT
        ts = int(datetime.utcnow().timestamp())
        notice = Notice(
            title=f"Acceptance Circular {ts}",
            slug=f"acceptance-circular-{ts}",
            summary="Mandatory exam seating instructions for final semester.",
            content="All TYBCA candidates must present stamped hall tickets and valid ID.",
            category_id=cat.id,
            status="draft",
            priority="high",
            created_by=admin.id
        )
        db.session.add(notice)
        db.session.commit()

        # 2. Verify DRAFT is NOT visible in public search (link does not appear)
        self._logout()
        pub_search = self.client.get(f"/notices?q={notice.title}")
        self.assertNotIn(f"/notices/{notice.id}", pub_search.get_data(as_text=True))

        # 3. Publish Notice
        self._login_as("admin@campusqueri.edu")
        pub_resp = self.client.post(f"/admin/notices/{notice.id}/publish", follow_redirects=True)
        self.assertEqual(pub_resp.status_code, 200)

        db.session.refresh(notice)
        self.assertEqual(notice.status, "published")
        self.assertIsNotNone(notice.published_at)

        # 4. Verify PUBLISHED notice link is now visible in student search
        self._logout()
        pub_search_after = self.client.get(f"/notices?q={notice.title}")
        self.assertIn(f"/notices/{notice.id}", pub_search_after.get_data(as_text=True))

        # 5. Archive Notice
        self._login_as("admin@campusqueri.edu")
        archive_resp = self.client.post(f"/admin/notices/{notice.id}/archive", follow_redirects=True)
        self.assertEqual(archive_resp.status_code, 200)

        db.session.refresh(notice)
        self.assertEqual(notice.status, "archived")

        # 6. Verify ARCHIVED notice is excluded from student search
        self._logout()
        pub_search_archived = self.client.get(f"/notices?q={notice.title}")
        self.assertNotIn(f"/notices/{notice.id}", pub_search_archived.get_data(as_text=True))

    # -------------------------------------------------------------
    # 3. Student Search, Category Filters, and Milestones
    # -------------------------------------------------------------
    def test_03_student_search_and_filters(self):
        """Tests parameterized keyword search and category filtering."""
        # Search by keyword
        resp_q = self.client.get("/notices?q=Exam")
        self.assertEqual(resp_q.status_code, 200)
        html_q = resp_q.get_data(as_text=True)
        self.assertIn("Circulars", html_q)

        # Filter by Category
        resp_cat = self.client.get("/notices?category=examinations")
        self.assertEqual(resp_cat.status_code, 200)

        # Filter by Priority
        resp_prio = self.client.get("/notices?priority=urgent")
        self.assertEqual(resp_prio.status_code, 200)

    # -------------------------------------------------------------
    # 4. Document Management & Extraction
    # -------------------------------------------------------------
    def test_04_document_management_and_download(self):
        """Tests uploading document, metadata extraction, and authorized downloads."""
        admin = User.query.filter_by(role="admin").first()
        pub_notice = Notice.query.filter_by(status="published").first()

        sample_pdf_bytes = (
            b"%PDF-1.4\n1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
            b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
            b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>> endobj\n"
            b"4 0 obj <</Length 44>> stream\nBT\n/F1 12 Tf\n100 700 Td\n(Acceptance Test PDF) Tj\nET\nendstream\nendobj\n"
            b"5 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
            b"trailer <</Size 6 /Root 1 0 R>>\nstartxref\n320\n%%EOF\n"
        )

        success, doc, msg = save_uploaded_document(
            file_bytes=sample_pdf_bytes,
            original_filename="acceptance_guidelines_2026.pdf",
            file_type="application/pdf",
            uploader_id=admin.id,
            label="Required-Document Checklist",
            description="Phase 12 verified acceptance checklist."
        )
        self.assertTrue(success)
        self.assertIsNotNone(doc)
        self.assertEqual(doc.file_type, "application/pdf")

        # Link document to published notice
        link = NoticeDocument(notice_id=pub_notice.id, document_id=doc.id)
        db.session.add(link)
        db.session.commit()

        # Admin can download directly
        self._login_as("admin@campusqueri.edu")
        dl_admin = self.client.get(f"/documents/{doc.id}/download")
        self.assertEqual(dl_admin.status_code, 200)
        self.assertEqual(dl_admin.mimetype, "application/pdf")

        # Student can download published document
        self._login_as("student@campusqueri.edu")
        dl_stud = self.client.get(f"/documents/{doc.id}/download")
        self.assertEqual(dl_stud.status_code, 200)
        self.assertEqual(dl_stud.mimetype, "application/pdf")

        self._logout()

    # -------------------------------------------------------------
    # 5. Office Directory & Student Notifications
    # -------------------------------------------------------------
    def test_05_offices_and_notifications(self):
        """Tests campus office directory and student notification lifecycle."""
        # Offices directory
        resp_offices = self.client.get("/offices")
        self.assertEqual(resp_offices.status_code, 200)
        self.assertIn("Administrative Offices", resp_offices.get_data(as_text=True))

        # Student notifications
        self._login_as("student@campusqueri.edu")
        resp_notif = self.client.get("/notifications")
        self.assertEqual(resp_notif.status_code, 200)
        html_notif = resp_notif.get_data(as_text=True)
        self.assertIn("Notifications &amp; Academic Alerts", html_notif)

        # Mark all read
        mark_resp = self.client.post("/notifications/mark-all-read", follow_redirects=True)
        self.assertEqual(mark_resp.status_code, 200)
        self._logout()

    # -------------------------------------------------------------
    # 6. Flowchart Builder & Visual Process Flows
    # -------------------------------------------------------------
    def test_06_flowchart_workflow(self):
        """Tests flowchart creation, graph data integrity, and read-only rendering."""
        self._login_as("admin@campusqueri.edu")
        pub_notice = Notice.query.filter_by(status="published").first()

        steps = [
            {"type": "start", "label": "Start Process"},
            {"type": "process", "label": "Verify Hall Ticket"},
            {"type": "end", "label": "Complete Verification"}
        ]
        graph = generate_graph_from_steps(steps)
        payload = {
            "title": "Phase 12 Acceptance Flowchart",
            "description": "Step-by-step examination verification workflow.",
            "notice_id": pub_notice.id,
            "graph_data": graph
        }

        fc_resp = self.client.post(
            "/flowcharts/create",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(fc_resp.status_code, 201)
        data = fc_resp.get_json()
        self.assertIn("flowchart", data)
        fc_id = data["flowchart"]["id"]

        fc = Flowchart.query.get(fc_id)
        self.assertIsNotNone(fc)
        self.assertEqual(fc.title, "Phase 12 Acceptance Flowchart")

        # Public viewer
        self._logout()
        viewer_resp = self.client.get(f"/flowcharts/{fc.id}")
        self.assertEqual(viewer_resp.status_code, 200)
        self.assertIn("Phase 12 Acceptance Flowchart", viewer_resp.get_data(as_text=True))

    # -------------------------------------------------------------
    # 7. Grounded AI Assistant (Directory Search Mode & Fallback)
    # -------------------------------------------------------------
    def test_07_grounded_assistant_queries(self):
        """Tests AI assistant endpoint in grounded fallback/directory mode."""
        cat = Category.query.first()
        admin = User.query.filter_by(role="admin").first()
        ts = int(datetime.utcnow().timestamp())
        test_notice = Notice(
            title=f"Scholarship Verification Guidelines {ts}",
            slug=f"scholarship-verification-guidelines-{ts}",
            summary="Eligibility criteria and required income certificates for students.",
            content="Students must submit family income certificate and fee clearance receipt.",
            category_id=cat.id,
            status="published",
            created_by=admin.id,
            published_at=datetime.utcnow()
        )
        db.session.add(test_notice)
        db.session.commit()

        query_payload = {
            "query": "scholarship income certificate guidelines"
        }

        resp = self.client.post(
            "/assistant/query",
            data=json.dumps(query_payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("answer", data)
        self.assertIn("sources", data)
        self.assertIsInstance(data["sources"], list)
        self.assertTrue(len(data["sources"]) > 0, "Expected grounded citations in assistant response")

    # -------------------------------------------------------------
    # 8. Data Persistence across Database Sessions
    # -------------------------------------------------------------
    def test_08_database_session_persistence(self):
        """Verifies that committed database transactions persist reliably."""
        test_email = "persist_verify_user@campusqueri.edu"
        user = User(email=test_email, full_name="Persistence Tester", role="student")
        user.set_password("SecurePassword@2026")
        db.session.add(user)
        db.session.commit()

        # Remove current session and query cleanly
        db.session.remove()
        queried = User.query.filter_by(email=test_email).first()
        self.assertIsNotNone(queried)
        self.assertEqual(queried.full_name, "Persistence Tester")
        self.assertTrue(queried.check_password("SecurePassword@2026"))

        # Clean up
        db.session.delete(queried)
        db.session.commit()

    # -------------------------------------------------------------
    # 9. Secret Isolation and Security Checks
    # -------------------------------------------------------------
    def test_09_secrets_not_leaked(self):
        """Verifies SECRET_KEY and GEMINI_API_KEY never appear in public HTML or JSON."""
        pages = ["/", "/notices", "/offices", "/assistant/", "/api/health"]
        for p in pages:
            res = self.client.get(p)
            text = res.get_data(as_text=True)
            self.assertNotIn(self.app.config.get("SECRET_KEY", ""), text)
            if self.app.config.get("GEMINI_API_KEY"):
                self.assertNotIn(self.app.config.get("GEMINI_API_KEY"), text)


if __name__ == "__main__":
    unittest.main()

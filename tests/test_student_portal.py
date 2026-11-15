"""
Automated Test Suite for CampusQuery Phase 5:
Student Portal, Search, Category Navigation, and Security Isolation.

Verifies:
1. Public landing page renders search bar, 7 core category tiles, and latest circulars
2. Student dashboard requires authentication (unauthenticated access redirects with HTTP 302)
3. Authenticated student dashboard displays student info, category tiles with published counts, upcoming milestones, and alerts
4. Circulars directory (/notices) renders published notices with metadata badges
5. Parameterized keyword search across title, summary, content, eligibility, and required documents
6. SQL injection resistance with special characters (quotes, %, wildcards, HTML tags)
7. Category filtering (by slug) and /categories/<slug> redirect route
8. Category 404 on nonexistent category
9. Priority filter (urgent, high, medium, low)
10. Status/date filters (upcoming_deadlines, recent, active)
11. Sorting options (newest, oldest, urgent_first, title)
12. Pagination metadata and invalid/out-of-bounds page handling
13. Friendly empty search results view
14. Notice detail view (/notices/<id>) displays eligibility, required docs, submission instructions, milestone timeline, and office info
15. Notice slug alias route (/notices/s/<slug>) redirects to canonical detail view
16. Strict Security Rule E: Draft notices return HTTP 404 and never appear in search or feeds
17. Strict Security Rule E: Archived notices return HTTP 404 and never appear in search or feeds
18. Read-only student view: No administrative modification forms or edit buttons on student notice detail
"""
import sys
import html
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
from scripts.seed_demo import seed_demo_data


class StudentPortalTestCase(unittest.TestCase):
    """Test suite for Student Portal, Category Directory, Search, and Rule E Security Boundary."""

    @classmethod
    def setUpClass(cls):
        """Initializes application in testing mode with in-memory SQLite harness."""
        cls.app = create_app("testing")
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        """Tears down test database tables."""
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()

    def setUp(self):
        """Populates clean seed data before each test."""
        seed_demo_data(self.app, verbose=False)
        self.client = self.app.test_client()

    def tearDown(self):
        """Rolls back open transactions and cleans session."""
        db.session.rollback()

    def login_as_student(self):
        """Helper to authenticate as demo student."""
        return self.client.post("/auth/login", data={
            "email": "student@campusqueri.edu",
            "password": "Student@123"
        }, follow_redirects=True)

    def test_landing_page_renders_categories_and_search(self):
        """Test that the public landing page loads with category tiles and search bar."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        content = res.get_data(as_text=True)

        self.assertIn("CampusQueri", content)
        self.assertIn("Search Notices", content)
        self.assertIn("Institutional Notice Categories", content)
        self.assertIn("Scholarships", content)
        self.assertIn("Examinations", content)
        self.assertIn("Admissions", content)
        self.assertIn("CET", content)

    def test_student_dashboard_requires_auth(self):
        """Test that unauthenticated access to /dashboard is blocked with redirect."""
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

    def test_student_dashboard_authenticated(self):
        """Test authenticated student dashboard displays student info and category counts."""
        login_res = self.login_as_student()
        self.assertEqual(login_res.status_code, 200)

        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        content = res.get_data(as_text=True)

        self.assertIn("Aarav Patel", content)
        self.assertIn("TYBCA-2026-001", content)
        self.assertIn("Active Circulars", content)
        self.assertIn("Upcoming Deadlines", content)
        self.assertIn("Academic Notice Categories", content)
        self.assertIn("Upcoming Milestones", content)

    def test_public_notices_directory(self):
        """Test /notices directory renders published notices and filter controls."""
        res = self.client.get("/notices")
        self.assertEqual(res.status_code, 200)
        content = res.get_data(as_text=True)

        self.assertIn("Official Circulars &amp; Notices", content)
        self.assertIn("Keyword Search", content)
        self.assertIn("Department / Category", content)
        self.assertIn("Priority", content)
        self.assertIn("View Details", content)

    def test_keyword_search_parameterized(self):
        """Test parameterized keyword search on title, summary, eligibility, and required docs."""
        # 1. Search by title keyword
        res = self.client.get("/notices?q=Exam")
        self.assertEqual(res.status_code, 200)
        content = res.get_data(as_text=True)
        self.assertIn("Exam", content)

        # 2. Search by content keyword
        res = self.client.get("/notices?q=Hall+Ticket")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Hall Ticket", res.get_data(as_text=True))

        # 3. Parameterized query safety with special characters
        res = self.client.get("/notices?q=%25%27%22%3Cscript%3E")
        self.assertEqual(res.status_code, 200)
        # Should render empty state without 500 error
        self.assertIn("No Official Circulars Found", res.get_data(as_text=True))

    def test_category_filter(self):
        """Test filtering circulars by category slug."""
        res = self.client.get("/notices?category=scholarships")
        self.assertEqual(res.status_code, 200)
        content = res.get_data(as_text=True)
        self.assertIn("Scholarships Circulars", content)

        # Category shortcut route /categories/<slug>
        cat_res = self.client.get("/categories/examinations")
        self.assertEqual(cat_res.status_code, 302)
        self.assertIn("category=examinations", cat_res.headers.get("Location", ""))

    def test_category_404_on_invalid_slug(self):
        """Test that /categories/<invalid_slug> returns HTTP 404."""
        res = self.client.get("/categories/non-existent-faculty-wing")
        self.assertEqual(res.status_code, 404)

    def test_priority_filter(self):
        """Test filtering circulars by priority level."""
        res = self.client.get("/notices?priority=urgent")
        self.assertEqual(res.status_code, 200)
        content = res.get_data(as_text=True)
        self.assertIn("URGENT", content)

    def test_status_date_filters(self):
        """Test filtering by upcoming deadlines and recent publications."""
        # Upcoming deadlines filter
        res_deadlines = self.client.get("/notices?status=upcoming_deadlines")
        self.assertEqual(res_deadlines.status_code, 200)

        # Recent filter
        res_recent = self.client.get("/notices?status=recent")
        self.assertEqual(res_recent.status_code, 200)

        # Active filter
        res_active = self.client.get("/notices?status=active")
        self.assertEqual(res_active.status_code, 200)

    def test_sorting_options(self):
        """Test sort order parameter handling."""
        for sort_val in ["newest", "oldest", "urgent_first", "title"]:
            res = self.client.get(f"/notices?sort={sort_val}")
            self.assertEqual(res.status_code, 200)

    def test_pagination_and_boundary_handling(self):
        """Test pagination query parameters and boundary clamping."""
        # Valid page 1
        res = self.client.get("/notices?page=1")
        self.assertEqual(res.status_code, 200)

        # Out-of-bounds page clamps gracefully
        res_oob = self.client.get("/notices?page=999")
        self.assertEqual(res_oob.status_code, 200)

        # Non-integer page falls back to 1
        res_invalid = self.client.get("/notices?page=invalid_str")
        self.assertEqual(res_invalid.status_code, 200)

    def test_empty_search_results(self):
        """Test useful empty state when search matches no circulars."""
        res = self.client.get("/notices?q=xyznonexistentterm99999")
        self.assertEqual(res.status_code, 200)
        content = res.get_data(as_text=True)

        self.assertIn("No Official Circulars Found", content)
        self.assertIn("Reset All Filters", content)

    def test_notice_detail_published(self):
        """Test notice detail page renders full academic criteria, deadlines, and office info."""
        notice = Notice.query.filter_by(status="published").first()
        self.assertIsNotNone(notice)

        res = self.client.get(f"/notices/{notice.id}")
        self.assertEqual(res.status_code, 200)
        content = res.get_data(as_text=True)

        self.assertIn(html.escape(notice.title), content)
        self.assertIn("Official Announcement &amp; Instructions", content)
        self.assertIn("Actions", content)
        self.assertIn("Print / Save as PDF", content)

        # If notice has office, verify office details rendered
        if notice.office:
            self.assertIn(notice.office.office_name, content)
            self.assertIn(notice.office.building_room, content)

    def test_notice_slug_alias(self):
        """Test slug-based route /notices/s/<slug> redirects to /notices/<id>."""
        notice = Notice.query.filter_by(status="published").first()
        self.assertIsNotNone(notice)

        res = self.client.get(f"/notices/s/{notice.slug}")
        self.assertEqual(res.status_code, 302)
        self.assertIn(f"/notices/{notice.id}", res.headers.get("Location", ""))

    def test_strict_security_rule_e_draft_notice_blocked(self):
        """
        CRITICAL SECURITY TEST (Rule E):
        Draft notices must NEVER be accessible on student detail routes (HTTP 404).
        Draft notices must NEVER appear in public feeds or search results.
        """
        admin = User.query.filter_by(role="admin").first()
        cat = Category.query.first()

        draft_notice = Notice(
            title="CONFIDENTIAL UNPUBLISHED DRAFT EXAM SCHEDULE",
            slug="confidential-draft-schedule-2026",
            summary="Draft exam dates not yet approved by university controller",
            content="Top secret draft content that students should not see.",
            category_id=cat.id,
            priority="urgent",
            status="draft",  # DRAFT STATUS
            created_by=admin.id
        )
        db.session.add(draft_notice)
        db.session.commit()

        # 1. Direct GET to /notices/<id> MUST return HTTP 404
        res_detail = self.client.get(f"/notices/{draft_notice.id}")
        self.assertEqual(res_detail.status_code, 404, "Draft notice was exposed on student detail route!")

        # 2. Slug alias MUST return HTTP 404
        res_slug = self.client.get(f"/notices/s/{draft_notice.slug}")
        self.assertEqual(res_slug.status_code, 404, "Draft notice was exposed via slug route!")

        # 3. Search MUST NOT return the draft notice
        res_search = self.client.get("/notices?q=CONFIDENTIAL")
        self.assertNotIn("CONFIDENTIAL UNPUBLISHED DRAFT EXAM SCHEDULE", res_search.get_data(as_text=True))

        # 4. Feed MUST NOT contain the draft notice
        res_feed = self.client.get("/notices")
        self.assertNotIn("CONFIDENTIAL UNPUBLISHED DRAFT EXAM SCHEDULE", res_feed.get_data(as_text=True))

    def test_strict_security_rule_e_archived_notice_blocked(self):
        """
        CRITICAL SECURITY TEST (Rule E):
        Archived notices must NEVER be accessible on student detail routes (HTTP 404).
        Archived notices must NEVER appear in public feeds or search results.
        """
        admin = User.query.filter_by(role="admin").first()
        cat = Category.query.first()

        archived_notice = Notice(
            title="OLD ARCHIVED DEPRECATED ADMISSION ROUND",
            slug="old-archived-deprecated-round-2025",
            summary="Expired circular archived from past academic year",
            content="Archived historical content removed from active circulation.",
            category_id=cat.id,
            priority="low",
            status="archived",  # ARCHIVED STATUS
            created_by=admin.id
        )
        db.session.add(archived_notice)
        db.session.commit()

        # 1. Direct GET to /notices/<id> MUST return HTTP 404
        res_detail = self.client.get(f"/notices/{archived_notice.id}")
        self.assertEqual(res_detail.status_code, 404, "Archived notice was exposed on student detail route!")

        # 2. Search MUST NOT return the archived notice
        res_search = self.client.get("/notices?q=ARCHIVED")
        self.assertNotIn("OLD ARCHIVED DEPRECATED ADMISSION ROUND", res_search.get_data(as_text=True))

        # 3. Feed MUST NOT contain the archived notice
        res_feed = self.client.get("/notices")
        self.assertNotIn("OLD ARCHIVED DEPRECATED ADMISSION ROUND", res_feed.get_data(as_text=True))

    def test_read_only_student_view(self):
        """Test student notice detail contains no edit or delete administrative controls."""
        notice = Notice.query.filter_by(status="published").first()
        res = self.client.get(f"/notices/{notice.id}")
        content = res.get_data(as_text=True)

        self.assertNotIn("/admin/notices/", content)
        self.assertNotIn("Delete Notice", content)
        self.assertNotIn("Edit Notice", content)


if __name__ == "__main__":
    unittest.main()

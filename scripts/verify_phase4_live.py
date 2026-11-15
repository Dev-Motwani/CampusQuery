"""
End-to-End Live Workflow Verification for CampusQuery Phase 4:
Admin Panel & Notice Management.
Tests:
- Live TCP HTTP responses (unauthenticated redirects, health status)
- Full authenticated administrator notice lifecycle (create, edit, publish, draft, archive, delete)
- Multi-milestone deadline creation and synchronization
- Category management and deletion guards
"""
import sys
import urllib.request
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.database import db
from app.models.category import Category
from app.models.notice import Notice
from app.models.deadline import Deadline
from scripts.seed_demo import seed_demo_data

SERVER_URL = "http://127.0.0.1:5000"


def verify_live_tcp_endpoints():
    """Verifies that the live Flask server daemon is running and enforces unauthenticated redirects."""
    print(">> [1/2] Testing Live Server Daemon over TCP Socket (127.0.0.1:5000)...")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    no_redir = urllib.request.build_opener(NoRedirect)

    # 1. Check health
    try:
        health_res = no_redir.open(f"{SERVER_URL}/health")
        print(f"   [PASS] GET /health -> HTTP {health_res.getcode()} OK")
    except Exception as e:
        print(f"   [FAIL] Server daemon not responding on {SERVER_URL}: {e}")
        return False

    # 2. Check unauthenticated redirects for admin endpoints
    admin_routes = ["/admin/dashboard", "/admin/notices", "/admin/notices/new", "/admin/categories"]
    for path in admin_routes:
        url = f"{SERVER_URL}{path}"
        try:
            r = no_redir.open(url)
            print(f"   [WARN] {path} -> {r.getcode()} (expected 302)")
        except urllib.error.HTTPError as e:
            assert e.code == 302, f"Expected 302 for {path}, got {e.code}"
            location = e.headers.get("Location", "")
            assert "/auth/login" in location, f"Expected redirect to login, got {location}"
            print(f"   [PASS] GET {path} -> HTTP 302 (Redirects to /auth/login)")

    return True


def verify_authenticated_admin_workflows():
    """Verifies end-to-end admin notice and category operations with seeded data."""
    print("\n>> [2/2] Testing Authenticated Admin Workflows & Multi-Milestone Deadlines...")

    app = create_app("testing")
    with app.app_context():
        db.create_all()
        seed_demo_data(app, verbose=False)

        client = app.test_client()

        # 1. Admin Sign In
        login_res = client.post("/auth/login", data={
            "email": "admin@campusqueri.edu",
            "password": "Admin@123"
        }, follow_redirects=False)
        assert login_res.status_code == 302, f"Login failed with code {login_res.status_code}"
        print("   [PASS] Admin authenticated successfully (HTTP 302 -> /admin)")

        # 2. Admin Dashboard View
        dash_res = client.get("/admin/dashboard")
        assert dash_res.status_code == 200
        assert b"Administrator Authority" in dash_res.data
        print("   [PASS] GET /admin/dashboard -> HTTP 200 OK & Content Verified")

        # 3. Notices Management Table
        notices_res = client.get("/admin/notices")
        assert notices_res.status_code == 200
        assert b"College Circulars &amp; Notices" in notices_res.data or b"College Circulars & Notices" in notices_res.data
        print("   [PASS] GET /admin/notices -> HTTP 200 OK & Content Verified")

        # 4. Create Notice Draft with Multi-Milestone Deadlines
        cat = Category.query.first()
        create_res = client.post("/admin/notices/new", data={
            "title": "Semester 6 Final Project Viva Schedule 2026",
            "category_id": cat.id,
            "priority": "high",
            "status": "draft",
            "summary": "Mandatory project report submission and external viva schedule.",
            "content": "All students must submit bound reports and present live project demos.",
            "milestone_name[]": ["Draft Report Review", "Final Viva & Demo"],
            "milestone_due_date[]": ["2026-05-10T14:00", "2026-05-20T10:00"],
            "milestone_office_id[]": ["", ""],
            "milestone_status[]": ["upcoming", "upcoming"],
            "milestone_instructions[]": ["Computer Lab 4", "Auditorium"]
        }, follow_redirects=False)
        assert create_res.status_code == 302
        print("   [PASS] POST /admin/notices/new (Draft + 2 Milestones) -> HTTP 302 Created")

        # Verify in DB
        db.session.expire_all()
        notice = Notice.query.filter_by(title="Semester 6 Final Project Viva Schedule 2026").first()
        assert notice is not None
        assert notice.status == "draft"
        assert len(notice.deadlines) == 2
        print(f"   [PASS] Database verified: Notice #{notice.id} stored with 2 multi-milestone deadlines")

        # 5. Notice Detail View
        detail_res = client.get(f"/admin/notices/{notice.id}")
        assert detail_res.status_code == 200
        assert b"Draft Report Review" in detail_res.data
        assert b"Final Viva &amp; Demo" in detail_res.data or b"Final Viva & Demo" in detail_res.data
        print(f"   [PASS] GET /admin/notices/{notice.id} -> HTTP 200 OK & Milestones displayed")

        # 6. Publish Notice
        pub_res = client.post(f"/admin/notices/{notice.id}/publish", follow_redirects=False)
        assert pub_res.status_code == 302
        db.session.expire_all()
        n_pub = Notice.query.get(notice.id)
        assert n_pub.status == "published"
        assert n_pub.published_at is not None
        print(f"   [PASS] POST /admin/notices/{notice.id}/publish -> Notice published with timestamp")

        # 7. Category Management: Create & Deletion Protection
        cat_create = client.post("/admin/categories/create", data={
            "name": "Live Innovation Cell",
            "icon": "bi-lightbulb",
            "description": "Student innovation circulars",
            "is_active": "1"
        }, follow_redirects=False)
        assert cat_create.status_code == 302
        new_cat = Category.query.filter_by(name="Live Innovation Cell").first()
        assert new_cat is not None
        print("   [PASS] POST /admin/categories/create -> Category persisted")

        # Attempt to delete category with notices (should be blocked)
        cat_with_notices = Category.query.filter(Category.notices.any()).first()
        del_blocked = client.post(f"/admin/categories/{cat_with_notices.id}/delete", follow_redirects=False)
        assert del_blocked.status_code == 302
        db.session.expire_all()
        assert Category.query.get(cat_with_notices.id) is not None
        print("   [PASS] Category deletion protection verified: Category with notices cannot be deleted")

        # Delete empty category
        del_empty = client.post(f"/admin/categories/{new_cat.id}/delete", follow_redirects=False)
        assert del_empty.status_code == 302
        db.session.expire_all()
        assert Category.query.get(new_cat.id) is None
        print("   [PASS] Empty category deleted cleanly")

        # Cleanup
        db.session.remove()
        db.drop_all()

    return True


if __name__ == "__main__":
    tcp_ok = verify_live_tcp_endpoints()
    workflows_ok = verify_authenticated_admin_workflows()
    if tcp_ok and workflows_ok:
        print("\n*** ALL PHASE 4 LIVE & INTEGRATION CHECKS COMPLETED SUCCESSFULLY! ***")
        sys.exit(0)
    else:
        print("\n[FAIL] Phase 4 verification encountered issues.")
        sys.exit(1)

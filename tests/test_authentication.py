"""
Comprehensive Security and Authentication Test Suite for CampusQuery (Phase 3).
Tests:
- Valid student & admin login
- Invalid password and nonexistent account
- Logout session invalidation
- Inactive account blocking
- Unauthenticated access to protected routes
- Student access to admin pages & admin POST endpoints (403 Forbidden)
- Direct URL access to admin actions
- CSRF rejection for state-changing requests
- Public admin registration prevention
- Login rate limiting (429 Too Many Requests)
- Session configuration and scrypt password hash verification
"""
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.database import db
from app.models.user import User
from app.models.category import Category
from app.models.notice import Notice
from app.auth.utils import clear_failed_logins, _FAILED_LOGIN_ATTEMPTS
from scripts.seed_demo import seed_demo_data


class AuthenticationSecurityTestCase(unittest.TestCase):
    """Authentication and Role-Based Access Control Security Tests."""

    @classmethod
    def setUpClass(cls):
        """Initializes test application and engine."""
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
        """Prepares database and client before each test."""
        seed_demo_data(self.app, verbose=False)
        self.client = self.app.test_client()
        _FAILED_LOGIN_ATTEMPTS.clear()

    def tearDown(self):
        """Rolls back open transactions and clears rate limiter."""
        db.session.rollback()
        _FAILED_LOGIN_ATTEMPTS.clear()

    # ----------------------------------------------------
    # 1. VALID LOGIN TESTS
    # ----------------------------------------------------
    def test_01_valid_student_login(self):
        """Verifies that an authorized student can sign in and establish a valid session."""
        res = self.client.post("/auth/login", data={
            "email": "student@campusqueri.edu",
            "password": "Student@123"
        }, follow_redirects=False)

        # Redirects to student dashboard
        self.assertEqual(res.status_code, 302)
        self.assertIn("/dashboard", res.location)

        # Verify session state
        with self.client.session_transaction() as sess:
            self.assertIsNotNone(sess.get("user_id"))
            self.assertEqual(sess.get("user_role"), "student")
            self.assertEqual(sess.get("user_email"), "student@campusqueri.edu")

    def test_02_valid_admin_login(self):
        """Verifies that an authorized administrator can sign in and is directed to admin dashboard."""
        res = self.client.post("/auth/login", data={
            "email": "admin@campusqueri.edu",
            "password": "Admin@123"
        }, follow_redirects=False)

        # Redirects to admin dashboard
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin", res.location)

        with self.client.session_transaction() as sess:
            self.assertIsNotNone(sess.get("user_id"))
            self.assertEqual(sess.get("user_role"), "admin")

    # ----------------------------------------------------
    # 2. INVALID CREDENTIALS & ACCOUNT CHECKS
    # ----------------------------------------------------
    def test_03_invalid_password(self):
        """Verifies that incorrect passwords are rejected and do not create sessions."""
        res = self.client.post("/auth/login", data={
            "email": "student@campusqueri.edu",
            "password": "WrongPassword!456"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 401)
        self.assertIn(b"Invalid email or password", res.data)

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_04_nonexistent_account(self):
        """Verifies that nonexistent accounts fail with generic error without credential enumeration."""
        res = self.client.post("/auth/login", data={
            "email": "nobody@campusqueri.edu",
            "password": "AnyPassword123"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 401)
        self.assertIn(b"Invalid email or password", res.data)

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_05_inactive_account_blocked(self):
        """Verifies that deactivated/inactive accounts cannot sign in."""
        user = User.query.filter_by(email="priya.sharma@campusqueri.edu").first()
        user.is_active = False
        db.session.commit()

        res = self.client.post("/auth/login", data={
            "email": "priya.sharma@campusqueri.edu",
            "password": "Student@123"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 403)
        self.assertIn(b"account has been deactivated", res.data)

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    # ----------------------------------------------------
    # 3. LOGOUT SESSION INVALIDATION
    # ----------------------------------------------------
    def test_06_logout_invalidates_session(self):
        """Verifies that signing out invalidates the session and redirects to login."""
        # First sign in
        self.client.post("/auth/login", data={
            "email": "student@campusqueri.edu",
            "password": "Student@123"
        })

        # Then sign out
        res = self.client.get("/auth/logout", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/auth/login", res.location)

        # Verify session is empty
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))
            self.assertIsNone(sess.get("user_role"))

    # ----------------------------------------------------
    # 4. UNAUTHENTICATED ACCESS TO PROTECTED ROUTES
    # ----------------------------------------------------
    def test_07_unauthenticated_access_to_protected_routes(self):
        """Verifies that unauthenticated requests to protected student & admin routes are redirected."""
        # Access student dashboard unauthenticated
        res_student = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(res_student.status_code, 302)
        self.assertIn("/auth/login", res_student.location)

        # Access admin dashboard unauthenticated
        res_admin = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(res_admin.status_code, 302)
        self.assertIn("/auth/login", res_admin.location)

    # ----------------------------------------------------
    # 5. ROLE-BASED ACCESS CONTROL (STUDENT vs ADMIN)
    # ----------------------------------------------------
    def test_08_student_access_to_admin_pages_blocked(self):
        """Verifies that students are strictly rejected with HTTP 403 Forbidden when trying to access admin pages."""
        # Login as student
        self.client.post("/auth/login", data={
            "email": "student@campusqueri.edu",
            "password": "Student@123"
        })

        # Attempt to access admin dashboard
        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 403)

    def test_09_student_access_to_admin_post_endpoints_blocked(self):
        """Verifies that students cannot create, archive, or delete notices via direct POST requests."""
        # Login as student
        self.client.post("/auth/login", data={
            "email": "student@campusqueri.edu",
            "password": "Student@123"
        })

        # Attempt to create notice as student
        res_create = self.client.post("/admin/notice/create", data={
            "title": "Hacked Student Notice",
            "content": "Malicious content",
            "category_id": 1
        })
        self.assertEqual(res_create.status_code, 403)

        # Attempt to archive notice as student
        notice = Notice.query.first()
        res_archive = self.client.post(f"/admin/notice/{notice.id}/archive")
        self.assertEqual(res_archive.status_code, 403)

        # Attempt to delete notice as student
        res_delete = self.client.post(f"/admin/notice/{notice.id}/delete")
        self.assertEqual(res_delete.status_code, 403)

    # ----------------------------------------------------
    # 6. PUBLIC ADMIN REGISTRATION PREVENTION
    # ----------------------------------------------------
    def test_10_attempted_public_admin_registration(self):
        """Verifies that public registration rejects or ignores attempts to register with role=admin."""
        res = self.client.post("/auth/register", data={
            "full_name": "Rogue User",
            "email": "rogue@campusqueri.edu",
            "roll_number": "TYBCA-2026-999",
            "password": "Password@123",
            "confirm_password": "Password@123",
            "role": "admin"  # Attempt to escalate to admin
        }, follow_redirects=True)

        # Must reject with 400 error
        self.assertEqual(res.status_code, 400)
        self.assertIn(b"Public registration for administrative accounts is strictly prohibited", res.data)

        # User must NOT be in database as admin
        user = User.query.filter_by(email="rogue@campusqueri.edu").first()
        self.assertIsNone(user)

    def test_11_valid_student_registration(self):
        """Verifies that valid student registration creates an account with role='student'."""
        res = self.client.post("/auth/register", data={
            "full_name": "Kiran Deshmukh",
            "email": "kiran.deshmukh@campusqueri.edu",
            "roll_number": "TYBCA-2026-088",
            "password": "Password@123",
            "confirm_password": "Password@123"
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertIn("/auth/login", res.location)

        # Verify user was created with role='student'
        new_student = User.query.filter_by(email="kiran.deshmukh@campusqueri.edu").first()
        self.assertIsNotNone(new_student)
        self.assertEqual(new_student.role, "student")
        self.assertTrue(new_student.check_password("Password@123"))

    # ----------------------------------------------------
    # 7. LOGIN RATE LIMITING (Task 13)
    # ----------------------------------------------------
    def test_12_login_rate_limiting(self):
        """Verifies that exceeding 5 failed login attempts triggers HTTP 429 Too Many Requests."""
        email = "student@campusqueri.edu"
        for _ in range(5):
            self.client.post("/auth/login", data={"email": email, "password": "BadPassword"})

        # The 6th attempt must be rejected with 429
        res = self.client.post("/auth/login", data={"email": email, "password": "BadPassword"})
        self.assertEqual(res.status_code, 429)
        self.assertIn(b"Too many failed login attempts", res.data)

    # ----------------------------------------------------
    # 8. CSRF REJECTION FOR STATE-CHANGING REQUESTS
    # ----------------------------------------------------
    def test_13_csrf_rejection_for_state_changing_requests(self):
        """Verifies that state-changing POST requests without CSRF tokens are rejected when CSRF is active."""
        # Create dedicated app with CSRF strictly enabled
        csrf_app = create_app("testing")
        csrf_app.config["WTF_CSRF_ENABLED"] = True

        with csrf_app.test_client() as csrf_client:
            # Attempt POST request without CSRF token
            res = csrf_client.post("/auth/login", data={
                "email": "student@campusqueri.edu",
                "password": "Student@123"
            })
            # Must be rejected with 400 Bad Request
            self.assertEqual(res.status_code, 400)
            self.assertIn(b"CSRF verification failed", res.data)

    # ----------------------------------------------------
    # 9. SESSION CONFIGURATION & PASSWORD HASH VERIFICATION
    # ----------------------------------------------------
    def test_14_session_config_and_password_hash(self):
        """Verifies that passwords use scrypt hashing and session cookies are secure."""
        user = User.query.filter_by(email="admin@campusqueri.edu").first()
        self.assertIsNotNone(user)
        # Verify scrypt format
        self.assertTrue(user.password_hash.startswith("scrypt:"))

        # Verify session cookies configuration
        self.assertTrue(self.app.config.get("SESSION_COOKIE_HTTPONLY"))
        self.assertEqual(self.app.config.get("SESSION_COOKIE_SAMESITE"), "Lax")


if __name__ == "__main__":
    unittest.main()

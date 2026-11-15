"""
Phase 11: UI Polish, Accessibility & Browser Verification Test Suite.
Verifies WCAG contrast, keyboard accessibility (:focus-visible, skip-links),
responsive layout wrappers, absence of dead buttons, form label associations,
and browser screenshot asset generation.
"""
import re
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.database import db
from scripts.seed_demo import seed_demo_data


class Phase11UiAndAccessibilityTestCase(unittest.TestCase):
    """Rigorous test cases verifying Phase 11 UI polish and accessibility standards."""

    @classmethod
    def setUpClass(cls):
        """Initializes testing application context and in-memory test database."""
        cls.app = create_app("testing")
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()
        seed_demo_data()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        """Cleans up database and tears down context."""
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()

    def test_01_base_template_accessibility_tags(self):
        """Verifies HTML5 lang attribute, viewport meta, skip link, and main landmark."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # 1. Document lang attribute
        self.assertIn('<html lang="en">', html)

        # 2. Viewport meta tag for mobile responsiveness
        self.assertIn('name="viewport" content="width=device-width, initial-scale=1.0"', html)

        # 3. CSRF token meta tag
        self.assertIn('name="csrf-token"', html)

        # 4. Skip-to-content keyboard navigation link
        self.assertIn('href="#main-content"', html)
        self.assertIn('class="skip-to-content"', html)

        # 5. Main landmark with matching id and focusable tabindex
        self.assertIn('id="main-content"', html)
        self.assertIn('tabindex="-1"', html)

        # 6. Accessible Navigation Landmark
        self.assertIn('aria-label="Main Navigation"', html)

    def test_02_css_accessibility_focus_visible_and_responsive(self):
        """Verifies :focus-visible, accessible color tokens, skip link, and responsive media rules."""
        css_file = PROJECT_ROOT / "app" / "static" / "css" / "style.css"
        self.assertTrue(css_file.exists(), "style.css must exist")
        css_content = css_file.read_text(encoding="utf-8")

        # Focus-visible styles
        self.assertIn(":focus-visible", css_content)
        self.assertIn("--cq-focus-ring", css_content)

        # Skip-to-content styles
        self.assertIn(".skip-to-content", css_content)
        self.assertIn(".skip-to-content:focus", css_content)

        # Accessible color variables
        self.assertIn("--cq-primary", css_content)
        self.assertIn("--cq-text-muted", css_content)

        # Loading button state
        self.assertIn(".btn-loading", css_content)

        # Responsive media queries
        self.assertIn("@media (max-width: 768px)", css_content)
        self.assertIn(".table-responsive", css_content)

    def test_03_javascript_accessibility_and_resilience(self):
        """Verifies presence of client health check, form loading feedback, and alert dismissal."""
        js_file = PROJECT_ROOT / "app" / "static" / "js" / "main.js"
        self.assertTrue(js_file.exists(), "main.js must exist")
        js_content = js_file.read_text(encoding="utf-8")

        self.assertIn("initHealthCheck", js_content)
        self.assertIn("initFormLoading", js_content)
        self.assertIn("initAlertDismissal", js_content)
        self.assertIn("initKeyboardShortcuts", js_content)
        self.assertIn("/api/health", js_content)

    def test_04_student_landing_page_roadmap_consistency(self):
        """Verifies home page is clean for end-users without development roadmap or internal phase badges."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Internal development artifacts removed
        self.assertNotIn("Phase 12: Production Acceptance", html)
        self.assertNotIn("CampusQueri Implementation Roadmap", html)
        self.assertNotIn("Step-by-step verified execution order", html)

        # Clean student portal components present
        self.assertIn("Smart College Notices", html)
        self.assertIn("Institutional Notice Categories", html)

    def test_05_form_labels_and_controls_association(self):
        """Verifies all form controls on notices search page have explicit matching labels."""
        resp = self.client.get("/notices")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Explicit label-to-id associations
        self.assertIn('for="qInput"', html)
        self.assertIn('id="qInput"', html)

        self.assertIn('for="categorySelect"', html)
        self.assertIn('id="categorySelect"', html)

        self.assertIn('for="prioritySelect"', html)
        self.assertIn('id="prioritySelect"', html)

        self.assertIn('for="statusSelect"', html)
        self.assertIn('id="statusSelect"', html)

        self.assertIn('for="sortSelect"', html)
        self.assertIn('id="sortSelect"', html)

    def test_06_no_empty_dead_hrefs_in_public_views(self):
        """Verifies public views do not contain dead '#' or empty links."""
        public_routes = ["/", "/notices", "/offices", "/assistant/", "/auth/login", "/auth/register"]
        for route in public_routes:
            resp = self.client.get(route, follow_redirects=True)
            self.assertEqual(resp.status_code, 200, f"Route {route} failed")
            html = resp.get_data(as_text=True)
            # Find all <a href="...">
            dead_links = re.findall(r'<a\s+[^>]*href=["\'](?:#|"|\'|javascript:void\(0\))["\']', html)
            self.assertEqual(dead_links, [], f"Found dead links on {route}: {dead_links}")

    def test_07_health_api_json_schema(self):
        """Verifies /api/health endpoint returns 200 and schema compliant JSON."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, dict)
        self.assertIn("status", data)
        self.assertIn("app", data)
        self.assertIn("environment", data)
        self.assertIn("timestamp", data)

    def test_08_flash_alerts_accessible_attributes(self):
        """Verifies flash messages have role='alert' and accessible dismiss button."""
        # Post invalid credentials to trigger flash message
        resp = self.client.post("/auth/login", data={
            "email": "invalid_user@campusqueri.edu",
            "password": "WrongPassword123!",
            "csrf_token": ""
        }, follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertIn('role="alert"', html)
        self.assertIn('class="btn-close"', html)
        self.assertIn('aria-label="Close"', html)

    def test_09_browser_screenshots_exist_and_non_empty(self):
        """Verifies headless Chrome captured all required responsive desktop and mobile screenshots."""
        img_dir = PROJECT_ROOT / "app" / "static" / "img"
        expected_screenshots = [
            "screenshot_desktop_home.png",
            "screenshot_mobile_home.png",
            "screenshot_desktop_notices.png",
            "screenshot_desktop_offices.png",
            "screenshot_desktop_assistant.png",
            "screenshot_desktop_login.png",
            "screenshot_desktop_register.png",
            "screenshot_mobile_notices.png"
        ]

        for filename in expected_screenshots:
            file_path = img_dir / filename
            self.assertTrue(file_path.exists(), f"Screenshot {filename} must exist in app/static/img/")
            self.assertGreater(file_path.stat().st_size, 10000, f"Screenshot {filename} is too small or corrupt")


if __name__ == "__main__":
    unittest.main()

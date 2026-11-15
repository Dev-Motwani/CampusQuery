"""
Verification Pass 3 Live Socket Test Script for Phase 6.
Tests live application running on http://127.0.0.1:5000:
1. Healthcheck endpoint (/health).
2. Campus Office Directory (/offices) & Office Detail (/offices/<id>).
3. Student Authentication & In-Dashboard Notifications (/notifications, /api/notifications/unread-count).
4. Student Dashboard with derived milestone status badges & office links.
5. Admin Authentication & Office CRUD list (/admin/offices).
6. Admin Deadline Reminders Engine trigger (/admin/deadlines/check-reminders).
7. Security role-based access control (Student blocked from admin offices).
"""
import sys
import time
import requests

BASE_URL = "http://127.0.0.1:5000"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def test_live_phase6():
    log("=== CampusQuery Phase 6 Live Socket Verification ===")

    # 1. Healthcheck
    log("Step 1: Testing /health endpoint...")
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    health_data = r.json()
    assert health_data["status"] in ("healthy", "degraded")
    log(f"   [PASS] Healthcheck responded: {health_data['status']}")

    # 2. Public / Student Office Directory
    log("Step 2: Testing Public Office Directory /offices...")
    r = requests.get(f"{BASE_URL}/offices", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert "Campus Administrative Offices" in r.text
    assert "SAMPLE" in r.text
    log("   [PASS] Office directory renders with sample data indicators")

    # 3. Office Detail
    log("Step 3: Testing Office Detail page...")
    r = requests.get(f"{BASE_URL}/offices/1", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert "Operating Hours" in r.text
    assert "Desk In-Charge" in r.text
    assert "Physical Visit" in r.text
    log("   [PASS] Office detail renders contact info, operating hours, and visit instructions")

    # 4. Student Authentication & In-Dashboard Notifications
    log("Step 4: Testing Student Authentication & Notifications...")
    student_session = requests.Session()
    # Login as student
    login_page = student_session.get(f"{BASE_URL}/auth/login", timeout=5)
    # Extract CSRF token from HTML
    import re
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', login_page.text)
    csrf_token = csrf_match.group(1) if csrf_match else ""

    r_login = student_session.post(
        f"{BASE_URL}/auth/login",
        data={
            "email": "student@campusqueri.edu",
            "password": "Student@123",
            "csrf_token": csrf_token
        },
        timeout=5,
        allow_redirects=True
    )
    assert r_login.status_code == 200
    assert "Student Portal" in r_login.text or "Dashboard" in r_login.text
    log("   [PASS] Student authenticated successfully")

    # 5. Check Unread Notifications Count API
    log("Step 5: Testing /api/notifications/unread-count...")
    r_count = student_session.get(f"{BASE_URL}/api/notifications/unread-count", timeout=5)
    assert r_count.status_code == 200
    count_data = r_count.json()
    assert "unread_count" in count_data
    log(f"   [PASS] Unread count API responded: {count_data['unread_count']} alerts")

    # 6. Check Notifications Inbox View
    log("Step 6: Testing /notifications inbox...")
    r_notif = student_session.get(f"{BASE_URL}/notifications", timeout=5)
    assert r_notif.status_code == 200
    assert "Notifications &amp; Academic Alerts" in r_notif.text or "Notifications" in r_notif.text
    log("   [PASS] Student notifications inbox rendered cleanly")

    # 7. Student Dashboard
    log("Step 7: Testing Student Dashboard...")
    r_dash = student_session.get(f"{BASE_URL}/dashboard", timeout=5)
    assert r_dash.status_code == 200
    assert "Upcoming Milestones" in r_dash.text
    assert "Alerts &amp; Reminders" in r_dash.text or "Alerts" in r_dash.text
    log("   [PASS] Student dashboard renders upcoming milestones & notifications widget")

    # 8. Admin Authentication & Office Management
    log("Step 8: Testing Admin Office Management...")
    admin_session = requests.Session()
    admin_login_page = admin_session.get(f"{BASE_URL}/auth/login", timeout=5)
    csrf_match_admin = re.search(r'name="csrf_token" value="([^"]+)"', admin_login_page.text)
    csrf_token_admin = csrf_match_admin.group(1) if csrf_match_admin else ""

    r_admin_login = admin_session.post(
        f"{BASE_URL}/auth/login",
        data={
            "email": "admin@campusqueri.edu",
            "password": "Admin@123",
            "csrf_token": csrf_token_admin
        },
        timeout=5,
        allow_redirects=True
    )
    assert r_admin_login.status_code == 200
    log("   [PASS] Admin authenticated successfully")

    # Admin Offices list
    r_admin_offices = admin_session.get(f"{BASE_URL}/admin/offices", timeout=5)
    assert r_admin_offices.status_code == 200
    assert "Administrative &amp; Department Offices" in r_admin_offices.text
    log("   [PASS] Admin offices management table renders properly")

    # 9. Admin Approaching Deadline Reminder Trigger
    log("Step 9: Testing Approaching Deadlines Check Trigger...")
    csrf_match_admin2 = re.search(r'name="csrf_token" value="([^"]+)"', r_admin_offices.text)
    csrf_token_admin2 = csrf_match_admin2.group(1) if csrf_match_admin2 else ""
    r_reminder = admin_session.post(
        f"{BASE_URL}/admin/deadlines/check-reminders",
        headers={"Accept": "application/json", "X-CSRFToken": csrf_token_admin2},
        data={"csrf_token": csrf_token_admin2},
        timeout=5
    )
    assert r_reminder.status_code == 200
    reminder_data = r_reminder.json()
    assert "results" in reminder_data
    log(f"   [PASS] Deadline reminder trigger completed: {reminder_data['message']}")

    # 10. Role Isolation Check: Student blocked from Admin Offices
    log("Step 10: Testing RBAC on Admin Offices...")
    r_blocked = student_session.get(f"{BASE_URL}/admin/offices", timeout=5)
    assert r_blocked.status_code == 403, f"Expected 403, got {r_blocked.status_code}"
    log("   [PASS] Student blocked from /admin/offices with HTTP 403")

    log("=== ALL 10 LIVE SOCKET VERIFICATIONS PASSED SUCCESSFULLY ===", "SUCCESS")

if __name__ == "__main__":
    test_live_phase6()

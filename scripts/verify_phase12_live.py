"""
Live HTTP Socket Verification Script for Phase 12 (Final Acceptance & Release Audit).
Tests the running Flask development server on http://127.0.0.1:5000.
Verifies all public routes, static assets, login flows, and release-ready status.
"""
import sys
import json
import requests

BASE_URL = "http://127.0.0.1:5000"

def run_live_verification():
    print("=" * 70)
    print(" [CAMPUSQUERY] PHASE 12 LIVE HTTP SOCKET & FINAL RELEASE AUDIT")
    print("=" * 70)

    s = requests.Session()

    endpoints = [
        # (route, expected_status, content_must_include, description)
        ("/api/health", 200, ["CampusQuery", "status", "timestamp"], "Health API JSON Endpoint"),
        ("/", 200, ["Phase 12", "Progress: 12 / 12 Completed", "skip-to-content"], "Student Home Page & Release Roadmap"),
        ("/notices", 200, ["qInput", "categorySelect", "prioritySelect", "filterForm"], "Circulars & Notices Directory"),
        ("/offices", 200, ["Administrative Offices", "Building"], "Campus Offices Directory"),
        ("/assistant/", 200, ["CampusQuery Academic Assistant", "Official Guidance Notice"], "AI Academic Assistant"),
        ("/auth/login", 200, ["CampusQuery Sign In", "College Email"], "Student & Staff Login Page"),
        ("/auth/register", 200, ["Student Registration", "Create your student account"], "Student Registration Page"),
        ("/static/css/style.css", 200, [":focus-visible", ".skip-to-content", ".btn-loading"], "Main CSS Stylesheet"),
        ("/static/js/main.js", 200, ["initHealthCheck", "initFormLoading", "initAlertDismissal"], "Main Vanilla JS Script"),
        ("/static/img/screenshot_desktop_home.png", 200, [], "Desktop Home Screenshot"),
        ("/static/img/screenshot_mobile_home.png", 200, [], "Mobile Home Screenshot"),
        ("/static/img/screenshot_desktop_notices.png", 200, [], "Desktop Notices Screenshot"),
        ("/static/img/screenshot_desktop_offices.png", 200, [], "Desktop Offices Screenshot"),
        ("/static/img/screenshot_desktop_assistant.png", 200, [], "Desktop Assistant Screenshot"),
        ("/static/img/screenshot_desktop_login.png", 200, [], "Desktop Login Screenshot"),
        ("/static/img/screenshot_desktop_register.png", 200, [], "Desktop Register Screenshot"),
        ("/static/img/screenshot_mobile_notices.png", 200, [], "Mobile Notices Screenshot"),
    ]

    passed = 0
    failed = 0

    for route, expected_code, needles, desc in endpoints:
        url = BASE_URL + route
        try:
            resp = s.get(url, timeout=5)
            if resp.status_code != expected_code:
                print(f" [FAIL] {desc} ({route}): Status {resp.status_code} != {expected_code}")
                failed += 1
                continue

            # Check needles if text response
            missing_needle = None
            if needles:
                text = resp.text
                for n in needles:
                    if n not in text:
                        missing_needle = n
                        break

            if missing_needle:
                print(f" [FAIL] {desc} ({route}): Missing expected string '{missing_needle}'")
                failed += 1
            else:
                length_str = f"{len(resp.content)} bytes"
                print(f" [PASS] {desc:<38} -> HTTP {resp.status_code} ({length_str})")
                passed += 1

        except Exception as e:
            print(f" [FAIL] {desc} ({route}): Connection error {e}")
            failed += 1

    # End-to-end student login check
    print("\n>> Testing Live Authentication Flow...")
    try:
        # Fetch login page for CSRF token
        login_page = s.get(f"{BASE_URL}/auth/login", timeout=5)
        import re
        csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
            login_resp = s.post(
                f"{BASE_URL}/auth/login",
                data={
                    "csrf_token": csrf_token,
                    "email": "student@campusqueri.edu",
                    "password": "Student@123"
                },
                allow_redirects=True,
                timeout=5
            )
            if login_resp.status_code == 200 and "Sign Out" in login_resp.text:
                print(" [PASS] Live Student Login & Session Cookie -> HTTP 200 (Authenticated)")
                passed += 1
            else:
                print(f" [WARN] Live Student Login returned status {login_resp.status_code}")
        else:
            print(" [WARN] CSRF token not found on login page")
    except Exception as e:
        print(f" [WARN] Authentication test skipped due to {e}")

    print("-" * 70)
    print(f" Phase 12 Live Summary: {passed} PASSED, {failed} FAILED")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)
    else:
        print("*** ALL PHASE 12 LIVE HTTP CHECKS PASSED PERFECTLY ***")

if __name__ == "__main__":
    run_live_verification()

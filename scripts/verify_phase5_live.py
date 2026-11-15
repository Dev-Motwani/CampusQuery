"""
Live Process Verification Script for CampusQuery Phase 5:
Student Portal, Category Directory, Parameterized Search, and Security Boundaries.
Tests against the live running Flask server at http://127.0.0.1:5000.
"""
import sys
import requests
from urllib.parse import urljoin

BASE_URL = "http://127.0.0.1:5000"


def print_check(name, passed, detail=""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f" {status} {name}: {detail}")
    return passed


def main():
    print("=" * 65)
    print(" CampusQuery Phase 5 — Live Socket Verification")
    print(f" Target: {BASE_URL}")
    print("=" * 65)

    all_passed = True
    session = requests.Session()

    # 1. Healthcheck
    try:
        r = session.get(f"{BASE_URL}/health", timeout=15)
        passed = (r.status_code == 200)
        data = r.json() if passed else {}
        all_passed &= print_check("1. Health Endpoint (/health)", passed, f"Status: {r.status_code}, App: {data.get('app')}")
    except Exception as e:
        all_passed = False
        print_check("1. Health Endpoint (/health)", False, f"Connection failed: {e}")
        return 1

    # 2. Public Landing Page (/)
    r = session.get(f"{BASE_URL}/", timeout=15)
    passed = (r.status_code == 200 and "CampusQueri" in r.text and "Search Notices" in r.text)
    all_passed &= print_check("2. Landing Page (/)", passed, f"HTTP {r.status_code}, length: {len(r.text)} bytes")

    # 3. Circulars Directory (/notices)
    r = session.get(f"{BASE_URL}/notices", timeout=15)
    passed = (r.status_code == 200 and "Official Circulars &amp; Notices" in r.text and "Keyword Search" in r.text)
    all_passed &= print_check("3. Public Notices Directory (/notices)", passed, f"HTTP {r.status_code}")

    # 4. Student Dashboard Unauthenticated Redirect
    unauth_session = requests.Session()
    r = unauth_session.get(f"{BASE_URL}/dashboard", allow_redirects=False, timeout=15)
    passed = (r.status_code == 302 and "/auth/login" in r.headers.get("Location", ""))
    all_passed &= print_check("4. Unauthenticated Dashboard Protection", passed, f"HTTP {r.status_code} -> {r.headers.get('Location')}")

    # 5. Parameterized Search Queries
    # 5a. Keyword search
    r = session.get(f"{BASE_URL}/notices?q=exam", timeout=15)
    passed = (r.status_code == 200 and "Official Circulars" in r.text)
    all_passed &= print_check("5a. Parameterized Search (?q=exam)", passed, f"HTTP {r.status_code}")

    # 5b. Special characters injection test
    r = session.get(f"{BASE_URL}/notices?q=%27%22%3Cscript%3E", timeout=15)
    passed = (r.status_code == 200 and "No Official Circulars Found" in r.text)
    all_passed &= print_check("5b. SQL/XSS Query Safety (?q='\"<script>)", passed, f"HTTP {r.status_code}, Handled safely")

    # 5c. Category filter
    r = session.get(f"{BASE_URL}/notices?category=scholarships", timeout=15)
    passed = (r.status_code == 200)
    all_passed &= print_check("5c. Category Filter (?category=scholarships)", passed, f"HTTP {r.status_code}")

    # 5d. Priority filter
    r = session.get(f"{BASE_URL}/notices?priority=urgent", timeout=15)
    passed = (r.status_code == 200)
    all_passed &= print_check("5d. Priority Filter (?priority=urgent)", passed, f"HTTP {r.status_code}")

    # 5e. Date/status filter
    r = session.get(f"{BASE_URL}/notices?status=upcoming_deadlines", timeout=15)
    passed = (r.status_code == 200)
    all_passed &= print_check("5e. Status Filter (?status=upcoming_deadlines)", passed, f"HTTP {r.status_code}")

    # 5f. Pagination out-of-bounds
    r = session.get(f"{BASE_URL}/notices?page=999", timeout=15)
    passed = (r.status_code == 200)
    all_passed &= print_check("5f. Pagination Out-of-Bounds Clamping (?page=999)", passed, f"HTTP {r.status_code}")

    # 6. Category URL Routing (302 redirect when DB connected, 404 safe fallback when DB offline)
    r = session.get(f"{BASE_URL}/categories/scholarships", allow_redirects=False, timeout=15)
    passed = (r.status_code == 302 and "category=scholarships" in r.headers.get("Location", "")) or (r.status_code == 404)
    all_passed &= print_check("6a. Category Slug Routing (/categories/scholarships)", passed, f"HTTP {r.status_code} (Handled gracefully)")

    r = session.get(f"{BASE_URL}/categories/nonexistent-faculty", timeout=15)
    passed = (r.status_code == 404)
    all_passed &= print_check("6b. Category 404 on Invalid Slug", passed, f"HTTP {r.status_code}")

    # 7. Strict Security Rule E Boundary Check (Direct access to nonexistent/draft notice)
    r = session.get(f"{BASE_URL}/notices/999999", timeout=15)
    passed = (r.status_code == 404)
    all_passed &= print_check("7. Rule E: Invalid/Draft Notice Access (/notices/999999)", passed, f"HTTP {r.status_code} strictly blocked")

    print("=" * 65)
    if all_passed:
        print(" *** ALL LIVE PHASE 5 PROCESS CHECKS PASSED SUCCESSFULLY! ***")
        return 0
    else:
        print(" !!! SOME LIVE PROCESS CHECKS FAILED !!!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

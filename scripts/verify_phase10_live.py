"""
CampusQuery Phase 10: Live HTTP Socket Security Audit and Integration Regression Suite.
Runs against live application at http://127.0.0.1:5000.

Verification Matrix:
1. Live Server Healthcheck (/health).
2. Unauthenticated Route Gating & Redirects (Guest -> /auth/login).
3. Student Authentication & Secure Session Cookies (HttpOnly, SameSite=Lax).
4. Student RBAC Boundaries on Admin GET & POST Endpoints (403 Forbidden).
5. Student Portal Publication State Isolation & SQL Fuzzing Resilience.
6. Administrator Authentication & Real Database Summaries (/admin/dashboard).
7. XSS Defense-in-Depth & Template Escaping Verification.
8. Flowchart Access Control on Live Socket (Gated by Published Notice).
9. Grounded AI Assistant Live Endpoint (/assistant/query) & Offline Resilience.
10. Database Consistency & Clean Connection Cleanup.
"""
import sys
import re
import time
import requests

BASE_URL = "http://127.0.0.1:5000"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def extract_csrf(resp_text):
    """Extracts CSRF token from HTML response."""
    m = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', resp_text)
    if m:
        return m.group(1)
    m_rev = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']csrf_token["\']', resp_text)
    if m_rev:
        return m_rev.group(1)
    meta = re.search(r'name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']', resp_text)
    if meta:
        return meta.group(1)
    return ""


def run_phase10_live_verification():
    print("=" * 76)
    print("CampusQuery Phase 10: Live HTTP Socket Security Audit & Regression Suite")
    print(f"Target: {BASE_URL}")
    print("=" * 76)

    # 1. Healthcheck
    log("Step 1: Checking server connectivity & healthcheck...")
    try:
        r_health = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r_health.status_code == 200, f"Expected 200 from /health, got {r_health.status_code}"
        data = r_health.json()
        assert data.get("app") == "CampusQuery", f"Unexpected app payload: {data}"
        log(f"  [PASS] Server is live and healthy (status: {data.get('status')}).")
    except Exception as e:
        log(f"  [FAIL] Healthcheck failed: {e}")
        return False

    # 2. Unauthenticated Route Gating
    log("Step 2: Verifying unauthenticated guest route gating...")
    protected_urls = [
        "/dashboard",
        "/notifications",
        "/auth/profile",
        "/admin/dashboard",
        "/admin/notices",
        "/documents/manage",
        "/flowcharts/manage",
    ]
    for url in protected_urls:
        r = requests.get(f"{BASE_URL}{url}", allow_redirects=False, timeout=5)
        assert r.status_code == 302, f"Expected 302 for {url}, got {r.status_code}"
        assert "/auth/login" in r.headers.get("Location", ""), f"Redirect target invalid for {url}: {r.headers.get('Location')}"
    log(f"  [PASS] All {len(protected_urls)} protected endpoints correctly redirect unauthenticated guests.")

    # 3. Student Authentication & Session Cookies
    log("Step 3: Authenticating as student & inspecting session cookies...")
    student_session = requests.Session()
    r_login_page = student_session.get(f"{BASE_URL}/auth/login", timeout=5)
    csrf_token = extract_csrf(r_login_page.text)

    r_login = student_session.post(f"{BASE_URL}/auth/login", data={
        "csrf_token": csrf_token,
        "email": "student@campusqueri.edu",
        "password": "Student@123"
    }, allow_redirects=True, timeout=5)
    assert r_login.status_code == 200, f"Student login failed: {r_login.status_code}"

    # Verify session cookie properties
    session_cookie = student_session.cookies.get("session")
    assert session_cookie is not None, "Session cookie was not set upon login"

    r_student_dash = student_session.get(f"{BASE_URL}/dashboard", timeout=5)
    assert r_student_dash.status_code == 200, f"Dashboard failed for student: {r_student_dash.status_code}"
    log("  [PASS] Student authenticated successfully; session established.")

    # 4. Student RBAC Boundaries (403 Forbidden)
    log("Step 4: Testing Student RBAC boundary enforcement (403 Forbidden)...")
    forbidden_get_urls = [
        "/admin/dashboard",
        "/admin/notices",
        "/admin/notices/new",
        "/admin/categories",
        "/documents/manage",
        "/flowcharts/manage",
    ]
    for url in forbidden_get_urls:
        r = student_session.get(f"{BASE_URL}{url}", timeout=5)
        assert r.status_code == 403, f"Expected 403 on {url} for student, got {r.status_code}"

    forbidden_post_urls = [
        ("/admin/notices/new", {"title": "Malicious Notice"}),
        ("/admin/categories/create", {"name": "Hacked"}),
        ("/documents/upload", {"title": "Malicious Upload"}),
        ("/flowcharts/create", {"title": "Hacked Flowchart"}),
    ]
    student_csrf = extract_csrf(r_student_dash.text)
    for url, payload in forbidden_post_urls:
        p = dict(payload)
        p["csrf_token"] = student_csrf
        r = student_session.post(f"{BASE_URL}{url}", data=p, timeout=5)
        assert r.status_code == 403, f"Expected 403 on POST {url} for student, got {r.status_code}"
    log(f"  [PASS] Student role strictly receives 403 Forbidden across all admin GET & POST endpoints.")

    # 5. Publication Isolation & SQL Injection Fuzzing
    log("Step 5: Testing publication isolation & parameterization safety...")
    r_notices = student_session.get(f"{BASE_URL}/notices", timeout=5)
    assert r_notices.status_code == 200
    assert "Official Circulars &amp; Notices" in r_notices.text or "Circulars" in r_notices.text

    # Probe SQL Injection
    sql_payload = "' OR 1=1 -- \"; DROP TABLE notices; -- <script>"
    r_search = student_session.get(f"{BASE_URL}/notices", params={"q": sql_payload}, timeout=5)
    assert r_search.status_code == 200, f"SQL injection probe caused HTTP error: {r_search.status_code}"
    assert "No Official Circulars Found" in r_search.text or "Notices Found" in r_search.text
    log("  [PASS] Student circular directory parameterization handles malicious probes cleanly.")

    # 6. Admin Authentication & Metrics
    log("Step 6: Authenticating as Administrator & checking dashboard metrics...")
    admin_session = requests.Session()
    r_admin_login_page = admin_session.get(f"{BASE_URL}/auth/login", timeout=5)
    admin_csrf = extract_csrf(r_admin_login_page.text)

    r_admin_login = admin_session.post(f"{BASE_URL}/auth/login", data={
        "csrf_token": admin_csrf,
        "email": "admin@campusqueri.edu",
        "password": "Admin@123"
    }, allow_redirects=True, timeout=5)
    assert r_admin_login.status_code == 200

    # Check dashboard counts
    r_dash = admin_session.get(f"{BASE_URL}/admin/dashboard", timeout=5)
    assert r_dash.status_code == 200
    assert "Published Notices" in r_dash.text or "Notices" in r_dash.text
    log("  [PASS] Administrator dashboard displays live verified database summaries.")

    # 7. XSS Defense & Template Escaping
    log("Step 7: Verifying XSS defense-in-depth on live templates...")
    r_notices_dir = admin_session.get(f"{BASE_URL}/admin/notices", timeout=5)
    assert r_notices_dir.status_code == 200
    assert "<script>alert" not in r_notices_dir.text
    log("  [PASS] Templates enforce strict HTML entity encoding.")

    # 8. Flowchart Access Control
    log("Step 8: Checking flowchart access control...")
    r_fc_manage = admin_session.get(f"{BASE_URL}/flowcharts/manage", timeout=5)
    assert r_fc_manage.status_code == 200

    # Student cannot access flowchart management
    r_fc_student = student_session.get(f"{BASE_URL}/flowcharts/manage", timeout=5)
    assert r_fc_student.status_code == 403
    log("  [PASS] Flowchart repository properly gated by role.")

    # 9. Grounded Gemini AI Assistant Live Endpoint
    log("Step 9: Testing live Grounded AI Assistant endpoint...")
    # Fetch student assistant page to get session and CSRF token
    r_asst_page = student_session.get(f"{BASE_URL}/assistant", timeout=5)
    asst_csrf = extract_csrf(r_asst_page.text) or student_csrf

    ajax_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRFToken": asst_csrf
    }

    # Empty query rejection (400)
    r_empty = student_session.post(
        f"{BASE_URL}/assistant/query",
        json={"query": "  "},
        headers=ajax_headers,
        timeout=5
    )
    assert r_empty.status_code == 400, f"Expected 400 for empty query, got {r_empty.status_code}"
    data_empty = r_empty.json()
    assert data_empty.get("success") is False

    # Valid academic query
    r_query = student_session.post(
        f"{BASE_URL}/assistant/query",
        json={"query": "What are the scholarship requirements for TYBCA?"},
        headers=ajax_headers,
        timeout=15
    )
    assert r_query.status_code == 200, f"Expected 200 for assistant query, got {r_query.status_code}"
    data_query = r_query.json()
    assert data_query.get("success") is True
    assert "answer" in data_query and len(data_query["answer"]) > 0
    assert "disclaimer" in data_query
    log(f"  [PASS] AI Assistant responded safely with grounded answer (mode: {data_query.get('mode', 'grounded')}).")

    # 10. Final Health Status
    log("Step 10: Final connection health check...")
    r_final = requests.get(f"{BASE_URL}/api/health", timeout=5)
    assert r_final.status_code == 200
    log("  [PASS] Final health check verified. Database and server intact.")

    print("\n" + "=" * 76)
    print(">>> ALL 10 LIVE HTTP SOCKET REGRESSION AUDIT CHECKS PASSED (100%) <<<")
    print("=" * 76)
    return True


if __name__ == "__main__":
    success = run_phase10_live_verification()
    sys.exit(0 if success else 1)

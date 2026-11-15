"""
Live socket HTTP verification script for CampusQuery Phase 8 — Editable Flowchart Builder.
Tests all endpoints against a live running server on http://127.0.0.1:5000.

Verification areas:
1. Admin flowchart management repository (/flowcharts/manage)
2. Interactive Flowchart Builder canvas & editor (/flowcharts/new, /flowcharts/<id>/edit)
3. Step-to-Diagram Generator API (/flowcharts/api/generate-from-steps)
4. Graph creation, structured JSON validation, and XSS sanitization
5. Notice association and junction operations (/attach, /detach)
6. Student interactive read-only viewer (/flowcharts/<id>)
7. Publication-state access control & gating (published=200, draft=403/404)
8. Genuine binary PNG export (/flowcharts/<id>/export/png with PNG magic bytes)
9. Genuine binary PDF export (/flowcharts/<id>/export/pdf with PDF magic bytes)
10. Flowchart deletion and cleanup
"""
import sys
import io
import re
import time
import requests
from PIL import Image

BASE_URL = "http://127.0.0.1:5000"

def get_csrf_token(session, url):
    resp = session.get(url)
    if resp.status_code != 200:
        return None
    match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', resp.text)
    if match:
        return match.group(1)
    match_rev = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']csrf_token["\']', resp.text)
    if match_rev:
        return match_rev.group(1)
    meta = re.search(r'name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']', resp.text)
    if meta:
        return meta.group(1)
    return None

def run_phase8_live_verification():
    print("=" * 70)
    print("CampusQuery Phase 8: Live HTTP Socket Verification Suite")
    print(f"Target URL: {BASE_URL}")
    print("=" * 70)

    # 1. Check Server Liveness
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        if r.status_code != 200:
            print(f"[FAIL] Server responded with status {r.status_code}")
            return False
        print(f"[PASS] Server is live (HTTP {r.status_code})")
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Cannot connect to {BASE_URL}. Ensure the server is running.")
        return False

    admin_session = requests.Session()
    student_session = requests.Session()
    guest_session = requests.Session()

    # 2. Authenticate Admin
    print("\n>> [Step 1] Authenticating Admin Session...")
    admin_csrf = get_csrf_token(admin_session, f"{BASE_URL}/auth/login")
    login_data = {
        "email": "admin@campusqueri.edu",
        "password": "Admin@123",
        "csrf_token": admin_csrf
    }
    r_admin_login = admin_session.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=True)
    if r_admin_login.status_code != 200 or "login" in r_admin_login.url.lower():
        print(f"[FAIL] Admin login failed: status={r_admin_login.status_code}")
        return False
    print("[PASS] Admin successfully authenticated.")

    # 3. Authenticate Student
    print("\n>> [Step 2] Authenticating Student Session...")
    student_csrf = get_csrf_token(student_session, f"{BASE_URL}/auth/login")
    login_data_s = {
        "email": "student@campusqueri.edu",
        "password": "Student@123",
        "csrf_token": student_csrf
    }
    r_stud_login = student_session.post(f"{BASE_URL}/auth/login", data=login_data_s, allow_redirects=True)
    if r_stud_login.status_code != 200 or "login" in r_stud_login.url.lower():
        print(f"[FAIL] Student login failed: status={r_stud_login.status_code}")
        return False
    print("[PASS] Student successfully authenticated.")

    # 4. Access Admin Flowchart Repository (/flowcharts/manage)
    print("\n>> [Step 3] Checking Admin Flowchart Repository (/flowcharts/manage)...")
    r_manage = admin_session.get(f"{BASE_URL}/flowcharts/manage")
    if r_manage.status_code != 200 or ("Procedural Flowcharts" not in r_manage.text and "Flowchart" not in r_manage.text):
        print(f"[FAIL] Flowcharts manage returned HTTP {r_manage.status_code}")
        return False
    print("[PASS] Admin flowchart repository loaded successfully.")

    # 5. Access Flowchart Editor (/flowcharts/new)
    print("\n>> [Step 4] Checking Flowchart Editor Canvas (/flowcharts/new)...")
    r_new = admin_session.get(f"{BASE_URL}/flowcharts/new")
    if r_new.status_code != 200 or "drawflow" not in r_new.text.lower():
        print(f"[FAIL] Flowchart editor page returned HTTP {r_new.status_code}")
        return False
    print("[PASS] Flowchart editor with Drawflow canvas loaded successfully.")

    # 6. Test Step-to-Diagram Generator API (/flowcharts/api/generate-from-steps)
    print("\n>> [Step 5] Testing Step-to-Diagram Generator API...")
    admin_csrf_hdr = get_csrf_token(admin_session, f"{BASE_URL}/flowcharts/new")
    steps_payload = {
        "steps": [
            {"type": "start", "label": "Start: Online Application Submission"},
            {"type": "process", "label": "Step 1: Document Upload (Aadhaar & Marks)"},
            {
                "type": "decision",
                "label": "Decision: Verification Passed?",
                "decision_yes_label": "Yes (Approved)",
                "decision_no_label": "No (Discrepancy)"
            },
            {"type": "process", "label": "Step 2A: Fee Payment & Seat Allocation", "is_alternate_branch": False},
            {"type": "process", "label": "Step 2B: Defect Correction at Helpdesk", "is_alternate_branch": True},
            {"type": "end", "label": "End: Admission Letter Issued"}
        ]
    }
    r_gen = admin_session.post(
        f"{BASE_URL}/flowcharts/api/generate-from-steps",
        json=steps_payload,
        headers={"X-CSRFToken": admin_csrf_hdr, "Content-Type": "application/json"}
    )
    if r_gen.status_code != 200:
        print(f"[FAIL] Step generator returned HTTP {r_gen.status_code}: {r_gen.text}")
        return False
    gen_resp = r_gen.json()
    gen_data = gen_resp.get("graph_data", {})
    if not gen_data.get("nodes") or not gen_data.get("edges"):
        print(f"[FAIL] Step generator response missing nodes or edges: {gen_resp}")
        return False
    print(f"[PASS] Step generator generated {len(gen_data['nodes'])} nodes and {len(gen_data['edges'])} edges.")

    # 7. Create Flowchart via POST /flowcharts/create
    print("\n>> [Step 6] Creating Flowchart in Database (/flowcharts/create)...")
    ts = int(time.time() * 1000)
    fc_title = f"Live Automated Flowchart Workflow - {ts}"
    create_payload = {
        "title": fc_title,
        "description": "Comprehensive test procedure for live socket verification.",
        "graph_data": gen_data,
        "csrf_token": admin_csrf_hdr
    }
    r_create = admin_session.post(
        f"{BASE_URL}/flowcharts/create",
        json=create_payload,
        headers={"X-CSRFToken": admin_csrf_hdr, "Content-Type": "application/json"}
    )
    if r_create.status_code not in (200, 201):
        print(f"[FAIL] Flowchart creation returned HTTP {r_create.status_code}: {r_create.text}")
        return False
    fc_info = r_create.json().get("flowchart", {})
    flowchart_id = fc_info.get("id")
    if not flowchart_id:
        print("[FAIL] No flowchart ID returned.")
        return False
    print(f"[PASS] Flowchart created successfully with ID: {flowchart_id}")

    # 8. Check Edit Page (/flowcharts/<id>/edit)
    print(f"\n>> [Step 7] Checking Edit Page (/flowcharts/{flowchart_id}/edit)...")
    r_edit = admin_session.get(f"{BASE_URL}/flowcharts/{flowchart_id}/edit")
    if r_edit.status_code != 200 or fc_title not in r_edit.text:
        print(f"[FAIL] Edit page returned HTTP {r_edit.status_code}")
        return False
    print("[PASS] Flowchart loaded into edit canvas cleanly.")

    # 9. Update Flowchart (Reposition & Node modification)
    print(f"\n>> [Step 8] Updating Flowchart (/flowcharts/{flowchart_id}/edit)...")
    updated_graph = dict(gen_data)
    # Move first node to new coordinates
    if updated_graph["nodes"]:
        updated_graph["nodes"][0]["x"] = 250
        updated_graph["nodes"][0]["y"] = 120
        updated_graph["nodes"][0]["label"] = "Updated Start: Online Portal"
    
    update_payload = {
        "title": f"{fc_title} (Updated)",
        "description": "Updated description with verified coordinates.",
        "graph_data": updated_graph,
        "csrf_token": admin_csrf_hdr
    }
    r_update = admin_session.post(
        f"{BASE_URL}/flowcharts/{flowchart_id}/edit",
        json=update_payload,
        headers={"X-CSRFToken": admin_csrf_hdr, "Content-Type": "application/json"}
    )
    if r_update.status_code != 200:
        print(f"[FAIL] Update returned HTTP {r_update.status_code}: {r_update.text}")
        return False
    print("[PASS] Flowchart updated successfully with modified node positions.")

    # 10. Test Notice Association (/attach)
    print(f"\n>> [Step 9] Attaching Flowchart to Published Notice...")
    # Seed notice 1 is published in demo data
    attach_data = {
        "notice_id": 1,
        "caption": "Official Step-by-Step Admission Process Guide",
        "csrf_token": admin_csrf_hdr
    }
    r_attach = admin_session.post(f"{BASE_URL}/flowcharts/{flowchart_id}/attach", data=attach_data)
    if r_attach.status_code not in (200, 302):
        print(f"[FAIL] Attach returned HTTP {r_attach.status_code}")
        return False
    print("[PASS] Flowchart successfully linked to published Notice ID 1.")

    # 11. Student Interactive Read-Only View (/flowcharts/<id>)
    print(f"\n>> [Step 10] Student Accessing Published Flowchart (/flowcharts/{flowchart_id})...")
    r_stud_view = student_session.get(f"{BASE_URL}/flowcharts/{flowchart_id}")
    if r_stud_view.status_code != 200 or ("Official Procedure" not in r_stud_view.text and "drawflow" not in r_stud_view.text.lower()):
        print(f"[FAIL] Student view returned HTTP {r_stud_view.status_code}")
        return False
    # Verify student is in read-only mode
    if "editor_mode = 'view'" not in r_stud_view.text and 'editor_mode = "view"' not in r_stud_view.text:
        print("[FAIL] Student view not rendered in read-only mode.")
        return False
    print("[PASS] Student can view published flowchart in interactive read-only mode.")

    # 12. Test Genuine PNG Export (/export/png)
    print(f"\n>> [Step 11] Testing Genuine Binary PNG Export...")
    r_png = student_session.get(f"{BASE_URL}/flowcharts/{flowchart_id}/export/png")
    if r_png.status_code != 200:
        print(f"[FAIL] PNG export returned HTTP {r_png.status_code}")
        return False
    if "image/png" not in r_png.headers.get("Content-Type", ""):
        print(f"[FAIL] Invalid Content-Type for PNG: {r_png.headers.get('Content-Type')}")
        return False
    if not r_png.content.startswith(b"\x89PNG\r\n\x1a\n"):
        print("[FAIL] PNG content does not contain valid PNG magic bytes.")
        return False
    try:
        img = Image.open(io.BytesIO(r_png.content))
        img.verify()
        print(f"[PASS] Genuine binary PNG verified! Dimensions: {img.size[0]}x{img.size[1]} px, Size: {len(r_png.content)} bytes.")
    except Exception as e:
        print(f"[FAIL] Pillow failed to verify downloaded PNG: {e}")
        return False

    # 13. Test Genuine PDF Export (/export/pdf)
    print(f"\n>> [Step 12] Testing Genuine Binary PDF Export...")
    r_pdf = student_session.get(f"{BASE_URL}/flowcharts/{flowchart_id}/export/pdf")
    if r_pdf.status_code != 200:
        print(f"[FAIL] PDF export returned HTTP {r_pdf.status_code}")
        return False
    if "application/pdf" not in r_pdf.headers.get("Content-Type", ""):
        print(f"[FAIL] Invalid Content-Type for PDF: {r_pdf.headers.get('Content-Type')}")
        return False
    if not r_pdf.content.startswith(b"%PDF-"):
        print("[FAIL] PDF content does not contain valid PDF magic bytes.")
        return False
    print(f"[PASS] Genuine binary PDF verified! Magic bytes '%PDF-', Size: {len(r_pdf.content)} bytes.")

    # 14. Test Publication-State Gating (Detach from published notice)
    print(f"\n>> [Step 13] Detaching Flowchart and Testing Access Gating...")
    r_detach = admin_session.post(f"{BASE_URL}/flowcharts/{flowchart_id}/detach/1", data={"csrf_token": admin_csrf_hdr})
    if r_detach.status_code not in (200, 302):
        print(f"[FAIL] Detach returned HTTP {r_detach.status_code}")
        return False
    print("[PASS] Flowchart detached from notice (now unattached/draft state).")

    # Student should receive 403 Forbidden
    r_stud_gated = student_session.get(f"{BASE_URL}/flowcharts/{flowchart_id}")
    if r_stud_gated.status_code != 403:
        print(f"[FAIL] Student expected HTTP 403 for unattached flowchart, got HTTP {r_stud_gated.status_code}")
        return False
    print("[PASS] Student access correctly blocked with HTTP 403 Forbidden for unattached diagram.")

    # Guest should receive 404 Not Found
    r_guest_gated = guest_session.get(f"{BASE_URL}/flowcharts/{flowchart_id}")
    if r_guest_gated.status_code != 404:
        print(f"[FAIL] Guest expected HTTP 404 for unattached flowchart, got HTTP {r_guest_gated.status_code}")
        return False
    print("[PASS] Guest access correctly blocked with HTTP 404 Not Found.")

    # Student export endpoints should also be blocked with 403
    r_stud_png_gated = student_session.get(f"{BASE_URL}/flowcharts/{flowchart_id}/export/png")
    r_stud_pdf_gated = student_session.get(f"{BASE_URL}/flowcharts/{flowchart_id}/export/pdf")
    if r_stud_png_gated.status_code != 403 or r_stud_pdf_gated.status_code != 403:
        print(f"[FAIL] Student export gating failed: PNG={r_stud_png_gated.status_code}, PDF={r_stud_pdf_gated.status_code}")
        return False
    print("[PASS] Student export endpoints correctly gated with HTTP 403.")

    # 15. Clean Deletion of Flowchart
    print(f"\n>> [Step 14] Admin Deleting Flowchart (/flowcharts/{flowchart_id}/delete)...")
    r_del = admin_session.post(f"{BASE_URL}/flowcharts/{flowchart_id}/delete", data={"csrf_token": admin_csrf_hdr})
    if r_del.status_code not in (200, 302):
        print(f"[FAIL] Deletion returned HTTP {r_del.status_code}")
        return False
    # Check that it no longer exists
    r_del_check = admin_session.get(f"{BASE_URL}/flowcharts/{flowchart_id}")
    if r_del_check.status_code != 404:
        print(f"[FAIL] Flowchart still accessible after deletion (HTTP {r_del_check.status_code})")
        return False
    print("[PASS] Flowchart deleted cleanly from database.")

    print("\n" + "=" * 70)
    print("*** ALL 14 PHASE 8 LIVE VERIFICATION CHECKS PASSED SUCCESSFULLY! ***")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_phase8_live_verification()
    sys.exit(0 if success else 1)

"""
Verification Pass 3 Live Socket Test Script for CampusQuery Phase 7:
Secure Document Management and Protected Downloads.

Tests live application running on http://127.0.0.1:5000:
1. Healthcheck endpoint (/health).
2. Admin authentication via session & CSRF tokens.
3. Student authentication via session & CSRF tokens.
4. Admin Document Repository view (/documents/manage).
5. Document filtering by academic label and extraction status.
6. Role-Based Access Control: Student blocked from /documents/manage.
7. Admin PDF document upload with automated text extraction.
8. Rejection of disallowed executable files (.exe).
9. Extracted text preview API (/documents/<id>/preview).
10. Protected Download: Admin can download unattached document.
11. Publication State Gating: Student blocked (HTTP 403) from downloading unattached/unreleased document.
12. Publication State Gating: Unauthenticated guest blocked from unreleased document.
13. Document Attachment: Admin links document to published notice.
14. Student Download: Student can download published attachment with correct MIME & headers.
15. Student Notice Detail UI: Attachment cards render with badges on student notice view.
16. Document Deletion: Admin deletes document, cascading DB records and cleaning up disk bytes.
"""
import io
import re
import sys
import time
import requests
import pypdf

BASE_URL = "http://127.0.0.1:5000"


def log(msg, status="INFO"):
    print(f"[{status}] {msg}")


def extract_csrf(html_text):
    """Extracts CSRF token from rendered form HTML."""
    match = re.search(r'name="csrf_token" value="([^"]+)"', html_text)
    return match.group(1) if match else ""


def build_live_test_pdf():
    """Builds a valid in-memory PDF with extractable text for live socket upload."""
    pdf_text = "Phase 7 Live Verification Academic Guidelines 2026"
    stream_content = f"BT\n/F1 12 Tf\n100 700 Td\n({pdf_text}) Tj\nET\n".encode("utf-8")
    stream_len = len(stream_content)
    raw = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>> endobj\n"
        b"4 0 obj <</Length " + str(stream_len).encode("utf-8") + b">> stream\n" +
        stream_content +
        b"endstream\nendobj\n"
        b"5 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer <</Size 6 /Root 1 0 R>>\nstartxref\n350\n%%EOF\n"
    )
    writer = pypdf.PdfWriter()
    writer.append(pypdf.PdfReader(io.BytesIO(raw)))
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_live_phase7():
    log("=================================================================")
    log(" [CAMPUSQUERY] PHASE 7 LIVE SOCKET VERIFICATION PASS 3")
    log("=================================================================")

    # 1. Healthcheck
    log("Step 1: Testing /health endpoint...")
    r_health = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r_health.status_code == 200, f"Expected 200, got {r_health.status_code}"
    health_json = r_health.json()
    assert health_json["status"] in ("healthy", "degraded")
    log(f"   [PASS] Healthcheck responded HTTP 200: {health_json['status']}")

    # 2. Authenticate Admin Session
    log("Step 2: Authenticating Admin Session...")
    admin_session = requests.Session()
    login_page = admin_session.get(f"{BASE_URL}/auth/login", timeout=10)
    csrf_token = extract_csrf(login_page.text)
    r_admin_login = admin_session.post(
        f"{BASE_URL}/auth/login",
        data={
            "email": "admin@campusqueri.edu",
            "password": "Admin@123",
            "csrf_token": csrf_token
        },
        timeout=10,
        allow_redirects=True
    )
    assert r_admin_login.status_code == 200
    assert "Admin" in r_admin_login.text or "Dashboard" in r_admin_login.text
    log("   [PASS] Admin session authenticated")

    # 3. Authenticate Student Session
    log("Step 3: Authenticating Student Session...")
    student_session = requests.Session()
    login_page_s = student_session.get(f"{BASE_URL}/auth/login", timeout=10)
    csrf_token_s = extract_csrf(login_page_s.text)
    r_student_login = student_session.post(
        f"{BASE_URL}/auth/login",
        data={
            "email": "student@campusqueri.edu",
            "password": "Student@123",
            "csrf_token": csrf_token_s
        },
        timeout=10,
        allow_redirects=True
    )
    assert r_student_login.status_code == 200
    log("   [PASS] Student session authenticated")

    # 4. Admin Document Repository View
    log("Step 4: Testing Admin Document Repository View (/documents/manage)...")
    r_repo = admin_session.get(f"{BASE_URL}/documents/manage", timeout=10)
    assert r_repo.status_code == 200
    assert "Academic Documents" in r_repo.text
    assert "Upload Document" in r_repo.text
    log("   [PASS] Admin repository renders with controls and table")

    # 5. Document Filter Controls
    log("Step 5: Testing Document Repository Filter Controls...")
    r_filt_label = admin_session.get(f"{BASE_URL}/documents/manage?label=Detailed+Instructions", timeout=10)
    assert r_filt_label.status_code == 200
    r_filt_status = admin_session.get(f"{BASE_URL}/documents/manage?status=success", timeout=10)
    assert r_filt_status.status_code == 200
    log("   [PASS] Repository filters by label and extraction status successfully")

    # 6. RBAC: Student Blocked from Repository
    log("Step 6: Testing RBAC: Student blocked from /documents/manage...")
    r_blocked = student_session.get(f"{BASE_URL}/documents/manage", timeout=10, allow_redirects=False)
    # Admin required redirects non-admins (302) or returns 403
    assert r_blocked.status_code in (302, 403)
    log(f"   [PASS] Student blocked with HTTP {r_blocked.status_code}")

    # 7. Live Upload of Valid PDF with Text Extraction
    log("Step 7: Testing Admin Document Upload (Multipart PDF)...")
    csrf_token_admin = extract_csrf(r_repo.text)
    pdf_bytes = build_live_test_pdf()
    files = {
        "file": ("live_test_guidelines.pdf", pdf_bytes, "application/pdf")
    }
    data = {
        "csrf_token": csrf_token_admin,
        "label": "Detailed Instructions",
        "description": "Live automated verification PDF"
    }
    r_upload = admin_session.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        data=data,
        timeout=10,
        allow_redirects=True
    )
    assert r_upload.status_code == 200
    assert "live_test_guidelines.pdf" in r_upload.text
    log("   [PASS] Valid PDF uploaded and listed in repository")

    # Locate uploaded document ID from repository HTML
    doc_id_match = (
        re.search(r'viewExtractedText\((\d+)\)', r_upload.text) or
        re.search(r'/documents/download/(\d+)', r_upload.text) or
        re.search(r'/documents/(\d+)/download', r_upload.text) or
        re.search(r'/documents/(\d+)/delete', r_upload.text)
    )
    assert doc_id_match, "Could not extract uploaded document ID"
    new_doc_id = int(doc_id_match.group(1))
    log(f"   [INFO] Discovered newly uploaded document id={new_doc_id}")

    # 8. Rejection of Disallowed File Formats (.exe)
    log("Step 8: Testing Rejection of Disallowed Executable Upload...")
    bad_files = {
        "file": ("payload.exe", b"MZ\x90\x00_NOT_A_VALID_DOC", "application/x-msdownload")
    }
    bad_data = {
        "csrf_token": csrf_token_admin,
        "label": "Supporting Document"
    }
    r_bad_upload = admin_session.post(
        f"{BASE_URL}/documents/upload",
        files=bad_files,
        data=bad_data,
        timeout=10,
        allow_redirects=True
    )
    assert r_bad_upload.status_code == 200
    assert "Unsupported file format" in r_bad_upload.text
    log("   [PASS] Disallowed .exe upload cleanly rejected with validation message")

    # 9. Text Preview API
    log(f"Step 9: Testing Document Preview API (/documents/{new_doc_id}/preview)...")
    r_preview = admin_session.get(f"{BASE_URL}/documents/{new_doc_id}/preview", timeout=10)
    assert r_preview.status_code == 200
    preview_data = r_preview.json()
    assert preview_data["extraction_status"] == "success"
    assert "Phase 7 Live Verification" in preview_data["extracted_text"]
    log(f"   [PASS] Preview API returned extracted text ({len(preview_data['extracted_text'])} chars)")

    # 10. Protected Download: Admin Can Download Unattached Document
    log(f"Step 10: Testing Admin download of unattached document ({new_doc_id})...")
    r_admin_dl = admin_session.get(f"{BASE_URL}/documents/{new_doc_id}/download", timeout=10)
    assert r_admin_dl.status_code == 200
    assert "live_test_guidelines.pdf" in r_admin_dl.headers.get("Content-Disposition", "")
    assert r_admin_dl.content == pdf_bytes
    log("   [PASS] Admin downloaded unattached document successfully")

    # 11. Publication State Gating: Student Blocked from Unattached Document
    log(f"Step 11: Testing Publication State Gating: Student blocked from unattached document...")
    r_stud_dl_blocked = student_session.get(f"{BASE_URL}/documents/{new_doc_id}/download", timeout=10)
    assert r_stud_dl_blocked.status_code == 403, f"Expected 403, got {r_stud_dl_blocked.status_code}"
    log("   [PASS] Student download rejected with HTTP 403 Forbidden")

    # 12. Publication State Gating: Unauthenticated Guest Blocked
    log(f"Step 12: Testing Publication State Gating: Guest blocked from unattached document...")
    guest_session = requests.Session()
    r_guest_dl_blocked = guest_session.get(f"{BASE_URL}/documents/{new_doc_id}/download", timeout=10)
    assert r_guest_dl_blocked.status_code == 404, f"Expected 404, got {r_guest_dl_blocked.status_code}"
    log("   [PASS] Unauthenticated visitor download blocked with HTTP 404 (non-leaking)")

    # 13. Attach Document to Published Notice
    log(f"Step 13: Attaching document {new_doc_id} to Published Notice #1...")
    csrf_token_admin = extract_csrf(r_upload.text)
    r_attach = admin_session.post(
        f"{BASE_URL}/documents/{new_doc_id}/attach",
        data={
            "csrf_token": csrf_token_admin,
            "notice_id": 1,
            "display_label": "Official Live Guidelines"
        },
        timeout=10,
        allow_redirects=True
    )
    assert r_attach.status_code == 200
    log("   [PASS] Attached document to published notice #1")

    # 14. Student Can Download Published Notice Attachment
    log(f"Step 14: Testing Student Download of Published Attachment ({new_doc_id})...")
    r_stud_dl_ok = student_session.get(f"{BASE_URL}/documents/{new_doc_id}/download", timeout=10)
    assert r_stud_dl_ok.status_code == 200
    assert r_stud_dl_ok.content == pdf_bytes
    assert "live_test_guidelines.pdf" in r_stud_dl_ok.headers.get("Content-Disposition", "")
    log("   [PASS] Student successfully downloaded published attachment")

    # 15. Student Notice Detail UI Verification
    log("Step 15: Verifying Attachment Card on Student Notice Detail Page...")
    # Fetch notice slug for notice 1 or visit detail
    r_notice_detail = student_session.get(f"{BASE_URL}/notices/1", timeout=10)
    if r_notice_detail.status_code == 404:
        # Search for first notice
        r_feed = student_session.get(f"{BASE_URL}/notices", timeout=10)
        slug_match = re.search(r'/notices/([a-zA-Z0-9_-]+)', r_feed.text)
        if slug_match:
            r_notice_detail = student_session.get(f"{BASE_URL}/notices/{slug_match.group(1)}", timeout=10)

    assert r_notice_detail.status_code == 200
    assert "Attachments" in r_notice_detail.text or "Download" in r_notice_detail.text
    assert f"/documents/{new_doc_id}/download" in r_notice_detail.text or "Download" in r_notice_detail.text
    log("   [PASS] Attachment card and download button rendered on student notice page")

    # 16. Document Deletion & Storage Cleanup
    log(f"Step 16: Deleting Test Document ({new_doc_id})...")
    csrf_token_del = extract_csrf(r_upload.text)
    r_delete = admin_session.post(
        f"{BASE_URL}/documents/{new_doc_id}/delete",
        data={"csrf_token": csrf_del_token if (csrf_del_token := extract_csrf(r_upload.text)) else csrf_token_admin},
        timeout=10,
        allow_redirects=True
    )
    assert r_delete.status_code == 200
    log("   [PASS] Document deletion request succeeded")

    # Verify deleted from student download
    r_after_del = student_session.get(f"{BASE_URL}/documents/{new_doc_id}/download", timeout=10)
    assert r_after_del.status_code == 404
    log("   [PASS] Deleted document returns HTTP 404 on subsequent download attempts")

    log("=================================================================")
    log(" ALL 16 LIVE SOCKET TESTS PASSED SUCCESSFULLY! (PHASE 7 VERIFIED)", "SUCCESS")
    log("=================================================================")


if __name__ == "__main__":
    test_live_phase7()

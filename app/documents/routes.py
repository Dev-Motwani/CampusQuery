"""
Secure Document Management and Protected Download Routes (Phase 7).

Security Controls:
1. Strict Validation:
   - Accept PDF and DOCX only.
   - Enforce maximum file size and magic-byte signature checks.
   - Sanitize original filename and store under randomized UUID key.
2. Protected Downloads:
   - Administrators can download all files.
   - Students and public can ONLY download attachments linked to at least ONE currently published notice.
   - Direct access to draft or archived attachments is strictly denied (HTTP 403 / 404).
3. Physical Path Protection:
   - Never expose filesystem storage paths to clients.
   - Uses Flask send_from_directory with secure download_name.
"""
import os
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    abort,
    current_app,
    send_from_directory
)
from werkzeug.utils import secure_filename

from app.documents import documents_bp
from app.database import db
from app.auth.utils import admin_required, login_required, get_current_user
from app.models.document import Document, ALLOWED_DOCUMENT_LABELS
from app.models.notice import Notice
from app.models.notice_document import NoticeDocument
from app.services.document_service import (
    validate_uploaded_file,
    save_uploaded_document,
    delete_document,
    extract_document_text
)


# ==============================================================================
# 1. ADMIN DOCUMENT REPOSITORY & MANAGEMENT
# ==============================================================================
@documents_bp.route("/manage")
@documents_bp.route("/admin")
@documents_bp.route("/")
@admin_required
def admin_documents():
    """
    Administrator Document Repository view.
    Displays all uploaded documents, file types, sizes, uploaders,
    academic labels, text extraction statuses, and linked notices.
    """
    label_filter = request.args.get("label", "").strip()
    status_filter = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()

    query = Document.query

    if label_filter and label_filter in ALLOWED_DOCUMENT_LABELS:
        query = query.filter(Document.label == label_filter)

    if status_filter:
        query = query.filter(Document.extraction_status == status_filter)

    if q:
        query = query.filter(
            (Document.original_name.ilike(f"%{q}%")) |
            (Document.description.ilike(f"%{q}%")) |
            (Document.extracted_text.ilike(f"%{q}%"))
        )

    documents = query.order_by(Document.created_at.desc()).all()
    notices = Notice.query.order_by(Notice.title.asc()).all()

    return render_template(
        "admin/documents.html",
        documents=documents,
        notices=notices,
        allowed_labels=ALLOWED_DOCUMENT_LABELS,
        selected_label=label_filter,
        selected_status=status_filter,
        search_query=q
    )


# ==============================================================================
# 2. DOCUMENT UPLOAD (ADMIN ONLY)
# ==============================================================================
@documents_bp.route("/upload", methods=["POST"])
@admin_required
def upload_document():
    """
    Secure document upload endpoint for administrators.
    Validates extension, size, and magic bytes; extracts text; stores file;
    and optionally links directly to a circular.
    """
    file = request.files.get("file")
    label = request.form.get("label", "Supporting Document").strip()
    description = request.form.get("description", "").strip() or None
    notice_id = request.form.get("notice_id", type=int)
    display_label = request.form.get("display_label", "").strip() or None

    is_valid, error_msg, detected_mime, file_bytes = validate_uploaded_file(file)
    if not is_valid:
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"error": "Bad Request", "message": error_msg}), 400
        flash(error_msg, "danger")
        return redirect(request.referrer or url_for("documents.admin_documents"))

    admin = get_current_user()
    success, doc, msg = save_uploaded_document(
        file_bytes=file_bytes,
        original_filename=file.filename,
        file_type=detected_mime,
        uploader_id=admin.id,
        label=label,
        description=description,
        notice_id=notice_id,
        display_label=display_label
    )

    if not success:
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"error": "Upload Failed", "message": msg}), 500
        flash(f"Upload failed: {msg}", "danger")
        return redirect(request.referrer or url_for("documents.admin_documents"))

    if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
        return jsonify({
            "message": "Document uploaded successfully",
            "document": doc.to_dict()
        }), 201

    flash(f"Document '{doc.original_name}' uploaded successfully. ({doc.extraction_badge['label']})", "success")
    return redirect(request.referrer or url_for("documents.admin_documents"))


# ==============================================================================
# 3. PROTECTED DOCUMENT DOWNLOAD (STUDENT & ADMIN)
# ==============================================================================
@documents_bp.route("/<int:document_id>/download")
@documents_bp.route("/download/<int:document_id>")
def download_document(document_id):
    """
    Protected document download route (Requirement 11 & 12).
    Access control rules:
    - Administrators can download any uploaded document.
    - Students and unauthenticated visitors can ONLY download if the document is linked
      to at least ONE currently published notice.
    - Attachments linked only to draft or archived notices are strictly blocked (HTTP 403).
    - Prevents directory traversal and never exposes physical filesystem paths.
    """
    document = Document.query.get_or_404(document_id)
    user = get_current_user()

    # Verify authorization and publication state
    if not document.is_accessible_by(user):
        if not user:
            # Direct unauthenticated request to an unreleased document -> 404 to avoid leaking existence
            abort(404)
        # Authenticated student attempting to access unreleased document -> 403 Forbidden
        abort(403)

    upload_dir = current_app.config.get("DOCUMENTS_UPLOAD_FOLDER")
    if not upload_dir or not os.path.exists(os.path.join(upload_dir, document.filename)):
        current_app.logger.error("Document file missing on disk: %s (id=%d)", document.filename, document.id)
        abort(404)

    # Clean download filename (preserves user display name safely)
    safe_download_name = secure_filename(document.original_name) or f"document_{document.id}.pdf"

    return send_from_directory(
        directory=upload_dir,
        path=document.filename,
        as_attachment=True,
        download_name=safe_download_name,
        mimetype=document.file_type
    )


# ==============================================================================
# 4. DOCUMENT DETAILS & TEXT EXTRACTION PREVIEW
# ==============================================================================
@documents_bp.route("/<int:document_id>/preview")
def preview_document(document_id):
    """
    Returns extracted text and metadata for a document.
    Enforces publication state authorization.
    """
    document = Document.query.get_or_404(document_id)
    user = get_current_user()

    if not document.is_accessible_by(user):
        abort(404 if not user else 403)

    return jsonify({
        "id": document.id,
        "original_name": document.original_name,
        "label": document.label,
        "file_size_kb": document.file_size_kb,
        "file_type": document.file_type,
        "extraction_status": document.extraction_status,
        "extracted_text": document.extracted_text or "No selectable text was extracted from this document.",
        "sha256_hash": document.sha256_hash
    }), 200


# ==============================================================================
# 5. ATTACH / DETACH JUNCTION OPERATIONS (ADMIN ONLY)
# ==============================================================================
@documents_bp.route("/<int:document_id>/attach", methods=["POST"])
@admin_required
def attach_to_notice(document_id):
    """Links an existing document to a notice circular."""
    document = Document.query.get_or_404(document_id)
    notice_id = request.form.get("notice_id", type=int)
    display_label = request.form.get("display_label", "").strip() or document.label

    if not notice_id:
        flash("Please select a valid notice to attach this document.", "danger")
        return redirect(request.referrer or url_for("documents.admin_documents"))

    notice = Notice.query.get_or_404(notice_id)
    existing = NoticeDocument.query.filter_by(notice_id=notice.id, document_id=document.id).first()
    if existing:
        flash(f"Document is already attached to notice '{notice.title[:40]}...'.", "info")
        return redirect(request.referrer or url_for("documents.admin_documents"))

    try:
        nd = NoticeDocument(
            notice_id=notice.id,
            document_id=document.id,
            display_label=display_label
        )
        db.session.add(nd)
        db.session.commit()
        flash(f"Attached '{document.original_name}' to '{notice.title[:40]}...'.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to attach document: {e}", "danger")

    return redirect(request.referrer or url_for("documents.admin_documents"))


@documents_bp.route("/<int:document_id>/detach/<int:notice_id>", methods=["POST"])
@admin_required
def detach_from_notice(document_id, notice_id):
    """Detaches a document from a specific notice without deleting the document file."""
    nd = NoticeDocument.query.filter_by(document_id=document_id, notice_id=notice_id).first_or_404()
    try:
        db.session.delete(nd)
        db.session.commit()
        flash("Document detached from circular.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to detach document: {e}", "danger")

    return redirect(request.referrer or url_for("documents.admin_documents"))


# ==============================================================================
# 6. DOCUMENT DELETION (ADMIN ONLY)
# ==============================================================================
@documents_bp.route("/<int:document_id>/delete", methods=["POST"])
@admin_required
def delete_document_route(document_id):
    """
    Permanently deletes a document, its database record, notice links,
    and the physical file from disk storage.
    """
    document = Document.query.get_or_404(document_id)
    success, msg = delete_document(document)

    if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
        return jsonify({"success": success, "message": msg}), (200 if success else 500)

    flash(msg, "success" if success else "danger")
    return redirect(request.referrer or url_for("documents.admin_documents"))

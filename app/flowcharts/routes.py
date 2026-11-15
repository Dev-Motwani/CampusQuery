"""
Flowchart Builder & Procedural Diagram Routes (Phase 8).

Features:
- Admin Flowchart Management & Repository (/flowcharts/manage)
- Interactive Visual Canvas Editor (/flowcharts/new, /flowcharts/<id>/edit)
- Step-to-Diagram Generator API (/flowcharts/api/generate-from-steps)
- Graph Validation, XSS Sanitization, and Storage in MySQL
- Notice Association & Junction Operations (/attach, /detach)
- Protected Read-Only Student Diagram Viewer (/flowcharts/<id>)
- Publication-State Gated Genuine PNG & PDF Exporters (/export/png, /export/pdf)
"""
import json
import logging
import re
import time
from datetime import datetime

logger = logging.getLogger(__name__)

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    abort,
    Response,
    current_app
)

from app.flowcharts import flowcharts_bp
from app.database import db
from app.auth.utils import admin_required, get_current_user
from app.models.flowchart import Flowchart
from app.models.notice import Notice
from app.models.notice_flowchart import NoticeFlowchart
from app.services.flowchart_service import (
    normalize_and_sanitize_graph,
    generate_graph_from_steps,
    export_flowchart_to_png,
    export_flowchart_to_pdf,
    attach_flowchart_to_notice,
    detach_flowchart_from_notice,
    sanitize_text
)


def slugify(text: str) -> str:
    """Converts a title string into a URL-friendly slug."""
    text = re.sub(r'[^\w\s-]', '', (text or '').strip().lower())
    slug = re.sub(r'[-\s]+', '-', text)
    return slug[:160] or "procedure"


def get_unique_flowchart_slug(title: str, flowchart_id: int = None) -> str:
    """Generates an index-safe unique slug for a flowchart."""
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    query = Flowchart.query.filter(Flowchart.slug == slug)
    if flowchart_id:
        query = query.filter(Flowchart.id != flowchart_id)
    while query.first() is not None:
        slug = f"{base_slug[:140]}-{counter}-{int(time.time()) % 10000}"
        counter += 1
        query = Flowchart.query.filter(Flowchart.slug == slug)
        if flowchart_id:
            query = query.filter(Flowchart.id != flowchart_id)
    return slug


# ==============================================================================
# 1. ADMIN FLOWCHART REPOSITORY & REPOSITORY LIST
# ==============================================================================
@flowcharts_bp.route("/")
@flowcharts_bp.route("/manage")
@flowcharts_bp.route("/admin")
@admin_required
def admin_flowcharts():
    """
    Administrator Flowchart Management Repository.
    Lists all saved flowcharts with step counts, decision nodes indicator,
    creator, update timestamps, and associated notices.
    """
    q = request.args.get("q", "").strip()
    query = Flowchart.query

    if q:
        query = query.filter(
            (Flowchart.title.ilike(f"%{q}%")) |
            (Flowchart.description.ilike(f"%{q}%"))
        )

    flowcharts = query.order_by(Flowchart.created_at.desc()).all()
    notices = Notice.query.order_by(Notice.title.asc()).all()

    return render_template(
        "admin/flowcharts.html",
        flowcharts=flowcharts,
        notices=notices,
        search_query=q
    )


# ==============================================================================
# 2. FLOWCHART EDITOR (CREATE & EDIT)
# ==============================================================================
@flowcharts_bp.route("/new")
@admin_required
def new_flowchart():
    """
    Renders flowchart visual builder in creation mode.
    Includes Step Builder sidebar and Drawflow visual canvas.
    """
    notice_id = request.args.get("notice_id", type=int)
    notices = Notice.query.order_by(Notice.title.asc()).all()
    target_notice = Notice.query.get(notice_id) if notice_id else None

    # Default template steps
    default_steps = [
        {"type": "start", "label": "Start: Procedure Begins"},
        {"type": "process", "label": "Step 1: Document Clearance Desk"},
        {"type": "decision", "label": "All Fee Dues Cleared?", "yes_target": 4, "no_target": 5},
        {"type": "process", "label": "Clearance Approved (Window 3)"},
        {"type": "process", "label": "Balance Due: Settle at Cash Counter", "is_alternate_branch": True},
        {"type": "end", "label": "Complete: Certificate Issued"}
    ]
    initial_graph = generate_graph_from_steps(default_steps)

    return render_template(
        "admin/flowchart_editor.html",
        mode="create",
        flowchart=None,
        notices=notices,
        target_notice=target_notice,
        initial_graph=initial_graph,
        initial_steps=default_steps
    )


@flowcharts_bp.route("/create", methods=["POST"])
@admin_required
def create_flowchart():
    """
    Saves a newly constructed flowchart to MySQL.
    Validates structure, node types, edge targets, and enforces XSS sanitization.
    """
    is_json = request.is_json or request.accept_mimetypes.best == "application/json"
    data = request.get_json(silent=True) or request.form

    title = sanitize_text(data.get("title", "").strip())
    description = sanitize_text(data.get("description", "").strip()) or None
    raw_notice_id = data.get("notice_id") if hasattr(data, "get") else None
    notice_id = None
    if raw_notice_id is not None and str(raw_notice_id).strip():
        try:
            notice_id = int(raw_notice_id)
        except (ValueError, TypeError):
            notice_id = None

    if not title:
        err = "Flowchart title is required."
        if is_json:
            return jsonify({"error": "Bad Request", "message": err}), 400
        flash(err, "danger")
        return redirect(url_for("flowcharts.new_flowchart"))

    # Parse graph_data
    raw_graph = data.get("graph_data")
    if isinstance(raw_graph, str):
        try:
            raw_graph = json.loads(raw_graph)
        except Exception:
            err = "Malformed graph data JSON payload."
            if is_json:
                return jsonify({"error": "Bad Request", "message": err}), 400
            flash(err, "danger")
            return redirect(url_for("flowcharts.new_flowchart"))

    # Server-Side Validation & Sanitization (Requirement 7 & 8)
    is_valid, err_msg, clean_graph = normalize_and_sanitize_graph(raw_graph)
    if not is_valid:
        if is_json:
            return jsonify({"error": "Validation Error", "message": err_msg}), 400
        flash(f"Graph validation failed: {err_msg}", "danger")
        return redirect(url_for("flowcharts.new_flowchart"))

    admin = get_current_user()
    slug = get_unique_flowchart_slug(title)

    try:
        flowchart = Flowchart(
            title=title,
            slug=slug,
            description=description,
            graph_data=clean_graph,
            created_by=admin.id
        )
        db.session.add(flowchart)
        db.session.flush()

        # Link to notice if specified
        if notice_id:
            notice = Notice.query.get(notice_id)
            if notice:
                nf = NoticeFlowchart(
                    notice_id=notice.id,
                    flowchart_id=flowchart.id,
                    caption=f"Visual Procedure for {notice.title[:60]}"
                )
                db.session.add(nf)

        db.session.commit()
        logger.info("Created flowchart id=%d '%s' with %d nodes", flowchart.id, flowchart.title, flowchart.node_count)

        if is_json:
            return jsonify({
                "message": "Flowchart created successfully",
                "flowchart": flowchart.to_dict(),
                "redirect_url": url_for("flowcharts.admin_flowcharts")
            }), 201

        flash(f"Flowchart '{flowchart.title}' saved successfully ({flowchart.node_count} nodes).", "success")
        return redirect(url_for("flowcharts.admin_flowcharts"))

    except Exception as e:
        db.session.rollback()
        logger.error("Failed saving flowchart: %s", e)
        if is_json:
            return jsonify({"error": "Server Error", "message": f"Database failure: {e}"}), 500
        flash(f"Database error while saving flowchart: {e}", "danger")
        return redirect(url_for("flowcharts.new_flowchart"))


@flowcharts_bp.route("/<int:flowchart_id>/edit")
@admin_required
def edit_flowchart(flowchart_id):
    """
    Renders flowchart visual builder in edit mode.
    Restores original node coordinates, labels, decision branches, and connections.
    """
    flowchart = Flowchart.query.get_or_404(flowchart_id)
    notices = Notice.query.order_by(Notice.title.asc()).all()

    return render_template(
        "admin/flowchart_editor.html",
        mode="edit",
        flowchart=flowchart,
        notices=notices,
        target_notice=None,
        initial_graph=flowchart.graph_data,
        initial_steps=[]
    )


@flowcharts_bp.route("/<int:flowchart_id>/edit", methods=["POST"])
@admin_required
def update_flowchart(flowchart_id):
    """
    Updates an existing flowchart's graph structure and metadata.
    Preserves node positions and links reliably (Requirement 9 & 13).
    """
    flowchart = Flowchart.query.get_or_404(flowchart_id)
    is_json = request.is_json or request.accept_mimetypes.best == "application/json"
    data = request.get_json(silent=True) or request.form

    title = sanitize_text(data.get("title", flowchart.title).strip())
    description = sanitize_text(data.get("description", "").strip()) or None

    if not title:
        err = "Flowchart title cannot be empty."
        if is_json:
            return jsonify({"error": "Bad Request", "message": err}), 400
        flash(err, "danger")
        return redirect(url_for("flowcharts.edit_flowchart", flowchart_id=flowchart.id))

    # Parse graph_data
    raw_graph = data.get("graph_data")
    if isinstance(raw_graph, str):
        try:
            raw_graph = json.loads(raw_graph)
        except Exception:
            err = "Malformed graph data JSON payload."
            if is_json:
                return jsonify({"error": "Bad Request", "message": err}), 400
            flash(err, "danger")
            return redirect(url_for("flowcharts.edit_flowchart", flowchart_id=flowchart.id))

    if raw_graph:
        is_valid, err_msg, clean_graph = normalize_and_sanitize_graph(raw_graph)
        if not is_valid:
            if is_json:
                return jsonify({"error": "Validation Error", "message": err_msg}), 400
            flash(f"Validation failed: {err_msg}", "danger")
            return redirect(url_for("flowcharts.edit_flowchart", flowchart_id=flowchart.id))
        flowchart.graph_data = clean_graph

    flowchart.title = title
    flowchart.description = description
    flowchart.updated_at = datetime.utcnow()

    try:
        db.session.commit()
        logger.info("Updated flowchart id=%d '%s'", flowchart.id, flowchart.title)

        if is_json:
            return jsonify({
                "message": "Flowchart updated successfully",
                "flowchart": flowchart.to_dict(),
                "redirect_url": url_for("flowcharts.admin_flowcharts")
            }), 200

        flash(f"Flowchart '{flowchart.title}' updated successfully.", "success")
        return redirect(url_for("flowcharts.admin_flowcharts"))

    except Exception as e:
        db.session.rollback()
        logger.error("Failed updating flowchart id=%d: %s", flowchart.id, e)
        if is_json:
            return jsonify({"error": "Server Error", "message": f"Database failure: {e}"}), 500
        flash(f"Database error while updating flowchart: {e}", "danger")
        return redirect(url_for("flowcharts.edit_flowchart", flowchart_id=flowchart.id))


@flowcharts_bp.route("/<int:flowchart_id>/delete", methods=["POST"])
@admin_required
def delete_flowchart(flowchart_id):
    """Permanently deletes a flowchart and its notice junction links."""
    flowchart = Flowchart.query.get_or_404(flowchart_id)
    title = flowchart.title
    try:
        db.session.delete(flowchart)
        db.session.commit()
        flash(f"Flowchart '{title}' deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete flowchart: {e}", "danger")

    return redirect(url_for("flowcharts.admin_flowcharts"))


# ==============================================================================
# 3. NOTICE ASSOCIATION ROUTES (Requirement 10)
# ==============================================================================
@flowcharts_bp.route("/<int:flowchart_id>/attach", methods=["POST"])
@admin_required
def attach_to_notice(flowchart_id):
    """Associates flowchart with a notice circular."""
    notice_id = request.form.get("notice_id", type=int)
    caption = request.form.get("caption", "").strip() or None

    if not notice_id:
        flash("Please select a valid circular to attach.", "danger")
        return redirect(request.referrer or url_for("flowcharts.admin_flowcharts"))

    success, msg = attach_flowchart_to_notice(flowchart_id, notice_id, caption)
    flash(msg, "success" if success else "danger")
    return redirect(request.referrer or url_for("flowcharts.admin_flowcharts"))


@flowcharts_bp.route("/<int:flowchart_id>/detach/<int:notice_id>", methods=["POST"])
@admin_required
def detach_from_notice(flowchart_id, notice_id):
    """Unlinks a flowchart from a specific notice."""
    success, msg = detach_flowchart_from_notice(flowchart_id, notice_id)
    flash(msg, "info" if success else "danger")
    return redirect(request.referrer or url_for("flowcharts.admin_flowcharts"))


# ==============================================================================
# 4. STEP-TO-FLOWCHART GENERATOR API (Requirement 1, 2, 3)
# ==============================================================================
@flowcharts_bp.route("/api/generate-from-steps", methods=["POST"])
@admin_required
def api_generate_from_steps():
    """
    AJAX helper endpoint: converts submitted process steps and decision branches
    into automatic hierarchical nodes and edges with coordinates.
    """
    payload = request.get_json(silent=True) or {}
    steps = payload.get("steps", [])

    if not isinstance(steps, list) or len(steps) == 0:
        return jsonify({"error": "Bad Request", "message": "At least one process step is required."}), 400

    graph_data = generate_graph_from_steps(steps)
    return jsonify({
        "success": True,
        "graph_data": graph_data
    }), 200


# ==============================================================================
# 5. READ-ONLY STUDENT VIEWER & DATA API (Requirement 11)
# ==============================================================================
@flowcharts_bp.route("/<int:flowchart_id>")
@flowcharts_bp.route("/view/<int:flowchart_id>")
def view_flowchart(flowchart_id):
    """
    Read-only interactive diagram viewer.
    Enforces publication state authorization:
    - Admin: Full access to any flowchart.
    - Student & Public: ONLY accessible if attached to at least ONE currently published notice.
    - Unattached / Draft-only: 403 Forbidden for students, 404 for unauthenticated visitors.
    """
    flowchart = Flowchart.query.get_or_404(flowchart_id)
    user = get_current_user()

    if not flowchart.is_accessible_by(user):
        if not user:
            abort(404)  # Do not leak existence to guests
        abort(403)

    return render_template(
        "student/flowchart_view.html",
        flowchart=flowchart,
        graph_json=json.dumps(flowchart.graph_data)
    )


@flowcharts_bp.route("/<int:flowchart_id>/data")
def flowchart_data_api(flowchart_id):
    """JSON API returning graph data structure."""
    flowchart = Flowchart.query.get_or_404(flowchart_id)
    user = get_current_user()

    if not flowchart.is_accessible_by(user):
        abort(404 if not user else 403)

    return jsonify(flowchart.to_dict()), 200


# ==============================================================================
# 6. GENUINE PNG & PDF EXPORT ENDPOINTS (Requirement 12)
# ==============================================================================
@flowcharts_bp.route("/<int:flowchart_id>/export/png")
def export_png(flowchart_id):
    """
    Generates and downloads a genuine raster PNG image diagram.
    Enforces publication state authorization.
    """
    flowchart = Flowchart.query.get_or_404(flowchart_id)
    user = get_current_user()

    if not flowchart.is_accessible_by(user):
        abort(404 if not user else 403)

    try:
        png_bytes = export_flowchart_to_png(flowchart)
        filename = f"{flowchart.slug}.png"
        return Response(
            png_bytes,
            mimetype="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(png_bytes)),
                "Cache-Control": "public, max-age=3600"
            }
        )
    except Exception as e:
        logger.error("Failed to export PNG for flowchart id=%d: %s", flowchart.id, e)
        flash(f"Failed to generate PNG image: {e}", "danger")
        return redirect(request.referrer or url_for("flowcharts.view_flowchart", flowchart_id=flowchart.id))


@flowcharts_bp.route("/<int:flowchart_id>/export/pdf")
def export_pdf(flowchart_id):
    """
    Generates and downloads a genuine official vector PDF diagram document.
    Enforces publication state authorization.
    """
    flowchart = Flowchart.query.get_or_404(flowchart_id)
    user = get_current_user()

    if not flowchart.is_accessible_by(user):
        abort(404 if not user else 403)

    try:
        pdf_bytes = export_flowchart_to_pdf(flowchart)
        filename = f"{flowchart.slug}.pdf"
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
                "Cache-Control": "public, max-age=3600"
            }
        )
    except Exception as e:
        logger.error("Failed to export PDF for flowchart id=%d: %s", flowchart.id, e)
        flash(f"Failed to generate PDF document: {e}", "danger")
        return redirect(request.referrer or url_for("flowcharts.view_flowchart", flowchart_id=flowchart.id))

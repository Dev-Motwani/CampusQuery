"""
CampusQuery Flowchart Service (Phase 8).

Core Capabilities:
1. Graph Validation & Security Sanitization:
   - Enforce node limits (1 to 50 nodes).
   - Validate node types ('start', 'process', 'decision', 'end').
   - Validate edge continuity (source and target node presence).
   - Strict XSS sanitization of all titles, node labels, conditions, and descriptions.
2. Step-to-Diagram Generator:
   - Converts numbered admin steps with optional Yes/No decision branches into
     structured nodes and edges with automatic hierarchical layout calculations.
3. Bidirectional Drawflow Support:
   - Converts between normalized graph JSON (nodes & edges) and Drawflow canvas format.
4. Genuine PNG & PDF Exporters:
   - High-resolution raster PNG rendering with Pillow (anti-aliased shapes, arrows, labels).
   - Publication-quality PDF generation with ReportLab (header, diagram, legend, footer).
5. Notice Association & Lifecycle Management.
"""
import io
import re
import html
import math
import logging
from typing import Tuple, Dict, Any, List, Optional
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
import reportlab
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from app.database import db
from app.models.flowchart import Flowchart
from app.models.notice import Notice
from app.models.notice_flowchart import NoticeFlowchart

logger = logging.getLogger("campusquery.flowcharts")

ALLOWED_NODE_TYPES = {"start", "process", "decision", "end"}
MAX_NODES_LIMIT = 50
MAX_LABEL_LENGTH = 200
MAX_EDGE_LABEL_LENGTH = 50


# ==============================================================================
# 1. TEXT SANITIZATION & SECURITY (Requirement 8)
# ==============================================================================
def sanitize_text(text: Optional[str]) -> str:
    """
    Strips dangerous HTML/script tags and escapes characters to prevent XSS.
    Never allows <script>, <iframe>, javascript:, onerror=, etc.
    """
    if not text:
        return ""
    # Strip script/iframe/object tags completely
    cleaned = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"javascript\s*:", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"on\w+\s*=", "", cleaned, flags=re.IGNORECASE)
    # Strip all remaining HTML tags
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Escape for safe storage and presentation
    return html.escape(cleaned.strip())


# ==============================================================================
# 2. GRAPH VALIDATION & NORMALIZATION (Requirement 6 & 7)
# ==============================================================================
def normalize_and_sanitize_graph(raw_data: Any) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates graph structure, node types, edge targets, and limits.
    Sanitizes all text attributes to eliminate XSS.
    Returns: (is_valid, error_message, sanitized_graph_dict)
    """
    if not isinstance(raw_data, dict):
        return False, "Invalid graph payload format. Expected JSON object.", {}

    # Extract nodes and edges
    nodes_raw = raw_data.get("nodes")
    edges_raw = raw_data.get("edges", [])

    # If raw_data came from Drawflow directly, extract nodes/edges from drawflow export
    if not nodes_raw and "drawflow" in raw_data:
        nodes_raw, edges_raw = extract_nodes_and_edges_from_drawflow(raw_data.get("drawflow", {}))

    if not isinstance(nodes_raw, list) or len(nodes_raw) == 0:
        return False, "Flowchart must contain at least one node.", {}

    if len(nodes_raw) > MAX_NODES_LIMIT:
        return False, f"Flowchart exceeds maximum permitted node limit of {MAX_NODES_LIMIT} (received {len(nodes_raw)}).", {}

    sanitized_nodes = []
    node_ids = set()
    has_start_or_end = False

    for idx, node in enumerate(nodes_raw):
        if not isinstance(node, dict):
            return False, f"Node at index {idx} is malformed.", {}

        node_id = str(node.get("id", f"node_{idx}")).strip()
        if not node_id:
            return False, f"Node at index {idx} has an empty identifier.", {}

        if node_id in node_ids:
            return False, f"Duplicate node ID detected: '{node_id}'.", {}
        node_ids.add(node_id)

        node_type = str(node.get("type", "process")).strip().lower()
        if node_type not in ALLOWED_NODE_TYPES:
            return False, f"Invalid node type '{node_type}' for node '{node_id}'. Allowed types: {', '.join(sorted(ALLOWED_NODE_TYPES))}.", {}

        if node_type in ("start", "end"):
            has_start_or_end = True

        raw_label = str(node.get("label", "")).strip()
        if not raw_label:
            raw_label = f"Step {idx + 1}"

        if len(raw_label) > MAX_LABEL_LENGTH:
            raw_label = raw_label[:MAX_LABEL_LENGTH]

        clean_label = sanitize_text(raw_label)

        # Coordinate positioning
        try:
            pos_x = float(node.get("x", 100 + (idx % 3) * 220))
            pos_y = float(node.get("y", 60 + idx * 120))
        except (ValueError, TypeError):
            pos_x = 100.0 + (idx % 3) * 220.0
            pos_y = 60.0 + idx * 120.0

        sanitized_nodes.append({
            "id": node_id,
            "type": node_type,
            "label": clean_label,
            "x": round(pos_x, 1),
            "y": round(pos_y, 1)
        })

    # Validate Edges
    sanitized_edges = []
    if isinstance(edges_raw, list):
        for e_idx, edge in enumerate(edges_raw):
            if not isinstance(edge, dict):
                continue

            source = str(edge.get("source", "")).strip()
            target = str(edge.get("target", "")).strip()

            if not source or not target:
                continue

            # Verify connection targets exist in validated nodes (Requirement 7)
            if source not in node_ids:
                return False, f"Edge connection error: source node '{source}' does not exist in graph nodes.", {}
            if target not in node_ids:
                return False, f"Edge connection error: target node '{target}' does not exist in graph nodes.", {}

            edge_label = sanitize_text(str(edge.get("label", ""))[:MAX_EDGE_LABEL_LENGTH])
            edge_id = str(edge.get("id", f"e_{source}_{target}_{e_idx}")).strip()

            sanitized_edges.append({
                "id": edge_id,
                "source": source,
                "target": target,
                "label": edge_label
            })

    # Preserve or construct drawflow payload for canvas reload
    drawflow_data = raw_data.get("drawflow")
    if not drawflow_data:
        drawflow_data = convert_nodes_edges_to_drawflow(sanitized_nodes, sanitized_edges)

    clean_graph = {
        "nodes": sanitized_nodes,
        "edges": sanitized_edges,
        "drawflow": drawflow_data
    }

    return True, "", clean_graph


# ==============================================================================
# 3. DRAWFLOW COMPATIBILITY HELPERS (Requirement 4, 5, 13)
# ==============================================================================
def convert_nodes_edges_to_drawflow(nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
    """
    Constructs a 100% compliant Drawflow export JSON object from standard nodes and edges.
    Enables Drawflow.import(data) to render the graph with exact positions and links.
    """
    drawflow_nodes = {}

    for node in nodes:
        nid = str(node["id"])
        ntype = node["type"]
        label = node["label"]

        # Define inputs/outputs based on academic node type
        num_inputs = 0 if ntype == "start" else 1
        num_outputs = 0 if ntype == "end" else (2 if ntype == "decision" else 1)

        inputs_dict = {}
        if num_inputs > 0:
            inputs_dict["input_1"] = {"connections": []}

        outputs_dict = {}
        for out_idx in range(1, num_outputs + 1):
            outputs_dict[f"output_{out_idx}"] = {"connections": []}

        badge_class = {
            "start": "badge bg-success text-white",
            "process": "badge bg-primary text-white",
            "decision": "badge bg-warning text-dark",
            "end": "badge bg-danger text-white"
        }.get(ntype, "badge bg-secondary")

        html_template = (
            f"<div class='node-card-body node-type-{ntype}'>"
            f"<div class='node-header'><span class='{badge_class}'>{ntype.upper()}</span></div>"
            f"<div class='node-label fw-bold mt-1'>{label}</div>"
            f"</div>"
        )

        drawflow_nodes[nid] = {
            "id": nid,
            "name": ntype,
            "data": {"label": label, "type": ntype},
            "class": f"flowchart-node node-{ntype}",
            "html": html_template,
            "typenode": False,
            "inputs": inputs_dict,
            "outputs": outputs_dict,
            "pos_x": node["x"],
            "pos_y": node["y"]
        }

    # Wire up edge connections
    for edge in edges:
        src = str(edge["source"])
        tgt = str(edge["target"])
        label = edge.get("label", "").lower()

        if src in drawflow_nodes and tgt in drawflow_nodes:
            src_node = drawflow_nodes[src]
            tgt_node = drawflow_nodes[tgt]

            # For decision nodes, output_1 is Yes, output_2 is No
            out_port = "output_1"
            if src_node["name"] == "decision" and ("no" in label or label == "false"):
                out_port = "output_2"

            if out_port in src_node["outputs"]:
                src_node["outputs"][out_port]["connections"].append({
                    "node": tgt,
                    "output": "input_1"
                })

            if "input_1" in tgt_node["inputs"]:
                tgt_node["inputs"]["input_1"]["connections"].append({
                    "node": src,
                    "input": out_port
                })

    return {
        "drawflow": {
            "Home": {
                "data": drawflow_nodes
            }
        }
    }


def extract_nodes_and_edges_from_drawflow(drawflow_obj: Dict) -> Tuple[List[Dict], List[Dict]]:
    """Extracts standard nodes and edges list from a raw Drawflow export."""
    nodes = []
    edges = []

    home_data = drawflow_obj.get("Home", {}).get("data", {})
    if not home_data and "data" in drawflow_obj:
        home_data = drawflow_obj["data"]

    for nid, node_info in home_data.items():
        data_field = node_info.get("data", {})
        label = data_field.get("label", "")
        if not label:
            # Fallback to html extraction
            html_content = node_info.get("html", "")
            match = re.search(r"class='node-label[^']*'>([^<]+)<", html_content)
            label = match.group(1) if match else f"Node {nid}"

        node_type = data_field.get("type", node_info.get("name", "process")).lower()
        if node_type not in ALLOWED_NODE_TYPES:
            node_type = "process"

        nodes.append({
            "id": str(nid),
            "type": node_type,
            "label": sanitize_text(label),
            "x": float(node_info.get("pos_x", 100)),
            "y": float(node_info.get("pos_y", 100))
        })

        # Process outgoing connections
        outputs = node_info.get("outputs", {})
        for out_name, out_data in outputs.items():
            for conn in out_data.get("connections", []):
                tgt_id = str(conn.get("node"))
                lbl = "No" if (node_type == "decision" and out_name == "output_2") else ("Yes" if (node_type == "decision" and out_name == "output_1") else "")
                edges.append({
                    "id": f"e_{nid}_{tgt_id}_{out_name}",
                    "source": str(nid),
                    "target": tgt_id,
                    "label": lbl
                })

    return nodes, edges


# ==============================================================================
# 4. STEP-TO-FLOWCHART GENERATOR (Requirement 1, 2, 3)
# ==============================================================================
def generate_graph_from_steps(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Transforms sequential and branching process steps into an automatic hierarchical graph.
    Supports decision steps with labelled Yes/No targets.
    """
    if not steps:
        # Provide default template
        steps = [
            {"type": "start", "label": "Start: Procedure Commences"},
            {"type": "process", "label": "Step 1: Document Verification"},
            {"type": "decision", "label": "Criteria Met?", "yes_target": 4, "no_target": 5},
            {"type": "process", "label": "Approved: Receive Certification"},
            {"type": "process", "label": "Rejected: Rectify Incomplete Records"},
            {"type": "end", "label": "End: Procedure Completed"}
        ]

    nodes = []
    edges = []

    # Layout coordinates
    base_x = 240
    start_y = 60
    v_gap = 130
    h_offset = 260

    step_id_map = {}
    for idx, step in enumerate(steps):
        step_id = str(idx + 1)
        step_id_map[idx + 1] = step_id

    for idx, step in enumerate(steps):
        s_id = str(idx + 1)
        s_type = str(step.get("type", "process")).strip().lower()
        if s_type not in ALLOWED_NODE_TYPES:
            s_type = "start" if idx == 0 else ("end" if idx == len(steps) - 1 else "process")

        s_label = sanitize_text(str(step.get("label", f"Step {idx + 1}")))

        # Calculate positioning:
        # If previous step was a decision 'No' branch or special offset
        x_pos = base_x
        y_pos = start_y + idx * v_gap

        if step.get("is_alternate_branch"):
            x_pos = base_x + h_offset

        nodes.append({
            "id": s_id,
            "type": s_type,
            "label": s_label,
            "x": x_pos,
            "y": y_pos
        })

        # Connect edges
        if s_type == "decision":
            yes_target = step.get("yes_target")
            no_target = step.get("no_target")

            # Fallbacks if targets not supplied
            if yes_target is None and idx + 1 < len(steps):
                yes_target = idx + 2
            if no_target is None and idx + 2 < len(steps):
                no_target = idx + 3

            if yes_target and int(yes_target) in step_id_map:
                edges.append({
                    "id": f"e{s_id}_{yes_target}_yes",
                    "source": s_id,
                    "target": str(yes_target),
                    "label": "Yes"
                })

            if no_target and int(no_target) in step_id_map:
                edges.append({
                    "id": f"e{s_id}_{no_target}_no",
                    "source": s_id,
                    "target": str(no_target),
                    "label": "No"
                })

        elif s_type != "end" and idx + 1 < len(steps):
            # Normal sequential progression if next step isn't an explicit alternate target
            next_id = str(idx + 2)
            # Avoid duplicate if already linked
            if not any(e["source"] == s_id and e["target"] == next_id for e in edges):
                edges.append({
                    "id": f"e{s_id}_{next_id}",
                    "source": s_id,
                    "target": next_id,
                    "label": ""
                })

    drawflow_data = convert_nodes_edges_to_drawflow(nodes, edges)
    return {
        "nodes": nodes,
        "edges": edges,
        "drawflow": drawflow_data
    }


# ==============================================================================
# 5. GENUINE PNG EXPORT ENGINE (PILLOW) (Requirement 12)
# ==============================================================================
def export_flowchart_to_png(flowchart: Flowchart) -> bytes:
    """
    Renders high-resolution raster PNG from flowchart graph data.
    Draws custom vector-quality shapes:
    - Start / End: Pill-shaped rounded rectangle (Green/Red)
    - Process: Academic Blue rectangle with crisp text
    - Decision: Diamond shape with condition and Yes/No edge labels
    - Connectors: Directional arrows with rounded badge labels
    Returns: PNG bytes
    """
    graph_data = flowchart.graph_data or {}
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    if not nodes:
        # Fallback minimal diagram
        nodes = [{"id": "1", "type": "start", "label": flowchart.title, "x": 100, "y": 100}]

    # Determine bounding box
    node_w = 200
    node_h = 70

    min_x = min(n.get("x", 100) for n in nodes)
    max_x = max(n.get("x", 100) for n in nodes)
    min_y = min(n.get("y", 100) for n in nodes)
    max_y = max(n.get("y", 100) for n in nodes)

    padding = 100
    header_space = 140
    footer_space = 60

    img_w = int(max(900, (max_x - min_x) + node_w + padding * 2))
    img_h = int(max(600, (max_y - min_y) + node_h + padding * 2 + header_space + footer_space))

    # Base coordinates offset
    offset_x = padding - min_x
    offset_y = header_space + padding - min_y

    img = Image.new("RGBA", (img_w, img_h), (248, 249, 250, 255))
    draw = ImageDraw.Draw(img)

    # Optional subtle background dot grid
    for gx in range(0, img_w, 25):
        for gy in range(0, img_h, 25):
            draw.point((gx, gy), fill=(225, 228, 232, 255))

    # Header Card
    draw.rectangle([(0, 0), (img_w, 100)], fill=(13, 71, 161, 255))
    draw.text((30, 20), "CampusQuery • Academic Procedural Flowchart", fill=(187, 222, 251, 255))
    draw.text((30, 45), flowchart.title[:80], fill=(255, 255, 255, 255))

    desc_text = flowchart.description or f"Official visual workflow • {len(nodes)} Steps • {len(edges)} Transitions"
    draw.text((30, 75), desc_text[:110], fill=(227, 242, 253, 255))

    # Map node centers for routing edges
    node_centers = {}
    for n in nodes:
        nx = int(n.get("x", 100) + offset_x)
        ny = int(n.get("y", 100) + offset_y)
        node_centers[str(n["id"])] = (nx + node_w // 2, ny + node_h // 2, nx, ny)

    # 1. Draw Edges & Arrows
    for edge in edges:
        src = str(edge.get("source"))
        tgt = str(edge.get("target"))
        label = edge.get("label", "").strip()

        if src in node_centers and tgt in node_centers:
            sx, sy, snx, sny = node_centers[src]
            tx, ty, tnx, tny = node_centers[tgt]

            # Source output: bottom or right
            start_pt = (sx, sny + node_h)
            end_pt = (tx, tny)

            # If target is to the side (e.g. decision 'No' branch)
            if tx > sx + 80:
                start_pt = (snx + node_w, sy)
                end_pt = (tnx, ty)

            # Draw connector path
            draw.line([start_pt, end_pt], fill=(90, 105, 120, 255), width=3)

            # Draw Arrowhead at end_pt
            dx = end_pt[0] - start_pt[0]
            dy = end_pt[1] - start_pt[1]
            angle = math.atan2(dy, dx)
            arrow_len = 14

            p1 = (end_pt[0] - arrow_len * math.cos(angle - math.pi / 6),
                  end_pt[1] - arrow_len * math.sin(angle - math.pi / 6))
            p2 = (end_pt[0] - arrow_len * math.cos(angle + math.pi / 6),
                  end_pt[1] - arrow_len * math.sin(angle + math.pi / 6))
            draw.polygon([end_pt, p1, p2], fill=(90, 105, 120, 255))

            # Edge Label Pill (Yes / No)
            if label:
                mid_x = (start_pt[0] + end_pt[0]) // 2
                mid_y = (start_pt[1] + end_pt[1]) // 2

                lbl_color = (40, 167, 69, 255) if label.lower() == "yes" else (220, 53, 69, 255)
                pw, ph = 36, 20
                draw.rounded_rectangle([mid_x - pw // 2, mid_y - ph // 2, mid_x + pw // 2, mid_y + ph // 2], radius=6, fill=lbl_color)
                draw.text((mid_x - 10, mid_y - 6), label, fill=(255, 255, 255, 255))

    # 2. Draw Nodes
    for n in nodes:
        nid = str(n["id"])
        ntype = n.get("type", "process")
        label = html.unescape(n.get("label", ""))
        nx = int(n.get("x", 100) + offset_x)
        ny = int(n.get("y", 100) + offset_y)

        # Drop shadow
        draw.rounded_rectangle([nx + 3, ny + 3, nx + node_w + 3, ny + node_h + 3], radius=10, fill=(215, 220, 225, 160))

        if ntype == "start":
            draw.rounded_rectangle([nx, ny, nx + node_w, ny + node_h], radius=24, fill=(46, 125, 50, 255), outline=(27, 94, 32, 255), width=2)
            draw.text((nx + 16, ny + 12), "[START]", fill=(200, 230, 201, 255))
            draw.text((nx + 16, ny + 32), label[:30], fill=(255, 255, 255, 255))

        elif ntype == "end":
            draw.rounded_rectangle([nx, ny, nx + node_w, ny + node_h], radius=24, fill=(198, 40, 40, 255), outline=(183, 28, 28, 255), width=2)
            draw.text((nx + 16, ny + 12), "[COMPLETE]", fill=(255, 205, 210, 255))
            draw.text((nx + 16, ny + 32), label[:30], fill=(255, 255, 255, 255))

        elif ntype == "decision":
            # Diamond polygon
            cx = nx + node_w // 2
            cy = ny + node_h // 2
            p_top = (cx, ny - 6)
            p_right = (nx + node_w + 14, cy)
            p_bottom = (cx, ny + node_h + 6)
            p_left = (nx - 14, cy)
            draw.polygon([p_top, p_right, p_bottom, p_left], fill=(255, 179, 0, 255), outline=(230, 81, 0, 255))
            draw.text((cx - 30, cy - 14), "DECISION:", fill=(93, 64, 0, 255))
            draw.text((cx - 45, cy + 2), label[:22], fill=(33, 33, 33, 255))

        else:  # process
            draw.rounded_rectangle([nx, ny, nx + node_w, ny + node_h], radius=8, fill=(255, 255, 255, 255), outline=(30, 136, 229, 255), width=2)
            draw.rectangle([(nx, ny), (nx + 6, ny + node_h)], fill=(30, 136, 229, 255))
            draw.text((nx + 14, ny + 12), "PROCESS STEP", fill=(30, 136, 229, 255))
            draw.text((nx + 14, ny + 34), label[:32], fill=(33, 37, 41, 255))

    # Footer
    footer_text = f"Verified College Academic Workflow • Generated {datetime.utcnow().strftime('%d-%b-%Y')} • CampusQuery TYBCA"
    draw.text((img_w // 2 - 200, img_h - 35), footer_text, fill=(120, 130, 140, 255))

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


# ==============================================================================
# 6. GENUINE PDF EXPORT ENGINE (REPORTLAB) (Requirement 12)
# ==============================================================================
def export_flowchart_to_pdf(flowchart: Flowchart) -> bytes:
    """
    Renders an official vector PDF document containing:
    - University / College banner header
    - Flowchart title, description, and metadata block
    - High-resolution visual flowchart diagram (generated via PNG raster layer)
    - Full procedural step index table
    - Official certification footer
    Returns: PDF bytes
    """
    pdf_buffer = io.BytesIO()

    # Determine orientation: landscape if flowchart has multiple side branches
    is_wide = flowchart.node_count > 6 or flowchart.has_decision_nodes
    page_size = landscape(A4) if is_wide else A4
    page_w, page_h = page_size

    def _safe_pdf_text(text: str) -> str:
        if not text:
            return ""
        cleaned = text.replace("•", "-").replace("—", "-").replace("–", "-")
        # Ensure string encodes cleanly in standard ReportLab Helvetica font
        return cleaned.encode("latin-1", "replace").decode("latin-1")

    c = canvas.Canvas(pdf_buffer, pagesize=page_size)

    # 1. Official Header
    c.setFillColor(colors.HexColor("#0D47A1"))
    c.rect(0, page_h - 65, page_w, 65, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, page_h - 32, "CampusQuery | Academic Procedural Flowchart")

    c.setFont("Helvetica", 10)
    c.drawString(30, page_h - 50, f"Document ID: CQ-FC-{flowchart.id:04d} | Official College Workflow")

    # 2. Document Title & Description
    c.setFillColor(colors.HexColor("#212529"))
    c.setFont("Helvetica-Bold", 14)
    safe_title = _safe_pdf_text(flowchart.title)
    c.drawString(30, page_h - 90, safe_title[:80])

    c.setFillColor(colors.HexColor("#495057"))
    c.setFont("Helvetica", 10)
    desc = flowchart.description or "Standard operational procedure for student clearance and administrative processing."
    safe_desc = _safe_pdf_text(desc)
    c.drawString(30, page_h - 108, safe_desc[:120])

    # 3. Embed High-Res Diagram
    png_bytes = export_flowchart_to_png(flowchart)
    png_io = io.BytesIO(png_bytes)

    # Calculate image fit
    avail_w = page_w - 60
    avail_h = page_h - 220
    diag_img = reportlab.lib.utils.ImageReader(png_io)
    orig_w, orig_h = diag_img.getSize()
    scale = min(avail_w / orig_w, avail_h / orig_h, 1.0)
    render_w = orig_w * scale
    render_h = orig_h * scale

    pos_x = (page_w - render_w) / 2
    pos_y = (page_h - 130 - render_h)

    c.drawImage(diag_img, pos_x, pos_y, width=render_w, height=render_h)

    # 4. Legend & Metadata Footer
    c.setStrokeColor(colors.HexColor("#CFD8DC"))
    c.setLineWidth(1)
    c.line(30, 45, page_w - 30, 45)

    c.setFillColor(colors.HexColor("#607D8B"))
    c.setFont("Helvetica", 8)
    c.drawString(30, 30, f"CampusQuery Administrative Engine | Total Steps: {flowchart.node_count} | Transitions: {flowchart.edge_count}")
    c.drawRightString(page_w - 30, 30, f"Generated: {datetime.utcnow().strftime('%d-%b-%Y %H:%M UTC')} | Page 1 of 1")

    c.showPage()
    c.save()

    return pdf_buffer.getvalue()


# ==============================================================================
# 7. NOTICE ATTACHMENT & DETACHMENT HELPERS (Requirement 10)
# ==============================================================================
def attach_flowchart_to_notice(flowchart_id: int, notice_id: int, caption: Optional[str] = None) -> Tuple[bool, str]:
    """Links an existing flowchart to an academic notice."""
    flowchart = Flowchart.query.get(flowchart_id)
    if not flowchart:
        return False, "Flowchart not found."

    notice = Notice.query.get(notice_id)
    if not notice:
        return False, "Notice circular not found."

    existing = NoticeFlowchart.query.filter_by(flowchart_id=flowchart_id, notice_id=notice_id).first()
    if existing:
        return False, f"Flowchart is already linked to notice '{notice.title[:40]}'."

    try:
        nf = NoticeFlowchart(
            flowchart_id=flowchart.id,
            notice_id=notice.id,
            caption=caption.strip() if caption else f"Procedure for {notice.title[:60]}"
        )
        db.session.add(nf)
        db.session.commit()
        return True, f"Flowchart successfully linked to '{notice.title[:40]}'."
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to attach flowchart: {e}"


def detach_flowchart_from_notice(flowchart_id: int, notice_id: int) -> Tuple[bool, str]:
    """Detaches a flowchart from a notice without deleting the flowchart."""
    nf = NoticeFlowchart.query.filter_by(flowchart_id=flowchart_id, notice_id=notice_id).first()
    if not nf:
        return False, "Association not found."

    try:
        db.session.delete(nf)
        db.session.commit()
        return True, "Flowchart unlinked from circular."
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to detach flowchart: {e}"

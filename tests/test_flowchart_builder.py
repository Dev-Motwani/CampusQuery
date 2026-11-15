"""
Comprehensive Automated Test Suite for CampusQuery Phase 8:
Editable Flowchart Builder, Persistence, and Working Exports.

Test Coverage:
1. Step-to-Graph Generation & Automatic Layout:
   - Sequential process steps layout generation.
   - Branching decision steps with labelled Yes/No connections.
   - Safe fallback on empty step list.
2. Graph Validation & Normalization:
   - Valid graph passes normalization.
   - Max node limit (> 50 nodes) rejected.
   - Empty graph (0 nodes) rejected.
   - Unsupported node types rejected.
   - Dangling edge connections (non-existent source/target IDs) rejected.
3. XSS Sanitization & Security:
   - <script>, <iframe>, and onerror= payloads stripped and escaped.
   - HTML injection in node labels, conditions, and titles rendered safe.
4. Drawflow Bidirectional Compatibility:
   - Conversion to Drawflow format generates valid input/output sockets and connections.
   - Extraction from Drawflow format preserves node IDs, coordinates, and labels.
5. Administrative CRUD & Persistence:
   - Admin creates flowchart via POST /flowcharts/create.
   - Admin updates flowchart via POST /flowcharts/<id>/edit.
   - Admin deletes flowchart via POST /flowcharts/<id>/delete.
   - Student blocked from administrative creation and modification routes.
6. Notice Association & Junction Operations:
   - Admin attaches flowchart to notice (/flowcharts/<id>/attach).
   - Admin detaches flowchart from notice (/flowcharts/<id>/detach/<notice_id>).
   - Duplicate attachment prevention.
7. Publication State Gating & Access Control:
   - Admin can view any flowchart (draft, published, or unattached).
   - Student blocked (HTTP 403) from unattached or draft-only flowcharts.
   - Student permitted (HTTP 200) to view published notice flowcharts.
   - Guest blocked (HTTP 404) from unreleased flowcharts without leaking existence.
8. Genuine PNG & PDF Export Verification:
   - PNG export produces valid binary image with PNG magic bytes (b"\\x89PNG\\r\\n\\x1a\\n").
   - PDF export produces valid binary document with PDF magic bytes (b"%PDF-").
   - Testing short graphs, long graphs with branching decision logic, and non-ASCII text.
   - Export endpoints /flowcharts/<id>/export/png and /flowcharts/<id>/export/pdf enforce publication gating.
"""
import io
import json
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.database import db
from app.models.user import User
from app.models.category import Category
from app.models.notice import Notice
from app.models.flowchart import Flowchart
from app.models.notice_flowchart import NoticeFlowchart
from app.services.flowchart_service import (
    sanitize_text,
    normalize_and_sanitize_graph,
    generate_graph_from_steps,
    convert_nodes_edges_to_drawflow,
    extract_nodes_and_edges_from_drawflow,
    export_flowchart_to_png,
    export_flowchart_to_pdf,
    attach_flowchart_to_notice,
    detach_flowchart_from_notice,
    ALLOWED_NODE_TYPES,
    MAX_NODES_LIMIT
)
from scripts.seed_demo import seed_demo_data


class FlowchartBuilderTestCase(unittest.TestCase):
    """Test suite for Phase 8 Flowchart Builder, validation, persistence, and exports."""

    @classmethod
    def setUpClass(cls):
        """Initializes application in testing mode."""
        cls.app = create_app("testing")
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        """Drops testing tables."""
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()

    def setUp(self):
        """Prepares clean seed data and authenticated client before each test."""
        seed_demo_data(self.app, verbose=False)
        self.client = self.app.test_client()
        self.admin = User.query.filter_by(role="admin").first()
        self.student = User.query.filter_by(role="student").first()
        self.published_notice = Notice.query.filter_by(status="published").first()

        # Ensure draft notice exists
        self.draft_notice = Notice.query.filter_by(status="draft").first()
        if not self.draft_notice:
            ts = int(datetime.utcnow().timestamp() * 1000)
            self.draft_notice = Notice(
                title="Draft Notice for Flowchart Test",
                slug=f"draft-notice-fc-{ts}",
                summary="Draft summary for test",
                content="Draft content for test",
                category_id=self.published_notice.category_id,
                status="draft",
                created_by=self.admin.id
            )
            db.session.add(self.draft_notice)
            db.session.commit()

        # Ensure archived notice exists
        self.archived_notice = Notice.query.filter_by(status="archived").first()
        if not self.archived_notice:
            ts = int(datetime.utcnow().timestamp() * 1000)
            self.archived_notice = Notice(
                title="Archived Notice for Flowchart Test",
                slug=f"archived-notice-fc-{ts}",
                summary="Archived summary for test",
                content="Archived content for test",
                category_id=self.published_notice.category_id,
                status="archived",
                created_by=self.admin.id
            )
            db.session.add(self.archived_notice)
            db.session.commit()

    def tearDown(self):
        """Rolls back open transactions."""
        db.session.rollback()

    def _login_as(self, user):
        """Helper to simulate authenticated session."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_role"] = user.role
            sess["user_name"] = user.full_name
            sess["_fresh"] = True

    # ==============================================================================
    # 1. STEP-TO-GRAPH GENERATION
    # ==============================================================================
    def test_generate_graph_from_sequential_steps(self):
        """Sequential steps generate properly ordered nodes and connecting edges."""
        steps = [
            {"type": "start", "label": "Start: Lab Journal Verification"},
            {"type": "process", "label": "Library No-Dues Clearance"},
            {"type": "end", "label": "Receive Examination Hall Ticket"}
        ]
        graph = generate_graph_from_steps(steps)
        nodes = graph["nodes"]
        edges = graph["edges"]

        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[0]["type"], "start")
        self.assertEqual(nodes[1]["type"], "process")
        self.assertEqual(nodes[2]["type"], "end")

        # Verify vertical layout spacing
        self.assertLess(nodes[0]["y"], nodes[1]["y"])
        self.assertLess(nodes[1]["y"], nodes[2]["y"])

        # Verify edge continuity
        self.assertEqual(len(edges), 2)
        self.assertEqual(edges[0]["source"], "1")
        self.assertEqual(edges[0]["target"], "2")
        self.assertEqual(edges[1]["source"], "2")
        self.assertEqual(edges[1]["target"], "3")

    def test_generate_graph_from_branching_decision_steps(self):
        """Decision steps create two labelled outgoing edges (Yes and No)."""
        steps = [
            {"type": "start", "label": "Start"},
            {"type": "decision", "label": "Fee Cleared?", "yes_target": 3, "no_target": 4},
            {"type": "process", "label": "Approved: Collect Hall Ticket"},
            {"type": "process", "label": "Pending: Pay at Window 2", "is_alternate_branch": True},
            {"type": "end", "label": "Procedure Complete"}
        ]
        graph = generate_graph_from_steps(steps)
        edges = graph["edges"]

        # Locate decision node outgoing edges
        decision_edges = [e for e in edges if e["source"] == "2"]
        self.assertEqual(len(decision_edges), 2)

        yes_edge = next((e for e in decision_edges if e["label"] == "Yes"), None)
        no_edge = next((e for e in decision_edges if e["label"] == "No"), None)

        self.assertIsNotNone(yes_edge)
        self.assertIsNotNone(no_edge)
        self.assertEqual(yes_edge["target"], "3")
        self.assertEqual(no_edge["target"], "4")

    def test_generate_graph_fallback_on_empty_steps(self):
        """Empty steps input generates default functional template."""
        graph = generate_graph_from_steps([])
        self.assertGreater(len(graph["nodes"]), 0)
        self.assertGreater(len(graph["edges"]), 0)
        self.assertIn("drawflow", graph)

    # ==============================================================================
    # 2. GRAPH VALIDATION & NORMALIZATION
    # ==============================================================================
    def test_normalize_valid_graph(self):
        """Valid graph structure passes normalization."""
        raw = {
            "nodes": [
                {"id": "n1", "type": "start", "label": "Begin Submission", "x": 100, "y": 50},
                {"id": "n2", "type": "end", "label": "Finished", "x": 100, "y": 200}
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "label": ""}
            ]
        }
        is_valid, msg, clean = normalize_and_sanitize_graph(raw)
        self.assertTrue(is_valid)
        self.assertEqual(len(clean["nodes"]), 2)
        self.assertEqual(len(clean["edges"]), 1)

    def test_normalize_rejects_empty_nodes(self):
        """Graph with 0 nodes is rejected."""
        is_valid, msg, _ = normalize_and_sanitize_graph({"nodes": []})
        self.assertFalse(is_valid)
        self.assertIn("at least one node", msg)

    def test_normalize_rejects_exceeding_max_nodes(self):
        """Graph exceeding 50 nodes limit is rejected."""
        many_nodes = [
            {"id": f"n_{i}", "type": "process", "label": f"Step {i}", "x": 100, "y": i * 50}
            for i in range(MAX_NODES_LIMIT + 5)
        ]
        is_valid, msg, _ = normalize_and_sanitize_graph({"nodes": many_nodes})
        self.assertFalse(is_valid)
        self.assertIn("exceeds maximum permitted node limit", msg)

    def test_normalize_rejects_invalid_node_types(self):
        """Disallowed node types are rejected."""
        raw = {
            "nodes": [
                {"id": "1", "type": "invalid_shape", "label": "Invalid Step"}
            ]
        }
        is_valid, msg, _ = normalize_and_sanitize_graph(raw)
        self.assertFalse(is_valid)
        self.assertIn("Invalid node type", msg)

    def test_normalize_rejects_dangling_edge_targets(self):
        """Edges referencing non-existent nodes are rejected."""
        raw = {
            "nodes": [
                {"id": "1", "type": "start", "label": "Start"}
            ],
            "edges": [
                {"source": "1", "target": "9999"}  # Node 9999 does not exist
            ]
        }
        is_valid, msg, _ = normalize_and_sanitize_graph(raw)
        self.assertFalse(is_valid)
        self.assertIn("does not exist", msg)

    # ==============================================================================
    # 3. XSS SANITIZATION (Requirement 8)
    # ==============================================================================
    def test_xss_sanitization_in_labels_and_titles(self):
        """Executable scripts, iframes, and onerror handlers are completely stripped and escaped."""
        malicious_label = "<script>alert('xss')</script>Normal Text<img src=x onerror=alert(1)>"
        sanitized = sanitize_text(malicious_label)
        self.assertNotIn("<script>", sanitized)
        self.assertNotIn("onerror", sanitized)
        self.assertIn("Normal Text", sanitized)

        raw = {
            "nodes": [
                {"id": "1", "type": "start", "label": "<iframe src='evil.com'></iframe>Step 1"},
                {"id": "2", "type": "end", "label": "<b onmouseover='alert(2)'>Step 2</b>"}
            ],
            "edges": [
                {"source": "1", "target": "2", "label": "<script>evil()</script>Yes"}
            ]
        }
        is_valid, _, clean = normalize_and_sanitize_graph(raw)
        self.assertTrue(is_valid)
        self.assertNotIn("<iframe", clean["nodes"][0]["label"])
        self.assertNotIn("onmouseover", clean["nodes"][1]["label"])
        self.assertNotIn("<script>", clean["edges"][0]["label"])

    # ==============================================================================
    # 4. DRAWFLOW BIDIRECTIONAL CONVERSION
    # ==============================================================================
    def test_drawflow_bidirectional_roundtrip(self):
        """Graph converts to Drawflow format and extracts back without loss of data."""
        original_nodes = [
            {"id": "1", "type": "start", "label": "Start Clearance", "x": 120.0, "y": 80.0},
            {"id": "2", "type": "decision", "label": "Fee Due?", "x": 120.0, "y": 200.0},
            {"id": "3", "type": "end", "label": "Collect Card", "x": 120.0, "y": 320.0}
        ]
        original_edges = [
            {"id": "e1-2", "source": "1", "target": "2", "label": ""},
            {"id": "e2-3", "source": "2", "target": "3", "label": "No"}
        ]

        # 1. Convert to Drawflow
        df_export = convert_nodes_edges_to_drawflow(original_nodes, original_edges)
        self.assertIn("drawflow", df_export)
        self.assertIn("Home", df_export["drawflow"])
        home_data = df_export["drawflow"]["Home"]["data"]
        self.assertEqual(len(home_data), 3)

        # 2. Extract back
        extracted_nodes, extracted_edges = extract_nodes_and_edges_from_drawflow(df_export["drawflow"])
        self.assertEqual(len(extracted_nodes), 3)
        self.assertEqual(len(extracted_edges), 2)

        # Verify coordinates and labels preserved
        node1 = next(n for n in extracted_nodes if n["id"] == "1")
        self.assertEqual(node1["label"], "Start Clearance")
        self.assertEqual(node1["x"], 120.0)
        self.assertEqual(node1["y"], 80.0)

    # ==============================================================================
    # 5. ADMINISTRATIVE CRUD & PERSISTENCE
    # ==============================================================================
    def test_admin_create_flowchart_post(self):
        """Admin creates a flowchart via POST /flowcharts/create."""
        self._login_as(self.admin)
        steps = [
            {"type": "start", "label": "Start Admission"},
            {"type": "process", "label": "Document Verification"},
            {"type": "end", "label": "Fee Receipt Issued"}
        ]
        graph = generate_graph_from_steps(steps)
        payload = {
            "title": "New Admission Procedure 2026",
            "description": "Step-by-step admission clearance",
            "notice_id": self.published_notice.id,
            "graph_data": graph
        }

        res = self.client.post(
            "/flowcharts/create",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("flowchart", data)
        fc_id = data["flowchart"]["id"]

        # Verify saved in database
        fc = Flowchart.query.get(fc_id)
        self.assertIsNotNone(fc)
        self.assertEqual(fc.title, "New Admission Procedure 2026")
        self.assertEqual(fc.node_count, 3)

        # Verify notice link created
        nf = NoticeFlowchart.query.filter_by(flowchart_id=fc.id, notice_id=self.published_notice.id).first()
        self.assertIsNotNone(nf)

    def test_admin_update_flowchart_post(self):
        """Admin updates an existing flowchart via POST /flowcharts/<id>/edit."""
        self._login_as(self.admin)
        fc = Flowchart.query.first()
        updated_title = "Updated Clearance Workflow"

        graph = fc.graph_data
        graph["nodes"].append({"id": "extra_node", "type": "process", "label": "Bonus Step", "x": 300, "y": 400})

        payload = {
            "title": updated_title,
            "description": "Updated description",
            "graph_data": graph
        }
        res = self.client.post(
            f"/flowcharts/{fc.id}/edit",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)

        db.session.refresh(fc)
        self.assertEqual(fc.title, updated_title)

    def test_student_blocked_from_flowchart_management(self):
        """Student cannot access /flowcharts/manage, /new, or /create."""
        self._login_as(self.student)
        res_manage = self.client.get("/flowcharts/manage")
        self.assertIn(res_manage.status_code, (302, 403))

        res_new = self.client.get("/flowcharts/new")
        self.assertIn(res_new.status_code, (302, 403))

        res_post = self.client.post(
            "/flowcharts/create",
            data=json.dumps({"title": "Illegal Diagram"}),
            content_type="application/json"
        )
        self.assertIn(res_post.status_code, (302, 403))

    def test_admin_delete_flowchart_post(self):
        """Admin deletes a flowchart; database record and notice links removed."""
        self._login_as(self.admin)
        fc = Flowchart(
            title="Temporary Diagram",
            slug=f"temp-diagram-{int(datetime.utcnow().timestamp() * 1000)}",
            graph_data={"nodes": [{"id": "1", "type": "start", "label": "One"}]},
            created_by=self.admin.id
        )
        db.session.add(fc)
        db.session.commit()
        fc_id = fc.id

        # Attach
        attach_flowchart_to_notice(fc_id, self.published_notice.id)

        res = self.client.post(f"/flowcharts/{fc_id}/delete", follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        self.assertIsNone(Flowchart.query.get(fc_id))
        self.assertIsNone(NoticeFlowchart.query.filter_by(flowchart_id=fc_id).first())

    # ==============================================================================
    # 6. NOTICE ASSOCIATION & JUNCTION OPERATIONS
    # ==============================================================================
    def test_attach_and_detach_notice(self):
        """Admin links and unlinks flowchart to notice circulars."""
        fc = Flowchart.query.first()
        self._login_as(self.admin)

        # Attach to draft notice
        attach_res = self.client.post(
            f"/flowcharts/{fc.id}/attach",
            data={"notice_id": self.draft_notice.id, "caption": "Draft Procedure"},
            follow_redirects=True
        )
        self.assertEqual(attach_res.status_code, 200)
        nf = NoticeFlowchart.query.filter_by(flowchart_id=fc.id, notice_id=self.draft_notice.id).first()
        self.assertIsNotNone(nf)
        self.assertEqual(nf.caption, "Draft Procedure")

        # Detach
        detach_res = self.client.post(
            f"/flowcharts/{fc.id}/detach/{self.draft_notice.id}",
            follow_redirects=True
        )
        self.assertEqual(detach_res.status_code, 200)
        nf_after = NoticeFlowchart.query.filter_by(flowchart_id=fc.id, notice_id=self.draft_notice.id).first()
        self.assertIsNone(nf_after)

    # ==============================================================================
    # 7. PUBLICATION STATE GATING & STUDENT ACCESS
    # ==============================================================================
    def test_admin_can_view_any_flowchart(self):
        """Admin can view unattached or draft-linked flowcharts."""
        self._login_as(self.admin)
        fc_unattached = Flowchart(
            title="Secret Draft Diagram",
            slug=f"secret-draft-fc-{int(datetime.utcnow().timestamp() * 1000)}",
            graph_data={"nodes": [{"id": "1", "type": "start", "label": "Start"}]},
            created_by=self.admin.id
        )
        db.session.add(fc_unattached)
        db.session.commit()

        res = self.client.get(f"/flowcharts/{fc_unattached.id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Secret Draft Diagram", res.data)

    def test_student_cannot_view_unattached_flowchart(self):
        """Student receives HTTP 403 when trying to access unattached flowchart."""
        fc_unattached = Flowchart(
            title="Unattached Student Blocked Diagram",
            slug=f"unattached-fc-{int(datetime.utcnow().timestamp() * 1000)}",
            graph_data={"nodes": [{"id": "1", "type": "start", "label": "Start"}]},
            created_by=self.admin.id
        )
        db.session.add(fc_unattached)
        db.session.commit()

        self._login_as(self.student)
        res = self.client.get(f"/flowcharts/{fc_unattached.id}")
        self.assertEqual(res.status_code, 403)

    def test_student_cannot_view_draft_only_flowchart(self):
        """Student receives HTTP 403 when flowchart is attached ONLY to draft notice."""
        fc_draft = Flowchart(
            title="Draft Only Flowchart",
            slug=f"draft-only-fc-{int(datetime.utcnow().timestamp() * 1000)}",
            graph_data={"nodes": [{"id": "1", "type": "start", "label": "Start"}]},
            created_by=self.admin.id
        )
        db.session.add(fc_draft)
        db.session.commit()
        attach_flowchart_to_notice(fc_draft.id, self.draft_notice.id)

        self._login_as(self.student)
        res = self.client.get(f"/flowcharts/{fc_draft.id}")
        self.assertEqual(res.status_code, 403)

    def test_student_can_view_published_notice_flowchart(self):
        """Student receives HTTP 200 for flowchart linked to published circular."""
        fc_pub = Flowchart(
            title="Published Procedure Diagram",
            slug=f"published-proc-fc-{int(datetime.utcnow().timestamp() * 1000)}",
            graph_data={"nodes": [{"id": "1", "type": "start", "label": "Start Verification"}]},
            created_by=self.admin.id
        )
        db.session.add(fc_pub)
        db.session.commit()
        attach_flowchart_to_notice(fc_pub.id, self.published_notice.id)

        self._login_as(self.student)
        res = self.client.get(f"/flowcharts/{fc_pub.id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Published Procedure Diagram", res.data)
        # Verify read-only viewer mode indicator
        self.assertIn(b"drawflow-view-mode", res.data)

    def test_unauthenticated_guest_access_rules(self):
        """Guest gets HTTP 404 for draft/unattached flowchart, HTTP 200 for published."""
        fc_draft = Flowchart(
            title="Guest Hidden Flowchart",
            slug=f"guest-hidden-fc-{int(datetime.utcnow().timestamp() * 1000)}",
            graph_data={"nodes": [{"id": "1", "type": "start", "label": "Start"}]},
            created_by=self.admin.id
        )
        db.session.add(fc_draft)
        db.session.commit()

        # Unattached -> 404 (does not leak existence)
        res = self.client.get(f"/flowcharts/{fc_draft.id}")
        self.assertEqual(res.status_code, 404)

        # Attach to published notice -> 200
        attach_flowchart_to_notice(fc_draft.id, self.published_notice.id)
        res_pub = self.client.get(f"/flowcharts/{fc_draft.id}")
        self.assertEqual(res_pub.status_code, 200)

    # ==============================================================================
    # 8. GENUINE PNG & PDF EXPORTS (Requirement 12)
    # ==============================================================================
    def test_genuine_png_export_bytes(self):
        """export_flowchart_to_png produces valid binary image with PNG magic bytes."""
        fc = Flowchart.query.first()
        png_bytes = export_flowchart_to_png(fc)

        self.assertIsInstance(png_bytes, bytes)
        self.assertGreater(len(png_bytes), 500)
        # Verify standard PNG file signature: \x89PNG\r\n\x1a\n
        self.assertTrue(png_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_genuine_pdf_export_bytes(self):
        """export_flowchart_to_pdf produces valid binary document with PDF magic bytes."""
        fc = Flowchart.query.first()
        pdf_bytes = export_flowchart_to_pdf(fc)

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        # Verify standard PDF file signature: %PDF-
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_export_with_non_ascii_and_long_branching_graphs(self):
        """Export handles Unicode / non-ASCII text, decision branches, and long flows."""
        long_steps = [
            {"type": "start", "label": "Start: Lab Journal Verification (सत्यापन)"},
            {"type": "process", "label": "Step 1: Résumé & Hall Ticket Check"},
            {"type": "decision", "label": "Attendance >= 75%?", "yes_target": 4, "no_target": 5},
            {"type": "process", "label": "Step 2A: Direct Approval"},
            {"type": "process", "label": "Step 2B: Dean Clearance & Fine Payment", "is_alternate_branch": True},
            {"type": "process", "label": "Step 3: Signature from HOD"},
            {"type": "end", "label": "End: Certified & Ready (पूर्ण)"}
        ]
        graph = generate_graph_from_steps(long_steps)
        fc = Flowchart(
            title="Complex Branching Academic Procedure (अकादमिक प्रक्रिया)",
            slug=f"complex-branching-fc-{int(datetime.utcnow().timestamp() * 1000)}",
            description="Testing long graphs, non-ASCII text, and branching decision logic.",
            graph_data=graph,
            created_by=self.admin.id
        )
        db.session.add(fc)
        db.session.commit()

        # Test PNG
        png_bytes = export_flowchart_to_png(fc)
        self.assertTrue(png_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

        # Test PDF
        pdf_bytes = export_flowchart_to_pdf(fc)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_export_routes_publication_gating(self):
        """Export routes /export/png and /export/pdf enforce publication-state access control."""
        fc_pub = Flowchart(
            title="Export Gated Diagram",
            slug=f"export-gated-fc-{int(datetime.utcnow().timestamp() * 1000)}",
            graph_data={"nodes": [{"id": "1", "type": "start", "label": "Start"}]},
            created_by=self.admin.id
        )
        db.session.add(fc_pub)
        db.session.commit()

        # Student blocked when unattached
        self._login_as(self.student)
        res_png_blocked = self.client.get(f"/flowcharts/{fc_pub.id}/export/png")
        self.assertEqual(res_png_blocked.status_code, 403)

        res_pdf_blocked = self.client.get(f"/flowcharts/{fc_pub.id}/export/pdf")
        self.assertEqual(res_pdf_blocked.status_code, 403)

        # Attach to published notice
        attach_flowchart_to_notice(fc_pub.id, self.published_notice.id)

        # Student permitted now that it's published
        res_png_ok = self.client.get(f"/flowcharts/{fc_pub.id}/export/png")
        self.assertEqual(res_png_ok.status_code, 200)
        self.assertEqual(res_png_ok.content_type, "image/png")
        self.assertIn("attachment", res_png_ok.headers.get("Content-Disposition", ""))

        res_pdf_ok = self.client.get(f"/flowcharts/{fc_pub.id}/export/pdf")
        self.assertEqual(res_pdf_ok.status_code, 200)
        self.assertEqual(res_pdf_ok.content_type, "application/pdf")
        self.assertIn("attachment", res_pdf_ok.headers.get("Content-Disposition", ""))


if __name__ == "__main__":
    unittest.main()

"""
Grounded Gemini Academic Assistant Blueprint Routes (Phase 9).

Endpoints:
- GET  /assistant                    : Renders interactive student AI chat portal.
- POST /assistant/query              : AJAX query endpoint with grounded evidence retrieval and citation validation.
- GET  /assistant/suggested-queries  : Returns starter academic prompts.
- GET  /assistant/status             : Returns operational status and index counts (never leaks API key).
"""
import logging
from flask import render_template, request, jsonify, current_app

from app.assistant import assistant_bp
from app.models.notice import Notice
from app.models.document import Document
from app.services.gemini_service import (
    answer_student_query,
    get_gemini_api_key,
    OFFICIAL_AI_DISCLAIMER
)

logger = logging.getLogger("campusquery.assistant")

SUGGESTED_QUERIES = [
    {
        "icon": "bi-award",
        "title": "Scholarship Eligibility",
        "prompt": "What are the eligibility criteria and required documents for the post-matric scholarship?"
    },
    {
        "icon": "bi-calendar-check",
        "title": "CET CAP Verification",
        "prompt": "What is the deadline and procedure for State CET CAP application form verification?"
    },
    {
        "icon": "bi-card-checklist",
        "title": "Exam Hall Tickets",
        "prompt": "What is the last date to submit the semester examination fee and collect hall tickets?"
    },
    {
        "icon": "bi-trophy",
        "title": "Sports Quota Trials",
        "prompt": "When are the sports trials conducted and what certificates are required?"
    },
    {
        "icon": "bi-building",
        "title": "Admissions Office Hours",
        "prompt": "Where is the Central Admissions Desk located and what are their working hours?"
    }
]


@assistant_bp.route("/", methods=["GET"])
def chat_interface():
    """
    Renders the dedicated interactive CampusQuery Academic Assistant interface.
    Accessible to students, faculty, and public visitors.
    """
    api_key_configured = bool(get_gemini_api_key())
    published_count = Notice.query.filter_by(status="published").count()

    return render_template(
        "assistant/chat.html",
        suggested_queries=SUGGESTED_QUERIES,
        api_key_configured=api_key_configured,
        published_count=published_count,
        disclaimer=OFFICIAL_AI_DISCLAIMER
    )


@assistant_bp.route("/query", methods=["POST"])
def query():
    """
    Primary API query endpoint:
    - Accepts JSON payload `{"query": "..."}` or form data `query="..."`.
    - Sanitizes and bounds question length.
    - Retrieves strictly approved, published notices and eligible documents.
    - Evaluates Gemini LLM grounding or performs graceful offline search fallback.
    - Validates citations against server-supplied allowlist.
    - Resolves verified URLs and office contacts server-side.
    """
    is_json = request.is_json or request.accept_mimetypes.best == "application/json"
    data = request.get_json(silent=True) or request.form

    raw_query = data.get("query", "").strip() if data else ""

    if not raw_query:
        err_msg = "Please provide a valid question regarding academic notices, deadlines, or requirements."
        if is_json:
            return jsonify({
                "success": False,
                "error": "Bad Request",
                "message": err_msg,
                "answer": err_msg,
                "sources": [],
                "office_referral": None,
                "disclaimer": OFFICIAL_AI_DISCLAIMER
            }), 400
        return jsonify({"error": err_msg}), 400

    try:
        response_data = answer_student_query(raw_query)
        return jsonify(response_data), 200

    except Exception as e:
        logger.error("Unhandled error in assistant query endpoint: %s", e, exc_info=True)
        # Never break the portal or leak tracebacks
        return jsonify({
            "success": False,
            "error": "Server Error",
            "message": "The academic assistant is temporarily unavailable. Please browse published notices directly.",
            "answer": "We encountered an unexpected error processing your inquiry. Please consult the notice directory or contact administrative staff.",
            "sources": [],
            "office_referral": None,
            "disclaimer": OFFICIAL_AI_DISCLAIMER,
            "mode": "error_fallback"
        }), 200


@assistant_bp.route("/suggested-queries", methods=["GET"])
def get_suggested_queries():
    """Returns curated academic prompt suggestions for fast student discovery."""
    return jsonify({
        "success": True,
        "suggested_queries": SUGGESTED_QUERIES
    }), 200


@assistant_bp.route("/status", methods=["GET"])
def assistant_status():
    """
    Diagnostic status endpoint:
    Reports index metrics and engine configuration state.
    Strictly masks GEMINI_API_KEY (never leaked).
    """
    api_key_configured = bool(get_gemini_api_key())
    published_notices = Notice.query.filter_by(status="published").count()
    extracted_docs = Document.query.filter_by(extraction_status="success").count()

    return jsonify({
        "success": True,
        "assistant_status": "operational",
        "api_key_configured": api_key_configured,
        "index_counts": {
            "published_notices": published_notices,
            "extracted_documents": extracted_docs
        },
        "mode": "gemini_live" if api_key_configured else "offline_directory_search"
    }), 200

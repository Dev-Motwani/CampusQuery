"""
Services package for CampusQuery.
"""
from app.services.deadline_service import (
    TIMEZONE_DOCUMENTATION,
    get_utc_now,
    utc_to_ist,
    format_academic_datetime,
    parse_milestone_datetime,
    notify_new_notice_published,
    notify_deadlines_changed,
    process_approaching_deadlines,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_unread_notification_count
)

from app.services.document_service import (
    ALLOWED_DOCUMENT_LABELS,
    validate_uploaded_file,
    save_uploaded_document,
    extract_document_text,
    delete_document
)
from app.services.flowchart_service import (
    sanitize_text,
    normalize_and_sanitize_graph,
    generate_graph_from_steps,
    convert_nodes_edges_to_drawflow,
    extract_nodes_and_edges_from_drawflow,
    export_flowchart_to_png,
    export_flowchart_to_pdf,
    attach_flowchart_to_notice,
    detach_flowchart_from_notice
)
from app.services.retrieval_service import (
    RetrievedItem,
    normalize_query_tokens,
    search_published_academic_content,
    build_evidence_context_prompt,
    check_notice_expiration
)
from app.services.gemini_service import (
    answer_student_query,
    generate_offline_grounded_answer,
    extract_verified_sources,
    extract_office_referral,
    get_gemini_api_key,
    OFFICIAL_AI_DISCLAIMER
)

__all__ = [
    "TIMEZONE_DOCUMENTATION",
    "get_utc_now",
    "utc_to_ist",
    "format_academic_datetime",
    "parse_milestone_datetime",
    "notify_new_notice_published",
    "notify_deadlines_changed",
    "process_approaching_deadlines",
    "mark_notification_as_read",
    "mark_all_notifications_as_read",
    "get_unread_notification_count",
    "ALLOWED_DOCUMENT_LABELS",
    "validate_uploaded_file",
    "save_uploaded_document",
    "extract_document_text",
    "delete_document",
    "sanitize_text",
    "normalize_and_sanitize_graph",
    "generate_graph_from_steps",
    "convert_nodes_edges_to_drawflow",
    "extract_nodes_and_edges_from_drawflow",
    "export_flowchart_to_png",
    "export_flowchart_to_pdf",
    "attach_flowchart_to_notice",
    "detach_flowchart_from_notice",
    "RetrievedItem",
    "normalize_query_tokens",
    "search_published_academic_content",
    "build_evidence_context_prompt",
    "check_notice_expiration",
    "answer_student_query",
    "generate_offline_grounded_answer",
    "extract_verified_sources",
    "extract_office_referral",
    "get_gemini_api_key",
    "OFFICIAL_AI_DISCLAIMER"
]


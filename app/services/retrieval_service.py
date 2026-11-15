"""
Academic Content Retrieval Engine for CampusQuery Grounded Assistant (Phase 9).

Responsibilities:
1. Query normalization, keyword tokenization, and stopword filtering.
2. Filtering strictly approved, published, non-archived notices.
3. Filtering eligible, non-archived extracted document text linked to published notices.
4. Scoring and ranking based on academic relevance (title, criteria, summary, deadlines).
5. Explicitly distinguishing current opportunities from expired/historical notices.
6. Enforcing context size limits and safe bounding.
7. Generating a server-supplied source allowlist and authorized link mappings.
8. Packaging untrusted document and notice text in secure data delimiters to prevent prompt injection.
"""
import re
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional

from app.database import db
from app.models.notice import Notice
from app.models.document import Document
from app.models.deadline import Deadline
from app.models.office import OfficeInformation


# Standard English and academic stop words to filter during keyword extraction
STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by",
    "as", "of", "from", "is", "are", "was", "were", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "can", "could", "shall", "should", "will",
    "would", "may", "might", "must", "i", "you", "he", "she", "it", "we", "they",
    "my", "your", "his", "her", "our", "their", "me", "him", "us", "them", "what",
    "which", "who", "whom", "this", "that", "these", "those", "how", "when", "where",
    "why", "any", "some", "all", "please", "tell", "give", "details", "info",
    "information", "about", "regarding", "available", "show", "get", "need", "want"
}

# Synonyms and prefix roots for common campus terms
QUERY_EXPANSIONS = {
    "scholarship": ["scholarship", "freeship", "mahadbt", "fellowship", "concession"],
    "fee": ["fee", "fees", "payment", "clearance", "dues", "challan"],
    "exam": ["exam", "examination", "hall ticket", "admit card", "timetable"],
    "cet": ["cet", "cap", "allotment", "facilitation", "fc"],
    "admission": ["admission", "admissions", "enrollment", "registration", "eligibility"],
    "sports": ["sports", "athletic", "tournament", "trials", "gymkhana"],
    "caste": ["caste", "validity", "category", "reservation"],
    "income": ["income", "tahsildar", "certificate", "creamy"],
    "hostel": ["hostel", "mess", "accommodation", "room"],
    "library": ["library", "book", "clearance", "dues"]
}


def normalize_query_tokens(query_text: str) -> List[str]:
    """
    Normalizes a user query into clean search tokens:
    - Lowercases text
    - Strips non-alphanumeric punctuation
    - Removes common stop words
    - Expands with domain-specific synonym terms
    """
    if not query_text:
        return []

    # Strip HTML tags if any present
    text = re.sub(r"<[^>]+>", " ", query_text.lower())
    # Extract alphanumeric words (at least 2 chars)
    raw_tokens = re.findall(r"[a-z0-9]{2,}", text)
    filtered = [t for t in raw_tokens if t not in STOP_WORDS]

    # Expand tokens with academic domain synonyms
    expanded = set(filtered)
    for t in filtered:
        for root, syns in QUERY_EXPANSIONS.items():
            if root in t or any(s in t for s in syns):
                expanded.update(syns)

    return list(expanded)


def sanitize_raw_text_for_prompt(text: str) -> str:
    """
    Sanitizes raw user/document text before embedding in LLM prompts.
    Strips internal prompt delimiter overrides and dangerous system escape phrases
    to defend against indirect prompt injection (Requirement 10 & 11).
    """
    if not text:
        return ""

    # Remove attempts to inject fake prompt termination delimiters
    sanitized = text.replace("<<<UNTRUSTED_ACADEMIC_DATA_END>>>", "")
    sanitized = sanitized.replace("<<<UNTRUSTED_ACADEMIC_DATA_START>>>", "")
    sanitized = re.sub(r"(?i)system\s*prompt:", "[text redacted]:", sanitized)
    sanitized = re.sub(r"(?i)ignore\s+(all\s+)?previous\s+instructions", "[instructions ignored]", sanitized)
    sanitized = re.sub(r"(?i)you\s+are\s+now\s+a", "[persona shift ignored]", sanitized)

    # Collapse excessive whitespace
    return " ".join(sanitized.split())


class RetrievedItem:
    """Container for scored academic content."""

    def __init__(
        self,
        source_id: str,
        source_type: str,
        entity_id: int,
        title: str,
        score: float,
        is_expired: bool,
        status_label: str,
        category: str,
        url: str,
        snippet: str,
        deadlines: Optional[List[Dict[str, Any]]] = None,
        office: Optional[Dict[str, Any]] = None,
        eligibility: Optional[str] = None,
        required_documents: Optional[str] = None,
        submission_instructions: Optional[str] = None
    ):
        self.source_id = source_id
        self.source_type = source_type  # 'notice' or 'document'
        self.entity_id = entity_id
        self.title = title
        self.score = score
        self.is_expired = is_expired
        self.status_label = status_label
        self.category = category
        self.url = url
        self.snippet = snippet
        self.deadlines = deadlines or []
        self.office = office
        self.eligibility = eligibility
        self.required_documents = required_documents
        self.submission_instructions = submission_instructions

    def to_allowlist_entry(self) -> Dict[str, Any]:
        """Returns safe verified metadata for the server-side source allowlist."""
        return {
            "source_id": self.source_id,
            "type": self.source_type,
            "id": self.entity_id,
            "title": self.title,
            "url": self.url,
            "is_expired": self.is_expired,
            "status_label": self.status_label,
            "category": self.category,
            "snippet": self.snippet[:250],
            "office_name": self.office.get("office_name") if self.office else None
        }


def check_notice_expiration(notice: Notice) -> Tuple[bool, str]:
    """
    Accurately determines whether a notice is currently active or historical/expired.
    Evaluates:
    - notice.expires_at timestamp
    - All associated notice deadlines
    Returns: (is_expired: bool, status_description: str)
    """
    now = datetime.utcnow()

    # If expires_at set and in the past
    if notice.expires_at and notice.expires_at < now:
        return True, f"EXPIRED / HISTORICAL NOTICE (Expired on {notice.expires_at.strftime('%d-%b-%Y')})"

    # Check deadlines if present
    if notice.deadlines:
        active_deadlines = [d for d in notice.deadlines if d.due_date >= now]
        if not active_deadlines:
            # All milestones have passed
            latest_past = max(d.due_date for d in notice.deadlines)
            return True, f"EXPIRED / HISTORICAL NOTICE (All deadlines passed on {latest_past.strftime('%d-%b-%Y')})"
        else:
            earliest_upcoming = min(d.due_date for d in active_deadlines)
            return False, f"ACTIVE / CURRENT NOTICE (Next Milestone: {earliest_upcoming.strftime('%d-%b-%Y')})"

    return False, "ACTIVE / CURRENT NOTICE"


def search_published_academic_content(
    query_text: str,
    top_k_notices: int = 4,
    top_k_documents: int = 2
) -> Tuple[List[RetrievedItem], Dict[str, Dict[str, Any]]]:
    """
    Grounded keyword retrieval across approved published college notices and documents.
    Strictly excludes:
    - Draft notices (Notice.status != 'published')
    - Archived notices (Notice.status != 'published')
    - Documents linked only to draft/archived notices
    - Documents without successfully extracted text

    Returns:
    - Ranked list of RetrievedItem objects
    - Server-side source allowlist dictionary {source_id: safe_metadata}
    """
    tokens = normalize_query_tokens(query_text)
    if not tokens:
        return [], {}

    retrieved_items: List[RetrievedItem] = []
    source_allowlist: Dict[str, Dict[str, Any]] = {}

    # ==========================================================================
    # 1. SEARCH PUBLISHED NOTICES
    # ==========================================================================
    published_notices = Notice.query.filter(Notice.status == "published").all()

    for notice in published_notices:
        score = 0.0

        title_lower = (notice.title or "").lower()
        cat_lower = (notice.category.name or "").lower() if notice.category else ""
        summary_lower = (notice.summary or "").lower()
        content_lower = (notice.content or "").lower()
        elig_lower = (notice.eligibility or "").lower()
        req_doc_lower = (notice.required_documents or "").lower()
        sub_inst_lower = (notice.submission_instructions or "").lower()

        # Score matching tokens with domain weights
        for token in tokens:
            if token in title_lower:
                score += 5.0
            if token in cat_lower:
                score += 3.5
            if token in summary_lower:
                score += 3.0
            if token in elig_lower:
                score += 2.5
            if token in req_doc_lower:
                score += 2.5
            if token in sub_inst_lower:
                score += 2.0
            if token in content_lower:
                score += 1.5

        # Check milestones
        for dl in notice.deadlines:
            dl_title_lower = dl.milestone_name.lower()
            for token in tokens:
                if token in dl_title_lower:
                    score += 2.0

        # Only retain if there is at least one keyword match
        if score > 0:
            is_expired, status_desc = check_notice_expiration(notice)

            # Boost active notices slightly over expired historical notices
            if not is_expired:
                score += 1.0

            deadlines_info = [
                {
                    "name": d.milestone_name,
                    "due_date": d.formatted_due_date,
                    "is_overdue": d.is_overdue,
                    "status": d.effective_status
                }
                for d in notice.deadlines
            ]

            office_info = notice.office.to_dict() if notice.office else None

            # Prepare snippet
            clean_snip = sanitize_raw_text_for_prompt(notice.summary or notice.content[:300])

            source_id = f"NOTICE-{notice.id}"
            item = RetrievedItem(
                source_id=source_id,
                source_type="notice",
                entity_id=notice.id,
                title=notice.title,
                score=score,
                is_expired=is_expired,
                status_label=status_desc,
                category=notice.category.name if notice.category else "General",
                url=f"/notices/{notice.id}",
                snippet=clean_snip,
                deadlines=deadlines_info,
                office=office_info,
                eligibility=sanitize_raw_text_for_prompt(notice.eligibility or ""),
                required_documents=sanitize_raw_text_for_prompt(notice.required_documents or ""),
                submission_instructions=sanitize_raw_text_for_prompt(notice.submission_instructions or "")
            )
            retrieved_items.append(item)

    # Sort notices by score descending and take top_k
    retrieved_items.sort(key=lambda x: x.score, reverse=True)
    top_notices = retrieved_items[:top_k_notices]

    # ==========================================================================
    # 2. SEARCH ELIGIBLE EXTRACTED DOCUMENTS
    # ==========================================================================
    # Strictly documents with extraction_status == 'success' and linked to published notices
    doc_candidates: List[RetrievedItem] = []
    eligible_documents = Document.query.filter(
        Document.extraction_status == "success",
        Document.extracted_text.isnot(None)
    ).all()

    for doc in eligible_documents:
        # Check publication-state gating (is accessible to student/guest)
        if not doc.is_accessible_by(None):
            continue

        doc_score = 0.0
        fname_lower = (doc.original_name or "").lower()
        label_lower = (doc.label or "").lower()
        desc_lower = (doc.description or "").lower()
        extracted_lower = (doc.extracted_text or "").lower()

        for token in tokens:
            if token in label_lower:
                doc_score += 4.0
            if token in fname_lower:
                doc_score += 3.0
            if token in desc_lower:
                doc_score += 2.0
            if token in extracted_lower:
                doc_score += 1.5

        if doc_score > 0:
            # Check status of linked notices
            linked_notices = [nl.notice for nl in doc.notice_links if nl.notice and nl.notice.status == "published"]
            doc_is_expired = all(check_notice_expiration(n)[0] for n in linked_notices) if linked_notices else False

            status_label = "ACTIVE / CURRENT DOCUMENT" if not doc_is_expired else "HISTORICAL DOCUMENT (Associated Notice Expired)"
            source_id = f"DOC-{doc.id}"

            clean_text = sanitize_raw_text_for_prompt(doc.extracted_text[:1200])

            doc_item = RetrievedItem(
                source_id=source_id,
                source_type="document",
                entity_id=doc.id,
                title=f"{doc.original_name} [{doc.label}]",
                score=doc_score,
                is_expired=doc_is_expired,
                status_label=status_label,
                category=doc.label,
                url=f"/documents/{doc.id}/download",
                snippet=clean_text
            )
            doc_candidates.append(doc_item)

    doc_candidates.sort(key=lambda x: x.score, reverse=True)
    top_docs = doc_candidates[:top_k_documents]

    # Combined top results
    final_results = top_notices + top_docs
    final_results.sort(key=lambda x: x.score, reverse=True)

    # Build server allowlist
    for item in final_results:
        source_allowlist[item.source_id] = item.to_allowlist_entry()

    return final_results, source_allowlist


def build_evidence_context_prompt(retrieved_items: List[RetrievedItem]) -> str:
    """
    Constructs bounded, structured evidence for the Gemini prompt.
    Encapsulates raw content inside explicit untrusted data markers.
    """
    if not retrieved_items:
        return "No published college notices or documents match this inquiry."

    sections = []
    for item in retrieved_items:
        header = f"=== SOURCE IDENTIFIER: [{item.source_id}] ==="
        meta = [
            f"Title: {item.title}",
            f"Type: {item.source_type.upper()}",
            f"Status: {item.status_label}",
            f"Category: {item.category}",
            f"Official Authorized Link: {item.url}"
        ]

        if item.office:
            meta.append(f"Responsible Office: {item.office.get('office_name', 'Administrative Office')} ({item.office.get('building_room', '')})")

        if item.deadlines:
            dl_lines = [f"  - {d['name']}: {d['due_date']} (Status: {d['status'].upper()})" for d in item.deadlines]
            meta.append("Target Milestones & Deadlines:\n" + "\n".join(dl_lines))

        if item.eligibility:
            meta.append(f"Eligibility Criteria: {item.eligibility}")

        if item.required_documents:
            meta.append(f"Mandatory Documents: {item.required_documents}")

        if item.submission_instructions:
            meta.append(f"Submission Procedure: {item.submission_instructions}")

        body = (
            f"{header}\n" +
            "\n".join(meta) + "\n" +
            "Relevant Content Excerpt (Untrusted Academic Data):\n" +
            "<<<UNTRUSTED_ACADEMIC_DATA_START>>>\n" +
            f"{item.snippet}\n" +
            "<<<UNTRUSTED_ACADEMIC_DATA_END>>>\n"
        )
        sections.append(body)

    return "\n--------------------------------------------------\n".join(sections)

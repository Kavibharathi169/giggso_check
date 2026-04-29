import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Per-chunk Groq calls are slow; default off — use keyword rules + default domain.
USE_LLM_DOMAIN = os.getenv("CLASSIFY_USE_LLM", "false").lower() in ("1", "true", "yes")
FAST_DOMAIN_DEFAULT = os.getenv("CLASSIFY_DEFAULT_DOMAIN", "audit_compliance")
_CLASSIFY_WORKERS = max(1, min(16, int(os.getenv("CLASSIFY_MAX_WORKERS", "8"))))

# ── Keyword map ───────────────────────────────────────────────
KEYWORD_MAP: dict[str, list[str]] = {
    "board_governance": [
        "board", "director", "chairman", "chairperson",
        "quorum", "trustee", "governance", "committee",
        "independent director", "board meeting",
        "board composition", "fiduciary"
    ],
    "data_privacy": [
        "privacy", "personal data", "gdpr", "consent",
        "data protection", "personal information",
        "data subject", "data controller", "data processor",
        "right to erasure", "right to access",
        "privacy policy", "confidentiality", "codes of conduct"
    ],
    "risk_management": [
        "risk", "control", "appetite", "mitigation",
        "risk management", "risk framework", "risk register",
        "internal control", "risk assessment",
        "risk tolerance", "risk appetite", "risk owner",
        "enterprise risk"
    ],
    "audit_compliance": [
        "audit", "compliance", "assurance",
        "internal audit", "external audit",
        "audit committee", "regulatory", "inspection",
        "audit report", "audit findings", "compliance officer",
        "sox", "internal controls over financial reporting"
    ],
    "shareholder_rights": [
        "shareholder", "voting", "agm", "dividend",
        "equity", "investor", "annual general meeting",
        "shareholder rights", "proxy", "share",
        "stockholder", "shareholder meeting",
        "voting rights", "minority shareholder"
    ],
    "csr": [
        "csr", "sustainability", "esg", "environment",
        "carbon", "social responsibility", "climate",
        "green", "renewable", "emission", "biodiversity",
        "corporate social responsibility", "social impact",
        "environmental policy"
    ],
    "hr_policy": [
        "salary", "recruitment", "employee", "conduct",
        "hr", "human resource", "compensation", "benefits",
        "leave policy", "code of conduct", "workplace",
        "staff", "personnel", "hiring", "termination",
        "performance review", "training"
    ],
    "financial_compliance": [
        "financial", "accounting", "ifrs", "gaap",
        "disclosure", "revenue", "financial statement",
        "balance sheet", "income statement", "cash flow",
        "financial reporting", "tax", "budget",
        "financial control", "treasury"
    ],
}

# ── Compliance framework keyword map ─────────────────────────
FRAMEWORK_MAP: dict[str, list[str]] = {
    "GDPR"          : ["gdpr", "general data protection"],
    "ISO_27001"     : ["iso 27001", "iso27001",
                       "information security management"],
    "SOX"           : ["sox", "sarbanes-oxley",
                       "sarbanes oxley"],
    "SEBI"          : ["sebi", "securities and exchange board"],
    "Companies_Act" : ["companies act", "corporate law",
                       "company act"],
}

# ── Japanese corporate TLDs ───────────────────────────────────
JAPANESE_TLDS = [".co.jp", ".or.jp", ".ne.jp", ".go.jp"]


def classify(
    section_title: str,
    chapter      : str,
    text         : str = ""
) -> str | None:
    """
    Classify a chunk into a governance domain using
    keyword matching on section_title and chapter.
    Returns domain label or None if no match found.
    """
    # Combine and lowercase for matching
    combined = (
        (section_title or "") + " " + (chapter or "") + " " + (text or "")
    ).lower().strip()

    if not combined:
        return None

    for domain, keywords in KEYWORD_MAP.items():
        for keyword in keywords:
            if keyword.lower() in combined:
                logger.debug(
                    f"Rule match: '{keyword}' → {domain} "
                    f"(section: '{section_title}')"
                )
                return domain

    logger.debug(
        f"No rule match for section: '{section_title}'"
    )
    return None


def assign_compliance_framework(
    text      : str,
    source_url: str
) -> str:
    """
    Assign a compliance framework label to a chunk.
    Scans text for known regulation keywords.
    Falls back to URL-based inference for Japanese domains.
    Returns framework label string.
    """
    text_upper = (text or "").upper()
    url_lower  = (source_url or "").lower()

    # Check text for framework keywords
    for framework, keywords in FRAMEWORK_MAP.items():
        for keyword in keywords:
            if keyword.upper() in text_upper:
                logger.debug(
                    f"Framework match: '{keyword}' "
                    f"→ {framework}"
                )
                return framework

    # Check source URL for Japanese TLD
    parsed = urlparse(source_url)
    netloc = parsed.netloc.lower()
    for tld in JAPANESE_TLDS:
        if netloc.endswith(tld):
            logger.debug(
                f"Japanese TLD detected in {source_url} "
                f"→ Companies_Act"
            )
            return "Companies_Act"

    return "unspecified_framework"


def assign_source_type(text: str) -> str:
    combined = (text or "").lower()
    regulatory_cues = (
        "article ", "section ", "rule ", "act", "regulation", "statutory",
        "shall", "must", "gdpr", "sox", "compliance with",
    )
    return "regulatory" if any(cue in combined for cue in regulatory_cues) else "operational_guideline"


from classification.llm_classifier import classify_with_llm
import concurrent.futures

def classify_chunk(chunk: dict) -> dict:
    """
    Run full classification on a single chunk.
    Attaches content_domain and compliance_framework.
    Returns updated chunk dict.
    """
    section_title = chunk.get("section_title", "")
    chapter       = chunk.get("chapter", "")
    text          = chunk.get("text", "")
    source_url    = chunk.get("source_url", "")

    # Classify domain
    domain = classify(section_title, chapter, text)

    if domain:
        chunk["content_domain"] = domain
        logger.debug(
            f"Rule classified: {domain} "
            f"(section: '{section_title}')"
        )
    elif USE_LLM_DOMAIN:
        fallback_domain = classify_with_llm(text, section_title)
        chunk["content_domain"] = fallback_domain
        logger.debug(
            f"LLM Fallback classified: {fallback_domain} "
            f"for: '{section_title}'"
        )
    else:
        chunk["content_domain"] = FAST_DOMAIN_DEFAULT
        logger.debug(
            f"Fast default domain: {FAST_DOMAIN_DEFAULT} "
            f"(section: '{section_title}')"
        )

    # Assign compliance framework
    chunk["compliance_framework"] = assign_compliance_framework(
        text, source_url
    )
    chunk["source_type"] = assign_source_type(text)

    return chunk

def classify_chunks(chunks: list[dict]) -> list[dict]:
    """Classify chunks in parallel; preserve original order for embedding alignment."""
    if not chunks:
        return []
    logger.info(
        f"Classifying {len(chunks)} chunks (workers={_CLASSIFY_WORKERS}, llm={USE_LLM_DOMAIN})..."
    )
    n = len(chunks)
    results = [None] * n
    with concurrent.futures.ThreadPoolExecutor(max_workers=_CLASSIFY_WORKERS) as executor:
        futures = {
            executor.submit(classify_chunk, chunk): idx
            for idx, chunk in enumerate(chunks)
        }
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.error(f"Error classifying chunk: {e}")
                results[idx] = chunks[idx]
    return results
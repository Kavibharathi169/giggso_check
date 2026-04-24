import logging
import os

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Groq client ───────────────────────────────────────────────
def _get_client() -> Groq:
    """Return a Groq API client."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found in environment variables"
        )
    return Groq(api_key=api_key)


# ── Allowed domain labels ─────────────────────────────────────
DOMAIN_LABELS = [
    "board_governance",
    "data_privacy",
    "risk_management",
    "audit_compliance",
    "shareholder_rights",
    "csr",
    "hr_policy",
    "financial_compliance",
]

DEFAULT_DOMAIN = "audit_compliance"

# ── Cache: avoid repeated LLM calls for same section_title ────
_cache: dict[str, str] = {}


def classify_with_llm(
    text         : str,
    section_title: str
) -> str:
    """
    Classify a chunk into a governance domain using
    Groq API (mixtral-8x7b-32768).
    Caches results by section_title.
    Returns domain label string.
    """
    # Check cache first
    cache_key = section_title.strip().lower()
    if cache_key in _cache:
        logger.debug(
            f"Cache hit for section: '{section_title}' "
            f"→ {_cache[cache_key]}"
        )
        return _cache[cache_key]

    model = os.getenv(
        "GROQ_CLASSIFIER_MODEL",
        "deepseek-r1-distill-llama-70b"
    )

    # Build prompt
    domains_str = ", ".join(DOMAIN_LABELS)
    prompt = (
        f"Classify the following governance text into "
        f"exactly one domain.\n"
        f"Return only the domain label, nothing else.\n"
        f"Domains: {domains_str}\n\n"
        f"Section: {section_title}\n"
        f"Text: {text[:500]}"
    )

    try:
        client   = _get_client()
        response = client.chat.completions.create(
            model      = model,
            messages   = [
                {
                    "role"   : "system",
                    "content": (
                        "You are a governance document "
                        "classifier. Return only the domain "
                        "label from the provided list. "
                        "No explanation. No punctuation. "
                        "Just the label."
                    )
                },
                {
                    "role"   : "user",
                    "content": prompt
                }
            ],
            temperature = 0.0,
            max_tokens  = 20,
        )

        raw_result = response.choices[0].message.content
        result     = raw_result.strip().lower()

        # Remove any punctuation just in case
        result = result.replace(".", "").replace(",", "").strip()

        # Validate against allowed labels
        if result in DOMAIN_LABELS:
            logger.info(
                f"LLM classified: '{section_title}' → {result}"
            )
            # Cache result
            _cache[cache_key] = result
            return result
        else:
            logger.warning(
                f"LLM returned invalid label: '{raw_result}' "
                f"for section: '{section_title}'. "
                f"Using default: {DEFAULT_DOMAIN}"
            )
            _cache[cache_key] = DEFAULT_DOMAIN
            return DEFAULT_DOMAIN

    except Exception as e:
        logger.error(
            f"Groq API call failed for "
            f"section '{section_title}': {e}. "
            f"Using default: {DEFAULT_DOMAIN}"
        )
        return DEFAULT_DOMAIN


def classify_chunk_with_llm(chunk: dict) -> dict:
    """
    Run LLM classification on a single chunk.
    Only called when rule-based classifier returned None.
    Attaches content_domain to chunk.
    Returns updated chunk dict.
    """
    section_title = chunk.get("section_title", "")
    text          = chunk.get("text", "")

    domain = classify_with_llm(text, section_title)
    chunk["content_domain"] = domain

    logger.debug(
        f"LLM fallback result: '{section_title}' → {domain}"
    )
    return chunk


def classify_chunks(chunks: list[dict]) -> list[dict]:
    """
    Run classification pipeline on a list of chunks.
    Uses rule-based first, LLM fallback for unmatched.
    Returns fully classified list of chunks.
    """
    from classification.rule_classifier import (
        classify_chunk,
        assign_compliance_framework
    )

    logger.info(
        f"Starting classification for {len(chunks)} chunks"
    )

    rule_matched = 0
    llm_fallback = 0

    for chunk in chunks:

        # Step 1 — Rule-based classification
        chunk = classify_chunk(chunk)

        # Step 2 — LLM fallback if no rule match
        if chunk.get("content_domain") is None:
            chunk = classify_chunk_with_llm(chunk)
            llm_fallback += 1
        else:
            rule_matched += 1

        # Step 3 — Ensure compliance_framework is set
        if not chunk.get("compliance_framework"):
            chunk["compliance_framework"] = (
                assign_compliance_framework(
                    chunk.get("text", ""),
                    chunk.get("source_url", "")
                )
            )

        # Step 4 — Ensure source_format is set
        if not chunk.get("source_format"):
            chunk["source_format"] = "unknown"

    logger.info(
        f"Classification complete — "
        f"rule matched: {rule_matched}, "
        f"llm fallback: {llm_fallback}, "
        f"total: {len(chunks)}"
    )

    return chunks
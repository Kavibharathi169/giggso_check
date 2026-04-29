import json
import logging
import os
import re
from dotenv import load_dotenv

from llm.groq_client import call_groq
from llm.prompt_templates import (
    CHECKLIST_SYSTEM_PROMPT,
    CHECKLIST_USER_PROMPT,
    CHECKLIST_VERIFY_SYSTEM_PROMPT,
    CHECKLIST_VERIFY_USER_PROMPT,
)

load_dotenv()

logger = logging.getLogger(__name__)
debug_logger = logging.getLogger("generator.debug")

# â”€â”€ Allowed domains â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€      
VALID_DOMAINS = [
    "board_governance",
    "data_privacy",
    "risk_management",
    "audit_compliance",
    "shareholder_rights",
    "csr",
    "hr_policy",
    "financial_compliance",
]

LOW_CONFIDENCE_LABELS = {"low", "very_low"}
VALID_SOURCE_TYPES = {"regulatory", "operational_guideline"}
UNSPECIFIED_ARTICLES = {"", "gdpr", "unspecified_framework", "unspecified_reference", "none", "null"}
ARTICLE_MAP = {
    "accountability": "Article 5(2)",
    "storage limitation": "Article 5(1)(e)",
    "data minimisation": "Article 5(1)(c)",
    "data minimization": "Article 5(1)(c)",
    "integrity confidentiality": "Article 5(1)(f)",
    "accuracy": "Article 5(1)(d)",
    "breach plan": "Article 33, Article 34",
    "provider evaluation": "Article 28",
    "technical measures": "Article 32",
    "identify laws": "Article 88",
    "privacy notice": "Article 13, Article 14",
    "publish privacy policy": "Article 13",
    "third party processors": "Article 5(1)(c)",
    "document processing": "Article 30",
    "right to rectification": "Article 16",
    "right to erasure": "Article 17",
    "right to access": "Article 15",
    "consent": "Article 6(1)(a)",
    "special categories": "Article 9",
}
MIN_ITEM_LENGTH = 30
MIN_GROUNDING_SCORE = 0.5


def build_violation_statement(item: dict) -> str | None:
    article = (item.get("article_reference", "") or "").strip()
    if article.lower() in UNSPECIFIED_ARTICLES:
        debug_logger.warning(
            "DROPPED item %s - article_reference too vague: '%s'",
            item.get("id", item.get("chunk_id", "?")),
            article,
        )
        return None
    return (
        f"I violated {article} - "
        f"{item.get('violation_condition', '').strip()} "
        f"Source: {item.get('source_quote', '').strip()}"
    ).strip()


def _clean_pdf_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u00ad", "").replace("\u200b", "")
    text = re.sub(r"([a-z])\s*\n\s*([a-z])", r"\1\2", text)
    text = re.sub(r"\s+\d+\.\s*$", "", text, flags=re.MULTILINE)
    return " ".join(text.split())


def _normalize_article(text: str) -> str:
    return (text or "").strip()


def _match_article_from_keywords(item: dict) -> str:
    haystack = " ".join(
        [
            str(item.get("item", "") or ""),
            str(item.get("source_quote", "") or ""),
            str(item.get("source_section", "") or ""),
        ]
    ).lower()
    for key, article in ARTICLE_MAP.items():
        if key in haystack:
            return article
    debug_logger.warning(
        "ARTICLE_MAP no match for item %s - section: '%s'",
        item.get("id", item.get("chunk_id", "?")),
        item.get("source_section", ""),
    )
    return ""


def _parse_json_response(raw: str) -> list[dict]:
    """
    Parse JSON array from LLM response.
    Handles cases where LLM adds extra text around JSON.
    """
    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON array from response
    try:
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except json.JSONDecodeError:
        pass

    logger.warning("Could not parse JSON from LLM response")
    return []


def _validate_items(items: list[dict]) -> list[dict]:
    """
    Validate and clean checklist items.
    Ensures all required fields exist.
    """
    valid = []
    for item in items:
        if not isinstance(item, dict):
            continue

        text = item.get("item", "").strip()
        if not text:
            continue
        if len(text) < MIN_ITEM_LENGTH:
            continue

        domain = item.get("domain", "").strip().lower()
        if domain not in VALID_DOMAINS:
            domain = "audit_compliance"

        source_quote = _clean_pdf_text((item.get("source_quote", "") or "").strip())
        initial_article = _normalize_article((item.get("article_reference", "") or "").strip())
        if initial_article.lower() in UNSPECIFIED_ARTICLES:
            initial_article = _match_article_from_keywords(item) or initial_article

        grounding_score = _word_overlap_score(text, source_quote)
        if grounding_score < MIN_GROUNDING_SCORE:
            debug_logger.warning(
                "DROPPED item %s - grounding_score %.3f below %.2f",
                item.get("id", item.get("chunk_id", "?")),
                grounding_score,
                MIN_GROUNDING_SCORE,
            )
            continue

        valid.append({
            "item"               : text,
            "domain"             : domain,
            "source_section"     : item.get("source_section", "—"),
            "page_number"        : int(item.get("page_number", 0) or 0),
            "source_quote"       : source_quote,
            "article_reference"  : initial_article,
            "violation_condition": (item.get("violation_condition", "") or "").strip(),
            "source_type"        : (item.get("source_type", "") or "").strip().lower(),
            "confidence"         : (item.get("confidence", "") or "").strip().lower() or "medium",
            "priority"           : item.get("priority", "Medium"),
            "action_type"        : item.get("action_type", "Process"),
            "evidence_required"  : item.get("evidence_required", "Documentation or log review."),
            "source_url"         : "",
            "chunk_id"           : str(item.get("chunk_id", "")),
            "compliance_framework": "unspecified_framework",
            "verified"           : None,
            "verification_confidence": None,
            "verification_evidence": "",
            "violation_statement": "",
            "grounding_score"    : grounding_score,
        })

    return valid


def _extract_article_reference(text: str) -> str:
    import re
    if not text:
        return ""
    patterns = [
        r"\bArticle\s+\d+[A-Za-z0-9()/-]*",
        r"\bSection\s+\d+(\.\d+)*",
        r"\bRule\s+\d+[A-Za-z0-9()/-]*",
        r"\bClause\s+\d+[A-Za-z0-9()/-]*",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return ""


def _infer_source_type(item: dict) -> str:
    src = " ".join(
        [
            str(item.get("item", "") or ""),
            str(item.get("source_quote", "") or ""),
            str(item.get("article_reference", "") or ""),
            str(item.get("compliance_framework", "") or ""),
        ]
    ).lower()
    regulatory_cues = ("article", "section", "rule", "act", "regulation", "gdpr", "sox", "iso")
    return "regulatory" if any(c in src for c in regulatory_cues) else "operational_guideline"


def _post_validate_items(items: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for item in items:
        art = _normalize_article(item.get("article_reference", ""))
        if art.lower() in UNSPECIFIED_ARTICLES:
            art = _match_article_from_keywords(item) or _extract_article_reference(
                f"{item.get('source_quote', '')} {item.get('item', '')}"
            )
        # Only keep an article reference if it is explicitly present in the source quote.
        source_quote_lower = str(item.get("source_quote", "") or "").lower()
        if art and art.lower() not in source_quote_lower:
            debug_logger.warning(
                "Clearing article_reference not present in source_quote for item %s: '%s'",
                item.get("id", item.get("chunk_id", "?")),
                art,
            )
            art = _extract_article_reference(item.get("source_quote", "") or "")
        item["article_reference"] = art or ""
        if not item.get("violation_condition"):
            req = item.get("item", "").rstrip(".")
            item["violation_condition"] = f"Violation occurs when the requirement is not met: {req}."
        if item.get("source_type") not in VALID_SOURCE_TYPES:
            item["source_type"] = _infer_source_type(item)
        # Explicit reclassification for known advisory/guideline items.
        advisory_cues = ("phishing awareness", "publish", "third part", "identify laws", "iapp", "opinion")
        cue_text = " ".join(
            [
                str(item.get("item", "") or ""),
                str(item.get("source_quote", "") or ""),
                str(item.get("source_section", "") or ""),
            ]
        ).lower()
        if any(c in cue_text for c in advisory_cues):
            item["source_type"] = "operational_guideline"

        if item.get("article_reference", "").lower() not in UNSPECIFIED_ARTICLES:
            item["compliance_framework"] = "GDPR"
            if item.get("source_type") not in VALID_SOURCE_TYPES:
                item["source_type"] = "regulatory"
        elif item.get("source_type") == "operational_guideline":
            item["compliance_framework"] = "operational_guideline"
        else:
            # Soft fallback: keep item as guideline instead of dropping later.
            item["article_reference"] = ""
            item["source_type"] = "operational_guideline"
            item["compliance_framework"] = "operational_guideline"

        statement = build_violation_statement(item)
        if statement:
            item["violation_statement"] = statement
        else:
            item["violation_statement"] = (
                f"Guideline breach - {item.get('violation_condition', '').strip()} "
                f"Source: {item.get('source_quote', '').strip()}"
            ).strip()
        cleaned.append(item)
    return cleaned


def _filter_valid_items(checklist: list[dict]) -> list[dict]:
    excluded_source_types = {"commentary", "opinion", "third_party_belief"}
    excluded_cues = ("iapp", "opinion", "third-party opinion")
    out: list[dict] = []
    for item in checklist:
        st = str(item.get("source_type", "") or "").strip().lower()
        text = " ".join(
            [
                str(item.get("item", "") or ""),
                str(item.get("source_quote", "") or ""),
                str(item.get("source_section", "") or ""),
            ]
        ).lower()
        if st in excluded_source_types:
            debug_logger.warning(
                "FILTERED item %s - source_type is '%s'",
                item.get("id", item.get("chunk_id", "?")),
                st,
            )
            continue
        if any(c in text for c in excluded_cues):
            debug_logger.warning(
                "FILTERED item %s - matched opinion cue",
                item.get("id", item.get("chunk_id", "?")),
            )
            continue
        out.append(item)
    debug_logger.info("filter_valid_items: %d in -> %d out", len(checklist), len(out))
    if not out and checklist:
        logger.error(
            "filter_valid_items removed all items; returning unfiltered list as safety net"
        )
        return checklist
    return out


def _tokenize_for_overlap(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {tok for tok in tokens if len(tok) > 2}


def _word_overlap_score(item_text: str, source_quote: str) -> float:
    item_tokens = _tokenize_for_overlap(item_text)
    if not item_tokens:
        return 0.0
    quote_tokens = _tokenize_for_overlap(source_quote)
    if not quote_tokens:
        return 0.0
    return len(item_tokens & quote_tokens) / len(item_tokens)


def _is_near_duplicate(a: dict, b: dict, threshold: float = 0.8) -> bool:
    tokens_a = _tokenize_for_overlap(str(a.get("item", "") or ""))
    tokens_b = _tokenize_for_overlap(str(b.get("item", "") or ""))
    if not tokens_a or not tokens_b:
        return False
    jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
    if jaccard < threshold:
        return False
    # Same legal obligation concept: prefer strict dedupe when article/domain align.
    domain_match = str(a.get("domain", "")) == str(b.get("domain", ""))
    article_match = str(a.get("article_reference", "")) == str(b.get("article_reference", ""))
    return domain_match or article_match


def _deduplicate_items(items: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    for item in items:
        replaced = False
        for idx, existing in enumerate(deduped):
            if _is_near_duplicate(existing, item):
                existing_score = float(existing.get("grounding_score", 0.0) or 0.0)
                new_score = float(item.get("grounding_score", 0.0) or 0.0)
                if new_score > existing_score:
                    deduped[idx] = item
                replaced = True
                debug_logger.info(
                    "DEDUP near-duplicate merged: kept score %.3f over %.3f",
                    max(existing_score, new_score),
                    min(existing_score, new_score),
                )
                break
        if not replaced:
            deduped.append(item)
    return deduped


def _build_result_maps(results: list[dict]) -> tuple[dict[str, dict], dict[str, str]]:
    chunk_map: dict[str, dict] = {}
    chunk_text_map: dict[str, str] = {}
    for r in results:
        cid = r.get("chunk_id") or r.get("metadata", {}).get("chunk_id", "")
        if not cid:
            continue
        chunk_map[cid] = r.get("metadata", {})
        chunk_text_map[cid] = (r.get("text", "") or "").strip()
    return chunk_map, chunk_text_map


def _is_item_grounded(item: dict, chunk_text_map: dict[str, str]) -> bool:
    """
    Deterministic grounding check to prevent hallucinations:
    - Item must reference a known chunk_id
    - source_quote should appear in that chunk (or one of top chunks fallback)
    """
    chunk_id = str(item.get("chunk_id", "") or "").strip()
    source_quote = str(item.get("source_quote", "") or "").strip()

    if not chunk_id or chunk_id not in chunk_text_map:
        return False

    if len(source_quote) < 20:
        return False

    own_chunk_text = chunk_text_map.get(chunk_id, "")
    if source_quote in own_chunk_text:
        return True

    # Small fallback for minor extraction drift on punctuation/newlines.
    normalized_quote = " ".join(source_quote.split())
    if not normalized_quote:
        return False
    for text in chunk_text_map.values():
        if normalized_quote in " ".join(text.split()):
            return True
    return False


def _enrich_with_metadata(
    items  : list[dict],
    results: list[dict]
) -> list[dict]:
    # Build lookup: chunk_id -> metadata
    chunk_map, _ = _build_result_maps(results)

    for item in items:
        cid = item.get("chunk_id", "")
        meta = chunk_map.get(cid)

        if meta:
            item["source_url"]           = meta.get("source_url","")
            item["compliance_framework"] = meta.get("compliance_framework","") or "unspecified_framework"
            if not item.get("page_number"):
                try:
                    item["page_number"] = int(meta.get("page_number", 0) or 0)
                except Exception:
                    item["page_number"] = 0
            if item.get("source_section") in ["—", "â€”", ""]:
                item["source_section"] = meta.get("section_heading") or meta.get("section_title", "—")
        else:
            source_section = item.get("source_section", "")
            for rcid, rmeta in chunk_map.items():
                sec = rmeta.get("section_heading") or rmeta.get("section_title", "")
                if sec and (source_section.lower() in sec.lower() or sec.lower() in source_section.lower()):
                    item["source_url"]           = rmeta.get("source_url","")
                    item["chunk_id"]             = rcid
                    item["compliance_framework"] = rmeta.get("compliance_framework","") or "unspecified_framework"
                    if not item.get("page_number"):
                        try:
                            item["page_number"] = int(rmeta.get("page_number", 0) or 0)
                        except Exception:
                            item["page_number"] = 0
                    break

    return items


def _verify_items_with_llm(items: list[dict], context_string: str) -> dict[str, dict]:
    if not items:
        return {}
    try:
        verify_prompt = CHECKLIST_VERIFY_USER_PROMPT.format(
            context=context_string,
            items_json=json.dumps(items, ensure_ascii=False),
        )
        raw = call_groq(
            system_prompt=CHECKLIST_VERIFY_SYSTEM_PROMPT,
            user_prompt=verify_prompt,
            temperature=0.0,
            max_tokens=3000,
        )
        parsed = _parse_json_response(raw)
    except Exception as e:
        logger.warning(f"Checklist verification call failed, using deterministic validation only: {e}")
        return {}

    out: dict[str, dict] = {}
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        cid = str(entry.get("chunk_id", "") or "").strip()
        if not cid:
            continue
        out[cid] = {
            "verified": bool(entry.get("verified", False)),
            "verification_confidence": float(entry.get("verification_confidence", 0.0) or 0.0),
            "verification_evidence": str(entry.get("verification_evidence", "") or "").strip(),
            "violation_statement": str(entry.get("violation_statement", "") or "").strip(),
        }
    return out


def _enforce_grounded_items(items: list[dict], results: list[dict]) -> list[dict]:
    if not items:
        return []

    _, chunk_text_map = _build_result_maps(results)
    filtered: list[dict] = []
    for item in items:
        confidence = str(item.get("confidence", "") or "").strip().lower()
        if confidence in LOW_CONFIDENCE_LABELS:
            debug_logger.warning(
                "DROPPED item %s - low confidence '%s'",
                item.get("id", item.get("chunk_id", "?")),
                confidence,
            )
            continue
        if _is_item_grounded(item, chunk_text_map):
            item["verified"] = True
            item["verification_confidence"] = 1.0
            item["verification_evidence"] = item.get("source_quote", "")
            stmt = build_violation_statement(item)
            if stmt:
                item["violation_statement"] = stmt
            filtered.append(item)
        else:
            debug_logger.warning(
                "DROPPED item %s - grounding check failed (chunk_id=%s)",
                item.get("id", item.get("chunk_id", "?")),
                item.get("chunk_id", ""),
            )
    debug_logger.info("grounding_filter: %d in -> %d out", len(items), len(filtered))
    if not filtered and items:
        logger.error("grounding removed all items; returning pre-grounded items as fallback")
        return items
    return filtered


def generate_checklist(
    context_string: str,
    results       : list[dict]
) -> list[dict]:
    """
    Generate a structured governance checklist
    from retrieved chunks using Groq API.
    """
    if not context_string or not context_string.strip():
        logger.warning(
            "generate_checklist called with empty context"
        )
        return []

    logger.info("Starting checklist generation via Groq API")
    debug_logger.info("STAGE 0 - input context chars: %d, retrieved results: %d", len(context_string), len(results))

    user_prompt = CHECKLIST_USER_PROMPT.format(
        context=context_string
    )

    # ACCURACY FIX: Lowered temperature to 0.0 (from 0.3) to force purely deterministic, factual outputs.
    # High temperatures allow the model to get "creative", which leads to hallucinations in legal/compliance checks.
    logger.info("Attempt 1: Generating checklist with 0.0 temperature for maximum accuracy...")
    try:
        raw = call_groq(
            system_prompt = CHECKLIST_SYSTEM_PROMPT,
            user_prompt   = user_prompt,
            temperature   = 0.0,  # Zero temperature for deterministic facts
            max_tokens    = 3000  # Increased token limit so it doesn't arbitrarily cut off long checklists
        )
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        return []

    items = _parse_json_response(raw)

    if not items:
        logger.warning("Attempt 1 failed. Retrying with stricter prompt...")
        strict_prompt = (
            user_prompt
            + "\n\nCRITICAL: Return ONLY a raw JSON array. "
            "Start with [ and end with ]. "
            "No markdown. No explanation. "
            "No text before or after the array."
        )
        try:
            raw = call_groq(
                system_prompt = CHECKLIST_SYSTEM_PROMPT,
                user_prompt   = strict_prompt,
                temperature   = 0.0,
                max_tokens    = 3000
            )
            items = _parse_json_response(raw)
        except Exception as e:
            logger.error(f"Retry failed: {e}")
            return []

    if not items:
        return []
    debug_logger.info("STAGE 1 - LLM parsed items: %d", len(items))

    items = _validate_items(items)
    debug_logger.info("STAGE 2 - validated items: %d", len(items))
    items = _enrich_with_metadata(items, results)
    debug_logger.info("STAGE 3 - metadata enriched items: %d", len(items))
    items = _post_validate_items(items)
    debug_logger.info("STAGE 4 - post-validated items: %d", len(items))
    items = _filter_valid_items(items)
    debug_logger.info("STAGE 5 - filtered items: %d", len(items))
    items = _deduplicate_items(items)
    debug_logger.info("STAGE 5.5 - deduplicated items: %d", len(items))
    verification_map = _verify_items_with_llm(items, context_string)
    if verification_map:
        for item in items:
            cid = str(item.get("chunk_id", "") or "").strip()
            if not cid:
                continue
            v = verification_map.get(cid)
            if not v:
                continue
            item["verified"] = v["verified"]
            item["verification_confidence"] = v["verification_confidence"]
            item["verification_evidence"] = v["verification_evidence"]
            stmt = build_violation_statement(item)
            if stmt:
                item["violation_statement"] = stmt
    items = _enforce_grounded_items(items, results)
    debug_logger.info("STAGE 6 - final output items: %d", len(items))
    
    return items


def generate_answer(
    query  : str,
    context: str
) -> str:
    from llm.prompt_templates import (
        ANSWER_SYSTEM_PROMPT,
        ANSWER_USER_PROMPT
    )

    if not query or not context:
        return "Insufficient context to answer this question."

    user_prompt = ANSWER_USER_PROMPT.format(
        query   = query,
        context = context
    )

    try:
        # ACCURACY FIX for Q&A Generation
        answer = call_groq(
            system_prompt = ANSWER_SYSTEM_PROMPT,
            user_prompt   = user_prompt,
            temperature   = 0.0, # Lock to zero to avoid Q&A hallucination
            max_tokens    = 1500
        )
        return answer
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        return f"Could not generate answer: {e}"

def stream_answer(
    query  : str,
    context: str
):
    from llm.prompt_templates import (
        ANSWER_SYSTEM_PROMPT,
        ANSWER_USER_PROMPT
    )
    from llm.groq_client import get_groq_client

    if not query or not context:
        yield "Insufficient context to answer this question."
        return

    user_prompt = ANSWER_USER_PROMPT.format(
        query   = query,
        context = context
    )
    
    model = os.getenv("GROQ_GENERATOR_MODEL", "deepseek-r1-distill-llama-70b")

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model       = model,
            messages    = [
                {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature = 0.0,
            max_tokens  = 1500,
            stream      = True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"Answer stream failed: {e}")
        yield f"Could not generate answer stream: {e}"

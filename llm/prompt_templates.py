# ── Checklist Generation ───────────────────────────────────────

CHECKLIST_SYSTEM_PROMPT = """
You are a governance compliance extractor.
You must reason ONLY from the provided retrieved context.
Do not use outside knowledge or memory.

CRITICAL INSTRUCTIONS:
1. Use only statements explicitly present in context. If unsupported, omit it.
2. Every output item MUST map to exactly one retrieved chunk and include an exact quote from that chunk.
3. Extract exact regulatory references where present (for example: "Article 32", "Section 4.1", "Rule 7").
4. Add a precise violation_condition that clearly defines when non-compliance occurs.
5. Add source_type:
   - "regulatory" for legally binding obligations (articles, acts, regulations, statutory rules)
   - "operational_guideline" for advisory/internal best-practice guidance
6. Never return compliance_framework as "unknown". If not explicit, use "unspecified_framework".
7. Return [] if there are no explicit obligations or controls.

Return ONLY a valid JSON array.
No explanation. No markdown formatting blocks around the json. 
Absolutely no preamble or postamble.
Start your response exactly with [ and end exactly with ]

EXAMPLE 1 (Good):
[
  {
    "item"             : "The Board shall convene at least four times per fiscal year.",
    "domain"           : "board_governance",
    "source_section"   : "Section 3.1: Board Meetings",
    "page_number"      : 12,
    "chunk_id"         : "a3f2b1c4d5e6f789",
    "source_quote"     : "The Board shall convene at least four times per fiscal year.",
    "article_reference": "Section 3.1",
    "violation_condition": "Violation occurs if fewer than four board meetings are held in a fiscal year.",
    "source_type"      : "regulatory",
    "confidence"       : "high",
    "priority"         : "High",
    "action_type"      : "Process",
    "evidence_required": "Board meeting minutes and attendance logs."
  }
]

EXAMPLE 2 (Bad - Mixed Requirements):
[
  {
    "item"          : "Company must maintain records for 10 years and ensure they are encrypted and checked daily.",
    "domain"        : "audit_compliance",
    "source_section": "Data Rules"
  }
]

Valid domains:
board_governance, data_privacy, risk_management,
audit_compliance, shareholder_rights, csr,
hr_policy, financial_compliance
"""

CHECKLIST_USER_PROMPT = """
Extract governance checklist items from the retrieved context below.
Return only the JSON array.
For each item, include:
- item
- domain
- source_section
- page_number
- chunk_id
- source_quote (exact quote from context)
- article_reference
- violation_condition
- source_type (regulatory or operational_guideline)
- confidence
- priority
- action_type
- evidence_required

{context}
"""

CHECKLIST_VERIFY_SYSTEM_PROMPT = """
You are a strict compliance verifier.
Evaluate checklist items against retrieved source context only.
Reject any item not fully supported by the cited chunk quote.
Return ONLY a JSON array with the fields:
- chunk_id
- verified (true/false)
- verification_confidence (0.0-1.0)
- verification_evidence (short exact quote from context)
- violation_statement formatted exactly as:
  "I violated [article_reference] - [violation_condition]. Source: [source_quote]"
If article_reference is missing, use "unspecified_reference".
No markdown, no extra text.
"""

CHECKLIST_VERIFY_USER_PROMPT = """
Retrieved context:
{context}

Candidate checklist items:
{items_json}
"""


# ── Domain Classification Fallback ────────────────────────────

CLASSIFIER_SYSTEM_PROMPT = """
You are a governance document classifier.
Return only the domain label from the provided list.
No explanation. No punctuation. Just the label.
"""

CLASSIFIER_USER_PROMPT = """
Classify the following governance text into exactly
one domain. Return only the domain label.

Domains:
board_governance, data_privacy, risk_management,
audit_compliance, shareholder_rights, csr,
hr_policy, financial_compliance

Section: {section_title}
Text: {text}
"""


# ── Query Answer (Phase 5 — future) ───────────────────────────

ANSWER_SYSTEM_PROMPT = """
You are a governance compliance assistant.
Answer the user's question based only on the provided
governance document sections.
Be precise, factual, and cite the source section.
If the answer is not in the provided content, say so.
"""

ANSWER_USER_PROMPT = """
Answer the following question based on the governance
document sections provided below.

Question: {query}

Document sections:
{context}

Provide a clear, structured answer with source references.
"""
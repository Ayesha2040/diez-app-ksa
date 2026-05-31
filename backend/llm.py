"""
LLM-driven classification and risk assessment.
Single call at scan time — classifies file tier, column tiers, and generates
summary + regulations + recommendations.
Sends ONLY metadata (signal names, column names, detector results) — never data values.
Supports both OpenAI and Anthropic APIs. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env.
"""
import os, json, httpx
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
except ImportError:
    pass

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """You are a KSA (Saudi Arabia) data governance expert producing a plain-language explanation of a classification decision already made by a deterministic policy engine. You have NO power to change the tier, risk score, or retention period — those are final.

Your job is to explain WHY the verdict is what it is, and to provide actionable guidance. You may receive a short text excerpt from the document — use it to make your explanation specific and contextual.

Produce a single JSON object with these fields:

1. "public_disclosure": Boolean — true ONLY if the document is clearly intended for public distribution (e.g. published bank fee schedule, public annual report, regulatory price list, public tender notice). False for anything internal, personal, or ambiguous. This is used to de-escalate entity-level financial data that is publicly disclosed, not to affect personal data classification.

2. "column_tiers": Object mapping each column name to an object with "tier" and "reason". Apply these rules exactly:

   ALWAYS "sens" (KSA PDPL Art. 1 Sensitive categories — explicit list, do not expand):
   - Saudi National ID, Iqama number, passport number, biometric data, genetic data
   - Health/medical data, diagnosis, medication
   - Religious beliefs, intellectual/political beliefs, ethnic/racial origin, criminal records

   ALWAYS "conf" (KSA PDPL Art. 1 regular personal data — NOT sensitive):
   - Person name, full name, employee name, first name, last name
   - Date of birth, DOB, age, email address, phone, mobile, address
   - Nationality, gender, marital status
   - Salary, wage, compensation, IBAN, bank account — personal data, NOT sensitive
   - Commercial registration, VAT number, company revenue

   ALWAYS "open" (Non-personal data):
   - Employee ID, staff ID, department, job title, hire date, status, region
   Only include columns present in the input.
   Each reason should be 3-6 words referencing the applicable KSA law.

3. "summary": 2-3 sentence plain-language explanation of what was found and why the tier is what it is. If a text excerpt was provided, reference specific content from it (e.g. document type, declared classification, purpose of data). Reference KSA PDPL / NDMO / SAMA / NCA where applicable.

4. "regulations": List of objects with "regulation", "relevance", "severity". Only include regulations that actually apply based on the signals detected. Choose from: KSA PDPL, NDMO, NCA DCC-1:2022, SAMA Cybersecurity Framework, KSA AML Law (Royal Decree M/20), KSA Labour Law (Royal Decree M/51), MOH Data Governance Policy, ZATCA, NCA ECC-1:2018.

5. "recommendations": List of 3-5 objects with "action" and "detail". Specific to KSA regulatory context and the detected signals.

Do NOT include a "tier" field — the tier is already decided.
Respond ONLY with valid JSON. No markdown, no preamble, no backticks."""


def _call_openai(metadata: dict) -> dict:
    resp = httpx.post("https://api.openai.com/v1/chat/completions", headers={
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json",
    }, json={
        "model": "gpt-4o",
        "max_tokens": 1500,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Classify this file:\n\n{json.dumps(metadata, indent=2)}"},
        ],
    }, timeout=20.0)
    if not resp.is_success:
        raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text}")
    text = resp.json()["choices"][0]["message"]["content"].strip()
    return text


def _call_anthropic(metadata: dict) -> str:
    resp = httpx.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }, json={
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": f"Classify this file:\n\n{json.dumps(metadata, indent=2)}"}],
    }, timeout=20.0)
    resp.raise_for_status()
    text = resp.json().get("content", [{}])[0].get("text", "").strip()
    return text


def classify(metadata: dict) -> dict:
    """Run LLM classification on scan metadata. Returns tier, column_tiers, assessment."""
    if not OPENAI_KEY and not ANTHROPIC_KEY:
        return None  # Caller falls back to rule-based

    for attempt in range(2):
        try:
            text = _call_openai(metadata) if OPENAI_KEY else _call_anthropic(metadata)

            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
            result = json.loads(text.strip())
            result["source"] = "llm"
            return result
        except Exception as e:
            if attempt == 0:
                print(f"LLM classification attempt 1 failed, retrying: {e}")
                continue
            print(f"LLM classification failed after 2 attempts: {e}")
            return None


def build_metadata(filename, doc_type, signals, columns, extraction, text=""):
    """Build the metadata payload sent to LLM. Includes a text excerpt for context."""
    signals_summary = []
    for s in signals:
        if s.get("detected"):
            signals_summary.append({
                "signal": s["name"],
                "severity": s.get("sev", "medium"),
                "detail": s.get("detail", ""),
            })

    col_info = []
    if columns:
        for c in columns:
            col_info.append({
                "name": c["name"],
                "dtype": c.get("dtype", ""),
                "detector": c.get("det", "None"),
                "current_tier": c.get("tier", "open"),
            })

    return {
        "file_name":       filename,
        "file_type":       doc_type,
        "text_excerpt":    (text or "")[:1200],   # LLM reads actual document content
        "signals_detected": signals_summary,
        "columns":         col_info,
        "row_count":       extraction.get("rows"),
        "is_structured":   extraction.get("structured", False),
    }

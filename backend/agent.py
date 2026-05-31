"""
Agentic detection layer — replaces the fixed detect → keyword → classify sequence.

The agent receives file metadata and uses Anthropic tool-use to decide which
detectors to run, in what order, and when it has enough signal to stop.
Falls back to full rule-based detection if no API key or agent call fails.

Tools available to the agent:
  run_pattern_detection  — regex patterns on unstructured text
  run_keyword_detection  — 18-category keyword scan (English + Arabic)
  run_column_detection   — structured file column analysis + sample validation
  finalize               — agent declares it has enough signal, returns result
"""
import os, json
import httpx
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
except ImportError:
    pass

from detectors import detect_patterns, detect_keywords, detect_columns

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

AGENT_SYSTEM = """You are a KSA data classification expert with access to detection tools.

You receive file metadata and must decide which tools to run to accurately classify the file.
Be efficient: run only what is needed.

Guidelines:
- Structured files (xlsx/csv): always run run_column_detection. Skip run_pattern_detection (causes false positives on formatted numbers).
- Unstructured files with sensitive names (kyc, salary, employee, health): run both run_pattern_detection and run_keyword_detection.
- Short policy or governance documents: run run_keyword_detection only.
- Strategy or board documents: run run_keyword_detection only.
- When you have enough findings, call finalize immediately — do not keep running tools.
- Maximum 3 tool calls before you must finalize.
"""

TOOLS = [
    {
        "name": "run_pattern_detection",
        "description": "Run regex pattern detection on text. Finds Saudi National IDs, Iqama numbers, IBANs, credit cards, SWIFT codes, emails, KSA mobile numbers, VAT numbers, credentials, and monetary values. Use for unstructured files (txt, docx, pdf) only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Extracted text to scan (max 5000 chars sent to avoid large payloads)"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "run_keyword_detection",
        "description": "Run keyword detection across 18 categories: health/medical, biometric, criminal, religious, ethnic, genetic, minors, AML/KYC, PEP, sanctions, suspicious activity, strategic content, employment, financial, security controls, legal privilege, governance, customer data. Works for both English and Arabic text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to scan"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "run_column_detection",
        "description": "For structured files (xlsx/csv): detect sensitive columns by name and sample data validation. Returns entity counts and per-column tier assignments. More accurate than text regex for structured data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cols": {
                    "type": "array",
                    "description": "Column metadata from extractor (name, dtype, samples)",
                    "items": {"type": "object"},
                },
                "rows": {"type": "integer", "description": "Number of data rows"},
            },
            "required": ["cols", "rows"],
        },
    },
    {
        "name": "finalize",
        "description": "Finalize detection — call this when you have collected enough signal. The classification engine will use your collected findings to assign the tier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "1-2 sentence explanation of what you found and why you stopped",
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Your confidence in the completeness of detection",
                },
            },
            "required": ["reasoning", "confidence"],
        },
    },
]


def run_agent(filename: str, extraction: dict) -> tuple:
    """
    Agentic detection. Returns (entities, keywords, col_details, hits).
    Falls back to full rule-based detection if agent is unavailable or fails.
    Per spec: agent is non-load-bearing — fallback always produces a verdict.
    """
    if not ANTHROPIC_KEY:
        return _rule_based(extraction)

    try:
        return _agent_loop(filename, extraction)
    except Exception as e:
        print(f"Agent failed, falling back to rule-based: {e}")
        return _rule_based(extraction)


def _agent_loop(filename: str, extraction: dict) -> tuple:
    text = extraction.get("text", "")
    cols = extraction.get("cols", [])
    rows = extraction.get("rows", 0) or 0
    is_structured = extraction.get("structured", False)

    col_names = [c["name"] for c in cols[:20]] if cols else []
    text_preview = text[:400] if text else ""

    initial = (
        f"File: {filename}\n"
        f"Type: {'Structured (xlsx/csv)' if is_structured else 'Unstructured'}\n"
        f"Rows: {rows if rows else 'N/A'}\n"
        f"Columns: {col_names if col_names else 'N/A'}\n"
        f"Text preview: {text_preview if text_preview else 'N/A'}\n\n"
        "Decide which detection tools to run."
    )

    messages = [{"role": "user", "content": initial}]
    entities: dict = {}
    keywords: dict = {}
    col_details = None
    all_hits: list = []

    for _ in range(4):  # max 4 rounds to stay within budget
        resp = _call_anthropic(messages)
        content_blocks = resp.get("content", [])

        tool_results = []
        finalized = False

        for block in content_blocks:
            if block.get("type") != "tool_use":
                continue

            tool_name = block["name"]
            tool_input = block.get("input", {})
            tool_id = block["id"]

            if tool_name == "run_pattern_detection":
                scan_text = tool_input.get("text", text)[:8000]
                result_entities, result_hits = detect_patterns(scan_text)
                entities.update(result_entities)
                all_hits.extend(result_hits)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(result_entities),
                })

            elif tool_name == "run_keyword_detection":
                scan_text = tool_input.get("text", text)
                result_kw, result_hits = detect_keywords(scan_text)
                for cat, matches in result_kw.items():
                    keywords.setdefault(cat, [])
                    keywords[cat] = list(set(keywords[cat] + matches))
                all_hits.extend(result_hits)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps({k: len(v) for k, v in result_kw.items()}),
                })

            elif tool_name == "run_column_detection":
                agent_cols = tool_input.get("cols", cols)
                agent_rows = tool_input.get("rows", rows)
                result_entities, result_cols, result_hits = detect_columns(agent_cols, agent_rows)
                entities.update(result_entities)
                col_details = result_cols
                all_hits.extend(result_hits)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps({
                        "entities_found": result_entities,
                        "columns_classified": len(result_cols),
                    }),
                })

            elif tool_name == "finalize":
                reasoning = tool_input.get("reasoning", "")
                print(f"Agent finalized: {reasoning}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": "Detection complete.",
                })
                finalized = True

        if tool_results:
            messages.append({"role": "assistant", "content": content_blocks})
            messages.append({"role": "user", "content": tool_results})

        if finalized or resp.get("stop_reason") == "end_turn":
            break

    return entities, keywords, col_details, all_hits


def _call_anthropic(messages: list) -> dict:
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",  # fast + cheap for planning
            "max_tokens": 1024,
            "system": AGENT_SYSTEM,
            "tools": TOOLS,
            "messages": messages,
        },
        timeout=20.0,
    )
    resp.raise_for_status()
    return resp.json()


def _rule_based(extraction: dict) -> tuple:
    """Full rule-based fallback — runs all detectors unconditionally."""
    text = extraction.get("text", "")
    cols = extraction.get("cols", [])
    rows = extraction.get("rows", 0) or 0

    col_details = None
    all_hits: list = []

    if extraction.get("structured") and cols:
        entities, col_details, col_hits = detect_columns(cols, rows)
        all_hits.extend(col_hits)
        # Also run keyword detection on structured text (for document context)
        _, kw_hits = detect_keywords(text)
        all_hits.extend(kw_hits)
    else:
        entities, pat_hits = detect_patterns(text)
        all_hits.extend(pat_hits)

    keywords, kw_hits = detect_keywords(text)
    if not extraction.get("structured"):
        all_hits.extend(kw_hits)

    return entities, keywords, col_details, all_hits

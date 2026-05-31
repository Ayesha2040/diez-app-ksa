"""
Pipeline orchestrator: extract → detect (agent) → classify → score → retain.
The policy engine (engine.py + frameworks.py) is the single source of truth for
the tier. The LLM never changes the tier — it only generates the plain-language
explanation after the verdict is final.
"""
import hashlib
from pathlib import Path

from extractors import EXTRACTORS
from engine import (classify_doc_type, build_signals, calc_risk_score,
                    calc_confidence, calc_breakdown, compute_action,
                    determine_severity, redact_preview)
from frameworks import determine_tier, determine_pdpl_tier, build_fw_note
from llm import classify as llm_explain, build_metadata as llm_build_metadata
from agent import run_agent
from retention import assign_retention


def scan(filename: str, content: bytes) -> dict:
    """Full scan pipeline. Returns a result dict with tier, risk, confidence, action, retention."""
    ext  = Path(filename).suffix.lower()
    size = len(content)
    size_str = f"{size / 1024:.0f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"

    # ── 1. EXTRACT ──────────────────────────────────────────────────────────
    extractor = EXTRACTORS.get(ext)
    if not extractor:
        return {"error": f"Unsupported file type: {ext}", "name": filename}

    extraction = extractor(content)
    text = extraction.get("text", "")

    # ── 2. DETECT (agent or rule-based fallback) ─────────────────────────────
    entities, keywords, col_details, hits = run_agent(filename, extraction)

    # ── 3. COVERAGE ──────────────────────────────────────────────────────────
    if extraction.get("structured"):
        total_cols   = len(extraction.get("cols", []))
        matched_cols = len([h for h in hits if "column" in h.get("method", "")])
        coverage = matched_cols / max(total_cols, 1) if total_cols else 0.5
    else:
        chars_read  = min(len(text), 15000)
        chars_total = extraction.get("chars_total", chars_read) or chars_read
        coverage    = min(1.0, chars_read / max(chars_total, 1))

    # ── 4. CLASSIFY ──────────────────────────────────────────────────────────
    doc_type = classify_doc_type(filename, extraction, entities, keywords)
    signals  = build_signals(doc_type, entities, keywords, extraction)

    # ── 5. POLICY ENGINE — single source of truth for the tier ───────────────
    rows_count = extraction.get("rows") or 0
    tier       = determine_tier(signals, rows_count)
    tier_pdpl  = determine_pdpl_tier(signals, rows_count)   # PDPL excludes entity-only signals
    severity   = determine_severity(signals)
    breakdown = calc_breakdown(entities, keywords)
    # fw_note uses the correct tier per framework
    fw_note   = build_fw_note(tier, doc_type, signals, tier_pdpl=tier_pdpl)

    # ── 6. CONFLICT DETECTION ─────────────────────────────────────────────────
    fn_lower     = filename.lower()
    public_hints = any(k in fn_lower for k in ("public", "open", "registry", "template", "sample"))
    has_sensitive = any(h.get("severity") in ("critical", "high") for h in hits)
    conflict = public_hints and has_sensitive

    # ── 7. RISK + CONFIDENCE (separate tracks) ──────────────────────────────
    risk_score = calc_risk_score(signals, extraction.get("rows") or 0)
    confidence = calc_confidence(hits, coverage, conflict=conflict)

    # ── 8. ACTION ROUTING ────────────────────────────────────────────────────
    action = compute_action(risk_score, confidence)

    # ── 9. DETECTORS LIST (for scan table display) ────────────────────────────
    detected_signals = [s for s in signals if s.get("detected") and s["sev"] != "info"]
    detectors = []
    for s in detected_signals[:4]:
        if s.get("entities"):
            detectors.append(s["entities"][0].split(" × ")[0])
        else:
            detectors.append(s["name"][:20])

    # ── 10. COLUMN METADATA ───────────────────────────────────────────────────
    columns = col_details  # built by detect_columns(), no second pass

    # ── 11. EXPLAIN (LLM — no decision power, explain-only) ─────────────────
    llm_result = None
    try:
        metadata   = llm_build_metadata(filename, doc_type, signals, columns, extraction, text)
        llm_result = llm_explain(metadata)
    except Exception as e:
        print(f"LLM explain skipped: {e}")

    # Apply LLM column reasoning text only — tier is NOT overridden
    if llm_result and llm_result.get("source") == "llm":
        col_tiers = llm_result.get("column_tiers", {})

        FLOOR_SENS_KEYS = {"credit_card", "national_id", "saudi_id", "iqama", "passport", "biometric"}
        CAP_CONF_KEYS   = {"name", "full_name", "first_name", "last_name", "person_name",
                           "display_name", "employee_name", "contact_name",
                           "email", "phone", "mobile", "tel", "address", "dob",
                           "date_of_birth", "birth_date", "birth", "age",
                           "nationality", "citizenship", "gender", "sex", "marital",
                           "trade_licence", "company", "employer", "revenue", "amount",
                           "iban", "bank_account",
                           "salary", "wage", "compensation", "basic_pay", "gross", "net_pay",
                           "allowance", "bonus", "incentive", "deduction", "payroll"}
        CAP_OPEN_KEYS   = {"employee_id", "employee_num", "employee_no", "emp_id", "emp_no",
                           "emp_num", "staff_id", "staff_num", "worker_id", "worker_num",
                           "department", "dept", "division", "cost_centre", "cost_center",
                           "job_title", "position", "designation", "grade", "band", "level",
                           "hire_date", "start_date", "join_date", "contract_date",
                           "status", "activity", "industry", "region"}
        TIER_ORDER = {"open": 0, "conf": 1, "sens": 2, "secret": 3}

        if columns and col_tiers:
            for col in columns:
                ct = col_tiers.get(col["name"])
                if not ct:
                    continue
                new_tier = ct.get("tier", col["tier"]) if isinstance(ct, dict) else ct
                if isinstance(ct, dict):
                    col["reason"] = ct.get("reason", "")
                n = col["name"].lower().replace(" ", "_").replace("-", "_")
                if any(k in n for k in FLOOR_SENS_KEYS):
                    col["tier"] = new_tier if TIER_ORDER.get(new_tier, 0) >= 2 else "sens"
                elif any(k in n for k in CAP_CONF_KEYS):
                    col["tier"] = new_tier if TIER_ORDER.get(new_tier, 0) <= 1 else "conf"
                elif any(k in n for k in CAP_OPEN_KEYS):
                    col["tier"] = "open"
                else:
                    col["tier"] = new_tier

    # ── 12. RETENTION ─────────────────────────────────────────────────────────
    retention = assign_retention({"signals": signals, "tier": tier,
                                  "detectors": detectors, "llmAssessment": llm_result})

    return {
        "id":          hashlib.md5(content[:4096]).hexdigest()[:8],  # content-based, not name+size
        "name":        filename,
        "source":      "Upload",
        "sourceTag":   "UP",
        "sourceColor": "#534AB7",
        "folder":      "Uploaded",
        "docType":     doc_type,
        "size":        size_str,
        "rows":        str(extraction["rows"]) if extraction.get("rows") else None,

        # Classification — NDMO tier is primary; PDPL tier is computed separately
        # because PDPL only governs personal data (entity-only signals → "open")
        "tier":        tier,
        "tierPdpl":    tier_pdpl,
        "severity":    severity,
        "fwNote":      fw_note,

        # Scoring (separate tracks)
        "riskScore":   risk_score,
        "conf":        confidence,
        "coverage":    round(coverage, 2),
        "conflict":    conflict,

        # Action routing
        "action":      action,

        # Detection detail
        "detectors":   detectors,
        "detBreakdown": breakdown,
        "signals":     signals,
        "columns":     columns,

        # LLM explanation (no tier power)
        "llmAssessment": llm_result,

        # Content preview (redacted)
        "contentPreview": redact_preview(text) if not extraction.get("structured") else None,

        # Retention
        "retention":   retention,
    }

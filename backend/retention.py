"""
Retention period assignment using client-specific record class schedule.
Maps each scan to one of 37 Authoritative Record Classes, then applies
the client-defined retention period for that class.
"""
from datetime import date

# ═══════════════════════════════════════════
# CLIENT RETENTION SCHEDULE — 37 record classes
# ═══════════════════════════════════════════

CLIENT_SCHEDULE: dict[str, dict] = {
    "Audit & Assurance Records":               {"years": 10, "action": "archive"},
    "Business Categorization Records":          {"years":  5, "action": "review"},
    "Business Impact Records":                  {"years":  5, "action": "review"},
    "Business Recovery Records":                {"years":  5, "action": "review"},
    "Business Requirements":                    {"years":  5, "action": "review"},
    "Communication Records":                    {"years":  5, "action": "review"},
    "Compliance & Regulatory Records":          {"years": 10, "action": "secure_delete"},
    "Contracts & Agreements Records":           {"years": 10, "action": "archive"},
    "Customer & Supplier Records":              {"years": 10, "action": "archive"},
    "Customer Care Records":                    {"years":  3, "action": "review"},
    "Customer Relationship Management Records": {"years":  3, "action": "review"},
    "Daily Reports":                            {"years":  3, "action": "review"},
    "Employment Records":                       {"years": 10, "action": "secure_delete"},
    "Environmental Records":                    {"years": 10, "action": "archive"},
    "Financial Records":                        {"years": 10, "action": "archive"},
    "Financial Reports":                        {"years": 10, "action": "archive"},
    "Financial Transactions Records":           {"years": 10, "action": "secure_delete"},
    "Incident Management Records":              {"years":  5, "action": "review"},
    "Internal policies and Procedures":         {"years": 10, "action": "archive"},
    "Inventory & Asset Management Records":     {"years": 10, "action": "archive"},
    "Legal & Regulatory Compliance Records":    {"years": 10, "action": "secure_delete"},
    "Marketing Records":                        {"years":  3, "action": "review"},
    "Miscellaneous Records":                    {"years":  3, "action": "review"},
    "Monthly Reports":                          {"years":  3, "action": "review"},
    "Operational Records":                      {"years":  3, "action": "review"},
    "Organizational Records":                   {"years":  5, "action": "review"},
    "Performance & KPI Records":                {"years":  5, "action": "review"},
    "Procurement Records":                      {"years": 10, "action": "archive"},
    "Project Management Records":               {"years": 10, "action": "archive"},
    "Research & Development Records":           {"years": 10, "action": "archive"},
    "Risk Management Records":                  {"years": 10, "action": "archive"},
    "Sales Records":                            {"years": 10, "action": "archive"},
    "Strategic Planning Records":               {"years": 10, "action": "secure_delete"},
    "Tax & Accounting Records":                 {"years": 10, "action": "archive"},
    "Technical Records":                        {"years": 10, "action": "archive"},
    "Training & Development Records":           {"years":  5, "action": "review"},
    "Warranty Claims":                          {"years":  3, "action": "review"},
}

RECORD_CLASS_NAMES = list(CLIENT_SCHEDULE.keys())


# ═══════════════════════════════════════════
# RULES-BASED RECORD CLASS MAPPER
# Deterministic: signal + doc_type → record class
# ═══════════════════════════════════════════

def classify_record_class_rules(doc_type: str, signals: list, tier: str) -> str:
    detected = {s["name"] for s in signals if s.get("detected") and s.get("sev") != "info"}

    if "AML/CFT regulated data" in detected:
        return "Compliance & Regulatory Records"
    if "Credentials / system access" in detected:
        return "Technical Records"
    if doc_type in ("KYC file", "KYC data file"):
        return "Compliance & Regulatory Records"
    if "Sensitive personal data" in detected:
        return "Legal & Regulatory Compliance Records"
    if doc_type == "Strategy document":
        return "Strategic Planning Records"
    if doc_type == "Policy document":
        return "Internal policies and Procedures"
    if doc_type == "Contract":
        return "Contracts & Agreements Records"
    if "Employment data linked to persons" in detected:
        return "Employment Records"
    if "Financial data linked to persons" in detected:
        return "Financial Transactions Records"
    if "Linkable identity" in detected:
        return "Customer & Supplier Records"
    if "Private entity data" in detected:
        return "Financial Records"
    if doc_type == "Governance document":
        return "Organizational Records"
    if doc_type in ("Data file", "KYC data file"):
        return "Operational Records"
    if "Strategic / classified content" in detected:
        return "Strategic Planning Records"
    if tier in ("sens", "secret"):
        return "Legal & Regulatory Compliance Records"
    if tier == "conf":
        return "Operational Records"
    return "Miscellaneous Records"


# ═══════════════════════════════════════════
# RETENTION ASSIGNMENT
# ═══════════════════════════════════════════

def assign_retention(scan_result: dict) -> dict:
    """
    Assign retention by mapping the document to a record class,
    then looking up the client schedule.
    record_class comes from LLM (AI mode) or rules (rules mode).
    """
    signals  = scan_result.get("signals", [])
    doc_type = scan_result.get("docType", "Document")
    tier     = scan_result.get("tier", "open")
    llm      = scan_result.get("llmAssessment") or {}

    # Use AI-assigned record class if available, else rules.
    # If the document tier is "open" (publicly disclosed), cap the retention
    # at Miscellaneous Records — open data has no mandatory retention obligation.
    if tier == "open":
        record_class = "Miscellaneous Records"
        class_method = "rules"
    else:
        ai_class = llm.get("record_class")
        if ai_class and ai_class in CLIENT_SCHEDULE:
            record_class = ai_class
            class_method = "ai"
        else:
            record_class = classify_record_class_rules(doc_type, signals, tier)
            class_method = "rules"

    schedule = CLIENT_SCHEDULE.get(record_class, {"years": 3, "action": "review"})
    years  = schedule["years"]
    action = schedule["action"]

    today = date.today()
    if years > 0:
        try:
            review_date = today.replace(year=today.year + years)
        except ValueError:
            review_date = today.replace(year=today.year + years, day=28)
        days_remaining = (review_date - today).days
        status = "overdue" if days_remaining < 0 else "review_due" if days_remaining <= 90 else "active"
        review_date_str = review_date.isoformat()
    else:
        review_date_str = None
        days_remaining  = None
        status          = "active"

    return {
        "recordClass":    record_class,
        "classMethod":    class_method,
        "periodYears":    years,
        "basis":          f"Client retention schedule — {record_class}",
        "reviewDate":     review_date_str,
        "disposalAction": action,
        "status":         status,
        "daysRemaining":  days_remaining,
    }

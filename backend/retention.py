"""
Retention period assignment — maps scan results to legally-grounded retention periods.
KSA regulatory basis: AML Law, PDPL Art. 18, Labour Law, MOH Policy, SAMA, ZATCA.
Always takes the longest applicable period when multiple rules match.
"""
from datetime import date

# Rules are evaluated in order; all that match are collected, longest period wins.
RETENTION_RULES = [
    {
        "signal":  "AML/CFT regulated data",
        "years":   10,
        "basis":   "KSA AML Law (Royal Decree M/20) — CDD and KYC records retained 10 years after relationship ends",
        "action":  "secure_delete",
    },
    {
        "keyword": "health_medical",
        "years":   10,
        "basis":   "MOH Data Governance Policy — medical and health records retained 10 years",
        "action":  "secure_delete",
    },
    {
        "signal":  "Financial data linked to persons",
        "years":   10,
        "basis":   "SAMA Cybersecurity Framework — financial records linked to persons retained 10 years",
        "action":  "secure_delete",
    },
    {
        "entity":  "VAT Registration (ZATCA)",
        "years":   10,
        "basis":   "ZATCA Regulations — VAT and tax records retained 10 years",
        "action":  "archive",
    },
    {
        "signal":  "Strategic / classified content",
        "years":   7,
        "basis":   "NDMO Top Secret / NCA DCC-1:2022 — strategic classified records retained 7 years",
        "action":  "secure_delete",
    },
    {
        "signal":  "Sensitive personal data",
        "years":   5,
        "basis":   "KSA PDPL Art. 18 — sensitive personal data retained only as long as necessary; 5-year default",
        "action":  "secure_delete",
    },
    {
        "signal":  "Linkable identity",
        "years":   5,
        "basis":   "KSA PDPL Art. 18 — personal data of identifiable persons retained only as long as necessary; 5-year default",
        "action":  "secure_delete",
    },
    {
        "signal":  "Employment data linked to persons",
        "years":   2,
        "basis":   "KSA Labour Law (Royal Decree M/51) — employee records retained 2 years after end of employment",
        "action":  "archive",
    },
    {
        "signal":  "Credentials / system access",
        "years":   3,
        "basis":   "NCA ECC-1:2018 — credential and access records retained 3 years for audit trail",
        "action":  "secure_delete",
    },
    {
        "tier":    "conf",
        "years":   3,
        "basis":   "NDMO Confidential — internal business records retained 3 years minimum",
        "action":  "review",
    },
    {
        "tier":    "open",
        "years":   0,
        "basis":   "No mandatory retention — open/public data; discretionary disposal",
        "action":  "discretionary",
    },
]


def assign_retention(scan_result: dict) -> dict:
    """
    Assign a retention period to a scan result.
    Returns a retention dict added to the scan result.
    """
    signals = scan_result.get("signals", [])
    keywords_detected = set()
    # Extract keyword categories from llmAssessment or signals entities
    llm = scan_result.get("llmAssessment") or {}
    regs = llm.get("regulations", [])
    if any("MOH" in (r.get("regulation") or "") for r in regs):
        keywords_detected.add("health_medical")

    # Also check signal entities for health keywords
    for s in signals:
        if s.get("detected") and "health" in s.get("name", "").lower():
            keywords_detected.add("health_medical")
        entities_text = " ".join(s.get("entities", []))
        if "health" in entities_text.lower() or "medical" in entities_text.lower():
            keywords_detected.add("health_medical")

    detected_signal_names = {s["name"] for s in signals if s.get("detected")}
    detected_entities = set(scan_result.get("detectors", []))
    tier = scan_result.get("tier", "open")

    best_years = 0
    best_basis = "No mandatory retention — discretionary"
    best_action = "discretionary"
    matched_rules = []

    for rule in RETENTION_RULES:
        matched = False
        if "signal" in rule and rule["signal"] in detected_signal_names:
            matched = True
        elif "keyword" in rule and rule["keyword"] in keywords_detected:
            matched = True
        elif "entity" in rule and rule["entity"] in detected_entities:
            matched = True
        elif "tier" in rule and rule["tier"] == tier and "signal" not in rule:
            matched = True

        if matched:
            matched_rules.append(rule)
            if rule["years"] > best_years:
                best_years = rule["years"]
                best_basis = rule["basis"]
                best_action = rule["action"]

    today = date.today()
    if best_years > 0:
        try:
            review_date = today.replace(year=today.year + best_years)
        except ValueError:
            # Feb 29 edge case
            review_date = today.replace(year=today.year + best_years, day=28)
        days_remaining = (review_date - today).days
        if days_remaining < 0:
            status = "overdue"
        elif days_remaining <= 90:
            status = "review_due"
        else:
            status = "active"
        review_date_str = review_date.isoformat()
    else:
        review_date_str = None
        days_remaining = None
        status = "active"

    return {
        "periodYears":    best_years,
        "basis":          best_basis,
        "reviewDate":     review_date_str,
        "disposalAction": best_action,
        "status":         status,
        "daysRemaining":  days_remaining,
        "regulationsApplied": [r["basis"].split(" — ")[0] for r in matched_rules],
    }

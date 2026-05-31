"""
Framework definitions: NDMO + NCA DCC-1:2022 (KSA).
Tier mapping logic. Framework notes generator.
Served via /api/frameworks so frontend is data-driven.
"""

FRAMEWORKS = {
    "ndmo": {
        "id": "ndmo",
        "label": "NDMO",
        "full": "Saudi National Data Management Office",
        "authority": "SDAIA — Saudi Data and AI Authority",
        "tiers": {
            "open":   {"label": "Public",       "bg": "#EAF3DE", "fg": "#27500A", "order": 0},
            "conf":   {"label": "Confidential", "bg": "#FAEEDA", "fg": "#633806", "order": 1},
            "sens":   {"label": "Secret",       "bg": "#FCEBEB", "fg": "#791F1F", "order": 2},
            "secret": {"label": "Top Secret",   "bg": "#EEEDFE", "fg": "#3C3489", "order": 3},
        },
    },
    "pdpl": {
        "id": "pdpl",
        "label": "KSA PDPL",
        "full": "KSA Personal Data Protection Law",
        "authority": "SDAIA — Saudi Data and AI Authority",
        "tiers": {
            "open":   {"label": "Non-personal data",           "bg": "#EAF3DE", "fg": "#27500A", "order": 0},
            "conf":   {"label": "Personal data",               "bg": "#FAEEDA", "fg": "#633806", "order": 1},
            "sens":   {"label": "Sensitive personal data",     "bg": "#FCEBEB", "fg": "#791F1F", "order": 2},
            "secret": {"label": "Sensitive data — restricted", "bg": "#EEEDFE", "fg": "#3C3489", "order": 3},
        },
    },
}


# Signals that involve personal data of identifiable individuals under PDPL.
# "Private entity data" is explicitly excluded — PDPL does not apply to entity
# financial data (fee schedules, price lists, company financials, etc.).
_PDPL_PERSONAL_SIGNALS = {
    "Linkable identity",
    "Financial data linked to persons",
    "Sensitive personal data",
    "AML/CFT regulated data",
    "Employment data linked to persons",
    "Personal data",
    "Credentials / system access",
}


def determine_pdpl_tier(signals: list, rows: int = 0) -> str:
    """
    PDPL-specific tier — only counts signals that involve personal data of
    identifiable individuals. 'Private entity data' maps to 'open' under PDPL
    because PDPL does not govern entity-level financial or business data.
    """
    pdpl_signals = [s for s in signals if s.get("name") in _PDPL_PERSONAL_SIGNALS]
    if not pdpl_signals:
        return "open"
    return determine_tier(pdpl_signals, rows)


def determine_tier(signals: list, rows: int = 0) -> str:
    det = [s for s in signals if s.get("detected")]
    if not det:
        return "open"

    sevs = [s["sev"] for s in det]
    has_strat_high = any(s["name"] == "Strategic / classified content" and s["sev"] in ("high", "critical") for s in det)
    has_creds      = any(s["name"] == "Credentials / system access" for s in det)
    has_aml        = any(s["name"] == "AML/CFT regulated data" for s in det)
    is_bulk        = rows > 1000

    if has_strat_high or has_creds:          return "secret"
    if has_aml and is_bulk:                  return "secret"   # bulk AML → Top Secret
    if "critical" in sevs and is_bulk:       return "secret"   # bulk sensitive PII → Top Secret
    if "critical" in sevs:                   return "sens"
    if "high" in sevs:                       return "sens"
    if "medium" in sevs:                     return "conf"
    return "open"


def determine_severity(signals: list) -> str:
    det = [s for s in signals if s.get("detected")]
    if not det:
        return "low"
    for sv in ["critical", "high", "medium", "low", "info"]:
        if any(s["sev"] == sv for s in det):
            return sv
    return "low"


def build_fw_note(tier: str, doc_type: str, signals: list, tier_pdpl: str = None) -> dict:
    notes = {}
    for fw_id, fw in FRAMEWORKS.items():
        # Use PDPL-specific tier for the PDPL framework note
        effective_tier = (tier_pdpl if tier_pdpl and fw_id == "pdpl" else tier)
        tier_label = fw["tiers"][effective_tier]["label"]

        if effective_tier == "open":
            if fw_id == "ndmo":
                notes[fw_id] = f"No sensitive data detected. Classified {tier_label} under NDMO policy. Suitable for publication on Saudi Open Data Platform (data.gov.sa)."
            else:
                notes[fw_id] = f"KSA PDPL does not apply — no personal data present. No consent or data subject rights obligations. Suitable for unrestricted sharing."
        elif effective_tier == "secret":
            if fw_id == "ndmo":
                notes[fw_id] = f"Classified {tier_label} under NDMO policy. Access restricted to named individuals only. SDAIA approval required before any exchange. Cross-border transfer prohibited without SDAIA sign-off per KSA PDPL Art. 29."
            else:
                notes[fw_id] = f"KSA PDPL Art. 1 Sensitive — explicit consent mandatory (Art. 5). Legitimate interest NOT valid for sensitive data. DPO appointment required. Cross-border transfer requires SDAIA adequacy assessment (Art. 29). Penalties: up to SAR 3M / 2 years imprisonment for unauthorised disclosure."
        elif effective_tier == "sens":
            if fw_id == "ndmo":
                notes[fw_id] = f"Classified {tier_label} under NDMO policy. Mandatory encryption at rest and in transit. Explicit consent required per KSA PDPL Art. 5. DPO appointment required if sensitive data processing is a core activity."
            else:
                notes[fw_id] = f"KSA PDPL Art. 1 Sensitive — contains one or more sensitive categories (health, biometric, genetic, criminal, religious/political beliefs, ethnic origin, unknown parental origin). Explicit consent mandatory (Art. 5). Cannot process for marketing purposes."
        else:  # conf
            if fw_id == "ndmo":
                notes[fw_id] = f"Classified {tier_label} under NDMO policy. Shareable with authorised entities under a data-sharing agreement. KSA PDPL Art. 1 personal data obligations apply."
            else:
                notes[fw_id] = f"KSA PDPL Art. 1 — personal data of identifiable natural persons. Lawful basis required for processing. Data subject rights apply: access, correction, erasure, restriction. Breach notification to SDAIA within 72 hours."

        # Doc-type specific additions
        if doc_type == "Policy document":
            notes[fw_id] += " Internal governance document — not for public release."
        elif doc_type in ("KYC file", "KYC data file"):
            notes[fw_id] += " AML/CFT regulated — access restricted to compliance function per SAMA AML guidelines."
        elif doc_type == "Strategy document":
            notes[fw_id] += " Strategic content — named-individual access only."

    return notes

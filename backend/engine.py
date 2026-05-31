"""
Classification engine: document-type classifier, signal analysis,
risk scoring, confidence scoring, action routing.

Risk and confidence are computed on separate tracks per the spec:
- Risk: intrinsic to the DATA (impact if leaked) — max+breadth+volume+linkage
- Confidence: reliability of the VERDICT — detection strength + corroboration + coverage
"""
import re
from math import log10
from collections import defaultdict
from detectors import has_credentials

# ═══════════════════════════════════════════
# DOCUMENT-TYPE CLASSIFIER
# ═══════════════════════════════════════════

def classify_doc_type(filename: str, extraction: dict, entities: dict, keywords: dict) -> str:
    fn = filename.lower()

    if extraction.get("structured") and extraction.get("rows", 0) > 0:
        if "aml_kyc" in keywords:
            return "KYC data file"
        return "Data file"

    if any(k in fn for k in ["kyc", "due_diligence", "cdd", "edd", "aml"]):
        return "KYC file"
    if "aml_kyc" in keywords and len(keywords.get("aml_kyc", [])) >= 2:
        return "KYC file"

    if any(k in fn for k in ["policy", "procedure", "guideline", "standard", "governance"]):
        return "Policy document"
    if "security_controls" in keywords and len(keywords.get("security_controls", [])) >= 3:
        return "Policy document"

    if any(k in fn for k in ["strategy", "board", "strategic", "roadmap"]):
        return "Strategy document"
    if "strategic_content" in keywords and len(keywords.get("strategic_content", [])) >= 3:
        return "Strategy document"

    if any(k in fn for k in ["contract", "agreement", "nda", "mou", "sla"]):
        return "Contract"

    if any(k in fn for k in ["template", "form", "application"]):
        return "Form template"

    if "governance" in keywords and len(keywords.get("governance", [])) >= 2:
        return "Governance document"

    return "Document"


# ═══════════════════════════════════════════
# SIGNAL ANALYSIS ENGINE — 9 signals
# ═══════════════════════════════════════════

def build_signals(doc_type: str, entities: dict, keywords: dict, extraction: dict) -> list:
    signals = []
    rows = extraction.get("rows") or 1
    is_policy   = doc_type == "Policy document"
    is_kyc      = doc_type in ("KYC file", "KYC data file")
    is_strategy = doc_type == "Strategy document"

    strong_ids = {"Saudi National ID", "Iqama Number", "Passport"}
    has_strong_id = bool(strong_ids & set(entities.keys()))
    has_name  = "PERSON name" in entities
    has_email = "Email address" in entities

    # ── 1. LINKABLE IDENTITY ──
    if not is_policy:
        link_ents = []
        link_detected = False
        for eid in ["Saudi National ID", "Iqama Number", "Passport"]:
            if eid in entities:
                link_ents.append(f"{eid} × {entities[eid]:,}")
                link_detected = True
        if has_name:
            link_ents.append(f"PERSON name × {entities['PERSON name']:,}")
            link_detected = True
        for pk in ["Email address", "KSA mobile", "KSA landline", "Phone", "Address", "Nationality"]:
            if pk in entities:
                lbl = {"Email address": "Email", "KSA mobile": "KSA mobile", "KSA landline": "KSA landline"}.get(pk, pk)
                link_ents.append(f"{lbl} × {entities[pk]:,}")
        if "Commercial Registration (CR)" in entities and is_kyc:
            link_ents.append(f"Commercial Registration × {entities['Commercial Registration (CR)']:,}")

        if link_detected:
            if has_strong_id and rows > 10: sev = "critical"
            elif has_strong_id:             sev = "critical"
            elif has_name and has_email and rows > 100: sev = "high"
            else: sev = "medium"
            signals.append({"name": "Linkable identity", "sev": sev, "detected": True, "entities": link_ents,
                "detail": f"Personal identifiers that uniquely identify {rows:,} individual{'s' if rows != 1 else ''}",
                "law": {"ndmo": "KSA PDPL Art. 1 — personal data of identifiable natural persons.", "pdpl": "KSA PDPL Art. 1 — personal identifiers. Art. 5: explicit consent required for sensitive IDs."}})

    # ── 2. FINANCIAL DATA LINKED TO PERSONS ──
    fin_ents = []
    has_fin = False
    for fk in ["Salary (SAR)", "SAR monetary value", "USD monetary value"]:
        if fk in entities:
            fin_ents.append(f"{fk} × {entities[fk]:,}")
            has_fin = True
    for ik in ["IBAN (Saudi)", "IBAN (international)", "Credit card", "SWIFT/BIC"]:
        if ik in entities:
            fin_ents.append(f"{ik} × {entities[ik]:,}")
            has_fin = True

    if has_fin and has_strong_id and not is_policy:
        sev = "critical" if rows > 100 else "high"
        signals.append({"name": "Financial data linked to persons", "sev": sev, "detected": True, "entities": fin_ents,
            "detail": "Financial values directly tied to identifiable individuals",
            "law": {"ndmo": "KSA PDPL Art. 1 — financial personal data. SAMA Cybersecurity Framework.", "pdpl": "KSA PDPL Art. 1 — financial identifiers linked to persons. SAMA framework mandates encryption."}})
    elif has_fin and (has_name or has_email) and not is_policy:
        signals.append({"name": "Financial data linked to persons", "sev": "high", "detected": True, "entities": fin_ents,
            "detail": "Financial values linked to identifiable persons (without strong unique ID)",
            "law": {"ndmo": "KSA PDPL Art. 1 — financial records linked to identifiable persons.", "pdpl": "KSA PDPL Art. 1 — financial records. Lawful basis required. SAMA framework applies."}})
    elif has_fin and not is_policy:
        pe_ents = []
        if "Commercial Registration (CR)" in entities:
            pe_ents.append(f"Commercial Registration × {entities['Commercial Registration (CR)']:,}")
        pe_ents.extend(fin_ents)
        signals.append({"name": "Private entity data", "sev": "medium", "detected": True, "entities": pe_ents,
            "detail": "Financial data for entities (not linked to identifiable individuals)",
            "law": {"ndmo": "NDMO Confidential — private entity financial data.", "pdpl": "KSA PDPL does not apply — entity financial data, not personal data."}})

    # ── 3. AML/CFT REGULATED DATA ──
    aml_kws  = keywords.get("aml_kyc", [])
    pep_kws  = keywords.get("pep", [])
    sanc_kws = keywords.get("sanctions", [])
    sar_kws  = keywords.get("suspicious_activity", [])
    aml_total = len(aml_kws) + len(pep_kws) + len(sanc_kws) + len(sar_kws)
    if aml_total >= 2 or is_kyc:
        ae = []
        if pep_kws:  ae.append(f"PEP screening × {len(pep_kws)}")
        if sanc_kws: ae.append(f"Sanctions check × {len(sanc_kws)}")
        if any(k in aml_kws for k in ["source of funds", "source of wealth"]): ae.append("Source of funds declaration × 1")
        if sar_kws:  ae.append(f"Suspicious activity × {len(sar_kws)}")
        if not ae:   ae.append(f"AML/KYC keywords × {aml_total}")
        signals.append({"name": "AML/CFT regulated data", "sev": "critical", "detected": True, "entities": ae,
            "detail": "Contains AML/CFT regulated content requiring strict access controls",
            "law": {"ndmo": "KSA AML Law (Royal Decree M/20). SAMA AML/CFT Guidelines.", "pdpl": "KSA PDPL Art. 1 — KYC data. AML Law (Royal Decree M/20)."}})

    # ── 4. SENSITIVE PERSONAL DATA (PDPL Art. 1) ──
    sensitive_cats = ["health_medical", "biometric", "criminal", "religious", "ethnic", "genetic", "minors"]
    sens_ents = []
    for cat in sensitive_cats:
        kws = keywords.get(cat, [])
        if kws:
            label = cat.replace("_", "/").replace("health/medical", "Health/medical")
            sens_ents.append(f"{label.title()} × {len(kws)}")
    if sens_ents:
        signals.append({"name": "Sensitive personal data", "sev": "critical", "detected": True, "entities": sens_ents,
            "detail": "Contains sensitive personal data categories under KSA PDPL Art. 1",
            "law": {"ndmo": "KSA PDPL Art. 1 Sensitive — explicit consent mandatory (Art. 5). DPO required.", "pdpl": "KSA PDPL Art. 1 Sensitive — explicit consent mandatory. Cannot process for marketing. DPO required."}})

    # ── 5. STRATEGIC / CLASSIFIED CONTENT ──
    strat_kws  = keywords.get("strategic_content", [])
    sec_kws    = keywords.get("security_controls", [])
    gov_kws    = keywords.get("governance", [])
    legal_kws  = keywords.get("legal_privilege", [])

    if is_strategy and strat_kws:
        signals.append({"name": "Strategic / classified content", "sev": "high", "detected": True,
            "entities": [f"{kw.title()} × 1" for kw in strat_kws[:6]],
            "detail": "Strategic business content — disclosure would cause significant damage",
            "law": {"ndmo": "NDMO Top Secret — strategic content.", "pdpl": "KSA PDPL does not apply directly — strategic content."}})
    elif is_policy and sec_kws:
        signals.append({"name": "Strategic / classified content", "sev": "medium", "detected": True,
            "entities": [f"{kw.title()} × 1" for kw in sec_kws[:6]],
            "detail": "Internal security procedures",
            "law": {"ndmo": "NDMO Confidential — internal operational procedures.", "pdpl": "KSA PDPL does not apply — policy document."}})
    elif gov_kws and len(gov_kws) >= 2:
        signals.append({"name": "Strategic / classified content", "sev": "medium", "detected": True,
            "entities": [f"{kw.title()} × 1" for kw in gov_kws[:4]],
            "detail": "Governance documentation with restricted distribution",
            "law": {"ndmo": "NDMO Confidential — governance records.", "pdpl": "KSA PDPL does not apply to governance records unless they contain personal data."}})
    elif legal_kws:
        signals.append({"name": "Strategic / classified content", "sev": "high", "detected": True,
            "entities": [f"{kw.title()} × 1" for kw in legal_kws[:4]],
            "detail": "Legally privileged content",
            "law": {"ndmo": "NDMO Secret — legally privileged material.", "pdpl": "KSA PDPL does not override legal privilege."}})

    # ── 6. EMPLOYMENT DATA LINKED TO PERSONS ──
    emp_ents = []
    for ek in ["Job title", "Department", "DATE (DOB)", "Gender", "Nationality"]:
        if ek in entities:
            emp_ents.append(f"{ek} × {entities[ek]:,}")
    emp_kws = keywords.get("employment", [])
    if emp_kws and not emp_ents:
        emp_ents = [f"{kw.title()} reference × 1" for kw in emp_kws[:3]]

    has_linkable = any(s["name"] == "Linkable identity" and s["detected"] for s in signals)
    if emp_ents and has_linkable and not is_policy:
        sev = "high" if rows > 100 else "low"
        signals.append({"name": "Employment data linked to persons", "sev": sev, "detected": True, "entities": emp_ents,
            "detail": "Employment records linked to named individuals",
            "law": {"ndmo": "KSA PDPL Art. 1 — personal data. KSA Labour Law (Royal Decree M/51).", "pdpl": "KSA PDPL Art. 1 — employment records. KSA Labour Law confidentiality obligations."}})
    elif emp_ents and not is_policy:
        signals.append({"name": "Employment data linked to persons", "sev": "low", "detected": True, "entities": emp_ents,
            "detail": "Employment context without strong personal identifiers",
            "law": {"ndmo": "NDMO Confidential — employment records.", "pdpl": "KSA PDPL Art. 1 — routine employment records."}})

    # ── 7. PERSONAL DATA (non-linkable) ──
    if not has_linkable and not is_policy:
        pd_ents = []
        for pk in ["PERSON name", "DATE (DOB)", "Employee number", "Email address", "Gender", "Nationality", "Address"]:
            if pk in entities:
                lbl = {"Email address": "Email"}.get(pk, pk)
                pd_ents.append(f"{lbl} × {entities[pk]:,}")
        if pd_ents:
            sev = "medium" if len(pd_ents) >= 2 else "low"
            signals.append({"name": "Personal data", "sev": sev, "detected": True, "entities": pd_ents,
                "detail": "Identifiable personal data without strong unique identifiers",
                "law": {"ndmo": "KSA PDPL Art. 1 — personal data. NDMO Confidential.", "pdpl": "KSA PDPL Art. 1 — identifiable personal data. 72-hour breach notification to SDAIA."}})

    # ── 8. CREDENTIALS / SYSTEM ACCESS ──
    if has_credentials(entities):
        cred_ents = []
        for ck in ["API key", "Connection string", "Private key marker", "Password in config"]:
            if ck in entities:
                cred_ents.append(f"{ck} × {entities[ck]:,}")
        signals.append({"name": "Credentials / system access", "sev": "critical", "detected": True, "entities": cred_ents,
            "detail": "System credentials or access keys detected — immediate security risk",
            "law": {"ndmo": "NCA ECC-1:2018 — credentials exposure is a security incident. NDMO Secret.", "pdpl": "NCA ECC-1:2018 applies. PDPL breach notification triggered if credentials enable data access."}})

    # ── 9. INCIDENTAL CONTACT DETAILS (policy docs) ──
    if is_policy:
        ic = []
        if "Email address" in entities: ic.append(f"Team email × {entities['Email address']}")
        if "KSA landline"  in entities: ic.append(f"KSA landline × {entities['KSA landline']}")
        if "KSA mobile"    in entities: ic.append(f"KSA mobile × {entities['KSA mobile']}")
        if ic:
            signals.append({"name": "Incidental contact details", "sev": "info", "detected": True, "entities": ic,
                "detail": "Departmental contact points — not personal data records",
                "law": {"ndmo": "Not classified as personal data — organisational contact.", "pdpl": "KSA PDPL does not apply — team-level contact information."}})

    # ── ALL CLEAR ──
    if not signals:
        ae = []
        if "Trade licence" in entities: ae.append(f"Trade licence (public) × {entities['Trade licence']:,}")
        if not ae: ae = ["No sensitive entities detected"]
        signals.append({"name": "All signals clear", "sev": "low", "detected": True, "entities": ae,
            "detail": "No personal, sensitive, or restricted content detected",
            "law": {"ndmo": "NDMO Public — suitable for publication on Saudi Open Data Platform (data.gov.sa).", "pdpl": "KSA PDPL does not apply — no personal data detected."}})

    # NOT-DETECTED PLACEHOLDERS
    det_names = {s["name"] for s in signals}
    for n in ["Linkable identity", "Financial data linked to persons", "Sensitive personal data",
              "AML/CFT regulated data", "Employment data linked to persons", "Strategic / classified content",
              "Credentials / system access"]:
        if n not in det_names:
            signals.append({"name": n, "sev": "info", "detected": False})

    return signals


# ═══════════════════════════════════════════
# RISK SCORING — spec formula
# max (not sum) + breadth (diminishing) + volume multiplier + linkage multiplier
# ═══════════════════════════════════════════

_RISK_SEVERITY = {"critical": 40, "high": 25, "medium": 12, "low": 4}
_BREADTH_INCREMENTS = [6, 4, 2]
_BREADTH_CAP = 15

_PERSON_SIGNALS = {
    "Linkable identity", "Financial data linked to persons",
    "Employment data linked to persons", "Sensitive personal data", "AML/CFT regulated data",
}

def calc_risk_score(signals: list, rows: int = 0) -> int:
    """Spec risk formula: severity floor (max) + breadth + volume × linkage."""
    detected = [s for s in signals if s.get("detected") and s.get("sev") not in ("info", None)]
    if not detected:
        return 0

    base = max(_RISK_SEVERITY.get(s["sev"], 4) for s in detected)

    severe_cats = {s["name"] for s in detected if s.get("sev") in ("critical", "high")}
    breadth = 0
    for i in range(1, len(severe_cats)):
        breadth += _BREADTH_INCREMENTS[min(i - 1, len(_BREADTH_INCREMENTS) - 1)]
    breadth = min(breadth, _BREADTH_CAP)

    content = base + breadth

    volume_mult  = min(1 + 0.18 * log10(max(rows or 0, 1)), 1.8)
    linked       = any(s["name"] in _PERSON_SIGNALS for s in detected)
    linkage_mult = 1.3 if linked else 1.0

    return min(100, round(content * volume_mult * linkage_mult))


# ═══════════════════════════════════════════
# CONFIDENCE SCORING — spec formula
# detection strength + corroboration + coverage − conflict
# ═══════════════════════════════════════════

_STRENGTH = {
    "checksum":       0.95,
    "column+pattern": 0.85,
    "pattern":        0.55,
    "heuristic":      0.35,
}

def _independent_method_count(hits: list) -> int:
    """Max number of distinct detector methods backing the same category."""
    cat_methods: dict = defaultdict(set)
    for h in hits:
        cat_methods[h["category"]].add(h["method"])
    return max((len(m) for m in cat_methods.values()), default=0)

def calc_confidence(hits: list, coverage: float, conflict: bool = False,
                    escalated: bool = False, escalation_resolved: bool = True) -> float:
    """Spec confidence formula."""
    if not hits:
        return round(min(0.6, 0.3 + 0.6 * coverage), 2)

    base    = max(_STRENGTH.get(h.get("match_type", "heuristic"), 0.35) for h in hits)
    corrob  = min(0.05 * max(_independent_method_count(hits) - 1, 0), 0.10)
    cov_fac = 0.7 + 0.3 * coverage
    penalty = 0.15 if conflict else 0.0

    conf = (base + corrob) * cov_fac - penalty

    if escalated and not escalation_resolved:
        conf = min(conf, 0.5)

    return round(max(0.0, min(conf, 0.99)), 2)


# ═══════════════════════════════════════════
# ACTION ROUTING — risk × confidence matrix
# ═══════════════════════════════════════════

def compute_action(risk_score: int, confidence: float,
                   risk_threshold: int = 60, conf_threshold: float = 0.75) -> str:
    """Map risk × confidence to an action."""
    risk_high = risk_score >= risk_threshold
    conf_high = confidence >= conf_threshold
    if   risk_high and     conf_high: return "auto-enforce"
    elif risk_high and not conf_high: return "human-review"
    elif not risk_high and conf_high: return "auto-file"
    else:                             return "spot-check"


# ═══════════════════════════════════════════
# HELPERS (kept for backward compat)
# ═══════════════════════════════════════════

def determine_severity(signals: list) -> str:
    det = [s for s in signals if s.get("detected")]
    if not det: return "low"
    for sv in ["critical", "high", "medium", "low", "info"]:
        if any(s["sev"] == sv for s in det): return sv
    return "low"

def calc_breakdown(entities: dict, keywords: dict) -> dict:
    from detectors import PATTERN_GROUPS
    pat = sum(entities.get(p, 0) for grp in PATTERN_GROUPS.values() for p in grp)
    kw  = sum(len(v) for v in keywords.values()) * 10
    ner = sum(v for k, v in entities.items() if k in (
        "PERSON name", "Job title", "Department", "DATE (DOB)", "Salary (SAR)",
        "Revenue / amount", "Gender", "Nationality", "Address", "Employee number"))
    total = max(pat + kw + ner, 1)
    p = round(pat / total * 100)
    k = round(kw  / total * 100)
    return {"pattern": p, "keyword": k, "ner": max(100 - p - k, 0)}

def redact_preview(text: str, max_len: int = 500) -> str:
    if not text: return None
    p = text[:max_len]
    p = re.sub(r"([a-zA-Z0-9._%+\-]{2})[a-zA-Z0-9._%+\-]+@", r"\1████@", p)
    p = re.sub(r"(\+966[\-\s]?5)[\d\-\s]{7,}", r"\1████", p)
    p = re.sub(r"(05\d)[\d\-\s]{6,}", r"\1████", p)
    p = re.sub(r"\b([12]\d{2})\d{7}\b", r"\1XXXXXXX", p)
    p = re.sub(r"(SA\d{2}\s?\d{4})\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}", r"\1 XXXX XXXX ████", p)
    p = re.sub(r"\b4(\d{3})[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?(\d{4})\b", r"4\1 XXXX XXXX \2", p)
    return p

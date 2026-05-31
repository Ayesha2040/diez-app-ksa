"""
Detection layer: regex patterns, keyword dictionaries, column-name matchers.
Each detector emits Hit objects carrying match_type so confidence scoring
can distinguish checksum-validated findings from bare pattern matches.
"""
import re
from collections import defaultdict

# ═══════════════════════════════════════════
# REGEX PATTERNS — KSA / GCC specific
# ═══════════════════════════════════════════

PATTERNS = {
    "Saudi National ID": re.compile(r"\b1\d{9}\b"),
    "Iqama Number":      re.compile(r"\b2\d{9}\b"),
    "Passport":          re.compile(r"\b[A-Z]{1,2}\d{7,9}\b"),

    "IBAN (Saudi)":        re.compile(r"SA\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}"),  # 24 chars total
    "IBAN (international)": re.compile(r"(?<![A-Z])(?!SA)[A-Z]{2}\d{2}\s?[\dA-Z]{4}\s?[\dA-Z]{4}\s?[\dA-Z]{4}(?:\s?[\dA-Z]{1,4}){0,4}"),
    "Credit card (Visa)":       re.compile(r"\b4\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
    "Credit card (Mastercard)": re.compile(r"\b5[1-5]\d{2}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
    "SWIFT/BIC":         re.compile(r"\b[A-Z]{4}[A-Z]{2}\d[A-Z0-9](?:[A-Z0-9]{3})?\b"),
    "SAR monetary value": re.compile(
        r"(?:SAR|SR|ر\.?س\.?|ريال(?:\s*سعودي)?)\s?[\d,]+(?:\.\d{2})?"
        r"|[\d,]+(?:\.\d{2})?\s*(?:ريال(?:\s*سعودي)?)", re.I),
    "USD monetary value": re.compile(r"(?:USD|\$)\s?[\d,]+(?:\.\d{2})?", re.I),

    "Email address": re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    "KSA mobile":   re.compile(r"(?:\+966|00966)[\-\s]?5[0-9][\-\s]?\d{3}[\-\s]?\d{4}|(?<!\d)05[0-9][\-\s]?\d{3}[\-\s]?\d{4}"),
    "KSA landline": re.compile(r"(?:\+966[\-\s]?[123]|0[123])[\-\s]?\d[\-\s]?\d{7}"),
    "PO Box":       re.compile(r"(?:P\.?O\.?\s*Box|PO\s*Box|ص\.?\s*ب\.?)\s*\d{3,6}", re.I),

    "DATE": re.compile(r"\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b"),

    "Saudi National ID (Arabic context)": re.compile(r"(?:رقم\s*الهوية|هوية\s*وطنية|الهوية\s*الوطنية|رقم\s*الإقامة|إقامة)[\s:]*\b[12]\d{9}\b"),
    "Saudi IBAN (Arabic context)":        re.compile(r"(?:رقم\s*الآيبان|الآيبان|رقم\s*الحساب)\s*:?\s*SA\d{2}\s?[\d\s]{18,22}", re.I),
    "KSA mobile (Arabic context)":        re.compile(r"(?:رقم\s*الجوال|الجوال|رقم\s*الهاتف|هاتف\s*محمول)[\s:]*(?:\+966|00966|05)\d{8,9}"),

    "Commercial Registration (CR)": re.compile(r"(?:CR|C\.R\.|commercial\s+reg(?:istration)?|reg(?:istration)?\s+no|سجل\s+تجاري|رقم\s+السجل)[\s.:]*\b[1-9]\d{9}\b", re.I),
    "VAT Registration (ZATCA)": re.compile(r"\b3\d{13}3\b"),

    "API key":            re.compile(r"(?:api[_\-]?key|apikey|api[_\-]?secret)[\s:=\"']+[A-Za-z0-9\-_]{20,}", re.I),
    "Connection string":  re.compile(r"(?:Server|Data Source|Host)=[^;\s]+;.*(?:Password|Pwd)=[^;\s]+", re.I),
    "Private key marker": re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
    "Password in config": re.compile(r"(?:password|passwd|pwd)[\s:=\"']+\S{6,}", re.I),
}

PATTERN_GROUPS = {
    "personal_id": ["Saudi National ID", "Iqama Number", "Passport"],
    "financial":   ["IBAN (Saudi)", "IBAN (international)", "Credit card (Visa)", "Credit card (Mastercard)", "SWIFT/BIC", "SAR monetary value", "USD monetary value"],
    "contact":     ["Email address", "KSA mobile", "KSA landline", "PO Box"],
    "business":    ["Commercial Registration (CR)", "VAT Registration (ZATCA)"],
    "credentials": ["API key", "Connection string", "Private key marker", "Password in config"],
    "dates":       ["DATE"],
}

# Severity of each entity type (used in hit objects)
ENTITY_SEVERITY = {
    "Saudi National ID": "critical", "Saudi National ID (Arabic context)": "critical",
    "Iqama Number": "critical",
    "Passport": "high",
    "IBAN (Saudi)": "high", "IBAN (international)": "medium", "Saudi IBAN (Arabic context)": "high",
    "Credit card": "critical",
    "SWIFT/BIC": "medium",
    "SAR monetary value": "medium", "USD monetary value": "low",
    "Email address": "medium",
    "KSA mobile": "medium", "KSA mobile (Arabic context)": "medium", "KSA landline": "low",
    "PO Box": "low", "DATE": "low",
    "Commercial Registration (CR)": "medium", "VAT Registration (ZATCA)": "medium",
    "API key": "critical", "Connection string": "critical",
    "Private key marker": "critical", "Password in config": "critical",
}

KEYWORD_SEVERITY = {
    "health_medical": "critical", "biometric": "critical", "criminal": "critical",
    "religious": "critical", "ethnic": "high", "genetic": "critical", "minors": "high",
    "aml_kyc": "critical", "pep": "high", "sanctions": "high", "suspicious_activity": "high",
    "strategic_content": "high", "employment": "medium", "financial": "medium",
    "security_controls": "medium", "legal_privilege": "high",
    "governance": "medium", "customer_data": "medium",
}

# ═══════════════════════════════════════════
# KEYWORD DICTIONARIES — 18 categories
# ═══════════════════════════════════════════

KEYWORDS = {
    "health_medical":  ["diagnosis", "treatment", "prescription", "medical record", "patient", "health condition", "disability", "blood type", "allergy", "vaccination", "hospital", "clinic", "medication", "chronic", "surgery"],
    "biometric":       ["fingerprint", "retina scan", "facial recognition", "biometric", "iris scan", "voice print", "dna sample", "palm print"],
    "criminal":        ["criminal record", "conviction", "arrest", "prosecution", "court order", "detention", "sentence", "parole", "probation order", "police report"],
    "religious":       ["religion", "religious belief", "sect", "mosque", "church", "temple", "faith", "denomination", "prayer time"],
    "ethnic":          ["ethnicity", "ethnic origin", "race", "tribal", "nationality", "national origin", "caste"],
    "genetic":         ["genetic data", "genome", "dna", "hereditary", "genetic test", "gene sequence", "chromosom"],
    "minors":          ["child", "minor", "juvenile", "under 18", "underage", "parental consent", "guardian", "school record", "student record"],
    "aml_kyc":         ["know your customer", "kyc", "due diligence", "cdd", "edd", "beneficial owner", "source of funds", "source of wealth", "money laundering", "aml", "terrorist financing", "cft"],
    "pep":             ["pep", "politically exposed", "senior political figure", "government official", "state-owned enterprise"],
    "sanctions":       ["sanctions", "screening", "watchlist", "ofac", "eu sanctions", "un sanctions", "designated person", "blacklist", "restricted party"],
    "suspicious_activity": ["suspicious activity report", "suspicious transaction report", "suspicious transaction", "unusual transaction", "structuring"],
    "strategic_content":   ["board resolution", "strategic plan", "revenue target", "growth strategy", "market expansion", "competitive analysis", "m&a", "acquisition target", "board approved", "not for distribution", "budget forecast", "capex", "strategic initiative"],
    "employment":      ["employee", "staff", "hire date", "termination", "probation", "performance review", "appraisal", "promotion", "disciplinary", "leave balance", "attendance", "training", "onboarding", "salary review"],
    "financial":       ["salary", "wage", "compensation", "bonus", "allowance", "payment", "invoice", "receipt", "bank account", "debit", "credit", "transaction", "ledger", "accounts payable", "accounts receivable", "revenue", "profit", "loss"],
    "security_controls": ["incident response", "escalation", "security policy", "access control", "firewall", "intrusion detection", "vulnerability", "penetration test", "security audit", "disaster recovery", "business continuity", "encryption policy", "authentication", "authorization", "security awareness", "phishing"],
    "legal_privilege": ["legal privilege", "attorney-client", "without prejudice", "settlement", "litigation", "arbitration", "legal advice", "counsel opinion"],
    "governance":      ["board minutes", "governance", "audit committee", "risk committee", "compliance report", "internal audit", "regulatory filing"],
    "customer_data":   ["customer data", "client information", "subscriber", "account holder", "user data", "consumer data", "personal information"],
}

KEYWORDS_AR = {
    "health_medical":  ["تشخيص", "علاج", "وصفة طبية", "سجل طبي", "مريض", "حالة صحية", "إعاقة", "فصيلة الدم", "حساسية", "تطعيم", "مستشفى", "عيادة", "دواء", "مزمن", "جراحة"],
    "biometric":       ["بصمة", "بصمة إصبع", "مسح شبكي", "التعرف على الوجه", "بيانات بيومترية", "مسح القزحية", "بصمة صوتية", "عينة الحمض النووي"],
    "criminal":        ["سجل جنائي", "إدانة", "اعتقال", "ملاحقة قضائية", "أمر محكمة", "احتجاز", "حكم", "إفراج مشروط", "تقرير شرطة"],
    "religious":       ["الدين", "المعتقد الديني", "طائفة", "مسجد", "كنيسة", "معبد", "إيمان", "عقيدة"],
    "ethnic":          ["عرق", "أصل عرقي", "قبيلة", "جنسية", "أصل قومي"],
    "genetic":         ["بيانات وراثية", "جينوم", "حمض نووي", "وراثي", "فحص جيني"],
    "minors":          ["طفل", "قاصر", "حدث", "دون الثامنة عشرة", "موافقة ولي الأمر", "وصي", "سجل مدرسي", "سجل الطالب"],
    "aml_kyc":         ["اعرف عميلك", "العناية الواجبة", "مكافحة غسل الأموال", "تمويل الإرهاب", "المالك المستفيد", "مصدر الأموال", "مصدر الثروة", "غسل أموال"],
    "pep":             ["شخص مكشوف سياسياً", "مسؤول حكومي", "شركة مملوكة للدولة"],
    "sanctions":       ["عقوبات", "قائمة مراقبة", "شخص مدرج", "قائمة سوداء"],
    "suspicious_activity": ["تقرير نشاط مشبوه", "معاملة مشبوهة", "معاملة غير معتادة"],
    "strategic_content": ["قرار مجلس الإدارة", "خطة استراتيجية", "هدف الإيرادات", "استراتيجية النمو", "التوسع في السوق", "تحليل تنافسي", "اندماج واستحواذ", "سري للغاية", "لا يُوزَّع", "ميزانية تقديرية", "مبادرة استراتيجية"],
    "employment":      ["موظف", "توظيف", "تاريخ التعيين", "إنهاء الخدمة", "تقييم الأداء", "ترقية", "إجراء تأديبي", "رصيد الإجازات", "الحضور", "التدريب"],
    "financial":       ["راتب", "أجر", "مكافأة", "بدل", "دفعة", "فاتورة", "حساب بنكي", "مدين", "دائن", "معاملة", "دفاتر الحسابات", "إيرادات", "ربح", "خسارة", "تمويل", "مرابحة", "ائتمان", "رهن", "قسط", "هامش ربح", "التمويل العقاري", "تصنيف ائتماني", "نسبة الالتزام", "سمة", "قيمة العقار", "مبلغ التمويل", "مدة التمويل", "البنك المركزي السعودي"],
    "security_controls": ["الاستجابة للحوادث", "سياسة أمنية", "التحكم في الوصول", "جدار الحماية", "كشف التسلل", "ثغرة أمنية", "تدقيق أمني", "تشفير", "مصادقة"],
    "governance":      ["محضر مجلس الإدارة", "حوكمة", "لجنة المراجعة", "لجنة المخاطر", "تقرير الامتثال", "تدقيق داخلي", "لجنة الائتمان", "مذكرة لجنة", "قرار تمويل"],
}

# ═══════════════════════════════════════════
# COLUMN-NAME MATCHERS (structured data)
# ═══════════════════════════════════════════

COLUMN_MATCHERS = {
    "Saudi National ID": re.compile(r"(?:national_?id|saudi_?id|id_?number|iqama|residency_?id|unified_?no|رقم الهوية|هوية وطنية|الهوية الوطنية|رقم الإقامة|إقامة)", re.I),
    "Employee number":   re.compile(r"(?:employee_?id|emp_?id|emp_?no|staff_?id|worker_?id|employee_?number)", re.I),
    "PERSON name":       re.compile(r"(?:full_?name|first_?name|last_?name|employee_?name|contact_?name|^name$|applicant|beneficiary|الاسم|اسم الموظف|الاسم الكامل|الاسم الأول|اسم العميل)", re.I),
    "Email address":     re.compile(r"(?:email|e_?mail|البريد الإلكتروني|إيميل)", re.I),
    "Salary (SAR)":      re.compile(r"(?:salary|basic_?pay|wage|compensation|allowance|gross_?pay|net_?pay|remuneration|الراتب|الراتب الأساسي|الأجر|المكافأة|البدل|صافي الراتب)", re.I),
    "IBAN":              re.compile(r"(?:iban|bank_?account|account_?no|account_?number|رقم الآيبان|الآيبان|رقم الحساب البنكي)", re.I),
    "Phone":             re.compile(r"(?:phone|mobile|cell|contact_?number|landline|tel|رقم الجوال|الجوال|رقم الهاتف|هاتف)", re.I),
    "DATE (DOB)":        re.compile(r"(?:dob|date_?of_?birth|birth_?date|تاريخ الميلاد|تاريخ ميلاد)", re.I),
    "DATE (employment)": re.compile(r"(?:hire_?date|join_?date|start_?date|termination_?date|end_?date|تاريخ التعيين|تاريخ الانضمام|تاريخ الانتهاء)", re.I),
    "Department":        re.compile(r"(?:department|dept|division|unit|section|team|القسم|الإدارة|الوحدة|الفريق)", re.I),
    "Job title":         re.compile(r"(?:job_?title|position|designation|role|^title$|grade|level|المسمى الوظيفي|الوظيفة|الدرجة الوظيفية)", re.I),
    "Commercial Registration": re.compile(r"(?:commercial_?reg|cr_?no|cr_?number|trade_?licen[cs]e|licence_?number|سجل تجاري|رقم السجل التجاري)", re.I),
    "Revenue / amount":  re.compile(r"(?:revenue|annual_revenue|invoice_amount|payment_amount|turnover|المبلغ|الإيرادات|الدفعة|الفاتورة)", re.I),
    "Passport":          re.compile(r"(?:passport|travel_?doc|رقم جواز السفر|جواز السفر)", re.I),
    "Nationality":       re.compile(r"(?:nationality|citizenship|country_?of_?origin|الجنسية|بلد الأصل)", re.I),
    "Gender":            re.compile(r"(?:gender|sex|الجنس|النوع الاجتماعي)", re.I),
    "Address":           re.compile(r"(?:address|street|city|region|postal|zip|location|العنوان|المدينة|المنطقة)", re.I),
}

# ═══════════════════════════════════════════
# NORMALIZATION
# ═══════════════════════════════════════════

_DIGIT_TABLE = str.maketrans(
    '٠١٢٣٤٥٦٧٨٩' '۰۱۲۳۴۵۶۷۸۹',
    '01234567890123456789'
)
_DIGIT_TABLE[0x066C] = ','
_DIGIT_TABLE[0x066B] = '.'

def _normalize(text: str) -> str:
    return text.translate(_DIGIT_TABLE)

# ═══════════════════════════════════════════
# CHECKSUM VALIDATION
# ═══════════════════════════════════════════

def validate_iban(iban: str) -> bool:
    """ISO 7064 MOD-97-10 checksum for IBAN."""
    clean = iban.replace(" ", "").upper()
    if len(clean) < 5:
        return False
    rearranged = clean[4:] + clean[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    try:
        return int(numeric) % 97 == 1
    except ValueError:
        return False

# ═══════════════════════════════════════════
# DETECTION FUNCTIONS
# Each returns (entity_counts_dict, hits_list) for backward compat + confidence scoring.
# ═══════════════════════════════════════════

def detect_patterns(text: str) -> tuple:
    """Run regex patterns. Returns (entity_counts, hits)."""
    normalized = _normalize(text)
    entity_counts = {}
    hits = []

    for label, pat in PATTERNS.items():
        matches = pat.findall(normalized)
        if not matches:
            continue

        # Determine match_type
        match_type = "pattern"
        if label in ("IBAN (Saudi)", "Saudi IBAN (Arabic context)"):
            if any(validate_iban(m.replace(" ", "")) for m in matches if len(m.replace(" ", "")) >= 15):
                match_type = "checksum"
        elif label == "IBAN (international)":
            if any(validate_iban(m.replace(" ", "")) for m in matches if len(m.replace(" ", "")) >= 15):
                match_type = "checksum"

        slug = label.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "")
        hits.append({
            "category": label,
            "severity": ENTITY_SEVERITY.get(label, "low"),
            "match_type": match_type,
            "method": f"regex.{slug}",
            "count": len(matches),
        })
        entity_counts[label] = len(matches)

    # Dedup: Saudi IBANs out of international count
    if "IBAN (international)" in entity_counts and "IBAN (Saudi)" in entity_counts:
        sa_set = set(PATTERNS["IBAN (Saudi)"].findall(normalized))
        intl = [m for m in PATTERNS["IBAN (international)"].findall(normalized) if m not in sa_set]
        if intl:
            entity_counts["IBAN (international)"] = len(intl)
            for h in hits:
                if h["category"] == "IBAN (international)":
                    h["count"] = len(intl)
        else:
            entity_counts.pop("IBAN (international)", None)
            hits = [h for h in hits if h["category"] != "IBAN (international)"]

    # Merge credit card variants
    visa = entity_counts.pop("Credit card (Visa)", 0)
    mc   = entity_counts.pop("Credit card (Mastercard)", 0)
    hits = [h for h in hits if h["category"] not in ("Credit card (Visa)", "Credit card (Mastercard)")]
    if visa + mc > 0:
        entity_counts["Credit card"] = visa + mc
        hits.append({"category": "Credit card", "severity": "critical", "match_type": "pattern", "method": "regex.credit_card", "count": visa + mc})

    return entity_counts, hits


def detect_keywords(text: str) -> tuple:
    """Run keyword dictionaries (EN + AR). Returns (keyword_dict, hits)."""
    tl = text.lower()
    results = {}
    hits_by_cat: dict = {}

    # English — word-boundary matching
    for cat, words in KEYWORDS.items():
        matched = []
        for w in words:
            if ' ' in w:
                if w in tl:
                    matched.append(w)
            else:
                if re.search(r'\b' + re.escape(w) + r'\b', tl):
                    matched.append(w)
        if matched:
            results[cat] = matched
            hits_by_cat[cat] = {"category": cat, "severity": KEYWORD_SEVERITY.get(cat, "medium"), "match_type": "heuristic", "method": f"keyword_en.{cat}", "count": len(matched)}

    # Arabic — substring matching
    for cat, words in KEYWORDS_AR.items():
        matched = [w for w in words if w in text]
        if matched:
            existing = results.get(cat, [])
            results[cat] = existing + matched
            if cat in hits_by_cat:
                hits_by_cat[cat]["count"] += len(matched)
                hits_by_cat[cat]["method"] = f"keyword_en_ar.{cat}"
            else:
                hits_by_cat[cat] = {"category": cat, "severity": KEYWORD_SEVERITY.get(cat, "medium"), "match_type": "heuristic", "method": f"keyword_ar.{cat}", "count": len(matched)}

    return results, list(hits_by_cat.values())


def detect_columns(cols: list, rows: int) -> tuple:
    """Column detection. Returns (entity_counts, col_details, hits)."""
    entity_counts = {}
    col_details = []
    hits_by_cat: dict = {}

    for ci in cols:
        cn = ci["name"]
        samples = ci.get("samples", [])
        col_tier = "open"
        col_det = "None"
        entity_label = None
        sample_validated = False

        for label, pat in COLUMN_MATCHERS.items():
            if not pat.search(cn):
                continue

            if label == "Saudi National ID":
                sample_validated = any(re.search(r"\b[12]\d{9}\b", s) for s in samples)
                col_det  = "Regex · National ID" if sample_validated else "Column · National ID"
                col_tier = "sens"
                entity_label = "Saudi National ID"

            elif label == "Employee number":
                if any(re.search(r"\b[12]\d{9}\b", s) for s in samples):
                    col_det = "Regex · National ID pattern"
                    col_tier = "sens"
                    entity_label = "Saudi National ID"
                    sample_validated = True
                else:
                    col_det = "None"
                    col_tier = "open"
                    entity_label = "Employee number"

            elif label == "PERSON name":
                col_det = "NER · Person"; col_tier = "conf"; entity_label = label

            elif label == "Email address":
                col_det = "Regex · Email"; col_tier = "conf"; entity_label = label

            elif label == "Salary (SAR)":
                if any(re.search(r"[\d,]+", s) for s in samples):
                    col_det = "Keyword · Salary"; col_tier = "conf"; entity_label = label; sample_validated = True

            elif label == "IBAN":
                if any(re.search(r"SA\d{2}", s) for s in samples):
                    iban_vals = [s for s in samples if re.search(r"SA\d{2}", s)]
                    sample_validated = any(validate_iban(v.replace(" ", "")) for v in iban_vals)
                    col_det = "Regex · Saudi IBAN"; col_tier = "conf"; entity_label = "IBAN (Saudi)"
                elif any(re.search(r"[A-Z]{2}\d{2}", s) for s in samples):
                    col_det = "Regex · IBAN (intl)"; col_tier = "conf"; entity_label = "IBAN (international)"

            elif label == "Phone":
                col_det = "Regex · Phone"; col_tier = "conf"; entity_label = label

            elif label == "DATE (DOB)":
                col_det = "Regex · DOB"; col_tier = "conf"; entity_label = label

            elif label == "DATE (employment)":
                col_det = "Regex · Date"; col_tier = "open"

            elif label == "Commercial Registration":
                col_det = "Regex · CR Number"; col_tier = "conf"; entity_label = label

            elif label == "Revenue / amount":
                col_det = "Keyword · Financial"; col_tier = "conf"; entity_label = label

            elif label == "Passport":
                col_det = "Regex · Passport"; col_tier = "sens"; entity_label = label

            elif label == "Nationality":
                col_det = "NER · Nationality"; col_tier = "conf"; entity_label = label

            elif label == "Gender":
                col_det = "NER · Gender"; col_tier = "conf"; entity_label = label

            elif label == "Address":
                col_det = "NER · Address"; col_tier = "conf"; entity_label = label

            break  # first match wins

        if entity_label:
            entity_counts[entity_label] = entity_counts.get(entity_label, 0) + rows
            match_type = "column+pattern" if sample_validated else "heuristic"
            if entity_label in hits_by_cat:
                hits_by_cat[entity_label]["count"] += rows
            else:
                hits_by_cat[entity_label] = {
                    "category": entity_label,
                    "severity": ENTITY_SEVERITY.get(entity_label, "medium"),
                    "match_type": match_type,
                    "method": f"column.{entity_label.lower().replace(' ', '_')}",
                    "count": rows,
                }

        col_details.append({"name": cn, "dtype": ci.get("dtype", ""), "tier": col_tier, "det": col_det, "sample": samples[0] if samples else "—"})

    return entity_counts, col_details, list(hits_by_cat.values())


def has_credentials(entities: dict) -> bool:
    cred_keys = {"API key", "Connection string", "Private key marker", "Password in config"}
    return bool(cred_keys & set(entities.keys()))

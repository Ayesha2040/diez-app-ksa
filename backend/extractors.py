"""
Text extraction for all supported file types.
Each extractor returns: {text, rows, cols, structured}
"""
import re, io, unicodedata
import pandas as pd


def _normalize_arabic(text: str) -> str:
    """
    NFKC decomposition converts Arabic presentation forms (U+FE70–U+FEFF ligatures
    like ﺑﻨﻚ) back to base Arabic characters (بنك) so keyword matching works on
    text extracted from Arabic PDFs and Word documents.
    """
    return unicodedata.normalize("NFKC", text)


def extract_xlsx(content: bytes) -> dict:
    try:
        df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
        cols = [{"name": str(c), "dtype": str(df[c].dtype),
                 "samples": df[c].dropna().head(8).astype(str).tolist()} for c in df.columns]
        return {"text": df.to_string(max_rows=300), "rows": len(df), "cols": cols, "structured": True}
    except Exception as e:
        return {"text": "", "rows": 0, "cols": [], "structured": True, "error": str(e)}


def extract_csv(content: bytes) -> dict:
    # Try encodings in order: UTF-8-BOM, UTF-8, Windows-1256 (Arabic), ISO-8859-6
    raw = None
    for enc in ("utf-8-sig", "utf-8", "windows-1256", "iso-8859-6", "latin-1"):
        try:
            raw = content.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if raw is None:
        raw = content.decode("utf-8", errors="replace")
    try:
        sep = "\t" if "\t" in raw[:500] else (";" if raw[:500].count(";") > raw[:500].count(",") else ",")
        df = pd.read_csv(io.StringIO(raw), sep=sep)
        cols = [{"name": str(c), "dtype": str(df[c].dtype),
                 "samples": df[c].dropna().head(8).astype(str).tolist()} for c in df.columns]
        return {"text": df.to_string(max_rows=300), "rows": len(df), "cols": cols, "structured": True}
    except Exception as e:
        return {"text": raw[:5000], "rows": 0, "cols": [], "structured": True, "error": str(e)}


def extract_txt(content: bytes) -> dict:
    text = _normalize_arabic(content.decode("utf-8", errors="replace"))
    chars_total = max(len(content), len(text))
    return {"text": text[:15000], "chars_total": chars_total, "rows": None, "cols": [], "structured": False}


def extract_docx(content: bytes) -> dict:
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        text = _normalize_arabic("\n".join(p.text for p in doc.paragraphs if p.text.strip()))
        chars_total = max(len(content) // 3, len(text))  # docx is compressed XML
        return {"text": text[:15000], "chars_total": chars_total, "rows": None, "cols": [], "structured": False}
    except Exception as e:
        return {"text": "", "chars_total": 0, "rows": None, "cols": [], "structured": False, "error": str(e)}


def extract_pdf(content: bytes) -> dict:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(content))
        raw  = "\n".join(p.extract_text() or "" for p in reader.pages[:30])
        text = _normalize_arabic(raw)
        # Estimate total chars from page count (pages not read are unknown territory)
        total_pages  = len(reader.pages)
        read_pages   = min(30, total_pages)
        chars_total  = max(len(text), int(len(text) * (total_pages / max(read_pages, 1))))
        return {"text": text[:15000], "chars_total": chars_total, "rows": None, "cols": [], "structured": False}
    except Exception as e:
        return {"text": "", "chars_total": 0, "rows": None, "cols": [], "structured": False, "error": str(e)}


EXTRACTORS = {
    ".xlsx": extract_xlsx, ".xls": extract_xlsx,
    ".csv": extract_csv, ".tsv": extract_csv,
    ".txt": extract_txt,
    ".docx": extract_docx,
    ".pdf": extract_pdf,
}

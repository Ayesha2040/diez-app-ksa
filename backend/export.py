"""
Export scan results as XLSX report for client handoff.
Summary sheet + detail sheet.
"""
import io
import pandas as pd
from frameworks import FRAMEWORKS


def export_xlsx(scan_results: list, framework: str = "dde") -> bytes:
    """Generate XLSX report from scan results."""
    fw = FRAMEWORKS.get(framework) or FRAMEWORKS["ndmo"]

    # Summary data
    tier_counts = {"open": 0, "conf": 0, "sens": 0, "secret": 0}
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for r in scan_results:
        tier_counts[r.get("tier", "open")] = tier_counts.get(r.get("tier", "open"), 0) + 1
        sev_counts[r.get("severity", "low")] = sev_counts.get(r.get("severity", "low"), 0) + 1

    summary_rows = []
    summary_rows.append({"Metric": "Total files scanned", "Value": len(scan_results)})
    summary_rows.append({"Metric": "Framework", "Value": fw["full"]})
    summary_rows.append({"Metric": "", "Value": ""})
    summary_rows.append({"Metric": "Classification Distribution", "Value": ""})
    for tier_id, count in tier_counts.items():
        label = fw["tiers"][tier_id]["label"]
        summary_rows.append({"Metric": f"  {label}", "Value": count})
    summary_rows.append({"Metric": "", "Value": ""})
    summary_rows.append({"Metric": "Severity Breakdown", "Value": ""})
    for sev, count in sev_counts.items():
        summary_rows.append({"Metric": f"  {sev.title()}", "Value": count})

    df_summary = pd.DataFrame(summary_rows)

    # Detail data
    detail_rows = []
    for r in scan_results:
        tier_label = fw["tiers"].get(r.get("tier", "open"), {}).get("label", r.get("tier", ""))
        detected_signals = [s for s in r.get("signals", []) if s.get("detected")]
        signal_names = "; ".join(s["name"] for s in detected_signals)
        entity_summary = "; ".join(
            ", ".join(s.get("entities", [])[:3]) for s in detected_signals if s.get("entities")
        )
        detail_rows.append({
            "File": r.get("name", ""),
            "Document type": r.get("docType", ""),
            "Classification": tier_label,
            "Severity": r.get("severity", "").title(),
            "Confidence": r.get("conf", 0),
            "Signals detected": signal_names,
            "Key entities": entity_summary[:200],
            "Size": r.get("size", ""),
            "Rows": r.get("rows", ""),
        })

    df_detail = pd.DataFrame(detail_rows)

    # Write to XLSX
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="Summary", index=False)
        df_detail.to_excel(writer, sheet_name="Detail", index=False)

        # Auto-width columns
        for sheet_name in ["Summary", "Detail"]:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

    buf.seek(0)
    return buf.read()

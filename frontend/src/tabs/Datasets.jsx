import { useState } from 'react';
import { Pill, SrcIcon, Card, MetricCard, FwToggle } from '../components';

// Sample datasets — used only when no files uploaded. Classifications reflect
// what the LLM would produce: trade licence = private entity data (conf),
// revenue = entity financial (conf), contact names = personal data (sens).
const SAMPLE_DATASETS = [
  {
    id: "hr", name: "HR_Employee_Master", source: "Oracle Fusion", sourceTag: "OR", sourceColor: "#993C1D",
    desc: "Core employee records — demographics, compensation, religion, org structure",
    rows: "2,847", tier: "sens",
    aiNote: "Classified Secret — religion column is sensitive personal data under KSA PDPL Art. 1 (religious belief). Names, National ID, email, salary, and IBAN are personal data (KSA PDPL Art. 1) — not sensitive. Internal employee IDs, department, job title, and dates are non-personal. Explicit consent required for religion column per Art. 5.",
    columns: [
      { name: "EMPLOYEE_ID",   dtype: "VARCHAR", tier: "open",  reason: "Internal reference — non-personal",             sample: "EMP-10XXXX" },
      { name: "FULL_NAME",     dtype: "VARCHAR", tier: "conf",  reason: "KSA PDPL Art. 1 — personal data",               sample: "A████ Al-O████" },
      { name: "NATIONAL_ID",   dtype: "VARCHAR", tier: "sens",  reason: "KSA PDPL Art. 1 Sensitive — national identifier", sample: "1XXXXXXXXX" },
      { name: "EMAIL",         dtype: "VARCHAR", tier: "conf",  reason: "KSA PDPL Art. 1 — personal data",               sample: "a.████@company.sa" },
      { name: "RELIGION",      dtype: "VARCHAR", tier: "sens",  reason: "KSA PDPL Art. 1 Sensitive — religious belief",  sample: "██████████" },
      { name: "SALARY_BASIC",  dtype: "NUMBER",  tier: "conf",  reason: "KSA PDPL Art. 1 — personal data (financial)",   sample: "SAR XX,XXX" },
      { name: "BANK_IBAN",     dtype: "VARCHAR", tier: "conf",  reason: "KSA PDPL Art. 1 — personal data (banking)",     sample: "SA## XXXX XXXX ████" },
      { name: "DEPARTMENT",    dtype: "VARCHAR", tier: "open",  reason: "Non-personal — organisational metadata",        sample: "Operations" },
      { name: "JOB_TITLE",     dtype: "VARCHAR", tier: "open",  reason: "Non-personal — employment metadata",            sample: "Senior Manager" },
      { name: "HIRE_DATE",     dtype: "DATE",    tier: "open",  reason: "Non-personal — employment date",                sample: "20XX-XX-XX" },
    ],
    fwNote: {
      ndmo: "Contains sensitive personal data (National ID and religion — KSA PDPL Art. 1 Sensitive). Classified Secret under NDMO policy. Explicit consent required per Art. 5. Salary and IBAN are personal data (Art. 1), not sensitive. DPO appointment mandatory.",
      pdpl: "KSA PDPL Art. 1 Sensitive — National ID and religion require explicit consent (Art. 5), cannot be processed for marketing, legitimate interest NOT valid. Salary and IBAN are personal data (Art. 1) only — standard lawful basis applies. Cross-border transfer restricted (Art. 29).",
    },
  },
  {
    id: "crm", name: "CRM_Customer_Accounts", source: "Salesforce", sourceTag: "SF", sourceColor: "#0F6E56",
    desc: "Customer relationship records — contacts, commercial registrations, revenue data",
    rows: "14,200", tier: "conf",
    aiNote: "Classified by AI based on column semantics and KSA PDPL Art. 1. Commercial registration and revenue are private entity data (NDMO Confidential), not personal data. Contact names and National IDs are personal data under KSA PDPL Art. 1.",
    columns: [
      { name: "ACCOUNT_NAME",       dtype: "VARCHAR", tier: "open",  reason: "Public entity name",                       sample: "Acme Trading LLC" },
      { name: "COMMERCIAL_REG",     dtype: "VARCHAR", tier: "conf",  reason: "Private entity data",                      sample: "1010XXXXXX" },
      { name: "CONTACT_NAME",       dtype: "VARCHAR", tier: "conf",  reason: "KSA PDPL Art. 1 — personal data",          sample: "M████ Al-Q████" },
      { name: "CONTACT_NATIONAL_ID",dtype: "VARCHAR", tier: "conf",  reason: "KSA PDPL Art. 1 — national identifier",    sample: "1XXXXXXXXX" },
      { name: "ANNUAL_REVENUE",     dtype: "NUMBER",  tier: "conf",  reason: "Entity financial data",                    sample: "SAR X,XXX,XXX" },
      { name: "INDUSTRY",           dtype: "VARCHAR", tier: "open",  reason: "Public classification",                    sample: "Construction" },
    ],
    fwNote: {
      ndmo: "Contains private entity data (commercial registration, revenue) and personal contact data. Classified Confidential under NDMO policy. Contact name and National ID columns require KSA PDPL Art. 1 protections.",
      pdpl: "KSA PDPL Art. 1 — contact names and National IDs are personal data. Standard protection obligations apply. No explicit consent required for legitimate business processing, but data subject rights (access, correction, erasure) must be honoured.",
    },
  },
  {
    id: "fin", name: "Vendor_Payment_Ledger", source: "Oracle Fusion", sourceTag: "OR", sourceColor: "#993C1D",
    desc: "Accounts payable — vendor payments, IBANs, invoice amounts",
    rows: "420", tier: "conf",
    aiNote: "Classified Confidential. IBAN is personal data under KSA PDPL Art. 1 (banking identifier linked to identifiable persons), not sensitive data. Payment amounts are entity financial data. VAT numbers are entity identifiers under ZATCA. Standard lawful basis required for processing.",
    columns: [
      { name: "VENDOR_NAME",    dtype: "VARCHAR", tier: "open",  reason: "Public entity name",                       sample: "Al Rajhi Trading" },
      { name: "IBAN",           dtype: "VARCHAR", tier: "conf",  reason: "KSA PDPL Art. 1 — personal data (banking)", sample: "SA## XXXX XXXX ████" },
      { name: "PAYMENT_AMOUNT", dtype: "NUMBER",  tier: "conf",  reason: "Entity financial data",                    sample: "SAR XXX,XXX" },
      { name: "VAT_NUMBER",     dtype: "VARCHAR", tier: "conf",  reason: "ZATCA — entity tax identifier",            sample: "3XXXXXXXXXXXXXXXXX" },
    ],
    fwNote: {
      ndmo: "Dataset classified Confidential under NDMO policy. IBAN and payment amounts are personal/entity financial data. ZATCA VAT numbers are entity identifiers. Data-sharing agreement required for third-party access.",
      pdpl: "KSA PDPL Art. 1 — IBAN is personal data (banking identifier) when linked to identifiable persons. Standard lawful basis required. Data subject rights apply. SAMA Cybersecurity Framework mandates encryption for financial identifiers.",
    },
  },
  {
    id: "cr", name: "Commercial_Registry_Extract", source: "Salesforce", sourceTag: "SF", sourceColor: "#0F6E56",
    desc: "Public registry extract — active commercial registrations in KSA",
    rows: "3,100", tier: "open",
    aiNote: "Classified by AI as non-personal. All columns are public registry data — company names, registration numbers, activity codes. No personal data present. Sourced from Ministry of Commerce public records.",
    columns: [
      { name: "CR_NUMBER",    dtype: "VARCHAR", tier: "open", reason: "Public entity identifier",  sample: "1010123456" },
      { name: "COMPANY_NAME", dtype: "VARCHAR", tier: "open", reason: "Public entity name",        sample: "Riyadh Tech Solutions" },
      { name: "ACTIVITY",     dtype: "VARCHAR", tier: "open", reason: "Public classification",     sample: "IT Consulting" },
      { name: "REGION",       dtype: "VARCHAR", tier: "open", reason: "Public location metadata",  sample: "Riyadh" },
      { name: "STATUS",       dtype: "VARCHAR", tier: "open", reason: "Metadata status",           sample: "Active" },
    ],
    fwNote: {
      ndmo: "Public registry data. Suitable for publication on Saudi Open Data Platform (data.gov.sa). NDMO 'Think Open' principle applies — no restrictions on sharing.",
      pdpl: "KSA PDPL does not apply — no personal data present. Public business identifiers only. No consent or data subject rights obligations.",
    },
  },
];

export default function Datasets({ fw, setFw, frameworks, scannedDocs }) {
  const [expanded, setExpanded] = useState(null);

  // Build dynamic datasets from uploaded structured files.
  // Backend runs LLM at scan time and sets column.tier + column.reason.
  // No regex-based inference on the frontend — we trust what backend returns.
  const uploadedStructured = scannedDocs
    .filter(d => d.columns && d.rows)
    .map(d => ({
      id: d.id,
      name: d.name.replace(/\.[^.]+$/, ''),
      source: d.source,
      sourceTag: d.sourceTag,
      sourceColor: d.sourceColor,
      desc: `Uploaded ${d.docType?.toLowerCase() || 'file'} — ${d.rows} rows`,
      rows: d.rows,
      tier: d.tier,
      aiNote: d.llmAssessment?.summary || null,
      aiClassified: d.llmAssessment?.source === 'llm',
      columns: d.columns.map(c => ({
        name: c.name,
        dtype: c.dtype,
        tier: c.tier || "open",
        reason: c.reason || c.det || "—",
        sample: c.sample || (c.samples && c.samples[0]) || "—",
      })),
      fwNote: d.fwNote,
    }));

  const allDatasets = [...uploadedStructured, ...SAMPLE_DATASETS];
  const sensCount = allDatasets.filter(d => d.tier === "sens" || d.tier === "secret").length;
  const confCount = allDatasets.filter(d => d.tier === "conf").length;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div style={{ fontSize: 18, fontWeight: 500, color: "#2C2C2A" }}>Structured datasets — Client</div>
        <FwToggle fw={fw} setFw={setFw} frameworks={frameworks} />
      </div>
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <MetricCard label="Datasets" value={allDatasets.length} sub={`${uploadedStructured.length} uploaded + ${SAMPLE_DATASETS.length} existing`} />
        <MetricCard label="Sensitive" value={sensCount} accent="#A32D2D" />
        <MetricCard label="Confidential" value={confCount} accent="#BA7517" />
      </div>

      {allDatasets.map(ds => (
        <Card key={ds.id} style={{ marginBottom: 12, cursor: "pointer" }}>
          <div onClick={() => setExpanded(expanded === ds.id ? null : ds.id)} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <SrcIcon tag={ds.sourceTag} color={ds.sourceColor} />
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: "#2C2C2A" }}>{ds.name}</div>
                <div style={{ fontSize: 12, color: "#888" }}>{ds.source} · {ds.rows} rows</div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {ds.aiClassified && (
                <span style={{
                  fontSize: 10, padding: "2px 8px", borderRadius: 8, fontWeight: 500,
                  background: "#EEEDFE", color: "#3C3489",
                  display: "inline-flex", alignItems: "center", gap: 4,
                }}>
                  <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="#3C3489" strokeWidth="2">
                    <circle cx="8" cy="8" r="6"/><path d="M8 5v3.5l2.5 1.5"/>
                  </svg>
                  AI classified
                </span>
              )}
              <Pill tier={ds.tier} fw={fw} frameworks={frameworks} />
              <span style={{ fontSize: 14, color: "#888", transform: expanded === ds.id ? "rotate(90deg)" : "none", transition: "transform 0.15s" }}>›</span>
            </div>
          </div>

          {expanded === ds.id && (
            <div style={{ marginTop: 16, borderTop: "0.5px solid #e5e4e0", paddingTop: 16 }}>
              <div style={{ fontSize: 13, color: "#5F5E5A", marginBottom: 14 }}>{ds.desc}</div>

              {ds.aiNote && (
                <div style={{
                  background: "#F1EFE8",
                  borderRadius: 8,
                  padding: "10px 12px",
                  marginBottom: 14,
                  display: "flex",
                  gap: 10,
                  alignItems: "flex-start",
                }}>
                  <svg style={{ width: 16, height: 16, flexShrink: 0, marginTop: 1 }} viewBox="0 0 16 16" fill="none" stroke="#3C3489" strokeWidth="1.5">
                    <circle cx="8" cy="8" r="6"/><path d="M8 5v3.5l2.5 1.5"/>
                  </svg>
                  <div style={{ fontSize: 12, color: "#2C2C2A", lineHeight: 1.5 }}>{ds.aiNote}</div>
                </div>
              )}

              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr>{["Column", "Type", "Classification", "Reasoning", "Sample"].map(h => (
                      <th key={h} style={{ textAlign: "left", padding: 8, fontWeight: 500, fontSize: 11, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0", textTransform: "uppercase", letterSpacing: 0.4 }}>{h}</th>
                    ))}</tr>
                  </thead>
                  <tbody>{ds.columns.map((c, i) => (
                    <tr key={i}>
                      <td style={{ padding: 8, fontWeight: 500, borderBottom: "0.5px solid #e5e4e0" }}>{c.name}</td>
                      <td style={{ padding: 8, color: "#888", borderBottom: "0.5px solid #e5e4e0" }}>{c.dtype}</td>
                      <td style={{ padding: 8, borderBottom: "0.5px solid #e5e4e0" }}><Pill tier={c.tier} fw={fw} frameworks={frameworks} /></td>
                      <td style={{ padding: 8, borderBottom: "0.5px solid #e5e4e0" }}>
                        <span style={{
                          display: "inline-flex", alignItems: "center", fontSize: 11,
                          padding: "2px 8px", borderRadius: 10,
                          background: "#F1EFE8", color: "#5F5E5A",
                        }}>{c.reason}</span>
                      </td>
                      <td dir="auto" style={{ padding: 8, fontFamily: "Tahoma, monospace", fontSize: 11, color: "#888", borderBottom: "0.5px solid #e5e4e0" }}>{c.sample}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>

              {ds.fwNote && (
                <div style={{ background: "#F5F4F0", borderRadius: 8, padding: "12px 14px", fontSize: 13, color: "#5F5E5A", lineHeight: 1.6, marginTop: 16 }}>
                  <span style={{ fontWeight: 500, color: "#2C2C2A" }}>{frameworks[fw]?.full || fw}:</span> {ds.fwNote[fw]}
                </div>
              )}
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}

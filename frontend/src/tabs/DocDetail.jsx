import { Pill, SevDot, Card, SignalAnalysis, MetaRow, FwToggle, ActionBadge } from '../components';
import { SEV, effectiveTier } from '../config';

const SEV_ACCENT = { critical: '#A32D2D', high: '#D85A30', medium: '#BA7517', low: '#639922', info: '#888780' };
const SEV_BG = { critical: '#FCEBEB', high: '#FAECE7', medium: '#FAEEDA', low: '#EAF3DE', info: '#F1EFE8' };
const SEV_FG = { critical: '#791F1F', high: '#712B13', medium: '#633806', low: '#27500A', info: '#5F5E5A' };
const SEV_BORDER = { critical: '#F7C1C1', high: '#F5C4B3', medium: '#FAC775', low: '#C0DD97', info: '#D3D1C7' };
const REG_DOT = { critical: '#A32D2D', high: '#D85A30', medium: '#BA7517' };

function ClassificationCard({ doc, fw, frameworks, assessment }) {
  const activeTier = effectiveTier(doc, fw);
  // When the effective tier is "open", show neutral styling even if underlying severity is higher
  const sev = activeTier === "open" ? "low" : (doc.severity || 'info');
  const detected = (doc.signals || []).filter(s => s.detected);
  const conf = doc.conf || 0;
  const tierLabel = frameworks[fw]?.tiers?.[activeTier]?.label || doc.tier;
  const riskScore = assessment?.risk_score ?? doc.riskScore ?? 0;

  return (
    <div style={{ background: SEV_BG[sev], border: `1px solid ${SEV_BORDER[sev]}`, borderRadius: 12, padding: 20, marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: SEV_ACCENT[sev], display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" strokeWidth="2">
              <path d="M12 9v4m0 4h.01M5.07 19h13.86c1.5 0 2.47-1.6 1.73-2.88L13.73 4.24c-.74-1.28-2.72-1.28-3.46 0L3.34 16.12C2.6 17.4 3.57 19 5.07 19z"/>
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 500, color: SEV_FG[sev] }}>{tierLabel}</div>
            <div style={{ fontSize: 13, color: SEV_FG[sev], opacity: 0.8, marginTop: 2, textTransform: 'capitalize' }}>
              {sev} risk — {detected.length} signal{detected.length !== 1 ? 's' : ''} detected
            </div>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 11, color: SEV_FG[sev], opacity: 0.7 }}>Risk score</div>
          <div style={{ fontSize: 32, fontWeight: 500, color: SEV_FG[sev], lineHeight: 1 }}>{riskScore}</div>
          <div style={{ fontSize: 13, color: SEV_FG[sev], opacity: 0.7 }}>/100</div>
        </div>
      </div>

      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 13, color: SEV_FG[sev], marginBottom: 6 }}>Classification confidence</div>
        <div style={{ height: 8, borderRadius: 4, background: 'rgba(0,0,0,0.1)', overflow: 'hidden' }}>
          <div style={{ height: '100%', borderRadius: 4, background: SEV_ACCENT[sev], width: `${Math.round(conf * 100)}%` }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: SEV_FG[sev] }}>{Math.round(conf * 100)}%</span>
        </div>
      </div>

      <div style={{ fontSize: 13, color: SEV_FG[sev], lineHeight: 1.6, paddingTop: 12, borderTop: '1px solid rgba(0,0,0,0.1)' }}>
        {assessment?.summary || 'Classification based on rule-based signal analysis.'}
      </div>
    </div>
  );
}

function Regulations({ regulations }) {
  if (!regulations?.length) return null;
  return (
    <Card>
      <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 12, color: '#2C2C2A', display: 'flex', alignItems: 'center', gap: 8 }}>
        <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#378ADD" strokeWidth="1.5">
          <rect x="2" y="2" width="12" height="12" rx="2"/><path d="M5 6h6M5 8.5h4M5 11h5"/>
        </svg>
        Applicable regulations
      </div>
      {regulations.map((r, i) => (
        <div key={i} style={{ padding: '8px 0', borderBottom: i < regulations.length - 1 ? '1px solid #F1EFE8' : 'none', display: 'flex', alignItems: 'flex-start', gap: 8 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: REG_DOT[r.severity] || '#888780', marginTop: 6, flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: 13, color: '#2C2C2A' }}>{r.regulation}</div>
            <div style={{ fontSize: 12, color: '#5F5E5A', marginTop: 2 }}>{r.relevance}</div>
          </div>
        </div>
      ))}
    </Card>
  );
}

const STATUS_STYLE = {
  active:     { bg: "#EAF3DE", fg: "#27500A", label: "Active" },
  review_due: { bg: "#FAEEDA", fg: "#633806", label: "Review due" },
  overdue:    { bg: "#FCEBEB", fg: "#791F1F", label: "Overdue" },
  disposed:   { bg: "#F1EFE8", fg: "#888780", label: "Disposed" },
};

const ACTION_LABEL = {
  secure_delete: "Secure delete",
  archive:       "Archive",
  review:        "Manual review",
  discretionary: "Discretionary",
};

function RetentionCard({ retention }) {
  if (!retention || retention.periodYears == null) {
    return (
      <Card style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, color: "#888", padding: "8px 0" }}>
          Retention data unavailable — re-upload this file to generate a retention schedule.
        </div>
      </Card>
    );
  }
  const st = STATUS_STYLE[retention.status] || STATUS_STYLE.active;
  const days = retention.daysRemaining;
  const daysLabel = days == null ? null
    : days < 0 ? `${Math.abs(days)} days overdue`
    : `${days} days remaining`;

  return (
    <Card style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 16, color: "#2C2C2A", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#5F5E5A" strokeWidth="1.5">
            <circle cx="8" cy="8" r="6"/><path d="M8 5v3.5l2.5 1.5"/>
          </svg>
          Retention schedule
        </div>
        <span style={{ background: st.bg, color: st.fg, padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 500 }}>
          {st.label}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 14 }}>
        <div style={{ background: "#F5F4F0", borderRadius: 8, padding: "10px 14px" }}>
          <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>Retention period</div>
          <div style={{ fontSize: 20, fontWeight: 500, color: "#2C2C2A" }}>
            {retention.periodYears > 0 ? `${retention.periodYears} years` : "No minimum"}
          </div>
          {daysLabel && (
            <div style={{ fontSize: 11, marginTop: 2, color: retention.status === "overdue" ? "#791F1F" : retention.status === "review_due" ? "#633806" : "#5F5E5A" }}>
              {daysLabel}
            </div>
          )}
        </div>

        <div style={{ background: "#F5F4F0", borderRadius: 8, padding: "10px 14px" }}>
          <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>Review date</div>
          <div style={{ fontSize: 14, fontWeight: 500, color: "#2C2C2A" }}>
            {retention.reviewDate || "—"}
          </div>
        </div>

        <div style={{ background: "#F5F4F0", borderRadius: 8, padding: "10px 14px" }}>
          <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>Disposal action</div>
          <div style={{ fontSize: 14, fontWeight: 500, color: "#2C2C2A" }}>
            {ACTION_LABEL[retention.disposalAction] || retention.disposalAction || "—"}
          </div>
        </div>
      </div>

      <div style={{ fontSize: 12, color: "#5F5E5A", lineHeight: 1.6, padding: "10px 14px", background: "#F5F4F0", borderRadius: 8 }}>
        <span style={{ fontWeight: 500, color: "#2C2C2A" }}>Legal basis: </span>
        {retention.basis || "—"}
      </div>

      {retention.regulationsApplied?.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
          {retention.regulationsApplied.map((r, i) => (
            <span key={i} style={{ background: "#EEEDFE", color: "#3C3489", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 500 }}>{r}</span>
          ))}
        </div>
      )}
    </Card>
  );
}

function AIAssessment({ assessment }) {
  if (!assessment) {
    return (
      <Card>
        <div style={{ padding: '16px 0', textAlign: 'center', color: '#888', fontSize: 13 }}>AI assessment unavailable — set ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env to enable</div>
      </Card>
    );
  }
  return (
    <Card>
      <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8, color: '#2C2C2A' }}>
        <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#BA7517" strokeWidth="1.5">
          <circle cx="8" cy="8" r="6"/><path d="M8 5v3.5l2.5 1.5"/>
        </svg>
        AI risk assessment
        {assessment.source === 'fallback' && (
          <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 12, background: '#FAEEDA', color: '#633806', marginLeft: 4 }}>Fallback — no API key</span>
        )}
        {assessment.source === 'llm' && (
          <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 12, background: '#EAF3DE', color: '#27500A', marginLeft: 4 }}>LLM</span>
        )}
      </div>

      {assessment.recommendations?.length > 0 && (
        <div>
          <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8, color: '#2C2C2A' }}>Recommended actions</div>
          {assessment.recommendations.map((r, i) => (
            <div key={i} style={{ display: 'flex', gap: 12, padding: '7px 0', borderBottom: i < assessment.recommendations.length - 1 ? '1px solid #F1EFE8' : 'none' }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: '#2C2C2A', minWidth: 160, flexShrink: 0 }}>{r.action}</span>
              <span style={{ fontSize: 13, color: '#5F5E5A' }}>{r.detail}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function DocDetail({ fw, setFw, frameworks, doc, onBack }) {
  const assessment = doc?.llmAssessment || null;

  if (!doc) return (
    <div style={{ padding: "3rem 0", textAlign: "center", color: "#888" }}>
      <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8, color: "#5F5E5A" }}>No document selected</div>
      <div style={{ fontSize: 13 }}>Click a document in the scan results to view details.</div>
    </div>
  );

  return (
    <div>
      {/* Back + framework toggle */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div onClick={onBack} style={{ fontSize: 13, color: "#5F5E5A", cursor: "pointer" }}>← Back to scan results</div>
        <FwToggle fw={fw} setFw={setFw} frameworks={frameworks} />
      </div>

      {/* File header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 4, flexWrap: "wrap", gap: 8 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 500, color: "#2C2C2A" }}>{doc.name}</div>
          <div style={{ fontSize: 13, color: "#5F5E5A", marginTop: 2 }}>
            {doc.source} · {doc.folder} · {doc.docType} · {doc.rows ? `${doc.rows} rows · ` : ""}{doc.size}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "12px 0 16px", flexWrap: "wrap" }}>
        <Pill tier={effectiveTier(doc, fw)} fw={fw} frameworks={frameworks} />
        {doc.action && <ActionBadge action={doc.action} />}
        <button style={{ padding: "6px 16px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer", background: "#F5F4F0", color: "#5F5E5A", border: "0.5px solid #e5e4e0" }}>Override</button>
        <button style={{ padding: "6px 16px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer", background: "#2C2C2A", color: "#fff", border: "none" }}>Apply policy</button>
      </div>

      {/* Classification result card — matches mockup exactly */}
      <ClassificationCard doc={doc} fw={fw} frameworks={frameworks} assessment={assessment} />

      {/* Applicable regulations — from LLM */}
      {assessment?.regulations && <Regulations regulations={assessment.regulations} />}

      {/* AI risk assessment — from LLM */}
      <AIAssessment assessment={assessment} />

      {/* Retention schedule */}
      <RetentionCard retention={doc.retention} />

      {/* Two columns: Signals + Metadata */}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", gap: 16, marginBottom: 24 }}>
        <Card>
          <SignalAnalysis signals={doc.signals || []} />
        </Card>
        <Card>
          <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 16, color: "#2C2C2A" }}>Metadata</div>
          <MetaRow k="Source" v={doc.source} />
          <MetaRow k="Doc type" v={doc.docType} />
          {doc.rows && <MetaRow k="Records" v={`${doc.rows} rows`} />}
          <MetaRow k="Size" v={doc.size} />
          <MetaRow k="Confidence" v={doc.conf?.toFixed(2)} />
          <MetaRow k="Coverage" v={doc.coverage != null ? `${Math.round(doc.coverage * 100)}%` : "—"} />
          <MetaRow k="Severity" v={<span style={{ color: SEV[doc.severity]?.color }}>{SEV[doc.severity]?.label}</span>} />

          {doc.detBreakdown && (
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8, color: "#2C2C2A" }}>Detection breakdown</div>
              <div style={{ height: 8, borderRadius: 4, display: "flex", overflow: "hidden", marginBottom: 8 }}>
                <div style={{ width: `${doc.detBreakdown.pattern}%`, background: "#A32D2D" }} />
                <div style={{ width: `${doc.detBreakdown.keyword}%`, background: "#BA7517" }} />
                <div style={{ width: `${doc.detBreakdown.ner}%`, background: "#534AB7" }} />
              </div>
              <div style={{ display: "flex", gap: 12, fontSize: 12, color: "#5F5E5A" }}>
                <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#A32D2D", marginRight: 4, verticalAlign: "middle" }} />Pattern {doc.detBreakdown.pattern}%</span>
                <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#BA7517", marginRight: 4, verticalAlign: "middle" }} />Keyword {doc.detBreakdown.keyword}%</span>
                <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#534AB7", marginRight: 4, verticalAlign: "middle" }} />NER {doc.detBreakdown.ner}%</span>
              </div>
            </div>
          )}

          {doc.fwNote && (
            <div style={{ background: "#F5F4F0", borderRadius: 8, padding: "12px 14px", fontSize: 13, color: "#5F5E5A", lineHeight: 1.6, marginTop: 16 }}>
              <span style={{ fontWeight: 500, color: "#2C2C2A" }}>{frameworks[fw]?.full || fw}:</span> {doc.fwNote[fw]}
            </div>
          )}
        </Card>
      </div>

      {/* Content preview — UNCHANGED from original */}
      {doc.contentPreview && (
        <Card>
          <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 12, color: "#2C2C2A" }}>Content preview (redacted)</div>
          <pre dir="auto" style={{ background: "#F5F4F0", borderRadius: 8, padding: 16, fontFamily: "Tahoma, monospace", fontSize: 13, lineHeight: 1.7, color: "#2C2C2A", whiteSpace: "pre-wrap", margin: 0 }}>{doc.contentPreview}</pre>
        </Card>
      )}
    </div>
  );
}

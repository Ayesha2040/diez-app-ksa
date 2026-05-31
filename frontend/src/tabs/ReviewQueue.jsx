import { useState, useEffect } from 'react';
import { API, SEV } from '../config';
import { Pill, Card, MetricCard, ActionBadge } from '../components';

export default function ReviewQueue({ fw, frameworks, docs, onDocUpdate }) {
  const [items, setItems]         = useState([]);
  const [resolving, setResolving] = useState(null);

  useEffect(() => {
    fetch(`${API}/review-queue`)
      .then(r => r.json())
      .then(data => setItems(Array.isArray(data) ? data : []))
      .catch(() => setItems(docs.filter(d => d.action === "human-review")));
  }, [docs]);

  const handleResolve = async (id, action) => {
    setResolving(id);
    try {
      const res = await fetch(`${API}/review-queue/${id}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        setItems(prev => prev.filter(it => it.id !== id));
        // Propagate the new action back to App.jsx so DocScan badge updates
        onDocUpdate?.(id, { action, reviewResolved: true });
      }
    } catch (e) {
      console.error("Resolve failed", e);
    } finally {
      setResolving(null);
    }
  };

  const avgRisk = items.length
    ? Math.round(items.reduce((s, r) => s + (r.riskScore || 0), 0) / items.length)
    : 0;

  if (items.length === 0) {
    return (
      <div style={{ padding: "3rem 0", textAlign: "center", color: "#888" }}>
        <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8, color: "#27500A" }}>
          Review queue is clear
        </div>
        <div style={{ fontSize: 13 }}>
          Files with high risk and low confidence appear here for human validation.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 500, color: "#2C2C2A" }}>Review queue</div>
          <div style={{ fontSize: 13, color: "#5F5E5A", marginTop: 2 }}>
            High-risk files where confidence is below threshold — require human validation
          </div>
        </div>
        <span style={{ background: "#FAEEDA", color: "#633806", padding: "4px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500 }}>
          {items.length} pending
        </span>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <MetricCard label="Pending review" value={items.length} accent="#BA7517" sub="Human decision required" />
        <MetricCard label="Avg risk score" value={avgRisk} accent="#A32D2D" sub="Of queued files" />
        <MetricCard label="Quadrant" value="Hi-risk / Lo-conf" accent="#534AB7" sub="Potential breach, uncertain" />
      </div>

      {items.map((doc, idx) => (
        <Card key={doc.id || idx} style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
                <div style={{ fontSize: 14, fontWeight: 500, color: "#2C2C2A" }}>{doc.name}</div>
                <Pill tier={doc.tier} fw={fw} frameworks={frameworks} />
                <ActionBadge action={doc.action} />
              </div>
              <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>
                {doc.docType} · Risk {doc.riskScore}/100 · Confidence {doc.conf != null ? `${Math.round(doc.conf * 100)}%` : "—"} · Coverage {doc.coverage != null ? `${Math.round(doc.coverage * 100)}%` : "—"}
              </div>
              {doc.conflict && (
                <div style={{ fontSize: 11, background: "#FAEEDA", color: "#633806", padding: "3px 8px", borderRadius: 6, display: "inline-block", marginBottom: 8 }}>
                  Filename/content conflict detected
                </div>
              )}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                {(doc.signals || []).filter(s => s.detected && s.sev !== "info").map((s, i) => (
                  <span key={i} style={{
                    fontSize: 11, padding: "2px 8px", borderRadius: 10,
                    background: s.sev === "critical" ? "#FCEBEB" : s.sev === "high" ? "#FAECE7" : "#FAEEDA",
                    color:      s.sev === "critical" ? "#791F1F"  : s.sev === "high" ? "#712B13"  : "#633806",
                  }}>{s.name}</span>
                ))}
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6, flexShrink: 0 }}>
              <div style={{ fontSize: 11, color: "#888", marginBottom: 2, textAlign: "right" }}>Resolve as</div>
              <button
                onClick={() => handleResolve(doc.id, "auto-enforce")}
                disabled={resolving === doc.id}
                style={{ padding: "5px 12px", borderRadius: 6, fontSize: 11, fontWeight: 500, cursor: "pointer", background: "#FCEBEB", color: "#791F1F", border: "0.5px solid #F7C1C1" }}>
                Enforce controls
              </button>
              <button
                onClick={() => handleResolve(doc.id, "auto-file")}
                disabled={resolving === doc.id}
                style={{ padding: "5px 12px", borderRadius: 6, fontSize: 11, fontWeight: 500, cursor: "pointer", background: "#EAF3DE", color: "#27500A", border: "0.5px solid #C0DD97" }}>
                File as-is
              </button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

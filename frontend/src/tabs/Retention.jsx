import { useState, useEffect } from 'react';
import { API, SEV } from '../config';
import { Pill, Card, MetricCard } from '../components';

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

function StatusBadge({ status }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.active;
  return (
    <span style={{ background: s.bg, color: s.fg, padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 500, whiteSpace: "nowrap" }}>
      {s.label}
    </span>
  );
}

function DaysChip({ days, status }) {
  if (status === "disposed" || days == null) return <span style={{ color: "#888", fontSize: 12 }}>—</span>;
  const color = days < 0 ? "#791F1F" : days <= 90 ? "#633806" : "#27500A";
  const label = days < 0 ? `${Math.abs(days)}d overdue` : `${days}d remaining`;
  return <span style={{ fontSize: 12, fontWeight: 500, color }}>{label}</span>;
}

export default function Retention({ fw, frameworks, docs }) {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("all");
  const [disposing, setDisposing] = useState(null);

  useEffect(() => {
    fetch(`${API}/retention`)
      .then(r => r.json())
      .then(data => {
        // Only keep items that have retention data — old persisted docs may not
        const valid = data.filter(it => it.retention && it.retention.periodYears != null);
        if (valid.length > 0) {
          setItems(valid);
        } else {
          // Fallback to local docs that have retention (re-scanned after Phase 3)
          setItems(docs.filter(d => d.retention).map(d => ({
            id: d.id, name: d.name, tier: d.tier,
            docType: d.docType, severity: d.severity,
            retention: d.retention,
          })));
        }
      })
      .catch(() => {
        setItems(docs.filter(d => d.retention).map(d => ({
          id: d.id, name: d.name, tier: d.tier,
          docType: d.docType, severity: d.severity,
          retention: d.retention,
        })));
      });
  }, [docs]);

  const handleDispose = async (id) => {
    setDisposing(id);
    try {
      await fetch(`${API}/retention/${id}/dispose`, { method: "POST" });
      setItems(prev => prev.map(it =>
        it.id === id
          ? { ...it, retention: { ...it.retention, status: "disposed", daysRemaining: null } }
          : it
      ));
    } catch (e) {
      console.error("Dispose failed", e);
    } finally {
      setDisposing(null);
    }
  };

  const filtered = filter === "all" ? items : items.filter(it => it.retention?.status === filter);

  const activeCount    = items.filter(it => it.retention?.status === "active").length;
  const reviewCount    = items.filter(it => it.retention?.status === "review_due").length;
  const overdueCount   = items.filter(it => it.retention?.status === "overdue").length;
  const disposedCount  = items.filter(it => it.retention?.status === "disposed").length;

  const filterBtn = (label, val) => (
    <button onClick={() => setFilter(val)} style={{
      padding: "4px 12px", borderRadius: 6, fontSize: 12, cursor: "pointer",
      background: filter === val ? "#2C2C2A" : "transparent",
      color: filter === val ? "#fff" : "#5F5E5A",
      border: filter === val ? "none" : "0.5px solid #e5e4e0",
      fontWeight: 500,
    }}>{label}</button>
  );

  if (items.length === 0) {
    return (
      <div style={{ padding: "3rem 0", textAlign: "center", color: "#888" }}>
        <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8, color: "#5F5E5A" }}>No retention data</div>
        <div style={{ fontSize: 13, marginBottom: 6 }}>Upload and scan files to see retention schedules.</div>
        <div style={{ fontSize: 12, color: "#aaa" }}>
          Files scanned before the retention feature was enabled need to be re-uploaded.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div style={{ fontSize: 18, fontWeight: 500, color: "#2C2C2A" }}>Retention schedule</div>
        {overdueCount > 0 && (
          <span style={{ background: "#FCEBEB", color: "#791F1F", padding: "4px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500 }}>
            {overdueCount} file{overdueCount !== 1 ? "s" : ""} overdue for disposal
          </span>
        )}
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <MetricCard label="Active"      value={activeCount}   sub="Within retention period" />
        <MetricCard label="Review due"  value={reviewCount}   sub="Within 90 days"           accent="#BA7517" />
        <MetricCard label="Overdue"     value={overdueCount}  sub="Past retention date"       accent="#A32D2D" />
        <MetricCard label="Disposed"    value={disposedCount} sub="Confirmed disposal"        accent="#888780" />
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {filterBtn("All", "all")}
        {filterBtn("Active", "active")}
        {filterBtn("Review due", "review_due")}
        {filterBtn("Overdue", "overdue")}
        {filterBtn("Disposed", "disposed")}
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr>
              {["File", "Classification", "Retention period", "Legal basis", "Disposal action", "Review date", "Status", ""].map(h => (
                <th key={h} style={{ textAlign: "left", padding: "10px 8px", fontWeight: 500, fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((item, idx) => {
              const ret = item.retention || {};
              const isDisposed = ret.status === "disposed";
              return (
                <tr key={item.id || idx} style={{ opacity: isDisposed ? 0.5 : 1 }}>
                  <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                    <div style={{ fontWeight: 500, color: "#2C2C2A", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.name}</div>
                    <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>{item.docType}</div>
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                    <Pill tier={item.tier} fw={fw} frameworks={frameworks} />
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                    <span style={{ fontWeight: 500, color: "#2C2C2A" }}>
                      {ret.periodYears > 0 ? `${ret.periodYears} years` : "No minimum"}
                    </span>
                    <DaysChip days={ret.daysRemaining} status={ret.status} />
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0", maxWidth: 220 }}>
                    <span style={{ fontSize: 11, color: "#5F5E5A", lineHeight: 1.5 }}>
                      {ret.basis || "—"}
                    </span>
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                    <span style={{ background: "#F1EFE8", color: "#5F5E5A", padding: "2px 8px", borderRadius: 4, fontSize: 11 }}>
                      {ACTION_LABEL[ret.disposalAction] || ret.disposalAction || "—"}
                    </span>
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0", whiteSpace: "nowrap" }}>
                    <span style={{ fontSize: 12, color: "#2C2C2A" }}>
                      {ret.reviewDate || "—"}
                    </span>
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                    <StatusBadge status={ret.status || "active"} />
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                    {!isDisposed && (
                      <button
                        onClick={() => handleDispose(item.id)}
                        disabled={disposing === item.id}
                        style={{
                          padding: "4px 10px", borderRadius: 6, fontSize: 11, cursor: "pointer",
                          background: "transparent", color: "#A32D2D",
                          border: "0.5px solid #A32D2D", fontWeight: 500,
                          opacity: disposing === item.id ? 0.5 : 1,
                        }}
                      >
                        {disposing === item.id ? "..." : "Mark disposed"}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 && (
        <div style={{ padding: "2rem 0", textAlign: "center", color: "#888", fontSize: 13 }}>
          No files match this filter.
        </div>
      )}
    </div>
  );
}

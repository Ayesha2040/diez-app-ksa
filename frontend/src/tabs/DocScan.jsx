import { useState } from 'react';
import { Pill, SevDot, SrcIcon, DetTag, ConfBar, MetricCard, FwToggle, ActionBadge } from '../components';
import { SEV, effectiveTier } from '../config';

export default function DocScan({ fw, setFw, frameworks, docs, onSelectDoc }) {
  const [sortBy, setSortBy] = useState(null);
  const [sortDir, setSortDir] = useState('desc');
  const [filter, setFilter] = useState('all');

  const sensCount = docs.filter(d => d.tier === "sens" || d.tier === "secret").length;
  const autoCount = docs.filter(d => d.conf >= 0.85).length;
  const pendingCount = docs.filter(d => d.conf < 0.85).length;

  const handleSort = (col) => {
    if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortBy(col); setSortDir('desc'); }
  };

  let filtered = [...docs];
  if (filter === 'sens') filtered = filtered.filter(d => d.tier === 'sens' || d.tier === 'secret');
  else if (filter === 'conf') filtered = filtered.filter(d => d.tier === 'conf');
  else if (filter === 'open') filtered = filtered.filter(d => d.tier === 'open');
  else if (filter === 'critical') filtered = filtered.filter(d => d.severity === 'critical');
  else if (filter === 'pending') filtered = filtered.filter(d => d.conf < 0.85);

  if (sortBy) {
    filtered.sort((a, b) => {
      let va, vb;
      if (sortBy === 'conf') { va = a.conf; vb = b.conf; }
      else if (sortBy === 'severity') {
        const order = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };
        va = order[a.severity] || 0; vb = order[b.severity] || 0;
      } else if (sortBy === 'tier') {
        const order = { secret: 3, sens: 2, conf: 1, open: 0 };
        va = order[a.tier] || 0; vb = order[b.tier] || 0;
      } else if (sortBy === 'name') { va = a.name; vb = b.name; }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }

  const filterBtn = (label, val) => (
    <button onClick={() => setFilter(val)} style={{
      padding: "4px 12px", borderRadius: 6, fontSize: 12, cursor: "pointer",
      background: filter === val ? "#2C2C2A" : "transparent",
      color: filter === val ? "#fff" : "#5F5E5A",
      border: filter === val ? "none" : "0.5px solid #e5e4e0",
      fontWeight: 500,
    }}>{label}</button>
  );

  const sortArrow = (col) => sortBy === col ? (sortDir === 'asc' ? ' ↑' : ' ↓') : '';

  if (docs.length === 0) {
    return (
      <div style={{ padding: "3rem 0", textAlign: "center", color: "#888" }}>
        <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8, color: "#5F5E5A" }}>No files scanned yet</div>
        <div style={{ fontSize: 13 }}>Upload files in the Upload tab to see scan results here.</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div style={{ fontSize: 18, fontWeight: 500, color: "#2C2C2A" }}>Scan results — Client estate</div>
          <span style={{ background: "#EAF3DE", color: "#27500A", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 500 }}>Scan complete</span>
        </div>
        <FwToggle fw={fw} setFw={setFw} frameworks={frameworks} />
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <MetricCard label="Total scanned" value={docs.length} sub="Uploaded files" />
        <MetricCard label="Sensitive / secret" value={sensCount} sub={`${Math.round(sensCount / docs.length * 100)}% of files`} accent="#A32D2D" />
        <MetricCard label="Auto-classified" value={autoCount} sub="Confidence ≥ 0.85" accent="#0F6E56" />
        <MetricCard label="Pending review" value={pendingCount} sub="Confidence < 0.85" accent="#BA7517" />
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {filterBtn("All", "all")}
        {filterBtn("Sensitive", "sens")}
        {filterBtn("Confidential", "conf")}
        {filterBtn("Open", "open")}
        {filterBtn("Critical", "critical")}
        {filterBtn("Pending", "pending")}
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr>
              <th onClick={() => handleSort('name')} style={{ textAlign: "left", padding: "10px 8px", fontWeight: 500, fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0", cursor: "pointer" }}>Document{sortArrow('name')}</th>
              <th style={{ textAlign: "left", padding: "10px 8px", fontWeight: 500, fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0" }}>Source</th>
              <th style={{ textAlign: "left", padding: "10px 8px", fontWeight: 500, fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0" }}>Doc type</th>
              <th onClick={() => handleSort('tier')} style={{ textAlign: "left", padding: "10px 8px", fontWeight: 500, fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0", cursor: "pointer" }}>Classification{sortArrow('tier')}</th>
              <th onClick={() => handleSort('conf')} style={{ textAlign: "left", padding: "10px 8px", fontWeight: 500, fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0", cursor: "pointer" }}>Confidence{sortArrow('conf')}</th>
              <th onClick={() => handleSort('severity')} style={{ textAlign: "left", padding: "10px 8px", fontWeight: 500, fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0", cursor: "pointer" }}>Severity{sortArrow('severity')}</th>
              <th style={{ textAlign: "left", padding: "10px 8px", fontWeight: 500, fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0" }}>Key detectors</th>
              <th style={{ textAlign: "left", padding: "10px 8px", fontWeight: 500, fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0" }}>Retention</th>
              <th style={{ textAlign: "left", padding: "10px 8px", fontWeight: 500, fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((doc, idx) => (
              <tr key={doc.id || idx} onClick={() => onSelectDoc(docs.indexOf(doc))} style={{ cursor: "pointer" }}>
                <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                  <div dir="auto" style={{ fontWeight: 500 }}>{doc.name}</div>
                  <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>{doc.rows ? `${doc.rows} rows · ` : "Unstructured · "}{doc.size}</div>
                </td>
                <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12 }}>
                    <SrcIcon tag={doc.sourceTag} color={doc.sourceColor} />{doc.folder}
                  </span>
                </td>
                <td style={{ padding: "10px 8px", fontSize: 12, color: "#5F5E5A", borderBottom: "0.5px solid #e5e4e0" }}>{doc.docType}</td>
                <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}><Pill tier={effectiveTier(doc, fw)} fw={fw} frameworks={frameworks} /></td>
                <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}><ConfBar val={doc.conf} sev={doc.severity} /></td>
                <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                    <SevDot sev={doc.severity} /><span style={{ fontSize: 12, color: SEV[doc.severity]?.color }}>{SEV[doc.severity]?.label}</span>
                  </span>
                </td>
                <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {(doc.detectors || []).map((d, i) => <DetTag key={i} t={d} />)}
                  </div>
                </td>
                <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0", whiteSpace: "nowrap" }}>
                  {doc.retention ? (
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 500, color: "#2C2C2A" }}>
                        {doc.retention.periodYears > 0 ? `${doc.retention.periodYears} yrs` : "None"}
                      </div>
                      <div style={{
                        fontSize: 10, fontWeight: 500, marginTop: 3, padding: "1px 6px",
                        borderRadius: 10, display: "inline-block",
                        background: doc.retention.status === "overdue" ? "#FCEBEB"
                          : doc.retention.status === "review_due" ? "#FAEEDA" : "#F1EFE8",
                        color: doc.retention.status === "overdue" ? "#791F1F"
                          : doc.retention.status === "review_due" ? "#633806" : "#5F5E5A",
                      }}>
                        {doc.retention.status === "overdue" ? "Overdue"
                          : doc.retention.status === "review_due" ? "Review due" : "Active"}
                      </div>
                    </div>
                  ) : <span style={{ color: "#ccc", fontSize: 12 }}>—</span>}
                </td>
                <td style={{ padding: "10px 8px", borderBottom: "0.5px solid #e5e4e0" }}>
                  {doc.action ? <ActionBadge action={doc.action} /> : <span style={{ color: "#ccc", fontSize: 12 }}>—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

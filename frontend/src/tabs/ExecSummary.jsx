import { Pill, SevDot, SrcIcon, Card, MetricCard, FwToggle } from '../components';
import { SEV, API } from '../config';

export default function ExecSummary({ fw, setFw, frameworks, docs }) {
  if (docs.length === 0) {
    return (
      <div style={{ padding: "3rem 0", textAlign: "center", color: "#888" }}>
        <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8, color: "#5F5E5A" }}>No data to summarise</div>
        <div style={{ fontSize: 13 }}>Upload and scan files first.</div>
      </div>
    );
  }

  const critCount = docs.filter(d => d.severity === "critical").length;
  const highCount = docs.filter(d => d.severity === "high").length;
  const medCount = docs.filter(d => d.severity === "medium").length;
  const lowCount = docs.filter(d => d.severity === "low").length;
  const pendingCount = docs.filter(d => d.conf < 0.85).length;

  const tierCounts = { open: 0, conf: 0, sens: 0, secret: 0 };
  docs.forEach(d => tierCounts[d.tier] = (tierCounts[d.tier] || 0) + 1);

  // Source breakdown
  const sources = {};
  docs.forEach(d => {
    const key = d.source || "Unknown";
    if (!sources[key]) sources[key] = { name: key, tag: d.sourceTag, color: d.sourceColor, count: 0 };
    sources[key].count++;
  });
  const sourceList = Object.values(sources).sort((a, b) => b.count - a.count);

  // Auto-generate recommendations from signals
  const recommendations = [];
  const critDocs = docs.filter(d => d.severity === "critical");
  if (critDocs.length > 0) {
    recommendations.push({
      sev: "critical",
      title: `Encrypt and restrict ${critDocs.length} critical file${critDocs.length > 1 ? 's' : ''} immediately`,
      desc: `${critDocs.map(d => d.name).join(', ')} contain${critDocs.length === 1 ? 's' : ''} bulk PII and/or AML-regulated data. Apply sensitivity labels, enable encryption, restrict to named individuals.`,
    });
  }
  const secretDocs = docs.filter(d => d.tier === "secret");
  if (secretDocs.length > 0) {
    recommendations.push({
      sev: "high",
      title: `Classify ${secretDocs.length} file${secretDocs.length > 1 ? 's' : ''} as Top Secret`,
      desc: `${secretDocs.map(d => d.name).join(', ')} contain${secretDocs.length === 1 ? 's' : ''} strategic content. Named-individual access only. NCA DCC-1:2022 Top Secret controls apply.`,
    });
  }
  const pendingDocs = docs.filter(d => d.conf < 0.85);
  if (pendingDocs.length > 0) {
    recommendations.push({
      sev: "medium",
      title: `Route ${pendingDocs.length} file${pendingDocs.length > 1 ? 's' : ''} to data steward for review`,
      desc: `Confidence below 0.85 — human validation required before auto-classification.`,
    });
  }
  const openDocs = docs.filter(d => d.tier === "open");
  if (openDocs.length > 0) {
    recommendations.push({
      sev: "low",
      title: `Confirm ${openDocs.length} file${openDocs.length > 1 ? 's' : ''} for open data publication`,
      desc: `${openDocs.map(d => d.name).join(', ')} — no sensitive data detected. Validate with NDMO and publish to Saudi Open Data Platform (data.gov.sa).`,
    });
  }

  const handleExport = async () => {
    try {
      const res = await fetch(`${API}/export?framework=${fw}`);
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Client_Classification_Report.xlsx';
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e) {
      console.error('Export failed', e);
    }
  };

  const tiers = frameworks[fw]?.tiers || {};

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20, flexWrap: "wrap", gap: 8 }}>
        <div style={{ fontSize: 18, fontWeight: 500, color: "#2C2C2A" }}>Executive summary — Client data estate</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <FwToggle fw={fw} setFw={setFw} frameworks={frameworks} />
          <button onClick={handleExport} style={{ padding: "6px 16px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer", background: "#2C2C2A", color: "#fff", border: "none" }}>Export report</button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <MetricCard label="Total files" value={docs.length} />
        <MetricCard label="Critical" value={critCount} accent="#A32D2D" sub="Immediate action" />
        <MetricCard label="High" value={highCount} accent="#D85A30" sub="Review within 7 days" />
        <MetricCard label="Pending review" value={pendingCount} accent="#BA7517" sub="Low confidence" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", gap: 16, marginBottom: 24 }}>
        <Card>
          <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 16, color: "#2C2C2A" }}>Classification distribution</div>
          {Object.entries(tiers).map(([k, t]) => (
            <div key={k} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
              <div style={{ minWidth: 200, flexShrink: 0 }}><Pill tier={k} fw={fw} frameworks={frameworks} /></div>
              <div style={{ flex: 1, height: 8, background: "#F5F4F0", borderRadius: 4, minWidth: 40 }}>
                <div style={{ width: `${(tierCounts[k] || 0) / docs.length * 100}%`, height: "100%", borderRadius: 4, background: t.fg, minWidth: (tierCounts[k] || 0) > 0 ? 4 : 0 }} />
              </div>
              <span style={{ fontSize: 13, color: "#5F5E5A", minWidth: 24, textAlign: "right" }}>{tierCounts[k] || 0}</span>
            </div>
          ))}
        </Card>
        <Card>
          <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 16, color: "#2C2C2A" }}>Severity breakdown</div>
          {[{ l: "Critical", c: critCount, s: "critical" }, { l: "High", c: highCount, s: "high" }, { l: "Medium", c: medCount, s: "medium" }, { l: "Low", c: lowCount, s: "low" }].map(r => (
            <div key={r.s} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
              <div style={{ width: 120, display: "flex", alignItems: "center", gap: 8 }}><SevDot sev={r.s} /><span style={{ fontSize: 13 }}>{r.l}</span></div>
              <div style={{ flex: 1, height: 8, background: "#F5F4F0", borderRadius: 4 }}>
                <div style={{ width: `${r.c / docs.length * 100}%`, height: "100%", borderRadius: 4, background: SEV[r.s]?.color, minWidth: r.c > 0 ? 4 : 0 }} />
              </div>
              <span style={{ fontSize: 13, color: "#5F5E5A", minWidth: 24, textAlign: "right" }}>{r.c}</span>
            </div>
          ))}
        </Card>
      </div>

      {recommendations.length > 0 && (
        <Card style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 16, color: "#2C2C2A" }}>Prioritised recommendations</div>
          {recommendations.map((rec, i) => (
            <div key={i} style={{ display: "flex", gap: 12, padding: "12px 0", borderBottom: i < recommendations.length - 1 ? "0.5px solid #e5e4e0" : "none" }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: SEV[rec.sev]?.color, flexShrink: 0, marginTop: 5 }} />
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: "#2C2C2A", marginBottom: 4 }}>{rec.title}</div>
                <div style={{ fontSize: 13, color: "#5F5E5A", lineHeight: 1.6 }}>{rec.desc}</div>
              </div>
            </div>
          ))}
        </Card>
      )}

      {sourceList.length > 0 && (
        <Card>
          <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 16, color: "#2C2C2A" }}>Source breakdown</div>
          {sourceList.map((env, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
              <div style={{ width: 160, display: "flex", alignItems: "center", gap: 8 }}>
                <SrcIcon tag={env.tag} color={env.color} />
                <span style={{ fontSize: 13, color: "#2C2C2A" }}>{env.name}</span>
              </div>
              <div style={{ flex: 1, height: 8, background: "#F5F4F0", borderRadius: 4 }}>
                <div style={{ width: `${env.count / docs.length * 100}%`, height: "100%", borderRadius: 4, background: env.color }} />
              </div>
              <span style={{ fontSize: 13, color: "#5F5E5A", minWidth: 30, textAlign: "right" }}>{env.count}</span>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}

import { SEV } from './config';

export const Pill = ({ tier, fw, frameworks }) => {
  if (!frameworks || !frameworks[fw]) return null;
  const t = frameworks[fw].tiers?.[tier];
  if (!t) return null;
  return <span style={{ background: t.bg, color: t.fg, padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 500, whiteSpace: "nowrap", display: "inline-block" }}>{t.label}</span>;
};

export const SevDot = ({ sev }) => (
  <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: SEV[sev]?.color || "#888", flexShrink: 0 }} />
);

export const SevBadge = ({ sev }) => {
  const sv = SEV[sev];
  if (!sv) return null;
  return <span style={{ background: sv.bg, color: sv.fg, padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 500, minWidth: 56, textAlign: "center", display: "inline-block" }}>{sv.label}</span>;
};

export const SrcIcon = ({ tag, color }) => (
  <span style={{ width: 22, height: 22, borderRadius: 4, display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 500, color: "#fff", background: color, flexShrink: 0 }}>{tag}</span>
);

export const DetTag = ({ t }) => (
  <span dir="auto" style={{ background: "#F1EFE8", color: "#5F5E5A", padding: "2px 6px", borderRadius: 4, fontSize: 11, fontFamily: "inherit" }}>{t}</span>
);

export const ConfBar = ({ val, sev }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
    <span style={{ display: "inline-block", width: 60, height: 6, background: "#F1EFE8", borderRadius: 3 }}>
      <span style={{ display: "block", width: `${val * 100}%`, height: "100%", borderRadius: 3, background: SEV[sev]?.color || "#888" }} />
    </span>
    <span style={{ fontSize: 12, color: "#5F5E5A" }}>{val.toFixed(2)}</span>
  </span>
);

export const Card = ({ children, style }) => (
  <div style={{ background: "#fff", border: "0.5px solid #e5e4e0", borderRadius: 12, padding: "1rem 1.25rem", ...style }}>{children}</div>
);

export const MetricCard = ({ label, value, sub, accent }) => (
  <div style={{ background: "#F5F4F0", borderRadius: 8, padding: "14px 16px", flex: 1, minWidth: 120 }}>
    <div style={{ fontSize: 12, color: "#5F5E5A", marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 22, fontWeight: 500, color: accent || "#2C2C2A" }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>{sub}</div>}
  </div>
);

export const FwToggle = ({ fw, setFw, frameworks }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
    <span style={{ fontSize: 12, color: "#5F5E5A", marginRight: 4 }}>Framework</span>
    {Object.entries(frameworks).map(([k, v]) => (
      <button key={k} onClick={() => setFw(k)} style={{
        padding: "4px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
        background: fw === k ? "#2C2C2A" : "transparent",
        color: fw === k ? "#fff" : "#5F5E5A",
        border: fw === k ? "none" : "0.5px solid #e5e4e0",
      }}>{v.label}</button>
    ))}
  </div>
);

export const SignalAnalysis = ({ signals }) => (
  <div>
    <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 16, color: "#2C2C2A" }}>Signal analysis</div>
    {signals.filter(sg => sg.detected).map((sg, i) => (
      <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "8px 0" }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: SEV[sg.sev]?.color || "#888", flexShrink: 0, marginTop: 5 }} />
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: "#2C2C2A" }}>{sg.name}</span>
            <SevBadge sev={sg.sev} />
          </div>
          {sg.entities && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {sg.entities.map((e, j) => (
                <span dir="auto" key={j} style={{ background: "#F1EFE8", color: "#5F5E5A", padding: "2px 8px", borderRadius: 4, fontSize: 11 }}>{e}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    ))}
    {signals.some(sg => !sg.detected) && (
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 16px", paddingTop: 8, marginTop: 4 }}>
        {signals.filter(sg => !sg.detected).map((sg, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#D3D1C7", flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: "#888" }}>{sg.name}</span>
          </div>
        ))}
      </div>
    )}
  </div>
);

export const MetaRow = ({ k, v }) => (
  <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "0.5px solid #e5e4e0", fontSize: 13 }}>
    <span style={{ color: "#5F5E5A" }}>{k}</span>
    <span style={{ color: "#2C2C2A", fontWeight: 500 }}>{v}</span>
  </div>
);

const ACTION_STYLES = {
  "auto-enforce":  { bg: "#FCEBEB", fg: "#791F1F", label: "Auto-enforce" },
  "human-review":  { bg: "#FAEEDA", fg: "#633806", label: "Human review" },
  "auto-file":     { bg: "#EAF3DE", fg: "#27500A", label: "Auto-file" },
  "spot-check":    { bg: "#F1EFE8", fg: "#5F5E5A", label: "Spot-check" },
};

export const ActionBadge = ({ action }) => {
  const s = ACTION_STYLES[action] || ACTION_STYLES["spot-check"];
  return (
    <span style={{ background: s.bg, color: s.fg, padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 500, whiteSpace: "nowrap" }}>
      {s.label}
    </span>
  );
};

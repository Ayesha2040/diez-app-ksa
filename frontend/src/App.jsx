import { useState, useEffect, useCallback } from 'react';
import { API } from './config';
import Upload from './tabs/Upload';
import Datasets from './tabs/Datasets';
import DocScan from './tabs/DocScan';
import DocDetail from './tabs/DocDetail';
import ExecSummary from './tabs/ExecSummary';
import Retention from './tabs/Retention';
import ReviewQueue from './tabs/ReviewQueue';

const TABS = ["Upload", "Datasets", "Document scan", "Document detail", "Executive summary", "Retention", "Review queue"];

const DEFAULT_FRAMEWORKS = {
  ndmo: { id: "ndmo", label: "NDMO", full: "Saudi National Data Management Office", tiers: {
    open:   { label: "Public",     bg: "#EAF3DE", fg: "#27500A" },
    conf:   { label: "Confidential", bg: "#FAEEDA", fg: "#633806" },
    sens:   { label: "Secret",     bg: "#FCEBEB", fg: "#791F1F" },
    secret: { label: "Top Secret", bg: "#EEEDFE", fg: "#3C3489" },
  }},
  pdpl: { id: "pdpl", label: "KSA PDPL", full: "KSA Personal Data Protection Law", tiers: {
    open:   { label: "Non-personal data",             bg: "#EAF3DE", fg: "#27500A" },
    conf:   { label: "Personal data",                 bg: "#FAEEDA", fg: "#633806" },
    sens:   { label: "Sensitive personal data",       bg: "#FCEBEB", fg: "#791F1F" },
    secret: { label: "Sensitive data — restricted",   bg: "#EEEDFE", fg: "#3C3489" },
  }},
};

export default function App() {
  const [tab, setTab] = useState(0);
  const [fw, setFw] = useState("ndmo");
  const [frameworks, setFrameworks] = useState(DEFAULT_FRAMEWORKS);
  const [scannedDocs, setScannedDocs] = useState([]);
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [scanning, setScanning] = useState(false);

  // Fetch framework definitions from backend
  useEffect(() => {
    fetch(`${API}/frameworks`)
      .then(r => r.json())
      .then(data => { if (data && Object.keys(data).length > 0) setFrameworks(data); })
      .catch(() => {});
  }, []);

  // Restore persisted scan results from backend store on mount
  useEffect(() => {
    fetch(`${API}/results`)
      .then(r => r.json())
      .then(data => { if (Array.isArray(data) && data.length > 0) setScannedDocs(data); })
      .catch(() => {});
  }, []);

  const handleScanResults = useCallback((results) => {
    const valid = results.filter(r => !r.error);
    if (valid.length === 0) return;
    setScannedDocs(prev => {
      const existingIds = new Set(prev.map(d => d.id));
      // Replace existing docs that were re-scanned, append genuinely new ones
      const updated = prev.map(d => valid.find(v => v.id === d.id) || d);
      const brandNew = valid.filter(v => !existingIds.has(v.id));
      return [...updated, ...brandNew];
    });
    setTab(2);
  }, []);

  // Called by ReviewQueue when a human-review item is resolved
  const handleDocUpdate = useCallback((id, patch) => {
    setScannedDocs(prev => prev.map(d => d.id === id ? { ...d, ...patch } : d));
  }, []);

  const handleSelectDoc = (idx) => { setSelectedIdx(idx); setTab(3); };
  const handleBack = () => setTab(2);

  const handleClearAll = useCallback(async () => {
    try { await fetch(`${API}/results`, { method: "DELETE" }); } catch (_) {}
    setScannedDocs([]);
    setSelectedIdx(null);
    setTab(0);
  }, []);

  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", color: "#2C2C2A", maxWidth: 960, margin: "0 auto", padding: "0 16px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 0 12px", flexWrap: "wrap", gap: 8 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 500 }}>Data Classification Tool</div>
          <div style={{ fontSize: 13, color: "#888" }}>Data discovery & governance</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <span style={{ background: "#EAF3DE", color: "#27500A", padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 500 }}>
            {scannedDocs.length} file{scannedDocs.length !== 1 ? 's' : ''} scanned
          </span>
          <span style={{ background: "#F5F4F0", color: "#5F5E5A", padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 500 }}>
            KSA Data & AI
          </span>
        </div>
      </div>

      {/* Tab navigation */}
      <div style={{ display: "flex", gap: 0, borderBottom: "0.5px solid #e5e4e0", marginBottom: 24 }}>
        {TABS.map((t, i) => (
          <div key={t} onClick={() => setTab(i)} style={{
            padding: "10px 18px", fontSize: 13, cursor: "pointer",
            color: tab === i ? "#2C2C2A" : "#5F5E5A",
            fontWeight: tab === i ? 500 : 400,
            borderBottom: tab === i ? "2px solid #2C2C2A" : "2px solid transparent",
          }}>{t}</div>
        ))}
      </div>

      {/* Tab content */}
      {tab === 0 && <Upload onResults={handleScanResults} scanning={scanning} setScanning={setScanning} frameworks={frameworks} fw={fw} />}
      {tab === 1 && <Datasets fw={fw} setFw={setFw} frameworks={frameworks} scannedDocs={scannedDocs} />}
      {tab === 2 && <DocScan fw={fw} setFw={setFw} frameworks={frameworks} docs={scannedDocs} onSelectDoc={handleSelectDoc} onClearAll={handleClearAll} />}
      {tab === 3 && <DocDetail fw={fw} setFw={setFw} frameworks={frameworks} doc={scannedDocs[selectedIdx]} onBack={handleBack} />}
      {tab === 4 && <ExecSummary fw={fw} setFw={setFw} frameworks={frameworks} docs={scannedDocs} />}
      {tab === 5 && <Retention fw={fw} frameworks={frameworks} docs={scannedDocs} />}
      {tab === 6 && <ReviewQueue fw={fw} frameworks={frameworks} docs={scannedDocs} onDocUpdate={handleDocUpdate} />}
    </div>
  );
}

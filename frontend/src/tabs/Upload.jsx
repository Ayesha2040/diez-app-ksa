import { useState, useRef } from 'react';
import { API } from '../config';

const STATES = {
  pending:     { label: 'Waiting...',       color: '#888780', bg: '#F1EFE8', pct: 0 },
  reading:     { label: 'Reading file...',  color: '#888780', bg: '#F1EFE8', pct: 15 },
  detecting:   { label: 'Detecting signals...', color: '#378ADD', bg: '#E6F1FB', pct: 45 },
  classifying: { label: 'Classifying with AI...', color: '#378ADD', bg: '#E6F1FB', pct: 75 },
  done:        { label: 'Complete',         color: '#3B6D11', bg: '#EAF3DE', pct: 100 },
  error:       { label: 'Error',            color: '#A32D2D', bg: '#FCEBEB', pct: 100 },
};

function fileExt(name) {
  const m = name.match(/\.([^.]+)$/);
  return m ? m[1].slice(0, 3).toUpperCase() : 'FILE';
}

function tierLabel(tier, frameworks, fw) {
  if (!tier || !frameworks) return '';
  return frameworks[fw]?.tiers?.[tier]?.label || tier;
}

export default function Upload({ onResults, scanning, setScanning, frameworks, fw }) {
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState([]); // [{name, ext, state, result, error}]
  const inputRef = useRef();

  const updateFile = (i, patch) => {
    setFiles(prev => prev.map((f, j) => j === i ? { ...f, ...patch } : f));
  };

  const handleFiles = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    const arr = Array.from(fileList);
    const initialFiles = arr.map(f => ({
      name: f.name,
      ext: fileExt(f.name),
      state: 'pending',
      result: null,
      error: null,
    }));
    setFiles(initialFiles);
    setScanning(true);

    const results = [];

    for (let i = 0; i < arr.length; i++) {
      // Animate through states during the actual scan
      updateFile(i, { state: 'reading' });
      const readTimer = setTimeout(() => updateFile(i, { state: 'detecting' }), 400);
      const detectTimer = setTimeout(() => updateFile(i, { state: 'classifying' }), 1200);

      const form = new FormData();
      form.append('file', arr[i]);

      try {
        const res = await fetch(`${API}/scan`, { method: 'POST', body: form });
        clearTimeout(readTimer);
        clearTimeout(detectTimer);

        if (res.ok) {
          const data = await res.json();
          results.push(data);
          updateFile(i, { state: 'done', result: data });
        } else {
          const err = await res.json().catch(() => ({}));
          results.push({ name: arr[i].name, error: err.error || 'Scan failed' });
          updateFile(i, { state: 'error', error: err.error || 'Scan failed' });
        }
      } catch (e) {
        clearTimeout(readTimer);
        clearTimeout(detectTimer);
        results.push({ name: arr[i].name, error: 'Cannot reach backend' });
        updateFile(i, { state: 'error', error: 'Cannot reach backend' });
      }
    }

    onResults(results);
    setScanning(false);
  };

  const clearAll = () => {
    setFiles([]);
  };

  const completedCount = files.filter(f => f.state === 'done' || f.state === 'error').length;
  const hasFiles = files.length > 0;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 18, fontWeight: 500, color: '#2C2C2A' }}>Upload data files</div>
        {hasFiles && (
          <button onClick={clearAll} style={{ fontSize: 12, padding: '6px 14px', borderRadius: 8, border: '0.5px solid #e5e4e0', background: 'transparent', color: '#5F5E5A', cursor: 'pointer' }}>
            Clear all
          </button>
        )}
      </div>

      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => !scanning && inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? '#2C2C2A' : '#D3D1C7'}`,
          borderRadius: 12,
          padding: '40px 20px',
          textAlign: 'center',
          marginBottom: 16,
          background: dragOver ? '#F5F4F0' : '#FFFFFF',
          cursor: scanning ? 'default' : 'pointer',
          transition: 'all 0.15s',
        }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".xlsx,.xls,.csv,.tsv,.txt,.docx,.pdf,.json"
          style={{ display: 'none' }}
          onChange={e => handleFiles(e.target.files)}
        />
        <div style={{ fontSize: 28, color: '#D3D1C7', marginBottom: 10 }}>+</div>
        <div style={{ fontSize: 14, fontWeight: 500, color: '#2C2C2A', marginBottom: 4 }}>
          Drop files here or click to browse
        </div>
        <div style={{ fontSize: 12, color: '#888' }}>CSV, Excel, JSON, TXT, DOCX, PDF</div>
      </div>

      {hasFiles && (
        <div>
          <div style={{
            padding: '10px 14px',
            background: '#FFFFFF',
            border: '0.5px solid #e5e4e0',
            borderBottom: 'none',
            borderTopLeftRadius: 12,
            borderTopRightRadius: 12,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: '#2C2C2A' }}>
              {scanning ? `Processing ${files.length} file${files.length !== 1 ? 's' : ''}` : `${completedCount} file${completedCount !== 1 ? 's' : ''} processed`}
            </span>
            <span style={{ fontSize: 10, fontWeight: 500, padding: '2px 10px', borderRadius: 8, background: '#EAF3DE', color: '#27500A' }}>
              {completedCount} of {files.length} complete
            </span>
          </div>

          <div style={{
            background: '#FFFFFF',
            border: '0.5px solid #e5e4e0',
            borderBottomLeftRadius: 12,
            borderBottomRightRadius: 12,
            overflow: 'hidden',
          }}>
            {files.map((f, i) => {
              const st = STATES[f.state] || STATES.pending;
              const statusText = f.state === 'done' && f.result?.tier
                ? `Complete · ${tierLabel(f.result.tier, frameworks, fw)}`
                : f.state === 'error'
                ? `Error: ${f.error}`
                : st.label;
              return (
                <div key={i} style={{
                  padding: '12px 14px',
                  borderBottom: i < files.length - 1 ? '0.5px solid #e5e4e0' : 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: 6,
                    background: '#F1EFE8', color: '#5F5E5A',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 10, fontWeight: 500, flexShrink: 0,
                  }}>{f.ext}</div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: '#2C2C2A', marginBottom: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {f.name}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <span style={{ fontSize: 11, color: st.color }}>{statusText}</span>
                      <span style={{ fontSize: 11, fontWeight: 500, color: '#2C2C2A' }}>{st.pct}%</span>
                    </div>
                    <div style={{ height: 4, background: '#F1EFE8', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%',
                        width: `${st.pct}%`,
                        background: st.color,
                        borderRadius: 2,
                        transition: 'width 0.3s ease',
                      }} />
                    </div>
                  </div>

                  <div style={{ flexShrink: 0, width: 16, height: 16 }}>
                    {f.state === 'done' && (
                      <svg viewBox="0 0 16 16" fill="none" stroke="#3B6D11" strokeWidth="2.5">
                        <path d="M3 8l3.5 3.5L13 5" />
                      </svg>
                    )}
                    {f.state === 'error' && (
                      <svg viewBox="0 0 16 16" fill="none" stroke="#A32D2D" strokeWidth="2.5">
                        <path d="M4 4l8 8M12 4l-8 8" />
                      </svg>
                    )}
                    {(f.state === 'reading' || f.state === 'detecting' || f.state === 'classifying') && (
                      <div style={{
                        width: 12, height: 12,
                        border: '2px solid #D3D1C7',
                        borderTopColor: '#378ADD',
                        borderRadius: '50%',
                        animation: 'diez-spin 0.8s linear infinite',
                      }} />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <style>{`@keyframes diez-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

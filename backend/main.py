"""
EY Data Classification Tool — API Server
In production (Docker/Render), FastAPI also serves the React frontend build.
"""
import io
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles

from pipeline import scan
from frameworks import FRAMEWORKS
from export import export_xlsx
import store

app = FastAPI(title="EY Classification Engine", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "engine": "agent+rules", "version": "2.0"}


@app.get("/api/frameworks")
async def get_frameworks():
    return FRAMEWORKS


@app.post("/api/scan")
async def scan_file(file: UploadFile = File(...)):
    content = await file.read()
    result = scan(file.filename or "unknown", content)
    if "error" not in result:
        store.append(result)
    return result


@app.post("/api/scan-batch")
async def scan_batch(files: list[UploadFile] = File(...)):
    results = []
    for f in files:
        content = await f.read()
        result = scan(f.filename or "unknown", content)
        if "error" not in result:
            store.append(result)
        results.append(result)
    return results


@app.get("/api/results")
async def get_results():
    """Return all stored scan results — used by frontend on load to restore state."""
    return store.load()


@app.get("/api/export")
async def export_report(framework: str = "ndmo"):
    results = store.load()
    if not results:
        return {"error": "No scan results to export. Scan files first."}
    xlsx_bytes = export_xlsx(results, framework)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=EY_Classification_Report.xlsx"},
    )


@app.delete("/api/results")
async def clear_results():
    store.clear()
    return {"status": "cleared"}


# ── Retention endpoints ──────────────────────────────────────────────────────

@app.get("/api/retention")
async def get_retention():
    """All scan results with their retention status, sorted by review date."""
    results = store.load()
    retention_view = []
    for r in results:
        ret = r.get("retention", {})
        retention_view.append({
            "id":             r.get("id"),
            "name":           r.get("name"),
            "tier":           r.get("tier"),
            "docType":        r.get("docType"),
            "severity":       r.get("severity"),
            "retention":      ret,
        })
    retention_view.sort(key=lambda x: x["retention"].get("reviewDate") or "9999-12-31")
    return retention_view


@app.get("/api/retention/alerts")
async def get_retention_alerts():
    """Files with status review_due or overdue."""
    results = store.load()
    return [r for r in results if r.get("retention", {}).get("status") in ("review_due", "overdue")]


# ── Review queue ─────────────────────────────────────────────────────────────

@app.get("/api/review-queue")
async def get_review_queue():
    """Files routed to human review (high risk, low confidence)."""
    results = store.load()
    queue = [r for r in results if r.get("action") == "human-review"]
    queue.sort(key=lambda r: r.get("riskScore", 0), reverse=True)
    return queue


@app.post("/api/review-queue/{scan_id}/resolve")
async def resolve_review(scan_id: str, body: dict = {}):
    """Mark a review-queue item as resolved with an outcome."""
    results = store.load()
    for r in results:
        if r.get("id") == scan_id:
            r["action"]         = body.get("action", "auto-file")
            r["reviewNote"]     = body.get("note", "")
            r["reviewResolved"] = True
            break
    store._save(results)
    return {"status": "resolved", "id": scan_id}


@app.post("/api/retention/{scan_id}/dispose")
async def dispose_result(scan_id: str):
    """Mark a file as disposed — records the disposal date."""
    store.update_retention(scan_id, "disposed")
    return {"status": "disposed", "id": scan_id}


# ── Static frontend (production only) ────────────────────────────────────────
# In Docker/Render the React build lives at ../frontend/dist.
# Vite dev server handles this in local development.

_dist = Path(__file__).parent.parent / "frontend" / "dist"

if _dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/")
    async def _root():
        return FileResponse(str(_dist / "index.html"))

    @app.get("/{full_path:path}")
    async def _spa(full_path: str):
        # Serve the file if it exists; otherwise fall back to index.html for SPA routing
        target = _dist / full_path
        if target.exists() and target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(_dist / "index.html"))

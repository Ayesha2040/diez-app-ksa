"""
Persistent scan result store — JSON file replaces the in-memory list.
Survives backend restarts. Thread-safe for single-worker use (demo context).
"""
import json
from pathlib import Path
from datetime import date

STORE_PATH = Path(__file__).parent / "data" / "scan_store.json"


def load() -> list:
    if not STORE_PATH.exists():
        return []
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def append(result: dict):
    results = load()
    scan_id = result.get("id", "")
    name    = result.get("name", "")
    # Replace any entry with the same ID or same filename — prevents duplicate rows
    # when the same file is re-scanned (even if the content hash changed)
    results = [r for r in results if r.get("id") != scan_id and r.get("name") != name]
    results.append(result)
    _save(results)


def clear():
    _save([])


def update_retention(scan_id: str, status: str):
    results = load()
    for r in results:
        if r.get("id") == scan_id and "retention" in r:
            r["retention"]["status"] = status
            if status == "disposed":
                r["retention"]["disposedAt"] = date.today().isoformat()
            break
    _save(results)


def _save(results: list):
    STORE_PATH.parent.mkdir(exist_ok=True)
    STORE_PATH.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

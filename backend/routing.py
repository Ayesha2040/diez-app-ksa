"""
Routing gate — deterministic escalation decision.
Decides whether a file needs the investigator agent based on residual uncertainty,
NOT on file format or size. Strong/resolved files skip straight to the policy engine.

Per spec: build the investigator agent only after step 1-4 error analysis shows
a material fraction of genuinely unresolvable files. This gate is ready to route
to the agent when it exists; for now it flags files for human review instead.
"""
from engine import _STRENGTH


def should_escalate(hits: list, coverage: float, signals: list, filename: str) -> bool:
    """
    Return True if the file has residual uncertainty that cheap detectors cannot resolve.
    Escalation criteria (any one triggers):
      1. Coverage is low — large unexamined surface
      2. Signal strength is marginal — pattern/heuristic only, no checksum or column+pattern
      3. Signals conflict — filename implies open, body implies sensitive
      4. File sits near a tier boundary — exactly one medium signal, no critical/high
    """
    # 1. Low coverage
    if coverage < 0.4:
        return True

    # 2. Weak signal strength only (no checksum or column+pattern confirmation)
    if hits:
        best_strength = max(_STRENGTH.get(h.get("match_type", "heuristic"), 0.35) for h in hits)
        if best_strength <= 0.55:
            return True

    # 3. Conflict — filename suggests public but signals are sensitive
    fn = filename.lower()
    public_hints = any(k in fn for k in ("public", "open", "registry", "template", "sample"))
    has_sensitive = any(h.get("severity") in ("critical", "high") for h in hits)
    if public_hints and has_sensitive:
        return True

    # 4. Near tier boundary — single marginal signal
    detected = [s for s in signals if s.get("detected") and s.get("sev") not in ("info", None)]
    if len(detected) == 1 and detected[0].get("sev") == "medium":
        return True

    return False


def escalation_note(hits: list, coverage: float, signals: list, filename: str) -> str:
    """Return a human-readable reason for escalation (for the review queue)."""
    reasons = []
    if coverage < 0.4:
        reasons.append(f"Low coverage ({round(coverage * 100)}% of content examined)")
    if hits:
        best = max(_STRENGTH.get(h.get("match_type", "heuristic"), 0.35) for h in hits)
        if best <= 0.55:
            reasons.append("Signal strength marginal (pattern/heuristic only, no checksum validation)")
    fn = filename.lower()
    if any(k in fn for k in ("public", "open", "registry")) and any(h.get("severity") in ("critical", "high") for h in hits):
        reasons.append("Filename/content conflict")
    return "; ".join(reasons) if reasons else "Near tier boundary"

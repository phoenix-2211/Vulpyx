"""
VULPYX – Confidence Scoring Engine
Parses AI analysis text and renders a visual confidence bar per finding.
"""
import re
from core.banner import (
    GRN, YEL, RED, CYN, MGN, WHT, DIM, R, BLD, _tw
)

# ── Score mappings ─────────────────────────────────────────────────────────────
_TEXT_TO_SCORE = {
    "critical":    1.0,
    "high":        0.85,
    "confirmed":   0.85,
    "medium":      0.6,
    "moderate":    0.6,
    "low":         0.3,
    "minimal":     0.2,
    "insufficient":0.1,
    "none":        0.0,
    "no evidence": 0.0,
}

_SCORE_LABELS = [
    (0.85, RED,   "CONFIRMED  "),
    (0.65, f"\033[1;31m", "HIGH       "),
    (0.45, YEL,   "MEDIUM     "),
    (0.20, GRN,   "LOW        "),
    (0.00, DIM,   "INSUFFICIENT"),
]


def _score_to_color_label(score: float) -> tuple[str, str]:
    for threshold, color, label in _SCORE_LABELS:
        if score >= threshold:
            return color, label
    return DIM, "INSUFFICIENT"


def _render_bar(score: float, width: int = 30) -> str:
    filled = int(score * width)
    empty  = width - filled
    col, _ = _score_to_color_label(score)
    return f"{col}{'█' * filled}{DIM}{'░' * empty}{R}"


# ── Parse confidence from AI text ─────────────────────────────────────────────
def extract_confidence_score(analysis_text: str) -> float:
    """
    Extract a 0.0–1.0 confidence score from LLM analysis text.
    Looks for keywords in the CONFIDENCE section or vulnerability lines.
    """
    text  = analysis_text.lower()

    # Direct confidence section
    match = re.search(r"confidence[:\s]+([\w\s]+)", text)
    if match:
        phrase = match.group(1).strip()
        for key, score in _TEXT_TO_SCORE.items():
            if key in phrase:
                return score

    # Vulnerability confirmed line
    if "vulnerability detected" in text:
        if re.search(r"vulnerability detected[:\s]+yes", text):
            # Check confidence after
            for key, score in _TEXT_TO_SCORE.items():
                if key in text[text.find("vulnerability"):text.find("vulnerability")+200]:
                    return score
            return 0.75  # yes but no explicit confidence

    # Fallback keyword scan
    for key, score in sorted(_TEXT_TO_SCORE.items(), key=lambda x: -x[1]):
        if key in text:
            return score

    return 0.1  # default if nothing found


# ── Extract per-finding scores ────────────────────────────────────────────────
def extract_findings(analysis_text: str) -> list[dict]:
    """
    Parse the structured FINDINGS block and return list of:
      { finding, confidence_score }
    """
    findings = []
    lines    = analysis_text.splitlines()

    in_findings = False
    for line in lines:
        stripped = line.strip()

        if re.match(r"findings?[:\s]*$", stripped.lower()):
            in_findings = True
            continue

        if in_findings:
            # Stop at next section
            if re.match(r"(open ports|vulnerability|confidence|recommended|decision)[:\s]",
                        stripped.lower()):
                in_findings = False
                continue

            if stripped.startswith("•") or stripped.startswith("-"):
                text = stripped.lstrip("•- ").strip()
                if text:
                    findings.append({
                        "finding": text,
                        "score":   _score_finding(text),
                    })

    return findings


def _score_finding(text: str) -> float:
    """Heuristic score for a single finding line."""
    t = text.lower()
    if any(k in t for k in ["critical", "rce", "remote code", "sql injection confirmed",
                              "authentication bypass"]):
        return 0.95
    if any(k in t for k in ["high", "exposed", "vulnerable", "outdated", "default password"]):
        return 0.80
    if any(k in t for k in ["medium", "misconfigured", "open", "enabled", "disclosed"]):
        return 0.55
    if any(k in t for k in ["low", "information", "banner", "version"]):
        return 0.30
    return 0.20


# ── Public: render confidence display ─────────────────────────────────────────
def print_confidence_display(analysis_text: str, step: int):
    tw      = _tw()
    overall = extract_confidence_score(analysis_text)
    col, label = _score_to_color_label(overall)

    print(f"\n{CYN}{'─' * tw}{R}")
    print(f"  {YEL}CONFIDENCE ASSESSMENT — Step {step}{R}\n")

    # Overall score bar
    bar = _render_bar(overall)
    pct = int(overall * 100)
    print(f"  {'Overall':<18}  {bar}  {col}{label}{R}  {WHT}{pct}%{R}\n")

    # Per-finding bars
    findings = extract_findings(analysis_text)
    if findings:
        print(f"  {DIM}Per-Finding Breakdown:{R}")
        for f in findings[:6]:   # cap at 6 for readability
            fbar     = _render_bar(f["score"], width=20)
            fcol, _  = _score_to_color_label(f["score"])
            fpct     = int(f["score"] * 100)
            short    = f["finding"][:55] + "…" if len(f["finding"]) > 55 else f["finding"]
            print(f"  {fbar}  {fcol}{fpct:>3}%{R}  {DIM}{short}{R}")

    print(f"{CYN}{'─' * tw}{R}\n")


# ── Format for LLM context ────────────────────────────────────────────────────
def confidence_summary_for_llm(analysis_text: str) -> str:
    score = extract_confidence_score(analysis_text)
    _, label = _score_to_color_label(score)
    return f"CONFIDENCE SCORE: {int(score*100)}% ({label.strip()})"

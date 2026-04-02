"""
VULPYX – Session Manager
Save full session state to JSON so engagements can be resumed.
"""
import os
import json
import glob
import datetime

from core.banner import (
    RED, print_info, print_ok, print_warn,
    GRN, YEL, CYN, MGN, WHT, DIM, R, BLD, _tw, _hr
)
from core.utils import ensure_dir, save_file

SESSION_FILE = "session.json"

# ── Schema ─────────────────────────────────────────────────────────────────────
def _empty_session(project: str, target: str, base: str) -> dict:
    return {
        "version":       "2.0",
        "project":       project,
        "target":        target,
        "base":          base,
        "created":       datetime.datetime.now().isoformat(),
        "last_updated":  datetime.datetime.now().isoformat(),
        "target_type":   None,
        "strategy_hint": "",       # populated by phase_target_detection
        "recon_done":    False,
        "recon_results": {},        # { tool: output_text }
        "recon_analysis":"",
        "cve_results":   {},        # { service: [cve,...] }
        "context":       "",
        "current_step":  1,
        "steps": [],                # list of { method, output, analysis, decision }
        "completed":     False,
        "vuln_found":    False,
    }


# ── Save ───────────────────────────────────────────────────────────────────────
def save_session(base: str, state: dict):
    state["last_updated"] = datetime.datetime.now().isoformat()
    path = os.path.join(base, SESSION_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ── Load ───────────────────────────────────────────────────────────────────────
def load_session(base: str) -> dict | None:
    path = os.path.join(base, SESSION_FILE)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── List all saved sessions ────────────────────────────────────────────────────
def list_sessions(projects_dir: str) -> list[dict]:
    """Return list of session dicts from all project folders."""
    sessions = []
    pattern  = os.path.join(projects_dir, "*", SESSION_FILE)
    for path in sorted(glob.glob(pattern), reverse=True):
        try:
            with open(path) as f:
                s = json.load(f)
            s["_path"] = os.path.dirname(path)
            sessions.append(s)
        except json.JSONDecodeError:
            print_warn(f"Corrupt session file skipped: {path}")
            continue
        except Exception:
            continue
    return sessions


# ── Pretty-print session list ─────────────────────────────────────────────────
def print_session_list(sessions: list[dict]) -> list[dict]:
    tw = _tw()
    print(f"\n{CYN}{'═' * tw}{R}")
    print(f"  {YEL}SAVED SESSIONS{R}")
    print(f"{CYN}{'─' * tw}{R}\n")

    if not sessions:
        print_warn("No saved sessions found.\n")
        return sessions

    for i, s in enumerate(sessions, 1):
        status = f"{GRN}COMPLETE{R}" if s.get("completed") else f"{YEL}IN PROGRESS{R}"
        vuln   = f"  {RED}[VULN CONFIRMED]{R}" if s.get("vuln_found") else ""
        ttype  = s.get("target_type") or "Unknown"
        step   = s.get("current_step", 1)
        updated = s.get("last_updated", "")[:16].replace("T", " ")

        print(f"  {CYN}[{i}]{R}  {BLD}{s['project']:<25}{R}  "
              f"{WHT}{s['target']:<20}{R}  "
              f"Type: {MGN}{ttype:<8}{R}  "
              f"Step: {step}  "
              f"{status}{vuln}")
        print(f"       {DIM}Last updated: {updated}   Path: {s['_path']}{R}")
        print()

    print(f"{CYN}{'═' * tw}{R}\n")
    return sessions


# ── Ask user to resume or start new ───────────────────────────────────────────
def resume_prompt(projects_dir: str) -> dict | None:
    """
    Show saved sessions and ask if user wants to resume one.
    Returns loaded session dict if resuming, None if starting fresh.
    """
    sessions = list_sessions(projects_dir)
    if not sessions:
        return None

    # Only show if there are incomplete sessions
    incomplete = [s for s in sessions if not s.get("completed")]
    if not incomplete:
        return None

    print_session_list(incomplete)
    print(f"  {CYN}❯{R}  Resume a session? Enter number (or press ENTER to start new): ",
          end="", flush=True)
    choice = input().strip()

    if not choice:
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(incomplete):
            chosen  = incomplete[idx]
            session = load_session(chosen["_path"])
            # Validate base path still exists
            if not os.path.exists(session.get("base", "")):
                print_warn(f"Session folder missing: {session.get('base')}")
                print_warn("Cannot resume — folder may have been moved or deleted.")
                return None
            print_ok(f"Resuming: {WHT}{session['project']}{R} → {session['target']}") # type: ignore
            return session
    except (ValueError, IndexError):
        pass

    print_warn("Invalid choice. Starting new session.")
    return None


# ── New session factory ────────────────────────────────────────────────────────
def new_session(project: str, target: str, base: str) -> dict:
    state = _empty_session(project, target, base)
    save_session(base, state)
    return state

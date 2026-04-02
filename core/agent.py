"""
VULPYX – Agent
KEY DESIGN:
- Every LLM call is a FRESH session (no accumulated context passed to Ollama)
- Methodology Step 1: uses ONLY recon summary + prompt (lightweight)
- Methodology Step 2+: uses ONLY the last step findings (not full history)
- Keeps 1.5B model fast and prevents context overflow/timeouts
"""
import os
from core.ollama_client import query_ollama
from core.utils         import load_prompt
from core.banner        import thinking_dots

_HERE        = os.path.dirname(os.path.abspath(__file__))
_PROMPTS_DIR = os.path.join(_HERE, "..", "prompts")

def _load(name: str) -> str:
    return load_prompt(os.path.join(_PROMPTS_DIR, f"{name}.txt"))

def _trim(text: str, max_chars: int = 2000) -> str:
    """Keep tail (most recent) if over limit."""
    if len(text) <= max_chars:
        return text
    return "[...trimmed...]\n" + text[-max_chars:]


def analyze_recon(recon_results: dict, target: str) -> str:
    combined = f"TARGET: {target}\n\n"
    for tool, output in recon_results.items():
        combined += f"=== {tool.upper()} ===\n{output[:1500]}\n\n"
    prompt = _load("system") + "\n\n" + _load("analyze_output").replace("{context}", combined)
    thinking_dots("Analyzing recon data", 2.0)
    return query_ollama(prompt)


def generate_methodology(context: str, step: int, recon_summary: str = "") -> str:
    """
    Step 1 → Recon summary + prompt ONLY (fresh start).
    Step 2+ → Last step findings ONLY (not full history).
    """
    if step == 1:
        enriched = (
            f"Step: 1 (FIRST STEP)\n\n"
            f"RECON SUMMARY:\n{_trim(recon_summary, 2000)}\n\n"
            f"Based on the recon above, suggest the FIRST penetration testing step."
        )
    else:
        enriched = (
            f"Step: {step}\n\n"
            f"LAST STEP FINDINGS:\n{_trim(context, 1500)}\n\n"
            f"Suggest the NEXT logical step. Do NOT repeat steps already done."
        )
    prompt = _load("system") + "\n\n" + _load("generate_methodology").replace("{context}", enriched)
    thinking_dots(f"Generating Methodology {step}", 1.5)
    return query_ollama(prompt)


def analyze_step_output(method: str, user_output: str, recon_summary: str) -> str:
    combined = (
        f"SUGGESTED METHOD:\n{_trim(method, 500)}\n\n"
        f"USER OUTPUT:\n{_trim(user_output, 1500)}\n\n"
        f"RECON CONTEXT:\n{_trim(recon_summary, 500)}"
    )
    prompt = _load("system") + "\n\n" + _load("analyze_output").replace("{context}", combined)
    thinking_dots("Analyzing tool output", 1.5)
    return query_ollama(prompt)


def decide_next(analysis: str) -> str:
    prompt = _load("system") + "\n\n" + _load("decision").replace("{context}", _trim(analysis, 1500))
    thinking_dots("Running decision engine", 1.0)
    return query_ollama(prompt)


def generate_final_report(context: str) -> str:
    prompt = _load("system") + "\n\n" + _load("final_report").replace("{context}", _trim(context, 2500))
    thinking_dots("Generating final report", 2.0)
    return query_ollama(prompt)


def vuln_confirmed(decision_text: str, analysis_text: str) -> bool:
    d = decision_text.lower()
    a = analysis_text.lower()
    return (
        "stop"       in d and
        ("confirmed" in d or "vulnerability" in d) and
        "yes"        in a and "vulnerability" in a
    )

"""
VULPYX – Agent
All AI-powered functions: methodology gen, analysis, decision, report.
"""
import os
from core.ollama_client import query_ollama
from core.utils         import load_prompt, load_file
from core.banner        import thinking_dots, print_info

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROMPTS_DIR = os.path.join(_HERE, "..", "prompts")

# ── Prompt helpers ─────────────────────────────────────────────────────────────
def _load(name: str) -> str:
    return load_prompt(os.path.join(_PROMPTS_DIR, f"{name}.txt"))


# ── Public functions ───────────────────────────────────────────────────────────

def analyze_recon(recon_results: dict, target: str) -> str:
    """
    Feed all recon outputs into the LLM for initial analysis.
    Returns a combined analysis string.
    """
    combined = f"TARGET: {target}\n\n"
    for tool, output in recon_results.items():
        combined += f"=== {tool.upper()} OUTPUT ===\n{output[:3000]}\n\n"

    system  = _load("system")
    prompt  = _load("analyze_output")
    final   = system + "\n\n" + prompt.replace("{context}", combined)

    thinking_dots("Analyzing recon data", 2.0)
    return query_ollama(final)


def generate_methodology(context: str, step: int) -> str:
    """
    Ask the LLM for the next best penetration testing step.
    """
    enriched = (
        f"Current step: {step}\n"
        f"Previous findings and context:\n{context}"
    )
    system = _load("system")
    prompt = _load("generate_methodology")
    final  = system + "\n\n" + prompt.replace("{context}", enriched)

    thinking_dots(f"Generating Methodology {step}", 1.5)
    return query_ollama(final)


def analyze_step_output(method: str, user_output: str, recon_summary: str) -> str:
    """
    Analyze what the user found after running the suggested command.
    """
    combined = (
        f"SUGGESTED METHOD:\n{method}\n\n"
        f"USER OUTPUT:\n{user_output}\n\n"
        f"RECON CONTEXT (summary):\n{recon_summary[:1500]}"
    )
    system = _load("system")
    prompt = _load("analyze_output")
    final  = system + "\n\n" + prompt.replace("{context}", combined)

    thinking_dots("Analyzing tool output", 1.5)
    return query_ollama(final)


def decide_next(analysis: str) -> str:
    """
    Ask the LLM: STOP (vuln confirmed) or CONTINUE?
    """
    system = _load("system")
    prompt = _load("decision")
    final  = system + "\n\n" + prompt.replace("{context}", analysis)

    thinking_dots("Running decision engine", 1.0)
    return query_ollama(final)


def generate_final_report(context: str) -> str:
    """
    Generate the professional markdown vulnerability report.
    """
    system = _load("system")
    prompt = _load("final_report")
    final  = system + "\n\n" + prompt.replace("{context}", context)

    thinking_dots("Generating final report", 2.0)
    return query_ollama(final)


def vuln_confirmed(decision_text: str, analysis_text: str) -> bool:
    """
    Heuristic check: did the AI confirm a vulnerability?
    Requires both decision AND analysis to agree – avoids false positives.
    """
    d = decision_text.lower()
    a = analysis_text.lower()

    stop_signal   = "stop"      in d
    vuln_in_dec   = "confirmed" in d or "vulnerability" in d
    vuln_in_ana   = "yes"       in a and "vulnerability" in a

    return stop_signal and vuln_in_dec and vuln_in_ana

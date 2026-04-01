"""
VULPYX – Ollama Client
Handles all LLM communication with streaming output and error handling.
Model is resolved dynamically from config._runtime so model picker takes effect.
"""
import json
import sys
import requests
from core.config  import OLLAMA_URL, get_model
from core.banner  import MGN, CYN, GRN, YEL, RED, DIM, R

# ── Anti-hallucination system prefix ──────────────────────────────────────────
_STRICT_PREFIX = (
    "You are a precise penetration testing assistant. "
    "STRICT RULES: "
    "1) NEVER invent vulnerability names, CVEs, or tool outputs not in the input. "
    "2) If evidence is insufficient, explicitly state 'Insufficient evidence'. "
    "3) Only reference tools available in Kali Linux. "
    "4) Ground every claim in the provided data. "
    "5) Be concise — no filler text.\n\n"
)


def _is_ollama_running() -> bool:
    try:
        r = requests.get("http://localhost:11434/", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def query_ollama(prompt: str, stream: bool = True) -> str:
    if not _is_ollama_running():
        return (
            f"{RED}[ERROR]{R} Ollama is not running!\n"
            "  Run:  ollama serve  (in a separate terminal)\n"
            "  Then: ollama pull qwen2.5-coder:1.5b"
        )

    model        = get_model()
    full_prompt  = _STRICT_PREFIX + prompt

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model":  model,
                "prompt": full_prompt,
                "stream": stream,
                "options": {
                    "temperature": 0.2,
                    "top_p":       0.9,
                    "num_predict": 1024,
                },
            },
            stream=stream,
            timeout=180,
        )

        if stream:
            collected = []
            sys.stdout.write(f"\n  {MGN}┌{'─'*60}┐{R}\n  {MGN}│{R} ")
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                try:
                    chunk = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                token = chunk.get("response", "")
                collected.append(token)
                for ch in token:
                    if ch == "\n":
                        sys.stdout.write(f"\n  {MGN}│{R} ")
                    else:
                        sys.stdout.write(ch)
                sys.stdout.flush()
                if chunk.get("done"):
                    break
            sys.stdout.write(f"\n  {MGN}└{'─'*60}┘{R}\n")
            sys.stdout.flush()
            return "".join(collected)
        else:
            return response.json().get("response", "No response from model.")

    except requests.exceptions.Timeout:
        return f"{RED}[ERROR]{R} Ollama request timed out. Try a lighter model."
    except requests.exceptions.ConnectionError:
        return f"{RED}[ERROR]{R} Cannot connect to Ollama at {OLLAMA_URL}"
    except Exception as e:
        return f"{RED}[ERROR]{R} Unexpected error: {e}"

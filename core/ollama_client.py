"""
VULPYX – Ollama Client
Handles all LLM communication with streaming output and error handling.
- Fresh context every call (no accumulated history bloating the model)
- Per-call timeout high enough for slow hardware
- Prompt trimmed to fit model context window
"""
import json
import sys
import requests
from core.config import OLLAMA_URL, get_model
from core.banner import MGN, CYN, GRN, YEL, RED, DIM, R

# ── Anti-hallucination prefix (kept SHORT to save context window) 
_STRICT_PREFIX = (
    "You are a precise penetration testing assistant on Kali Linux.\n"
    "RULES: Never invent CVEs/tool outputs. Only report what is in the input.\n"
    "If evidence is missing say: 'Insufficient evidence'. Be concise.\n\n"
)

# Max chars sent to model — keeps prompt small for 1.5B model
_MAX_CONTEXT_CHARS = 3000

# Timeout for Ollama — high enough for slow hardware
_OLLAMA_TIMEOUT = 600   # 10 minutes


def _is_ollama_running() -> bool:
    try:
        r = requests.get("http://localhost:11434/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _trim_prompt(prompt: str) -> str:
    """
    Trim prompt to _MAX_CONTEXT_CHARS.
    Keeps the LAST portion (most recent context = most relevant for 1.5B model).
    """
    full = _STRICT_PREFIX + prompt
    if len(full) <= _MAX_CONTEXT_CHARS:
        return full
    tail = prompt[-(  _MAX_CONTEXT_CHARS - len(_STRICT_PREFIX)):]
    return _STRICT_PREFIX + "[...trimmed for model capacity...]\n\n" + tail


def query_ollama(prompt: str, stream: bool = True) -> str:
    """
    Send prompt to Ollama. Completely stateless —
    fresh session every call, no accumulated history.
    """
    if not _is_ollama_running():
        return (
            f"{RED}[ERROR]{R} Ollama is not running!\n"
            "  Fix:  ollama serve  (run in a separate terminal)\n"
            "  Then retry."
        )

    model        = get_model()
    final_prompt = _trim_prompt(prompt)

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model":   model,
                "prompt":  final_prompt,
                "stream":  stream,
                "context": [],          # FRESH SESSION — no history carried over
                "options": {
                    "temperature":  0.2,
                    "top_p":        0.9,
                    "num_predict":  512,   # shorter = faster on 1.5B
                    "num_ctx":      2048,  # context window size for 1.5B
                },
            },
            stream=stream,
            timeout=_OLLAMA_TIMEOUT,
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
        return (
            f"{RED}[ERROR]{R} Ollama timed out after {_OLLAMA_TIMEOUT}s.\n"
            f"  Try: ollama pull qwen2.5-coder:1.5b  (use lighter model)\n"
        )
    except requests.exceptions.ConnectionError:
        return f"{RED}[ERROR]{R} Cannot connect to Ollama at {OLLAMA_URL}"
    except Exception as e:
        return f"{RED}[ERROR]{R} Unexpected error: {e}"

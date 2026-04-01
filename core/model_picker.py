"""
VULPYX – Model Picker
Lists locally installed Ollama models and lets the user pick one at startup.
Recommends models by capability tier for pentesting tasks.
"""
import requests
from core.banner import (
    print_info, print_ok, print_warn, print_err,
    GRN, YEL, RED, CYN, MGN, WHT, DIM, R, BLD, _tw
)

OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

# ── Model recommendations ──────────────────────────────────────────────────────
# key = substring that appears in model name → (tier, description)
_MODEL_TIERS = {
    "llama3.1:70b":        ("S", "Best reasoning, needs 48 GB+ RAM"),
    "llama3.1:8b":         ("A", "Excellent balance, needs 8 GB RAM"),
    "llama3":              ("A", "Strong general reasoning"),
    "mistral":             ("A", "Fast, great at structured output"),
    "mixtral":             ("S", "Best for complex multi-step tasks"),
    "qwen2.5-coder:7b":   ("A", "Best code-focused model for pentesting"),
    "qwen2.5-coder:1.5b": ("B", "Lightweight, works on 4 GB RAM"),
    "qwen2.5":             ("A", "Strong reasoning, code-aware"),
    "codellama":           ("B", "Code-focused, decent for commands"),
    "phi3":                ("B", "Microsoft Phi, efficient on low RAM"),
    "gemma2":              ("A", "Google Gemma 2, strong reasoning"),
    "deepseek-coder":      ("A", "Strong at code and command generation"),
}

_TIER_COLOR = {"S": RED, "A": YEL, "B": GRN, "C": DIM}
_TIER_LABEL = {"S": "ELITE", "A": "GREAT", "B": "GOOD", "C": "BASIC"}


def _get_tier(model_name: str) -> tuple[str, str]:
    name = model_name.lower()
    for key, (tier, desc) in _MODEL_TIERS.items():
        if key.lower() in name:
            return tier, desc
    return "C", "Unknown model — may have limited pentesting ability"


# ── Fetch available models from Ollama ────────────────────────────────────────
def get_available_models() -> list[str]:
    try:
        resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
        if resp.status_code == 200:
            data   = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return sorted(models)
    except Exception:
        pass
    return []


# ── Print model picker UI ─────────────────────────────────────────────────────
def print_model_picker(models: list[str]):
    tw = _tw()
    print(f"\n{CYN}{'═' * tw}{R}")
    print(f"  {YEL}AVAILABLE AI MODELS{R}")
    print(f"{CYN}{'─' * tw}{R}\n")

    if not models:
        print_warn("No models found. Make sure Ollama is running and a model is pulled.\n")
        print_info("Pull a model:  ollama pull qwen2.5-coder:1.5b")
        print_info("Pull a model:  ollama pull llama3.1:8b\n")
        return

    for i, model in enumerate(models, 1):
        tier, desc = _get_tier(model)
        col        = _TIER_COLOR.get(tier, WHT)
        label      = _TIER_LABEL.get(tier, "")
        print(f"  {CYN}[{i:>2}]{R}  {BLD}{model:<35}{R}  "
              f"{col}[{label}]{R}  {DIM}{desc}{R}")

    print(f"\n  {DIM}Recommended for best results: llama3.1:8b or qwen2.5-coder:7b{R}")
    print(f"{CYN}{'═' * tw}{R}\n")


# ── Public: interactive model selection ───────────────────────────────────────
def pick_model(default: str = "qwen2.5-coder:1.5b") -> str:
    """
    Show available models, let user pick one.
    Returns the model name string to use.
    """
    models = get_available_models()

    if not models:
        print_warn(f"Could not fetch model list. Using default: {default}")
        return default

    print_model_picker(models)

    print(f"  {CYN}❯{R}  Select model number (or press ENTER for default [{WHT}{default}{R}]): ",
          end="", flush=True)
    choice = input().strip()

    if not choice:
        # Use default if installed, else first available
        if default in models:
            print_ok(f"Using: {WHT}{default}{R}")
            return default
        else:
            selected = models[0]
            print_ok(f"Default not found. Using: {WHT}{selected}{R}")
            return selected

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            selected = models[idx]
            print_ok(f"Selected: {WHT}{selected}{R}")
            return selected
    except ValueError:
        # User typed a model name directly
        if choice in models:
            print_ok(f"Using: {WHT}{choice}{R}")
            return choice

    print_warn(f"Invalid choice. Using default: {default}")
    return default

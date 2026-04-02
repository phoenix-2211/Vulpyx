"""
VULPYX – Recon Engine
Runs all recon tools (when present), shows progress bars, saves outputs.
"""
import os
import sys
import time
import subprocess
import threading

from core.config  import RECON_TOOLS
from core.utils   import ensure_dir, save_file, cmd_available
from core.banner  import (
    GRN, YEL, CYN, RED, MGN, WHT, DIM, R, BLD,
    print_info, print_ok, print_warn, print_err, _tw
)

# ── Per-tool timeouts (seconds) ────────────────────────────────────────────────
_TOOL_TIMEOUTS = {
    "nmap":        300,   # 5 min
    "nikto":       600,   # 10 min
    "gobuster":    300,   # 5 min
    "ffuf":        300,   # 5 min
    "amass":       900,   # 15 min — slow by nature
    "whatweb":     120,   # 2 min
    "theharvester":600,   # 10 min
    "nuclei":      900,   # 15 min — lots of templates
    "sqlmap":      600,   # 10 min
    "wpscan":      600,   # 10 min
    "enum4linux":  300,   # 5 min
    "subfinder":   300,   # 5 min
}
_DEFAULT_TIMEOUT = 300   # fallback for unlisted tools


# ── Progress bar rendered in a background thread ───────────────────────────────
class _ProgressThread(threading.Thread):
    def __init__(self, label: str, timeout: int, width: int = 40):
        super().__init__(daemon=True)
        self.label   = label
        self.width   = width
        self.timeout = timeout
        self._stop   = threading.Event()
        self._done   = False
        self._start  = time.time()

    def run(self):
        chars = "▓"
        empty = "░"
        while not self._stop.is_set():
            elapsed  = time.time() - self._start
            ratio    = min(elapsed / self.timeout, 0.99)   # never hits 100% while running
            filled   = int(ratio * self.width)
            bar      = chars * filled + empty * (self.width - filled)
            pct      = int(ratio * 100)
            mins, secs = divmod(int(elapsed), 60)
            timer    = f"{mins:02d}:{secs:02d}"
            sys.stdout.write(
                f"\r  {CYN}{self.label:<18}{R}  [{GRN}{bar}{R}]  {WHT}{pct:>3}%{R}  {DIM}{timer}{R}"
            )
            sys.stdout.flush()
            time.sleep(0.5)

        # Final state
        elapsed = time.time() - self._start
        mins, secs = divmod(int(elapsed), 60)
        timer  = f"{mins:02d}:{secs:02d}"
        bar    = chars * self.width
        state  = f"{GRN}DONE ✔{R}" if self._done else f"{RED}FAIL ✘{R}"
        sys.stdout.write(
            f"\r  {CYN}{self.label:<18}{R}  [{GRN}{bar}{R}]  {state}  {DIM}{timer}{R}          \n"
        )
        sys.stdout.flush()

    def finish(self, success: bool = True):
        self._done = success
        self._stop.set()


# ── Run a single recon tool ────────────────────────────────────────────────────
def _run_tool(name: str, tool_cfg: dict, target: str, outfile: str) -> str:
    """
    Execute one recon tool, capture output, return content string.
    """
    cmd     = tool_cfg["cmd"].format(target=target, outfile=outfile)
    timeout = _TOOL_TIMEOUTS.get(name.lower(), _DEFAULT_TIMEOUT)

    bar = _ProgressThread(name.upper(), timeout=timeout)
    bar.start()

    success = False
    try:
        result = subprocess.run(
            cmd, shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        output  = result.stdout or ""
        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        output  = f"[TIMEOUT] {name} timed out after {timeout}s — partial results may be saved."
        success = False
    except Exception as e:
        output  = f"[ERROR] {name}: {e}"
        success = False
    finally:
        bar.finish(success)

    save_file(outfile, output)
    return output


# ── Public: run all available recon tools ─────────────────────────────────────
def run_recon_phase(target: str, recon_dir: str) -> dict[str, str]:
    """
    Run every recon tool that is installed.
    Returns dict {tool_name: output_text}.
    """
    ensure_dir(recon_dir)

    # Some tools install under a different binary name than config key
    _BINARY_ALIASES = {"theharvester": "theHarvester"}

    available = {
        name: cfg
        for name, cfg in RECON_TOOLS.items()
        if cmd_available(_BINARY_ALIASES.get(name, name))
           or cmd_available(name.lower())
    }

    if not available:
        print_warn("No recon tools found. Running nmap only (apt fallback).")
        available = {"nmap": RECON_TOOLS["nmap"]}

    print()
    results = {}
    for name, cfg in available.items():
        outfile = os.path.join(recon_dir, f"{name}.txt")
        output  = _run_tool(name, cfg, target, outfile)
        results[name] = output

    return results


# ── Public: pretty-print recon summary ────────────────────────────────────────
def print_recon_summary(results: dict[str, str]):
    tw = _tw()
    print(f"\n{CYN}{'═' * tw}{R}")
    print(f"  {YEL}RECON SUMMARY{R}")
    print(f"{CYN}{'─' * tw}{R}")
    for name, output in results.items():
        lines      = [l for l in output.strip().splitlines() if l.strip()]
        lcount     = len(lines)
        max_preview = tw - 40   # dynamic width based on terminal
        if output.startswith("[TIMEOUT]") or output.startswith("[ERROR]"):
            status  = f"{RED}✘{R}"
            preview = f"{RED}{output[:max_preview]}{R}"
        else:
            status  = f"{GRN}✔{R}"
            preview = lines[0][:max_preview] if lines else "(empty output)"
            preview = f"{DIM}{preview}{R}"
        print(f"  {status}  {BLD}{name.upper():<14}{R}  {WHT}{lcount:>4} lines{R}  │  {preview}")
    print(f"{CYN}{'═' * tw}{R}\n")

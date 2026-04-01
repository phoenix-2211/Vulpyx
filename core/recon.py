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


# ── Progress bar rendered in a background thread ───────────────────────────────
class _ProgressThread(threading.Thread):
    def __init__(self, label: str, width: int = 40):
        super().__init__(daemon=True)
        self.label   = label
        self.width   = width
        self._stop   = threading.Event()
        self._done   = False

    def run(self):
        filled = 0
        chars  = "▓"
        empty  = "░"
        while not self._stop.is_set():
            ratio    = min(filled / self.width, 1.0)
            bar      = chars * filled + empty * (self.width - filled)
            pct      = int(ratio * 100)
            sys.stdout.write(
                f"\r  {CYN}{self.label:<18}{R}  [{GRN}{bar}{R}]  {WHT}{pct:>3}%{R}"
            )
            sys.stdout.flush()
            time.sleep(0.15)
            if filled < self.width - 1:
                filled += 1
        # Final state
        bar = chars * self.width
        state = f"{GRN}DONE ✔{R}" if self._done else f"{RED}FAIL ✘{R}"
        sys.stdout.write(
            f"\r  {CYN}{self.label:<18}{R}  [{GRN}{bar}{R}]  {state}          \n"
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
    cmd = tool_cfg["cmd"].format(target=target, outfile=outfile)

    bar = _ProgressThread(name.upper())
    bar.start()

    try:
        result = subprocess.run(
            cmd, shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
        )
        output = result.stdout or ""
        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        output  = f"[TIMEOUT] {name} timed out after 180 s"
        success = False
    except Exception as e:
        output  = f"[ERROR] {name}: {e}"
        success = False

    bar.finish(success)

    # Also save to file
    save_file(outfile, output)
    return output


# ── Public: run all available recon tools ─────────────────────────────────────
def run_recon_phase(target: str, recon_dir: str) -> dict[str, str]:
    """
    Run every recon tool that is installed.
    Returns dict {tool_name: output_text}.
    """
    ensure_dir(recon_dir)

    available = {
        name: cfg
        for name, cfg in RECON_TOOLS.items()
        if cmd_available(name) or cmd_available(name.lower())
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
        lines   = [l for l in output.strip().splitlines() if l.strip()]
        preview = lines[0][:80] if lines else "(empty output)"
        lcount  = len(lines)
        print(f"  {GRN}{'▸'}{R}  {BLD}{name.upper():<14}{R}  {lcount:>4} lines  │  {DIM}{preview}{R}")
    print(f"{CYN}{'═' * tw}{R}\n")

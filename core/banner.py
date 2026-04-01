"""
VULPYX – Banner & UI helpers
"""
import shutil
import sys
import time

# ── ANSI colour codes ──────────────────────────────────────────────────────────
R   = "\033[0m"          # reset
RED = "\033[1;31m"
YEL = "\033[1;33m"
CYN = "\033[1;36m"
GRN = "\033[1;32m"
MGN = "\033[1;35m"
BLU = "\033[1;34m"
WHT = "\033[1;37m"
DIM = "\033[2m"
BLD = "\033[1m"

# ── Terminal width helper ──────────────────────────────────────────────────────
def _tw():
    return shutil.get_terminal_size((100, 30)).columns

def _center(text, width=None):
    w = width or _tw()
    return text.center(w)

def _hr(char="═", width=None, color=CYN):
    w = width or _tw()
    return f"{color}{char * w}{R}"


# ── VULPYX Logo (pyfiglet-free, pure ASCII art) ────────────────────────────────
LOGO_LINES = [
    r" __   ___   _ _     _______  __",
    r" \ \ / / | | | |   |  __ \ \/ /",
    r"  \ V /| | | | |   | |__) \  / ",
    r"   > < | | | | |   |  ___//  \ ",
    r"  / . \| |_| | |___| |   / /\ \\",
    r" /_/ \_\\___/|_____|_|  /_/  \_\\",
]

TAGLINE = "[ AI-Powered Penetration Testing Assistant ]"
VERSION = "v2.0  |  Qwen2.5-Coder  |  Kali Linux"

def show_banner():
    """Print the full pinned banner (top ~25 % of screen)."""
    tw = _tw()

    print()
    print(_hr("═", tw, CYN))
    print()

    # Logo – centred, red gradient fade to yellow
    colours = [RED, RED, YEL, YEL, MGN, MGN]
    for line, col in zip(LOGO_LINES, colours):
        print(f"{col}{line.center(tw)}{R}")

    print()
    print(f"{CYN}{TAGLINE.center(tw)}{R}")
    print(f"{DIM}{VERSION.center(tw)}{R}")
    print()
    print(_hr("─", tw, DIM))
    print()


def show_section(title: str):
    """Print a styled section heading."""
    tw = _tw()
    bar  = f"{CYN}{'═' * tw}{R}"
    head = f"  {YEL}❯❯  {WHT}{title.upper()}{R}"
    print(f"\n{bar}")
    print(head)
    print(f"{bar}\n")


def print_info(msg: str):
    print(f"  {CYN}[*]{R}  {msg}")

def print_ok(msg: str):
    print(f"  {GRN}[✔]{R}  {msg}")

def print_warn(msg: str):
    print(f"  {YEL}[!]{R}  {msg}")

def print_err(msg: str):
    print(f"  {RED}[✘]{R}  {msg}")

def print_step(label: str, msg: str):
    print(f"  {MGN}[»]{R}  {BLD}{label}{R}  {msg}")


def progress_bar(label: str, duration: float = 2.0, width: int = 50):
    """
    Animate a progress bar for visual effect.
    `duration` is total seconds for the animation.
    """
    import time
    step_delay = duration / width
    sys.stdout.write(f"\n  {CYN}{label:<20}{R}  [")
    sys.stdout.flush()
    for i in range(width):
        time.sleep(step_delay)
        sys.stdout.write(f"{GRN}#{R}")
        sys.stdout.flush()
    sys.stdout.write(f"]  {GRN}DONE{R}\n\n")
    sys.stdout.flush()


def spinner(label: str, seconds: float = 1.5):
    """Tiny spinner for short waits."""
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    end = time.time() + seconds
    i   = 0
    while time.time() < end:
        sys.stdout.write(f"\r  {CYN}{frames[i % len(frames)]}{R}  {label} ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write(f"\r  {GRN}✔{R}  {label}{'  '*10}\n")
    sys.stdout.flush()


def thinking_dots(label: str = "AI is thinking", seconds: float = 1.0):
    """Animated dots while LLM responds."""
    frames = [".  ", ".. ", "..."]
    end = time.time() + seconds
    i   = 0
    while time.time() < end:
        sys.stdout.write(f"\r  {MGN}[AI]{R}  {label}{frames[i % len(frames)]}")
        sys.stdout.flush()
        time.sleep(0.35)
        i += 1
    sys.stdout.write("\n")
    sys.stdout.flush()

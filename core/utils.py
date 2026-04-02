"""
VULPYX – Utility functions
"""
import os
import sys
import subprocess

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_file(path: str, data: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def load_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as e:
        return f"[ERROR reading {path}: {e}]"


def load_prompt(path: str) -> str:
    content = load_file(path)
    if not content:
        raise FileNotFoundError(f"Prompt file missing or empty: {path}")
    return content


def cmd_available(cmd: str) -> bool:
    """Return True if `cmd` is on PATH."""
    return subprocess.run(
        ["which", cmd],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ).returncode == 0


def run_cmd(cmd: str) -> tuple[int, str]:
    """Run a shell command; return (returncode, combined output)."""
    result = subprocess.run(
        cmd, shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    return result.returncode, result.stdout


def multiline_input(prompt: str) -> str:
    """
    Collect multi-line input until the user types END (alone on a line).
    Returns the collected text.
    """
    print(prompt)
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "END":
            break
        lines.append(line)
    return "\n".join(lines)

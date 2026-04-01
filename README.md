# VULPYX — AI-Powered Penetration Testing Assistant

```
 __   ___   _ _     _______  __
 \ \ / / | | | |   |  __ \ \/ /
  \ V /| | | | |   | |__) \  /
   > < | | | | |   |  ___//  \
  / . \| |_| | |___| |   / /\ \
 /_/ \_\___/|_____|_|  /_/  \_\
```

> *"VULPYX transforms penetration testing from tool execution into intelligent decision-making."*

---

## What is VULPYX?

VULPYX is a **human-in-the-loop AI pentesting assistant** that runs entirely on your local Kali Linux machine. It:

1. **Runs all available recon tools** automatically with live progress bars
2. **Feeds every result into a local LLM** (Ollama + Qwen2.5-Coder 1.5B)
3. **Generates step-by-step methodology** based on what the data actually shows
4. **Analyzes your tool outputs** to find vulnerabilities — no hallucinations
5. **Decides** whether to continue or stop, then **generates a professional report**

---

## Features

| Feature | Description |
|---|---|
| 🤖 AI-Guided Methodology | Dynamic next-step generation, not hardcoded paths |
| 🛡️ Anti-Hallucination | Strict prompts force the LLM to cite evidence |
| 📡 Full Recon Suite | nmap, nikto, gobuster, ffuf, amass, whatweb, nuclei, sqlmap + more |
| 📊 Live Progress Bars | Visual feedback for every running tool |
| 💾 Structured Output | Every step saved: recon/, analysis/, methodology/, report/ |
| 🔒 100% Offline | Local LLM via Ollama — no data leaves your machine |
| 📝 Professional Report | Markdown report ready for client delivery |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/vulpyx.git
cd vulpyx

# 2. Run setup (installs tools, Ollama, model — ONE command)
chmod +x setup.sh
sudo ./setup.sh

# 3. In a separate terminal — keep Ollama running
ollama serve

# 4. Launch VULPYX
python3 vulpyx.py
```

---

## Workflow

```
┌─────────────────────────────────────────────────┐
│  Enter Project Name + Target (IP / Domain)      │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  PHASE 1 – Recon                                │
│  nmap ████████████████████ DONE ✔               │
│  nikto ████████████████████ DONE ✔              │
│  gobuster ████████████████████ DONE ✔           │
│  ...                                            │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  PHASE 2 – AI Recon Analysis                    │
│  (LLM analyzes all recon outputs combined)      │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  PHASE 3 – Methodology Loop                     │
│  [1] AI generates next step                     │
│  [2] You run the command in Kali terminal       │
│  [3] Paste output → AI analyzes                 │
│  [4] Decision Engine: STOP or CONTINUE          │
│  [5] Repeat until vulnerability confirmed       │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  PHASE 4 – Final Report                         │
│  Professional markdown report generated         │
└─────────────────────────────────────────────────┘
```

---

## Project Structure

```
vulpyx/
├── vulpyx.py               ← Entry point — run this
├── setup.sh                ← One-command installer
├── requirements.txt
├── core/
│   ├── config.py           ← Model, URL, tool definitions
│   ├── banner.py           ← CLI UI, colours, progress bars
│   ├── utils.py            ← File I/O helpers
│   ├── recon.py            ← Recon engine with progress bars
│   ├── agent.py            ← All LLM interaction logic
│   └── ollama_client.py    ← Ollama API client (streaming)
├── prompts/
│   ├── system.txt          ← AI personality & rules
│   ├── generate_methodology.txt
│   ├── analyze_output.txt
│   ├── decision.txt
│   └── final_report.txt
└── projects/               ← All engagement data saved here
    └── <project_timestamp>/
        ├── recon/          ← nmap.txt, nikto.txt, etc.
        ├── methodology/    ← AI-generated steps + your outputs
        ├── analysis/       ← AI interpretations
        ├── decisions/      ← STOP/CONTINUE logs
        ├── context/        ← Cumulative memory of scan
        └── report/         ← Final .md report
```

---

## Requirements

- **OS:** Kali Linux (recommended) or any Debian-based Linux
- **Python:** 3.10+
- **RAM:** 4 GB minimum (8 GB recommended)
- **Disk:** ~2 GB for Ollama + model
- **Network:** Required only during setup (model download)

---

## Anti-Hallucination Design

VULPYX uses a **triple-layer** approach to prevent LLM hallucinations:

1. **System prompt** forces the model to only reference data present in input
2. **Structured output format** prevents freeform invention
3. **Decision engine** requires both HIGH/MEDIUM confidence AND explicit evidence before stopping

---

## Disclaimer

> VULPYX is designed for **authorized penetration testing** and **security research** in lab environments only. Never use against systems you do not own or have explicit written permission to test. The authors are not responsible for misuse.

---

*Built with ❤️ on Kali Linux*

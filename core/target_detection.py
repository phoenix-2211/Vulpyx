"""
VULPYX – Target Type Detection Engine
Analyses recon output to classify the target and select the optimal tool strategy.

Target types:
  WEB      → HTTP/HTTPS services, web apps, CMS
  NETWORK  → Internal hosts, routers, open TCP services (no web)
  AD       → Active Directory / Windows domain environments
  API      → REST/GraphQL APIs detected
  MIXED    → Multiple types detected
"""
import re
from core.banner import (
    print_info, print_ok, print_warn,
    GRN, YEL, RED, CYN, MGN, WHT, DIM, R, BLD, _tw
)

# ── Detection signatures ───────────────────────────────────────────────────────
_WEB_PORTS    = {"80", "443", "8080", "8443", "8000", "8888", "3000", "5000"}
_AD_PORTS     = {"88", "389", "636", "3268", "3269", "445", "464", "593"}
_API_SIGNS    = ["api", "graphql", "swagger", "rest", "json", "openapi", "fastapi", "flask"]
_CMS_SIGNS    = ["wordpress", "wp-", "joomla", "drupal", "magento", "typo3"]
_AD_SIGNS     = ["kerberos", "ldap", "active directory", "domain controller",
                 "msrpc", "netlogon", "samr", "lsarpc", "microsoft-ds"]
_WIN_SIGNS    = ["windows", "microsoft", "iis", "smb", "netbios"]

# ── Tool strategy per target type ─────────────────────────────────────────────
STRATEGY = {
    "WEB": {
        "label":       "Web Application",
        "color":       CYN,
        "icon":        "🌐",
        "description": "HTTP/HTTPS services detected. Focused web app attack surface.",
        "priority_tools": [
            ("nikto",        "Web server vulnerability scan"),
            ("gobuster",     "Directory & file enumeration"),
            ("ffuf",         "Virtual host & parameter fuzzing"),
            ("wpscan",       "WordPress-specific scanner (if CMS detected)"),
            ("nuclei",       "Template-based CVE scanning"),
            ("sqlmap",       "SQL injection testing on forms/params"),
        ],
        "methodology_hint": (
            "Focus on: web server version vulns, directory traversal, "
            "authentication bypass, SQL injection, XSS, file upload, CMS vulns."
        ),
    },
    "NETWORK": {
        "label":       "Network / Infrastructure",
        "color":       YEL,
        "icon":        "🔌",
        "description": "Open TCP/UDP services detected. Network-level attack surface.",
        "priority_tools": [
            ("nmap",         "Deep service/version scan with NSE scripts"),
            ("enum4linux",   "SMB/NetBIOS enumeration"),
            ("hydra",        "Credential brute-force on open services"),
            ("snmpwalk",     "SNMP community string enumeration"),
            ("ncrack",       "Network authentication cracking"),
            ("metasploit",   "Exploit known service vulnerabilities"),
        ],
        "methodology_hint": (
            "Focus on: service version exploits, default credentials, "
            "SNMP community strings, open shares, unpatched daemons."
        ),
    },
    "AD": {
        "label":       "Active Directory / Windows Domain",
        "color":       RED,
        "icon":        "🏰",
        "description": "Active Directory indicators detected. Domain attack surface.",
        "priority_tools": [
            ("nmap",         "Enumerate AD-specific ports (88,389,445,3268)"),
            ("enum4linux",   "SMB share and user enumeration"),
            ("ldapsearch",   "LDAP anonymous bind & user enumeration"),
            ("kerbrute",     "Kerberos user enumeration & AS-REP roasting"),
            ("crackmapexec", "SMB relay, pass-the-hash, lateral movement"),
            ("bloodhound",   "AD attack path visualisation"),
        ],
        "methodology_hint": (
            "Focus on: Kerberoasting, AS-REP roasting, SMB relay, "
            "LDAP anonymous bind, DCSync, pass-the-hash, BloodHound paths."
        ),
    },
    "API": {
        "label":       "API / Microservices",
        "color":       MGN,
        "icon":        "⚡",
        "description": "API endpoints detected. REST/GraphQL attack surface.",
        "priority_tools": [
            ("ffuf",         "API endpoint fuzzing"),
            ("nuclei",       "API-specific CVE templates"),
            ("gobuster",     "API path enumeration"),
            ("sqlmap",       "SQL injection on API parameters"),
            ("nikto",        "Web server and API header analysis"),
            ("curl",         "Manual API request crafting"),
        ],
        "methodology_hint": (
            "Focus on: broken object level auth (BOLA/IDOR), "
            "missing authentication, JWT weaknesses, mass assignment, rate limiting."
        ),
    },
    "MIXED": {
        "label":       "Mixed / Complex Environment",
        "color":       MGN,
        "icon":        "🔀",
        "description": "Multiple target types detected. Broad attack surface.",
        "priority_tools": [
            ("nmap",         "Full port & service fingerprint"),
            ("nikto",        "Web component scan"),
            ("enum4linux",   "SMB/NetBIOS if Windows present"),
            ("nuclei",       "Broad CVE template scan"),
            ("gobuster",     "Web directory enumeration"),
            ("ffuf",         "Fuzzing web + API endpoints"),
        ],
        "methodology_hint": (
            "Prioritise the highest-risk surface first (AD > Web > Network > API). "
            "Use context from each phase to narrow focus."
        ),
    },
}


# ── Detection logic ────────────────────────────────────────────────────────────
def detect_target_type(recon_combined: str) -> tuple[str, dict, list[str]]:
    """
    Analyse combined recon text and return:
      (type_key, strategy_dict, evidence_list)
    """
    text     = recon_combined.lower()
    evidence = []
    scores   = {"WEB": 0, "NETWORK": 0, "AD": 0, "API": 0}

    # ── Web signals ───────────────────────────────────────────────────────
    for port in _WEB_PORTS:
        if re.search(rf"\b{port}/tcp\b.*open", text) or f":{port}" in text:
            scores["WEB"] += 2
            evidence.append(f"Port {port} open (web)")

    for sign in _CMS_SIGNS:
        if sign in text:
            scores["WEB"] += 3
            evidence.append(f"CMS detected: {sign}")

    if "http" in text:
        scores["WEB"] += 1

    # ── API signals ───────────────────────────────────────────────────────
    for sign in _API_SIGNS:
        if sign in text:
            scores["API"] += 2
            evidence.append(f"API indicator: {sign}")

    # ── AD signals ────────────────────────────────────────────────────────
    for port in _AD_PORTS:
        if re.search(rf"\b{port}/tcp\b.*open", text):
            scores["AD"] += 3
            evidence.append(f"Port {port} open (AD/Windows)")

    for sign in _AD_SIGNS:
        if sign in text:
            scores["AD"] += 2
            evidence.append(f"AD/Windows service: {sign}")

    for sign in _WIN_SIGNS:
        if sign in text:
            scores["AD"] += 1

    # ── Network signals (any open port that isn't already scored) ─────────
    open_ports = re.findall(r"(\d+)/tcp\s+open", text)
    net_ports  = [p for p in open_ports if p not in _WEB_PORTS | _AD_PORTS]
    if net_ports:
        scores["NETWORK"] += len(net_ports)
        evidence.append(f"Non-web/AD open ports: {', '.join(net_ports[:5])}")

    # ── Determine winner ──────────────────────────────────────────────────
    top_score = max(scores.values())
    winners   = [k for k, v in scores.items() if v == top_score and v > 0]

    if len(winners) == 0:
        ttype = "NETWORK"   # default fallback
    elif len(winners) == 1:
        ttype = winners[0]
    else:
        # API is a sub-type of WEB — merge upward
        if set(winners) == {"WEB", "API"}:
            ttype = "API"
        else:
            ttype = "MIXED"

    return ttype, STRATEGY[ttype], evidence[:8]


# ── Pretty-print detection result ─────────────────────────────────────────────
def print_target_detection(ttype: str, strategy: dict, evidence: list[str]):
    tw  = _tw()
    col = strategy["color"]

    print(f"\n{col}{'═' * tw}{R}")
    print(f"  {col}{strategy['icon']}  TARGET TYPE DETECTED:{R}  "
          f"{BLD}{strategy['label'].upper()}{R}")
    print(f"{col}{'─' * tw}{R}")
    print(f"  {DIM}{strategy['description']}{R}\n")

    print(f"  {WHT}Evidence:{R}")
    for e in evidence:
        print(f"    {GRN}▸{R}  {e}")

    print(f"\n  {WHT}Priority Tool Chain:{R}")
    for i, (tool, reason) in enumerate(strategy["priority_tools"], 1):
        print(f"    {CYN}{i}.{R}  {BLD}{tool:<16}{R}  {DIM}{reason}{R}")

    print(f"\n  {YEL}Methodology Focus:{R}")
    print(f"  {DIM}{strategy['methodology_hint']}{R}")
    print(f"{col}{'═' * tw}{R}\n")


# ── Format strategy hint for LLM prompts ──────────────────────────────────────
def strategy_context_for_llm(ttype: str, strategy: dict) -> str:
    tools = "\n".join(
        f"  {i}. {t} — {r}"
        for i, (t, r) in enumerate(strategy["priority_tools"], 1)
    )
    return (
        f"TARGET TYPE: {strategy['label']}\n"
        f"METHODOLOGY FOCUS: {strategy['methodology_hint']}\n"
        f"PRIORITY TOOLS:\n{tools}"
    )

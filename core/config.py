# ============================================================
#  VULPYX – Configuration
# ============================================================

OLLAMA_URL   = "http://localhost:11434/api/generate"
MODEL        = "qwen2.5-coder:1.5b"   # default; overridden at runtime
MAX_METHODS  = 10

# ── Runtime model (set after model picker) ────────────────────────────────────
_runtime = {"model": MODEL}

def set_model(name: str):  _runtime["model"] = name
def get_model() -> str:    return _runtime["model"]


# ── Recon tools ────────────────────────────────────────────────────────────────
RECON_TOOLS = {
    "nmap": {
        "cmd":  "nmap -sV -sC -T4 -oN {outfile} {target}",
        "desc": "Service & version detection + default scripts",
        "apt":  "nmap",
    },
    "nikto": {
        "cmd":  "nikto -h {target} -output {outfile}",
        "desc": "Web server vulnerability scanner",
        "apt":  "nikto",
    },
    "gobuster": {
        "cmd":  "test -f /usr/share/wordlists/dirb/common.txt && gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt -o {outfile} || echo '[SKIP] wordlist not found: /usr/share/wordlists/dirb/common.txt'",
        "desc": "Directory/file brute-force",
        "apt":  "gobuster",
    },
    "ffuf": {
        "cmd":  "test -f /usr/share/wordlists/dirb/common.txt && ffuf -u http://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt -o {outfile} -of json || echo '[SKIP] wordlist not found: /usr/share/wordlists/dirb/common.txt'",
        "desc": "Fast web fuzzer for hidden paths",
        "apt":  "ffuf",
    },
    "amass": {
        "cmd":  "amass enum -passive -d {target} -o {outfile}",
        "desc": "Subdomain enumeration",
        "apt":  "amass",
    },
    "whatweb": {
        "cmd":  "whatweb -a 3 {target} | tee {outfile}",
        "desc": "Web technology fingerprinting",
        "apt":  "whatweb",
    },
    "theharvester": {
        "cmd":  "theHarvester -d {target} -b all -f {outfile}",
        "desc": "Email, hostname, IP harvest",
        "apt":  "theharvester",
    },
    "nuclei": {
        "cmd":  "nuclei -u {target} -o {outfile}",
        "desc": "Template-based vulnerability scanner",
        "apt":  "nuclei",
    },
    "sqlmap": {
        "cmd":  "sqlmap -u http://{target} --batch --output-dir={outfile}",
        "desc": "Automated SQL injection detection",
        "apt":  "sqlmap",
    },
    "wpscan": {
        "cmd":  "wpscan --url http://{target} -o {outfile}",
        "desc": "WordPress vulnerability scanner",
        "apt":  "wpscan",
    },
    "enum4linux": {
        "cmd":  "enum4linux -a {target} | tee {outfile}",
        "desc": "SMB/NetBIOS enumeration (AD/Windows)",
        "apt":  "enum4linux",
    },
    "subfinder": {
        "cmd":  "subfinder -d {target} -o {outfile}",
        "desc": "Passive subdomain discovery",
        "apt":  "subfinder",
    },
    "crackmapexec": {
        "cmd":  "crackmapexec smb {target} | tee {outfile}",
        "desc": "SMB enumeration and credential testing (AD)",
        "apt":  "crackmapexec",
    },
    "ldapsearch": {
        "cmd":  "ldapsearch -x -H ldap://{target} -b '' -s base | tee {outfile}",
        "desc": "LDAP anonymous bind enumeration (AD)",
        "apt":  "ldap-utils",
    },
}

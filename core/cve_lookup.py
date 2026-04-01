"""
VULPYX – CVE Lookup Engine
Queries the NIST NVD API (free, no key required) for real CVEs
based on services/versions discovered during recon.
"""
import re
import time
import requests

from core.banner import (
    print_info, print_ok, print_warn, print_err,
    GRN, YEL, RED, CYN, MGN, WHT, DIM, R, BLD, _tw
)

NVD_API   = "https://services.nvd.nist.gov/rest/json/cves/2.0"
TIMEOUT   = 10
MAX_CVES  = 5   # per service — keep output readable

# ── Severity colour map ────────────────────────────────────────────────────────
SEV_COLOR = {
    "CRITICAL": RED,
    "HIGH":     f"\033[1;31m",   # bright red
    "MEDIUM":   YEL,
    "LOW":      GRN,
    "NONE":     DIM,
}

def _sev_color(sev: str) -> str:
    return SEV_COLOR.get(sev.upper(), WHT)


# ── Parse nmap output for service/version strings ─────────────────────────────
def extract_services(nmap_output: str) -> list[dict]:
    """
    Parse nmap -sV output and return list of:
      { port, protocol, service, version }
    """
    services = []
    # Match lines like: 80/tcp  open  http  Apache httpd 2.4.49
    pattern = re.compile(
        r"(\d+)/(\w+)\s+open\s+([\w\-]+)\s*(.*)"
    )
    for line in nmap_output.splitlines():
        m = pattern.match(line.strip())
        if m:
            port, proto, svc, version = m.groups()
            services.append({
                "port":     port,
                "protocol": proto,
                "service":  svc.strip(),
                "version":  version.strip(),
            })
    return services


# ── Query NVD for a single keyword ────────────────────────────────────────────
def _query_nvd(keyword: str) -> list[dict]:
    """Return list of CVE dicts for a keyword search."""
    try:
        resp = requests.get(
            NVD_API,
            params={
                "keywordSearch":  keyword,
                "resultsPerPage": MAX_CVES,
            },
            timeout=TIMEOUT,
            headers={"User-Agent": "VULPYX/2.0"},
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        results = []
        for item in data.get("vulnerabilities", []):
            cve   = item.get("cve", {})
            cve_id = cve.get("id", "N/A")

            # Description
            descs = cve.get("descriptions", [])
            desc  = next((d["value"] for d in descs if d["lang"] == "en"), "No description")
            desc  = desc[:120] + "..." if len(desc) > 120 else desc

            # CVSS score + severity
            score    = "N/A"
            severity = "NONE"
            metrics  = cve.get("metrics", {})
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if key in metrics and metrics[key]:
                    m = metrics[key][0].get("cvssData", {})
                    score    = str(m.get("baseScore", "N/A"))
                    severity = m.get("baseSeverity", "NONE")
                    break

            results.append({
                "id":       cve_id,
                "score":    score,
                "severity": severity.upper(),
                "desc":     desc,
            })
        return results

    except Exception:
        return []


# ── Public: run CVE lookup for all discovered services ────────────────────────
def run_cve_lookup(nmap_output: str) -> dict[str, list[dict]]:
    """
    Extract services from nmap output, query NVD for each,
    return dict { "service_string": [cve, ...] }
    """
    services = extract_services(nmap_output)
    if not services:
        print_warn("No services parsed from nmap output for CVE lookup.")
        return {}

    results = {}
    for svc in services:
        # Build search keyword — prefer version string, fallback to service name
        keyword = svc["version"] if svc["version"] else svc["service"]
        if not keyword or keyword in ("tcpwrapped", "unknown"):
            continue

        label = f"{svc['port']}/{svc['service']}"
        print_info(f"CVE lookup → {WHT}{label}{R}  ({keyword[:40]})")

        cves = _query_nvd(keyword)
        if cves:
            results[label] = cves
            print_ok(f"  {len(cves)} CVE(s) found")
        else:
            print_warn(f"  No CVEs found")

        time.sleep(0.6)   # NVD rate-limit: ~10 req/min without API key

    return results


# ── Public: pretty-print CVE table ────────────────────────────────────────────
def print_cve_table(cve_results: dict[str, list[dict]]):
    if not cve_results:
        print_warn("No CVEs to display.\n")
        return

    tw = _tw()
    print(f"\n{CYN}{'═' * tw}{R}")
    print(f"  {YEL}CVE LOOKUP RESULTS{R}")
    print(f"{CYN}{'─' * tw}{R}\n")

    for service, cves in cve_results.items():
        print(f"  {MGN}▸  {BLD}{service}{R}")
        for cve in cves:
            col  = _sev_color(cve["severity"])
            bar  = _confidence_bar(float(cve["score"]) if cve["score"] != "N/A" else 0)
            print(f"     {CYN}{cve['id']:<20}{R}  "
                  f"{col}{cve['severity']:<8}{R}  "
                  f"CVSS {WHT}{cve['score']:<4}{R}  {bar}")
            print(f"     {DIM}{cve['desc']}{R}")
        print()

    print(f"{CYN}{'═' * tw}{R}\n")


def _confidence_bar(score: float, width: int = 10) -> str:
    """Mini CVSS score bar."""
    filled = int((score / 10.0) * width)
    empty  = width - filled
    if score >= 9.0:   col = RED
    elif score >= 7.0: col = f"\033[1;31m"
    elif score >= 4.0: col = YEL
    else:              col = GRN
    return f"{col}{'█' * filled}{DIM}{'░' * empty}{R}"


# ── Public: format CVEs for LLM context ───────────────────────────────────────
def cve_summary_for_llm(cve_results: dict[str, list[dict]]) -> str:
    if not cve_results:
        return "No CVEs found for discovered services."

    lines = ["KNOWN CVEs FOR DISCOVERED SERVICES:\n"]
    for service, cves in cve_results.items():
        lines.append(f"Service: {service}")
        for c in cves:
            lines.append(f"  - {c['id']} | CVSS {c['score']} | {c['severity']} | {c['desc']}")
        lines.append("")
    return "\n".join(lines)

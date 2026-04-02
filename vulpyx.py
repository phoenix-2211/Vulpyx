#!/usr/bin/env python3
"""
VULPYX v3 – AI-Powered Penetration Testing Assistant
"""
import os, sys, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from core.banner           import (show_banner, show_section, print_info,
                                    print_ok, print_warn, print_err,
                                    RED, YEL, CYN, GRN, MGN, WHT, DIM, R, BLD, _tw)
from core.utils            import (clear_screen, ensure_dir, save_file,
                                    load_file, multiline_input)
from core.config           import MAX_METHODS, set_model
from core.model_picker     import pick_model
from core.session          import new_session, save_session, resume_prompt
from core.recon            import run_recon_phase, print_recon_summary
from core.target_detection import detect_target_type, print_target_detection, strategy_context_for_llm
from core.cve_lookup       import run_cve_lookup, print_cve_table, cve_summary_for_llm
from core.agent            import (analyze_recon, generate_methodology,
                                    analyze_step_output, decide_next,
                                    generate_final_report, vuln_confirmed)
from core.confidence       import print_confidence_display, confidence_summary_for_llm
from core.pdf_report       import generate_pdf

# ── Helpers ────────────────────────────────────────────────────────────────────
def _sep(c="─", col=DIM): print(f"{col}{c*_tw()}{R}")
def _pause(m="Press ENTER to continue..."): input(f"\n  {DIM}{m}{R}\n")
def _ask(p, d=""): v=input(f"  {CYN}❯{R}  {p} ").strip(); return v or d


# ═══════════════════════════════════════════════════════════
#  PHASE 0 – STARTUP
# ═══════════════════════════════════════════════════════════
def startup():
    clear_screen(); show_banner()
    show_section("Model Selection")

    model = pick_model()
    set_model(model)

    projects_dir = os.path.join(_HERE, "projects")
    ensure_dir(projects_dir)

    # Resume prompt
    session = resume_prompt(projects_dir)
    if session:
        return session, True   # (session, is_resume)

    show_section("New Engagement")
    project = _ask("Project Name         :")
    while not project:
        print_warn("Name cannot be empty.")
        project = _ask("Project Name         :")

    target = _ask("Target (IP / Domain) :")
    while not target:
        print_warn("Target cannot be empty.")
        target = _ask("Target (IP / Domain) :")

    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(projects_dir, f"{project}_{ts}")
    for d in ["recon","methodology","analysis","decisions","context","report"]:
        ensure_dir(os.path.join(base, d))

    session = new_session(project, target, base)
    print_ok(f"Project : {WHT}{project}{R}")
    print_ok(f"Target  : {WHT}{target}{R}")
    print_ok(f"Folder  : {WHT}{base}{R}")
    _sep(); _pause()
    return session, False


# ═══════════════════════════════════════════════════════════
#  PHASE 1 – RECON
# ═══════════════════════════════════════════════════════════
def phase_recon(session: dict) -> dict:
    if session.get("recon_done"):
        print_ok("Recon already completed — skipping.")
        return session

    clear_screen(); show_banner()
    show_section("Phase 1 — Reconnaissance")
    print_info("Running all available recon tools…\n")

    recon_dir = os.path.join(session["base"], "recon")
    results   = run_recon_phase(session["target"], recon_dir)
    print_recon_summary(results)

    combined = f"TARGET: {session['target']}\n\n"
    for tool, output in results.items():
        combined += f"=== {tool.upper()} OUTPUT ===\n{output[:4000]}\n\n"

    save_file(os.path.join(session["base"], "context", "recon_combined.txt"), combined)
    session["recon_results"] = {k: v[:4000] for k, v in results.items()}
    session["recon_done"]    = True
    save_session(session["base"], session)
    _pause(); return session


# ═══════════════════════════════════════════════════════════
#  PHASE 1b – TARGET DETECTION
# ═══════════════════════════════════════════════════════════
def phase_target_detection(session: dict) -> dict:
    if session.get("target_type"):
        print_ok(f"Target type already detected: {session['target_type']}")
        return session

    clear_screen(); show_banner()
    show_section("Target Type Detection")

    recon_combined = load_file(
        os.path.join(session["base"], "context", "recon_combined.txt")
    )
    ttype, strategy, evidence = detect_target_type(recon_combined)
    print_target_detection(ttype, strategy, evidence)

    session["target_type"]     = ttype
    session["strategy_hint"]   = strategy_context_for_llm(ttype, strategy)
    save_session(session["base"], session)
    _pause(); return session


# ═══════════════════════════════════════════════════════════
#  PHASE 1c – CVE LOOKUP
# ═══════════════════════════════════════════════════════════
def phase_cve_lookup(session: dict) -> dict:
    if session.get("cve_results"):
        print_ok("CVE lookup already done — skipping.")
        return session

    clear_screen(); show_banner()
    show_section("CVE Lookup — NVD Database")
    print_info("Querying NIST NVD for known CVEs against discovered services…\n")

    nmap_output = session["recon_results"].get("nmap", "")
    if not nmap_output:
        print_warn("No nmap output available for CVE lookup.")
        return session

    cve_results = run_cve_lookup(nmap_output)
    print_cve_table(cve_results)

    session["cve_results"] = cve_results
    save_session(session["base"], session)
    save_file(
        os.path.join(session["base"], "analysis", "cve_lookup.txt"),
        cve_summary_for_llm(cve_results)
    )
    _pause(); return session


# ═══════════════════════════════════════════════════════════
#  PHASE 2 – RECON ANALYSIS
# ═══════════════════════════════════════════════════════════
def phase_recon_analysis(session: dict) -> dict:
    if session.get("recon_analysis"):
        print_ok("Recon analysis already done — skipping.")
        return session

    clear_screen(); show_banner()
    show_section("Phase 2 — AI Recon Analysis")
    print_info("Feeding recon + CVE data into VULPYX AI…\n")

    analysis = analyze_recon(session["recon_results"], session["target"])
    save_file(os.path.join(session["base"], "analysis", "recon_analysis.txt"), analysis)

    # Build initial context with all enrichment
    recon_combined = load_file(
        os.path.join(session["base"], "context", "recon_combined.txt")
    )
    session["recon_analysis"] = analysis
    session["context"] = (
        f"TARGET: {session['target']}\n\n"
        f"TARGET TYPE: {session.get('target_type','Unknown')}\n\n"
        f"{session.get('strategy_hint','')}\n\n"
        f"CVE FINDINGS:\n{cve_summary_for_llm(session.get('cve_results',{}))}\n\n"
        f"RECON ANALYSIS:\n{analysis}\n\n"
    )

    save_session(session["base"], session)
    print_ok("Recon analysis complete.\n")
    _pause(); return session


# ═══════════════════════════════════════════════════════════
#  PHASE 3 – METHODOLOGY LOOP
# ═══════════════════════════════════════════════════════════
def phase_methodology(session: dict) -> dict:
    step       = session.get("current_step", 1)
    context    = session.get("context", "")
    vuln_found = session.get("vuln_found", False)

    recon_combined_path = os.path.join(session["base"], "context", "recon_combined.txt")
    recon_combined = (
        load_file(recon_combined_path)
        if os.path.exists(recon_combined_path) else ""
    )

    while step <= MAX_METHODS and not vuln_found:

        # ── Generate ──────────────────────────────────────────────────────────
        clear_screen(); show_banner()
        show_section(f"Methodology {step} — AI Generates Next Step")

        method = generate_methodology(context, step)
        save_file(
            os.path.join(session["base"], "methodology", f"step_{step}_plan.txt"),
            method
        )

        if "EXHAUSTED" in method.upper():
            print_warn("AI: All logical steps exhausted.")
            break

        # ── Display methodology clearly ───────────────────────────────────────
        tw = _tw()
        print(f"\n{CYN}{'═' * tw}{R}")
        print(f"  {YEL}METHODOLOGY STEP {step}  —  GENERATED COMMAND{R}")
        print(f"{CYN}{'─' * tw}{R}")
        for line in method.strip().splitlines():
            print(f"  {line}")
        print(f"{CYN}{'═' * tw}{R}\n")
        _sep("═", CYN)
        print(f"\n  {YEL}YOUR TURN{R}  — Run the command above in your Kali terminal.\n")
        print_info("Paste the full output below.")
        print_warn("Type  END  alone on a new line when done. Type  NA  to skip.\n")
        _sep()

        user_output = multiline_input(
            f"  {CYN}❯  Output of Methodology {step}{R}  (END to finish):"
        )
        save_file(
            os.path.join(session["base"], "methodology", f"step_{step}_output.txt"),
            user_output
        )

        if user_output.strip().upper() == "NA":
            print_warn("Step skipped.")
            step += 1
            session["current_step"] = step
            save_session(session["base"], session)
            continue

        # ── AI Analysis ───────────────────────────────────────────────────────
        clear_screen(); show_banner()
        show_section(f"Methodology {step} — AI Analysis")

        analysis = analyze_step_output(method, user_output, recon_combined)
        save_file(
            os.path.join(session["base"], "analysis", f"step_{step}_analysis.txt"),
            analysis
        )

        # ── Confidence bar ────────────────────────────────────────────────────
        print_confidence_display(analysis, step)

        # ── Decision ──────────────────────────────────────────────────────────
        show_section(f"Methodology {step} — Decision Engine")
        decision = decide_next(analysis)
        save_file(
            os.path.join(session["base"], "decisions", f"step_{step}_decision.txt"),
            decision
        )

        # ── Update context + session ──────────────────────────────────────────
        conf_summary = confidence_summary_for_llm(analysis)
        context += (
            f"\n[STEP {step}]\n"
            f"METHOD:\n{method}\n\n"
            f"USER OUTPUT:\n{user_output}\n\n"
            f"ANALYSIS:\n{analysis}\n\n"
            f"{conf_summary}\n\n"
            f"DECISION:\n{decision}\n\n"
            f"{'─'*60}\n"
        )
        save_file(
            os.path.join(session["base"], "context", "cumulative_context.txt"),
            context
        )
        session["context"]      = context
        session["current_step"] = step + 1
        session["steps"].append({
            "step":     step,
            "method":   method[:500],
            "output":   user_output[:500],
            "analysis": analysis[:500],
            "decision": decision[:200],
        })
        save_session(session["base"], session)

        # ── Check confirmed ───────────────────────────────────────────────────
        if vuln_confirmed(decision, analysis):
            print()
            print(f"\n  {GRN}{'█'*58}{R}")
            print(f"  {GRN}  ✔  VULNERABILITY CONFIRMED — GENERATING REPORT  {R}")
            print(f"  {GRN}{'█'*58}{R}\n")
            vuln_found = True
            break

        _pause(); step += 1

    session["vuln_found"] = vuln_found
    save_session(session["base"], session)
    return session


# ═══════════════════════════════════════════════════════════
#  PHASE 4 – FINAL REPORT (MD + PDF)
# ═══════════════════════════════════════════════════════════
def phase_report(session: dict):
    clear_screen(); show_banner()
    show_section("Phase 4 — Final Report Generation")
    print_info("Generating professional penetration test report…\n")

    report_md = generate_final_report(session["context"])
    ts         = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    md_path    = os.path.join(session["base"], "report", f"vulpyx_report_{ts}.md")
    pdf_path   = os.path.join(session["base"], "report", f"vulpyx_report_{ts}.pdf")

    save_file(md_path, report_md)
    print_ok(f"Markdown report : {WHT}{md_path}{R}")

    # PDF
    generate_pdf(report_md, pdf_path,
                 project=session["project"],
                 target=session["target"])

    session["completed"] = True
    save_session(session["base"], session)
    return md_path, pdf_path


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
def main():
    try:
        session, is_resume = startup()

        if not is_resume:
            session = phase_recon(session)
            session = phase_target_detection(session)
            session = phase_cve_lookup(session)
            session = phase_recon_analysis(session)
        else:
            # Resume — re-run any incomplete phases
            if not session.get("recon_done"):
                session = phase_recon(session)
            if not session.get("target_type"):
                session = phase_target_detection(session)
            if not session.get("cve_results"):
                session = phase_cve_lookup(session)
            if not session.get("recon_analysis"):
                session = phase_recon_analysis(session)

        session  = phase_methodology(session)
        md_path, pdf_path = phase_report(session)

        # ── Done ──────────────────────────────────────────────────────────────
        clear_screen(); show_banner()
        _sep("═", GRN)
        if session["vuln_found"]:
            print(f"\n  {GRN}[✔]{R}  {BLD}Vulnerability confirmed. Reports generated.{R}")
        else:
            print(f"\n  {YEL}[!]{R}  {BLD}No confirmed vulnerability. Reports saved.{R}")

        print(f"\n  {WHT}Markdown  :{R}  {md_path}")
        print(f"  {WHT}PDF       :{R}  {pdf_path}")
        print(f"  {WHT}Project   :{R}  {session['base']}\n")
        _sep("═", GRN)

    except KeyboardInterrupt:
        print(f"\n\n  {YEL}[!]{R}  Session interrupted. Progress saved.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n  {RED}[FATAL]{R}  {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

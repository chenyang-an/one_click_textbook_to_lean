#!/usr/bin/env python3
"""
Stage 5: Final validation of the entire project.
Runs lake build and per-chapter checks (no sorry, no axiom, coverage).
Generates a summary report at <project_root>/final_summary.md.
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime


def count_theorems(content):
    """Count theorem/corollary/lemma declarations with the Ch*_ naming pattern."""
    return len(re.findall(r'^theorem\s+Ch\d+_', content, re.MULTILINE))


def count_defs(content):
    """Count def declarations."""
    return len(re.findall(r'^def\s+', content, re.MULTILINE))


def count_lines(filepath):
    """Count lines in a file."""
    if not os.path.exists(filepath):
        return 0
    with open(filepath) as f:
        return sum(1 for _ in f)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, help="Lean project root")
    p.add_argument("--chapters", required=True, help="Comma-separated chapter numbers")
    p.add_argument("--evaluation", required=True, help="Path to evaluation/ dir")
    args = p.parse_args()

    chapters = [int(c) for c in args.chapters.split(",")]
    project = args.output
    all_pass = True
    report_lines = []

    def report(line=""):
        report_lines.append(line)
        print(line)

    report("# Formalization Summary Report")
    report()
    report(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report(f"**Project:** `{project}`")
    report(f"**Chapters:** {len(chapters)} ({', '.join(str(c) for c in chapters)})")
    report()

    # --- 1. Full project build ---
    report("---")
    report()
    report("## 1. Build Verification")
    report()
    build_result = subprocess.run(
        ["lake", "build"], cwd=project, capture_output=True, text=True
    )
    if build_result.returncode != 0:
        report("**Status:** FAIL")
        report()
        report("```")
        report(build_result.stderr.strip())
        report("```")
        all_pass = False
    else:
        report("**Status:** PASS")
    report()

    # --- 2. Per-chapter checks ---
    report("---")
    report()
    report("## 2. Per-Chapter Results")
    report()

    total_theorems = 0
    total_defs = 0
    total_lines = 0
    chapter_results = []

    for ch in chapters:
        lean_file = os.path.join(project, "Formalization", f"ch{ch}.lean")
        specs_file = os.path.join(project, "Formalization", "intermediate_files", f"ch{ch}", f"ch{ch}_specs.lean")
        proof_verify_file = os.path.join(project, "experiments", "auto", f"ch{ch}", "verification", "fl_proof_verification_result.md")
        stmt_verify_file = os.path.join(project, "experiments", "auto", f"ch{ch}", "verification_fl_statement", "fl_statements_verification_result.md")
        proof_status_file = os.path.join(project, "experiments", "auto", f"ch{ch}", "verification", "fl_proof_status.md")

        ch_pass = True
        sorry_count = 0
        axiom_count = 0
        theorem_count = 0
        def_count = 0
        line_count = 0
        coverage_status = "N/A"

        report(f"### Chapter {ch}")
        report()

        if not os.path.exists(lean_file):
            report(f"**Status:** FAIL -- `ch{ch}.lean` does not exist")
            report()
            all_pass = False
            chapter_results.append(("FAIL", ch, 0, 0, 0))
            continue

        with open(lean_file) as f:
            content = f.read()

        line_count = content.count("\n") + 1
        theorem_count = count_theorems(content)
        def_count = count_defs(content)
        sorry_count = content.count("sorry")
        axiom_count = len(re.findall(r'^\s*axiom\s+', content, re.MULTILINE))

        total_theorems += theorem_count
        total_defs += def_count
        total_lines += line_count

        # Sorry check
        sorry_status = "PASS" if sorry_count == 0 else "FAIL"
        if sorry_count > 0:
            ch_pass = False
            all_pass = False

        # Axiom check
        axiom_status = "PASS" if axiom_count == 0 else "FAIL"
        if axiom_count > 0:
            ch_pass = False
            all_pass = False

        # Coverage check
        if os.path.exists(specs_file):
            cov_script = os.path.join(args.evaluation, "check_coverage_lean_statement.py")
            cov_result = subprocess.run(
                [sys.executable, cov_script, specs_file, lean_file],
                capture_output=True, text=True,
            )
            if cov_result.returncode != 0:
                coverage_status = "FAIL"
                ch_pass = False
                all_pass = False
            else:
                coverage_status = "PASS"
        else:
            coverage_status = "SKIP (no specs file)"

        overall = "PASS" if ch_pass else "FAIL"

        report(f"| Check | Status |")
        report(f"|-------|--------|")
        report(f"| Sorry-free | {sorry_status} ({sorry_count} found) |")
        report(f"| Axiom-free | {axiom_status} ({axiom_count} found) |")
        report(f"| Coverage preserved | {coverage_status} |")
        report(f"| **Overall** | **{overall}** |")
        report()
        report(f"| Metric | Value |")
        report(f"|--------|-------|")
        report(f"| Theorems | {theorem_count} |")
        report(f"| Definitions | {def_count} |")
        report(f"| Lines | {line_count} |")
        report()
        report(f"**Verification reports:**")
        report()
        if os.path.exists(stmt_verify_file):
            report(f"- Statement verification: `{os.path.relpath(stmt_verify_file, project)}`")
        if os.path.exists(proof_verify_file):
            report(f"- Proof verification: `{os.path.relpath(proof_verify_file, project)}`")
        if os.path.exists(proof_status_file):
            report(f"- Proof search log: `{os.path.relpath(proof_status_file, project)}`")
        if not any(os.path.exists(f) for f in [stmt_verify_file, proof_verify_file, proof_status_file]):
            report(f"- No verification reports found")
        report()

        chapter_results.append((overall, ch, theorem_count, def_count, line_count))

    # --- 3. Overall summary ---
    report("---")
    report()
    report("## 3. Overall Summary")
    report()
    report(f"| Metric | Value |")
    report(f"|--------|-------|")
    report(f"| Chapters | {len(chapters)} |")
    report(f"| Total theorems | {total_theorems} |")
    report(f"| Total definitions | {total_defs} |")
    report(f"| Total lines | {total_lines} |")
    report(f"| Build | {'PASS' if build_result.returncode == 0 else 'FAIL'} |")
    report(f"| **Final verdict** | **{'ALL PASS' if all_pass else 'SOME CHECKS FAILED'}** |")
    report()

    passed = sum(1 for r in chapter_results if r[0] == "PASS")
    failed = sum(1 for r in chapter_results if r[0] == "FAIL")
    report(f"Chapters passed: {passed}/{len(chapters)}")
    if failed > 0:
        failed_chs = [str(r[1]) for r in chapter_results if r[0] == "FAIL"]
        report(f"Chapters failed: {', '.join(failed_chs)}")
    report()

    # --- Write report ---
    report_path = os.path.join(project, "final_summary.md")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines) + "\n")

    print(f"\nReport written to: {report_path}")

    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()

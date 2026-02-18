#!/usr/bin/env python3
"""
Stage 5: Final validation of the entire project.
Runs lake build and per-chapter checks (no sorry, no axiom, coverage).
"""

import argparse
import os
import subprocess
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, help="Lean project root")
    p.add_argument("--chapters", required=True, help="Comma-separated chapter numbers")
    p.add_argument("--evaluation", required=True, help="Path to evaluation/ dir")
    args = p.parse_args()

    chapters = [int(c) for c in args.chapters.split(",")]
    project = args.output
    all_pass = True

    # 1. Full project build
    print("=== Final lake build ===")
    result = subprocess.run(["lake", "build"], cwd=project, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAIL: lake build failed\n{result.stderr}")
        all_pass = False
    else:
        print("PASS: lake build succeeded")

    # 2. Per-chapter checks
    for ch in chapters:
        lean_file = os.path.join(project, "Formalization", f"ch{ch}.lean")
        specs_file = os.path.join(project, "Formalization", "intermediate_files", f"ch{ch}", f"ch{ch}_specs.lean")

        if not os.path.exists(lean_file):
            print(f"FAIL: ch{ch}.lean does not exist")
            all_pass = False
            continue

        print(f"\n--- Chapter {ch} ---")

        # Sorry check
        with open(lean_file) as f:
            content = f.read()
        sorry_count = content.count("sorry")
        if sorry_count > 0:
            print(f"  FAIL: {sorry_count} sorry found in ch{ch}.lean")
            all_pass = False
        else:
            print(f"  PASS: no sorry in ch{ch}.lean")

        # Axiom check
        import re
        axiom_matches = re.findall(r'^\s*axiom\s+', content, re.MULTILINE)
        if axiom_matches:
            print(f"  FAIL: {len(axiom_matches)} axiom declarations in ch{ch}.lean")
            all_pass = False
        else:
            print(f"  PASS: no axiom in ch{ch}.lean")

        # Coverage check (statement preservation)
        if os.path.exists(specs_file):
            cov_script = os.path.join(args.evaluation, "check_coverage_lean_statement.py")
            cov_result = subprocess.run(
                [sys.executable, cov_script, specs_file, lean_file],
                capture_output=True, text=True,
            )
            if cov_result.returncode != 0:
                print(f"  FAIL: coverage check failed for ch{ch}")
                print(f"  {cov_result.stdout}")
                all_pass = False
            else:
                print(f"  PASS: coverage check for ch{ch}")
        else:
            print(f"  SKIP: no specs file for ch{ch} (statement preservation check skipped)")

    # Summary
    print("\n" + "=" * 50)
    if all_pass:
        print("FINAL RESULT: ALL CHECKS PASSED")
    else:
        print("FINAL RESULT: SOME CHECKS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()

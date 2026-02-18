#!/usr/bin/env python3
"""
Main orchestrator: takes a directory of ch*.txt LaTeX chapter files and
produces a verified Lean 4 formalization project.

Stages:
  0. Scaffold Lean project (dirs, root import, copy raw data)
  1. Extract theorem blocks from each chapter
  2. Render agent prompts and shell scripts from templates
  3. Statement formalization (sequential by chapter order)
  4. Proof search (parallel across chapters)
  5. Final validation
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import yaml


def discover_chapters(input_dir: str) -> list:
    """Find all ch*.txt files, return sorted chapter numbers."""
    files = glob.glob(os.path.join(input_dir, "ch*.txt"))
    nums = []
    for f in files:
        m = re.search(r'ch(\d+)\.txt$', os.path.basename(f))
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def run_cmd(cmd, **kwargs):
    """Run a command, printing it first."""
    if isinstance(cmd, list):
        print(f"  $ {' '.join(cmd)}")
    else:
        print(f"  $ {cmd}")
    subprocess.check_call(cmd, **kwargs)


def stage0_scaffold(input_dir, project_root, chapters, pipeline_dir, evaluation_dir):
    """Generate the Lean project skeleton."""
    run_cmd([
        sys.executable, os.path.join(pipeline_dir, "pipeline", "scaffold.py"),
        "--input", input_dir,
        "--output", project_root,
        "--chapters", ",".join(str(c) for c in chapters),
        "--evaluation", evaluation_dir,
    ])


def stage0_fetch_mathlib(project_root):
    """Fetch Mathlib cache (pre-built oleans)."""
    print("  Fetching Mathlib cache (this may take a few minutes on first run)...")
    run_cmd(["lake", "exe", "cache", "get"], cwd=project_root)


def stage1_extract(input_dir, project_root, chapters, evaluation_dir):
    """Extract theorem blocks from each chapter."""
    theorems_dir = os.path.join(project_root, "natural_language", "raw_data", "theorems_only")
    os.makedirs(theorems_dir, exist_ok=True)
    script = os.path.join(evaluation_dir, "keep_only_theorems.py")
    for ch in chapters:
        src = os.path.join(input_dir, f"ch{ch}.txt")
        dst = os.path.join(theorems_dir, f"ch{ch}.txt")
        print(f"  ch{ch}: extracting theorem blocks...")
        run_cmd([sys.executable, script, src, dst])


def stage2_render(project_root, chapters, config_path, templates_dir):
    """Render agent prompts and shell scripts from templates."""
    run_cmd([
        sys.executable, os.path.join(os.path.dirname(templates_dir), "pipeline", "render_prompts.py"),
        "--output", project_root,
        "--chapters", ",".join(str(c) for c in chapters),
        "--config", config_path,
        "--templates", templates_dir,
    ])


def run_chapter_full(project_root, ch):
    """Run the full pipeline (statements + proofs) for one chapter."""
    ch_dir = os.path.join(project_root, "experiments", "auto", f"ch{ch}")
    run_script = os.path.join(ch_dir, "run.sh")
    subprocess.check_call(["bash", run_script])


def run_chapter_statements(project_root, ch):
    """Run only the statement formalization loop for one chapter."""
    ch_dir = os.path.join(project_root, "experiments", "auto", f"ch{ch}")
    subprocess.check_call(["bash", os.path.join(ch_dir, "run_statement.sh")])


def snapshot_specs(project_root, ch):
    """Snapshot ch*.lean as ch*_specs.lean before proof search."""
    src = os.path.join(project_root, "Formalization", f"ch{ch}.lean")
    dst_dir = os.path.join(project_root, "Formalization", "intermediate_files", f"ch{ch}")
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, f"ch{ch}_specs.lean")
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"  ch{ch}: specs snapshot saved")


def run_chapter_proofs(project_root, ch):
    """Run only the proof search loop for one chapter."""
    ch_dir = os.path.join(project_root, "experiments", "auto", f"ch{ch}")
    subprocess.check_call(["bash", os.path.join(ch_dir, "run_proof.sh")])


def stage5_validate(project_root, chapters, evaluation_dir):
    """Final full-project validation."""
    pipeline_dir = os.path.dirname(evaluation_dir)
    run_cmd([
        sys.executable, os.path.join(pipeline_dir, "pipeline", "validate.py"),
        "--output", project_root,
        "--chapters", ",".join(str(c) for c in chapters),
        "--evaluation", evaluation_dir,
    ])


def main():
    p = argparse.ArgumentParser(description="One-click textbook to Lean formalization pipeline")
    p.add_argument("--input", required=True, help="Directory containing ch*.txt LaTeX chapter files")
    p.add_argument("--output", required=True, help="Lean project root (this repo's root)")
    p.add_argument("--config", required=True, help="Path to config.yaml")
    p.add_argument("--templates", required=True, help="Path to templates/ dir")
    p.add_argument("--evaluation", required=True, help="Path to evaluation/ dir")
    args = p.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    pipeline_cfg = config.get("pipeline", {})
    project_root = os.path.abspath(args.output)
    pipeline_dir = os.path.dirname(args.templates)  # OneClickTextbookToLean/

    chapters = discover_chapters(args.input)
    if not chapters:
        print(f"ERROR: No ch*.txt files found in {args.input}")
        sys.exit(1)

    print(f"=== Discovered {len(chapters)} chapters: {chapters} ===")
    print(f"=== Project root: {project_root} ===")
    print()

    # -------------------------------------------------------
    # Stage 0: Scaffold
    # -------------------------------------------------------
    print("=" * 60)
    print("STAGE 0: Scaffolding Lean project")
    print("=" * 60)
    stage0_scaffold(args.input, project_root, chapters, pipeline_dir, args.evaluation)
    stage0_fetch_mathlib(project_root)
    print()

    # -------------------------------------------------------
    # Stage 1: Extract theorem blocks
    # -------------------------------------------------------
    print("=" * 60)
    print("STAGE 1: Extracting theorem blocks")
    print("=" * 60)
    stage1_extract(args.input, project_root, chapters, args.evaluation)
    print()

    # -------------------------------------------------------
    # Stage 2: Render prompts
    # -------------------------------------------------------
    print("=" * 60)
    print("STAGE 2: Rendering agent prompts and shell scripts")
    print("=" * 60)
    stage2_render(project_root, chapters, args.config, args.templates)
    print()

    # -------------------------------------------------------
    # Stage 3: Formalization (statements → proofs, per chapter)
    # -------------------------------------------------------
    print("=" * 60)
    print("STAGE 3: Formalization (sequential by chapter)")
    print("=" * 60)
    failed_chapters = []
    for ch in chapters:
        print(f"\n{'=' * 60}")
        print(f"Chapter {ch}: statements → proofs")
        print(f"{'=' * 60}")
        try:
            run_chapter_full(project_root, ch)
            print(f"  Chapter {ch}: DONE")
        except Exception as e:
            print(f"  Chapter {ch}: FAILED: {e}")
            failed_chapters.append(ch)

    if failed_chapters:
        print(f"\nWARNING: Chapters {failed_chapters} failed (max iterations reached)")
    print()

    # -------------------------------------------------------
    # Stage 5: Final validation
    # -------------------------------------------------------
    print("=" * 60)
    print("STAGE 5: Final validation")
    print("=" * 60)
    stage5_validate(project_root, chapters, args.evaluation)

    print()
    print("=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Project at: {project_root}")
    print(f"Run 'cd {project_root} && lake build' to verify independently.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Stage 2: Render Jinja2 templates into per-chapter agent prompts and shell scripts.
"""

import argparse
import os
import stat
import yaml
from jinja2 import Environment, FileSystemLoader


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, help="Lean project root (absolute path)")
    p.add_argument("--chapters", required=True, help="Comma-separated chapter numbers")
    p.add_argument("--config", required=True, help="Path to config.yaml")
    p.add_argument("--templates", required=True, help="Path to templates/ dir")
    args = p.parse_args()

    chapters = [int(c) for c in args.chapters.split(",")]
    project = os.path.abspath(args.output)

    with open(args.config) as f:
        config = yaml.safe_load(f)

    pipeline_cfg = config.get("pipeline", {})
    claude_cfg = config.get("claude", {})

    # Set up Jinja2
    env = Environment(
        loader=FileSystemLoader(args.templates),
        keep_trailing_newline=True,
    )

    # Pipeline tools dir (where evaluation scripts live)
    # This is the OneClickTextbookToLean dir, which is a sibling of templates
    pipeline_base = os.path.dirname(args.templates)
    evaluation_dir = os.path.join(pipeline_base, "evaluation")

    for ch in chapters:
        prior = [c for c in chapters if c < ch]

        # Common template variables
        variables = {
            "ch_num": ch,
            "project_root": project,
            "lean_chapter_file": os.path.join(project, "Formalization", f"ch{ch}.lean"),
            "lean_src_dir": os.path.join(project, "Formalization"),
            "raw_data_dir": os.path.join(project, "natural_language", "raw_data"),
            "theorems_and_defs_dir": os.path.join(project, "natural_language", "raw_data", "theorems_and_defs"),
            "evaluation_dir": evaluation_dir,
            "experiment_ch_dir": os.path.join(project, "experiments", "auto", f"ch{ch}"),
            "verification_dir": os.path.join(project, "experiments", "auto", f"ch{ch}", "verification"),
            "verification_fl_statement_dir": os.path.join(project, "experiments", "auto", f"ch{ch}", "verification_fl_statement"),
            "intermediate_dir": os.path.join(project, "Formalization", "intermediate_files", f"ch{ch}"),
            "prior_chapters": prior,
            "max_statement_iterations": pipeline_cfg.get("max_statement_iterations", 9),
            "max_proof_iterations": pipeline_cfg.get("max_proof_iterations", 9),
            "statement_check_interval": pipeline_cfg.get("statement_check_interval", 1),
            "claude_flags": claude_cfg.get("flags", "--dangerously-skip-permissions --verbose --output-format stream-json"),
        }

        agent_dir = os.path.join(project, "experiments", "auto", f"ch{ch}", "agent")
        ch_dir = os.path.join(project, "experiments", "auto", f"ch{ch}")

        # Render prompt templates
        prompt_templates = {
            "prompts/statement_fl.md.j2": "CLAUDE_statement_fl.md",
            "prompts/statement_verify.md.j2": "CLAUDE_statement_verify.md",
            "prompts/proof_search.md.j2": "CLAUDE_proof_search.md",
            "prompts/proof_verify.md.j2": "CLAUDE_proof_verify.md",
            "prompts/verdict.md.j2": "CLAUDE_verdict.md",
            "prompts/verdict_statement.md.j2": "CLAUDE_verdict_statement.md",
            "prompts/check_statement_change.md.j2": "CLAUDE_check_statement_change.md",
        }
        for template_path, output_name in prompt_templates.items():
            tmpl = env.get_template(template_path)
            rendered = tmpl.render(**variables)
            out_path = os.path.join(agent_dir, output_name)
            with open(out_path, "w") as f:
                f.write(rendered)

        # Render shell script templates
        shell_templates = {
            "shell/run.sh.j2": "run.sh",
            "shell/run_statement.sh.j2": "run_statement.sh",
            "shell/run_proof.sh.j2": "run_proof.sh",
        }
        for template_path, output_name in shell_templates.items():
            tmpl = env.get_template(template_path)
            rendered = tmpl.render(**variables)
            out_path = os.path.join(ch_dir, output_name)
            with open(out_path, "w") as f:
                f.write(rendered)
            # Make shell scripts executable
            os.chmod(out_path, os.stat(out_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        print(f"  Chapter {ch}: rendered 7 prompts + 3 shell scripts")

    print(f"All prompts rendered for chapters {chapters}")


if __name__ == "__main__":
    main()

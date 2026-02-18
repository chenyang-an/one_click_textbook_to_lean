# One-Click Textbook to Lean

Automated pipeline that takes LaTeX textbook chapters and produces a fully formalized Lean 4 project with Mathlib, including theorem statements and proofs.

## Prerequisites

- **[elan](https://github.com/leanprover/elan)** -- Lean version manager (installs `lake` automatically)
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** -- `claude` CLI
- **Python 3.8+** with `pip`
- **jq** -- JSON processor (`apt install jq` / `brew install jq`)

## Quick Start

```bash
# 1. Clone this repo
git clone https://github.com/<you>/one_click_textbook_to_lean.git
cd one_click_textbook_to_lean

# 2. Run the pipeline
./OneClickTextbookToLean/formalize.sh /path/to/your/chapters/

# 3. Verify the result
lake build
```

## Input Format

The input directory should contain one `.txt` file per chapter, named `ch1.txt`, `ch2.txt`, ..., `chN.txt`. Each file contains the LaTeX source of that chapter.

```
my_textbook_chapters/
├── ch1.txt    # LaTeX source of Chapter 1
├── ch2.txt    # LaTeX source of Chapter 2
├── ch3.txt    # LaTeX source of Chapter 3
└── ...
```

The LaTeX should contain standard theorem environments (`\begin{theorem}...\end{theorem}`, `\begin{lemma}...\end{lemma}`, `\begin{corollary}...\end{corollary}`).

## What the Pipeline Does

The pipeline runs 6 stages:

| Stage | What | How |
|-------|------|-----|
| **0. Scaffold** | Generate Lean project structure, fetch Mathlib cache | `lake exe cache get` |
| **1. Extract** | Pull out `\begin{theorem}` blocks from each chapter | Regex (deterministic) |
| **2. Render** | Generate per-chapter agent prompts from templates | Jinja2 |
| **3. Statements** | Formalize theorem statements in Lean (sequential) | Claude CLI loop |
| **4. Proofs** | Prove all theorems (parallel across chapters) | Claude CLI loop |
| **5. Validate** | Full `lake build`, no-sorry check, coverage check | Deterministic |

Stages 3 and 4 each run an iterative loop (up to 9 iterations by default) of:
formalize/prove -> verify -> verdict (DONE/CONTINUE).

## Configuration

Edit `OneClickTextbookToLean/config.yaml`:

```yaml
pipeline:
  max_statement_iterations: 9    # max attempts per chapter for statements
  max_proof_iterations: 9        # max attempts per chapter for proofs
  max_parallel_chapters: 2       # concurrent proof search processes
  statement_check_interval: 1    # check statement drift every N iterations
```

## Project Structure After Running

```
one_click_textbook_to_lean/
├── Formalization.lean              # Root import (auto-generated)
├── Formalization/
│   ├── ch1.lean ... chN.lean       # Formalized chapters with proofs
│   └── intermediate_files/         # Spec snapshots for drift detection
├── natural_language/
│   └── raw_data/                   # Copied input + extracted theorems
├── experiments/
│   └── auto/
│       └── ch*/                    # Agent prompts, logs, verification artifacts
├── OneClickTextbookToLean/         # Pipeline code (committed)
│   ├── formalize.sh                # Entry point
│   ├── config.yaml
│   ├── pipeline/                   # Python orchestration scripts
│   ├── templates/                  # Jinja2 templates for prompts
│   └── evaluation/                 # Coverage check scripts
├── lakefile.toml
├── lean-toolchain
└── lake-manifest.json
```

## Monitoring Progress

While the pipeline runs, check per-chapter status:

```bash
# Statement formalization status
cat experiments/auto/ch1/verification_fl_statement/AUTO_RUN_STATUS.md

# Proof search status
cat experiments/auto/ch1/AUTO_RUN_STATUS.md

# Detailed logs
tail -f experiments/auto/ch1/AUTO_RUN_LOG.txt
```

#!/bin/bash
set -euo pipefail

# ============================================================
# One-Click Textbook to Lean Formalization
# ============================================================
# Usage: ./OneClickTextbookToLean/formalize.sh /path/to/chapters/
#
# The input directory should contain ch1.txt, ch2.txt, ..., chN.txt
# where each file is the LaTeX source of one chapter.
#
# This script will:
#   1. Fetch Mathlib cache (pre-built oleans)
#   2. Extract theorem blocks from each chapter
#   3. Generate agent prompts for Claude
#   4. Run statement formalization (sequential by chapter)
#   5. Run proof search (parallel across chapters)
#   6. Validate the final project
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INPUT_DIR="${1:?Usage: ./OneClickTextbookToLean/formalize.sh <path-to-chapter-txt-dir>}"

# Resolve to absolute path
INPUT_DIR="$(cd "$INPUT_DIR" && pwd)"

echo "============================================================"
echo "One-Click Textbook to Lean Formalization"
echo "============================================================"
echo "Input directory: $INPUT_DIR"
echo "Project root:    $REPO_ROOT"
echo "Pipeline:        $SCRIPT_DIR"
echo "============================================================"
echo ""

# --- Prerequisites check ---
check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        echo "ERROR: '$1' not found."
        echo "  $2"
        exit 1
    fi
}

check_cmd elan   "Install from: https://github.com/leanprover/elan"
check_cmd lake   "Installed automatically by elan"
check_cmd claude "Install from: https://docs.anthropic.com/en/docs/claude-code"
check_cmd python3 "Install Python 3.8+"
check_cmd jq     "Install jq (apt install jq / brew install jq)"

# Check Python dependencies
python3 -c "import jinja2" 2>/dev/null || {
    echo "Installing Python dependencies..."
    pip3 install -r "$SCRIPT_DIR/requirements.txt"
}
python3 -c "import yaml" 2>/dev/null || {
    echo "Installing Python dependencies..."
    pip3 install -r "$SCRIPT_DIR/requirements.txt"
}

# --- Validate input ---
shopt -s nullglob
CH_FILES=("$INPUT_DIR"/ch*.txt)
shopt -u nullglob
if [ ${#CH_FILES[@]} -eq 0 ]; then
    echo "ERROR: No ch*.txt files found in $INPUT_DIR"
    echo "Expected files like ch1.txt, ch2.txt, etc."
    exit 1
fi
echo "Found ${#CH_FILES[@]} chapter file(s):"
for f in "${CH_FILES[@]}"; do
    echo "  $(basename "$f")"
done
echo ""

# --- Run the pipeline ---
python3 "$SCRIPT_DIR/pipeline/orchestrate.py" \
    --input "$INPUT_DIR" \
    --output "$REPO_ROOT" \
    --config "$SCRIPT_DIR/config.yaml" \
    --templates "$SCRIPT_DIR/templates" \
    --evaluation "$SCRIPT_DIR/evaluation"

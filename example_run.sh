#!/bin/bash
# Example: run numina-lean-agent on a folder of .lean files using the
# autosearch coordinator prompt — NO-GOLF variant (default).
#
# This uses prompts/autosearch_no_golf/, which never spawns a golfer agent and
# never runs any golf / simplify pass on completed proofs. A lemma is done as
# soon as it compiles with no `sorry`. For the golfing variant, use
# ./example_run_with_golf.sh instead.
#
# Usage:
#   bash ./example_run.sh [target_folder]

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

##############################################################################
# --- Reference resources (consumed by prompts/autosearch_no_golf/main_entry.md) ---
# main_entry.md reads this via `echo "$REFERENCE_RESOURCES"` and hands the
# path(s) to each subagent. Use a colon-separated list for multiple paths.
# Optional: leave empty or unset if you have no reference files.

# substitute with real example resources path here (or leave empty)
# ICML26 heapsort demo: the task README + the original Rust source give the
# agent context on what the algorithm does and what to prove.
export REFERENCE_RESOURCES="$REPO_ROOT/ICML26_demo/README.md:$REPO_ROOT/ICML26_demo/rust/src/lib.rs"

# --- Target folder ---
# The .lean file or folder the agent will work on. Overridden by the
# [target_folder] CLI argument if provided. Must live inside a buildable
# Lean project (an ancestor directory contains lakefile.lean / lakefile.toml
# and the project has been built with `lake build`).

# substitute with your target path here
TARGET_FOLDER="$REPO_ROOT/ICML26_demo/lean/spec_and_proofs"
##############################################################################

# --- Activate Python environment ---
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi


PROMPT_FILE="prompts/autosearch_no_golf/main_entry.md"
RESULT_DIR="results/autosearch_nogolf_$(date +%Y%m%d_%H%M%S)"
MAX_ROUNDS=10

echo "========================================"
echo "Mode                : NO-GOLF (default)"
echo "Target folder       : $TARGET_FOLDER"
echo "Prompt              : $PROMPT_FILE"
echo "Result dir          : $RESULT_DIR"
echo "Max rounds          : $MAX_ROUNDS"
echo "REFERENCE_RESOURCES : $REFERENCE_RESOURCES"
echo "CLI log             : $RESULT_DIR/<task_id>/cli.log  (runner sets CLI_LOG_PATH per-task)"
echo "========================================"

python -m scripts.run_claude from-folder "$TARGET_FOLDER" \
    --prompt-file "$PROMPT_FILE" \
    --max-rounds "$MAX_ROUNDS" \
    --result-dir "$RESULT_DIR"

echo ""
echo "Done. Results under: $RESULT_DIR"

#!/bin/bash
# ==============================================================================
# test_patch_validation.sh
# ==============================================================================
# Automates the end-to-end proof:
#   1. Runs MiniAOD -> NanoAOD with UNPATCHED CMSSW_15_0_2 (Baseline).
#   2. Runs MiniAOD -> NanoAOD with PATCHED CMSSW_15_0_2 (HWJ Fix).
#   3. Executes compare_htxs_results.py to produce the side-by-side report.
#
# Examples:
#   # Dry run (generate configurations without executing heavy cmsRun):
#   ./validation/test_patch_validation.sh --no-exec
#
#   # Run 50 events on real 2024 MiniAOD:
#   ./validation/test_patch_validation.sh --events 50
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_DIR"

EVENTS=50
NO_EXEC=0
TEST_MINIAOD="root://cms-xrd-global.cern.ch///store/mc/RunIII2024Summer24MiniAODv6/WplusH-WtoLNu-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/MINIAODSIM/150X_mcRun3_2024_realistic_v2-v2/2560000/83f664c1-9c57-4032-b004-19aabb01f466.root"

print_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --input, -i       Path or LFN of test MiniAOD file"
    echo "  --events, -n      Number of events to test (default: 50)"
    echo "  --no-exec         Generate python configs only; do not run cmsRun"
    echo "  --help, -h        Show this help message"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input|-i)
            TEST_MINIAOD="$2"; shift 2 ;;
        --events|-n)
            EVENTS="$2"; shift 2 ;;
        --no-exec)
            NO_EXEC=1; shift ;;
        --help|-h)
            print_help ;;
        *)
            echo "Unknown option: $1" >&2
            print_help ;;
    esac
done

UNPATCHED_OUT="$REPO_DIR/validation/nano_unpatched.root"
PATCHED_OUT="$REPO_DIR/validation/nano_patched.root"

NO_EXEC_FLAG=""
if [ "$NO_EXEC" -eq 1 ]; then
    NO_EXEC_FLAG="--no-exec"
fi

echo "========================================================================"
echo " Starting Automated Patch Validation Workflow"
echo "========================================================================"
echo " Test MiniAOD: $TEST_MINIAOD"
echo " Events:       $EVENTS"
echo " Dry Run:      $([ "$NO_EXEC" -eq 1 ] && echo 'YES' || echo 'NO')"
echo "========================================================================"

# Step 1: Unpatched Run
echo ""
echo ">>> [STAGE 1/3] Generating UNPATCHED NanoAOD (Baseline)..."
./scripts/run_mini_to_nano.sh \
    --input "$TEST_MINIAOD" \
    --output "$UNPATCHED_OUT" \
    --events "$EVENTS" \
    $NO_EXEC_FLAG

# Step 2: Patched Run
echo ""
echo ">>> [STAGE 2/3] Generating PATCHED NanoAOD (with HWJ Fix)..."
./scripts/run_mini_to_nano.sh \
    --input "$TEST_MINIAOD" \
    --output "$PATCHED_OUT" \
    --events "$EVENTS" \
    --apply-patch \
    $NO_EXEC_FLAG

# Step 3: Comparison
if [ "$NO_EXEC" -eq 0 ]; then
    echo ""
    echo ">>> [STAGE 3/3] Running Side-by-Side Comparison & Benchmark..."
    python3 "$REPO_DIR/validation/compare_htxs_results.py" \
        --unpatched "$UNPATCHED_OUT" \
        --patched "$PATCHED_OUT" \
        --entries "$EVENTS"
else
    echo ""
    echo "[INFO] Dry run complete. Both unpatched and patched cmsDriver configs are generated."
    echo "       To run full comparison: ./validation/test_patch_validation.sh --events 50"
fi

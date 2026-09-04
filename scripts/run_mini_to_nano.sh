#!/bin/bash
# ==============================================================================
# run_mini_to_nano.sh
# ==============================================================================
# Standalone, modular driver for the MiniAOD -> NanoAODv15 step in Run 3 (2024).
# Supports both:
#   1. Baseline / unpatched production (demonstrating the WH HTXS bug).
#   2. Patched production (compiling the HTXSRivetProducer fix with scram b).
#
# Examples:
#   # 1. Dry run: generate cmsDriver python config without executing
#   ./scripts/run_mini_to_nano.sh --input /path/to/miniaod.root --no-exec
#
#   # 2. Run 200 events with the patch applied:
#   ./scripts/run_mini_to_nano.sh --input /path/to/miniaod.root --events 200 --apply-patch --output nano_patched.root
#
#   # 3. Run directly from CMS remote XRootD redirector:
#   ./scripts/run_mini_to_nano.sh --input "root://cms-xrd-global.cern.ch///store/mc/RunIII2024Summer24MiniAODv6/.../sample.root" --events 100
# ==============================================================================

set -e

# Default parameters (from McM HIG-RunIII2024Summer24NanoAODv15-00064)
CMSSW_RELEASE="CMSSW_15_0_2"
CONDITIONS="150X_mcRun3_2024_realistic_v2"
ERA="Run3_2024"
DATATIER="NANOAODSIM"
EVENTCONTENT="NANOAODSIM"
EVENTS=100
THREADS=4
APPLY_PATCH=0
NO_EXEC=0
INPUT_FILE=""
OUTPUT_FILE=""
WORK_DIR="$(pwd)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PATCH_FILE="$REPO_DIR/patches/cmssw_htxs_hwj.patch"

# ------------------------------------------------------------------------------
# Argument Parsing
# ------------------------------------------------------------------------------
print_help() {
    echo "Usage: $0 --input <FILE|LFN> [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --input, -i       Input MiniAOD file path (local, root://..., or LFN /store/...)"
    echo "  --output, -o      Output NanoAOD file path (default: nanoaod_out.root)"
    echo "  --events, -n      Number of events to process (default: 100, -1 for all)"
    echo "  --threads, -t     Number of CPU threads (default: 4)"
    echo "  --apply-patch     Apply HTXSRivetProducer patch and recompile with scram b"
    echo "  --cmssw           CMSSW release to use (default: CMSSW_15_0_2)"
    echo "  --conditions      Global tag conditions (default: 150X_mcRun3_2024_realistic_v2)"
    echo "  --no-exec         Generate python config only; do not run cmsRun"
    echo "  --help, -h        Show this help message"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input|-i)
            INPUT_FILE="$2"; shift 2 ;;
        --output|-o)
            OUTPUT_FILE="$2"; shift 2 ;;
        --events|-n)
            EVENTS="$2"; shift 2 ;;
        --threads|-t)
            THREADS="$2"; shift 2 ;;
        --apply-patch)
            APPLY_PATCH=1; shift ;;
        --cmssw)
            CMSSW_RELEASE="$2"; shift 2 ;;
        --conditions)
            CONDITIONS="$2"; shift 2 ;;
        --no-exec)
            NO_EXEC=1; shift ;;
        --help|-h)
            print_help ;;
        *)
            echo "Unknown argument: $1" >&2
            print_help ;;
    esac
done

if [ -z "$INPUT_FILE" ]; then
    echo "[ERROR] Missing required --input argument." >&2
    print_help
fi

# Set default output name if omitted
if [ -z "$OUTPUT_FILE" ]; then
    if [ "$APPLY_PATCH" -eq 1 ]; then
        OUTPUT_FILE="nanoaod_2024_patched.root"
    else
        OUTPUT_FILE="nanoaod_2024_unpatched.root"
    fi
fi

# Format input file: add XRootD prefix if given a bare /store/... LFN
if [[ "$INPUT_FILE" == /store/* ]]; then
    INPUT_FILE="root://cms-xrd-global.cern.ch//$INPUT_FILE"
fi

# ------------------------------------------------------------------------------
# 1. Environment Setup
# ------------------------------------------------------------------------------
echo "========================================================================"
echo " Starting MiniAOD -> NanoAODv15 Production"
echo "========================================================================"
echo " CMSSW Release: $CMSSW_RELEASE"
echo " Conditions:    $CONDITIONS"
echo " Era:           $ERA"
echo " Events:        $EVENTS"
echo " Threads:       $THREADS"
echo " Apply Patch:   $([ "$APPLY_PATCH" -eq 1 ] && echo 'YES (HWJ Fix)' || echo 'NO (Baseline)')"
echo " Input File:    $INPUT_FILE"
echo " Output File:   $OUTPUT_FILE"
echo "========================================================================"

# Check grid proxy if using remote XRootD
if [[ "$INPUT_FILE" == root://* ]] || [[ "$INPUT_FILE" == *cern.ch* ]]; then
    if [ -z "$X509_USER_PROXY" ] || [ ! -f "$X509_USER_PROXY" ]; then
        DEFAULT_PROXY="/tmp/x509up_u$(id -u)"
        if [ -f "$DEFAULT_PROXY" ]; then
            export X509_USER_PROXY="$DEFAULT_PROXY"
        fi
    fi
    if [ -n "$X509_USER_PROXY" ] && [ -f "$X509_USER_PROXY" ]; then
        echo "[INFO] Using Grid Proxy: $X509_USER_PROXY"
    else
        echo "[WARNING] Accessing remote XRootD file without active X509_USER_PROXY. Run 'voms-proxy-init -voms cms' if authorization fails."
    fi
fi

# Source setup helper
source "$SCRIPT_DIR/setup_cmssw_env.sh" "$CMSSW_RELEASE" "$WORK_DIR"

CMSSW_SRC="$CMSSW_BASE/src"
cd "$CMSSW_SRC"

# ------------------------------------------------------------------------------
# 2. Patching and Local Compilation (Optional)
# ------------------------------------------------------------------------------
if [ "$APPLY_PATCH" -eq 1 ]; then
    echo "[INFO] Checking out GeneratorInterface/RivetInterface..."
    if [ ! -d "GeneratorInterface/RivetInterface" ]; then
        git cms-addpkg GeneratorInterface/RivetInterface
    fi

    TARGET_CC="$CMSSW_SRC/GeneratorInterface/RivetInterface/plugins/HTXSRivetProducer.cc"
    if grep -q 'line.find("HWJ")' "$TARGET_CC" 2>/dev/null; then
        echo "[INFO] Patch is already applied to HTXSRivetProducer.cc."
    else
        echo "[INFO] Applying patch: $PATCH_FILE"
        if [ -f "$PATCH_FILE" ]; then
            patch -p1 -N < "$PATCH_FILE" || {
                echo "[WARNING] Patch utility returned non-zero. Verifying if changes were already present..."
                grep -q 'line.find("HWJ")' "$TARGET_CC" || { echo "[ERROR] Patch failed to apply!"; exit 1; }
            }
        else
            echo "[ERROR] Patch file not found at $PATCH_FILE!"
            exit 1
        fi
    fi

    echo "[INFO] Compiling patched package with scram b -j $THREADS..."
    scram b -j "$THREADS" || { echo "[ERROR] scram b compilation failed!"; exit 1; }
    echo "[INFO] Compilation successful."
fi

# ------------------------------------------------------------------------------
# 3. Generate cmsDriver Python Configuration
# ------------------------------------------------------------------------------
OUT_BASENAME="$(basename "$OUTPUT_FILE" .root)"
CONFIG_PY="nano_step_${OUT_BASENAME}_cfg.py"
REPORT_XML="nano_step_${OUT_BASENAME}_report.xml"

echo "[INFO] Generating cmsDriver configuration: $CONFIG_PY"


# Exact configuration matched to McM HIG-RunIII2024Summer24NanoAODv15-00064
cmsDriver.py step_nano \
    --scenario pp \
    --era "$ERA" \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --step NANO \
    --conditions "$CONDITIONS" \
    --datatier "$DATATIER" \
    --eventcontent "$EVENTCONTENT" \
    --python_filename "$CONFIG_PY" \
    --fileout "file:$OUTPUT_FILE" \
    --filein "$INPUT_FILE" \
    --number "$EVENTS" \
    --nThreads "$THREADS" \
    --no_exec \
    --mc

echo "[INFO] Generated configuration: $CONFIG_PY"

# ------------------------------------------------------------------------------
# 4. Execution
# ------------------------------------------------------------------------------
if [ "$NO_EXEC" -eq 1 ]; then
    echo "[INFO] --no-exec flag was passed. Halting before cmsRun execution."
    echo "[INFO] To run manually:"
    echo "       cd $CMSSW_SRC && eval \$(scramv1 runtime -sh) && cmsRun $CONFIG_PY"
    exit 0
fi

echo "[INFO] Executing cmsRun $CONFIG_PY..."
START_TIME=$(date +%s)

cmsRun -e -j "$REPORT_XML" "$CONFIG_PY"

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "========================================================================"
echo " MiniAOD -> NanoAOD Step Completed Successfully in ${ELAPSED}s"
echo " Output File: $OUTPUT_FILE"
echo " Report XML:  $REPORT_XML"
echo "========================================================================"

# Quick check on generated file if inspect_nanov15_htxs.py is available
if [ -f "$REPO_DIR/inspect_nanov15_htxs.py" ]; then
    echo "[INFO] Running quick HTXS branch inspection on output file..."
    python3 "$REPO_DIR/inspect_nanov15_htxs.py" --file "$OUTPUT_FILE" --entries 3 --verbose 2>/dev/null || true
fi


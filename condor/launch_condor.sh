#!/bin/bash
# ==============================================================================
# launch_condor.sh
# ==============================================================================
# User-friendly launcher for HTCondor jobs on lxplus.
# Validates proxy, prepares directories, and submits jobs.
#
# Examples:
#   ./condor/launch_condor.sh --dry-run
#   ./condor/launch_condor.sh --mode mini2nano --input-file "root://cms-xrd-global.cern.ch//..." --njobs 10
#   ./condor/launch_condor.sh --mode fullchain --njobs 5 --events 200
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_DIR"

MODE="mini2nano"
NJOBS=1
EVENTS=200
DRY_RUN=0
INPUT_FILE=""
EOS_DIR=""

print_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --mode            Job mode: 'mini2nano' or 'fullchain' (default: mini2nano)"
    echo "  --njobs, -n       Number of parallel jobs to queue (default: 1)"
    echo "  --events, -e      Number of events per job (default: 200)"
    echo "  --input-file, -i  Input MiniAOD file/LFN (required for mini2nano)"
    echo "  --eos-dir, -o     Target EOS output directory"
    echo "  --dry-run         Prepare proxy and submit files, but do not invoke condor_submit"
    echo "  --help, -h        Show this help message"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            MODE="$2"; shift 2 ;;
        --njobs|-n)
            NJOBS="$2"; shift 2 ;;
        --events|-e)
            EVENTS="$2"; shift 2 ;;
        --input-file|-i)
            INPUT_FILE="$2"; shift 2 ;;
        --eos-dir|-o)
            EOS_DIR="$2"; shift 2 ;;
        --dry-run)
            DRY_RUN=1; shift ;;
        --help|-h)
            print_help ;;
        *)
            echo "Unknown option: $1" >&2
            print_help ;;
    esac
done

# Ensure logs directory exists
mkdir -p logs

# Proxy validation and copy
echo "[launch_condor] Checking X.509 grid proxy..."
PROXY_SRC="$X509_USER_PROXY"
if [ -z "$PROXY_SRC" ] || [ ! -f "$PROXY_SRC" ]; then
    DEFAULT_PROXY="/tmp/x509up_u$(id -u)"
    if [ -f "$DEFAULT_PROXY" ]; then
        PROXY_SRC="$DEFAULT_PROXY"
    else
        PROXY_SRC=$(voms-proxy-info -path 2>/dev/null || true)
    fi
fi

if [ -z "$PROXY_SRC" ] || [ ! -f "$PROXY_SRC" ]; then
    echo "[ERROR] No valid grid proxy found. Please run 'voms-proxy-init -voms cms' first." >&2
    exit 1
fi

TIMELEFT=$(voms-proxy-info -file "$PROXY_SRC" -timeleft 2>/dev/null || echo 0)
if [ "$TIMELEFT" -lt 3600 ]; then
    echo "[WARNING] Grid proxy has less than 1 hour remaining ($TIMELEFT seconds). Consider renewing."
fi

cp "$PROXY_SRC" condor/x509up
chmod 600 condor/x509up
echo "[launch_condor] Active proxy copied to condor/x509up."

chmod +x condor/*.sh
chmod +x scripts/*.sh

# Determine submit file
if [ "$MODE" == "mini2nano" ]; then
    SUB_FILE="condor/submit_mini_to_nano.sub"
    APPEND_ARGS=""
    if [ -n "$INPUT_FILE" ]; then
        APPEND_ARGS="$APPEND_ARGS -append InputFile=$INPUT_FILE"
    else
        echo "[WARNING] No --input-file specified. Submitting with default test sample in submit file."
    fi
elif [ "$MODE" == "fullchain" ]; then
    SUB_FILE="condor/submit_full_chain_2024.sub"
    APPEND_ARGS=""
else
    echo "[ERROR] Unknown mode: $MODE (must be 'mini2nano' or 'fullchain')" >&2
    exit 1
fi

if [ -n "$EOS_DIR" ]; then
    APPEND_ARGS="$APPEND_ARGS -append EosDir=$EOS_DIR"
fi
APPEND_ARGS="$APPEND_ARGS -append Events=$EVENTS"

echo "========================================================================"
echo " HTCondor Submission Preparation"
echo "========================================================================"
echo " Mode:        $MODE"
echo " Submit File: $SUB_FILE"
echo " Jobs Queue:  $NJOBS"
echo " Events/Job:  $EVENTS"
echo " Dry Run:     $([ "$DRY_RUN" -eq 1 ] && echo 'YES' || echo 'NO')"
echo "========================================================================"

SUBMIT_CMD="condor_submit $SUB_FILE $APPEND_ARGS -queue $NJOBS"

if [ "$DRY_RUN" -eq 1 ]; then
    echo "[INFO] Dry run requested. Command to execute:"
    echo "       $SUBMIT_CMD"
    exit 0
fi

echo "[INFO] Executing: $SUBMIT_CMD"
eval "$SUBMIT_CMD"
echo "[INFO] Jobs submitted successfully. Monitor status with 'condor_q'."

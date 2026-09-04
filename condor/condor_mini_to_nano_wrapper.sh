#!/bin/bash
# ==============================================================================
# condor_mini_to_nano_wrapper.sh
# ==============================================================================
# HTCondor execution wrapper for MiniAOD -> NanoAOD step on lxplus.
# Arguments:
#   $1: Proxy file name (x509up)
#   $2: Cluster ID
#   $3: Process ID
#   $4: Input MiniAOD file (path or LFN)
#   $5: Target EOS output directory
#   $6: Apply patch flag (1 or 0)
#   $7: Events per job (default: 500)
# ==============================================================================

set -e

PROXY_FILE=$1
CLUSTER=$2
PROCESS=$3
INPUT_FILE=$4
EOS_DIR=$5
APPLY_PATCH=${6:-0}
EVENTS=${7:-500}
SAMPLE_TAG=${8:-"sample"}

echo "[CONDOR WORKER] Starting MiniAOD -> NanoAOD Job: Cluster $CLUSTER, Process $PROCESS ($SAMPLE_TAG)"
echo "[CONDOR WORKER] Hostname: $(hostname)"
echo "[CONDOR WORKER] Timestamp: $(date)"

# Grid proxy setup
export X509_USER_PROXY="$(pwd)/$PROXY_FILE"
if [ -f "$X509_USER_PROXY" ]; then
    voms-proxy-info -file "$X509_USER_PROXY"
else
    echo "[WARNING] Proxy file $X509_USER_PROXY not found!"
fi

chmod +x scripts/run_mini_to_nano.sh
chmod +x scripts/setup_cmssw_env.sh

PATCH_ARG=""
if [ "$APPLY_PATCH" -eq 1 ]; then
    PATCH_ARG="--apply-patch"
fi

OUT_LOCAL="$(pwd)/nanoaod_${SAMPLE_TAG}_job${PROCESS}.root"

./scripts/run_mini_to_nano.sh \
    --input "$INPUT_FILE" \
    --output "$OUT_LOCAL" \
    --events "$EVENTS" \
    --threads 4 \
    $PATCH_ARG

# Fallback check if output was placed inside CMSSW_15_0_2/src
if [ ! -f "$OUT_LOCAL" ]; then
    CANDIDATE="$(pwd)/CMSSW_15_0_2/src/nanoaod_${SAMPLE_TAG}_job${PROCESS}.root"
    if [ -f "$CANDIDATE" ]; then
        OUT_LOCAL="$CANDIDATE"
    fi
fi

# Transfer to target EOS directory
if [ -n "$EOS_DIR" ] && [ -f "$OUT_LOCAL" ]; then

    TARGET_NAME="NanoAODv15_${SAMPLE_TAG}_job${PROCESS}.root"
    FINAL_DEST="${EOS_DIR}/${TARGET_NAME}"
    echo "[CONDOR WORKER] Staging output to EOS: $FINAL_DEST"
    mkdir -p "$EOS_DIR" 2>/dev/null || true
    if [[ "$EOS_DIR" == /eos/user/* ]] || [[ "$EOS_DIR" == /eos/cms/* ]]; then
        xrdcp -f "$OUT_LOCAL" "root://eosuser.cern.ch//$FINAL_DEST" || cp "$OUT_LOCAL" "$FINAL_DEST"
    else
        cp "$OUT_LOCAL" "$FINAL_DEST"
    fi
    rm -f "$OUT_LOCAL"
    echo "[CONDOR WORKER] Transfer complete."
fi


echo "[CONDOR WORKER] Finished successfully at $(date)."


#!/bin/bash
# ==============================================================================
# condor_full_chain_wrapper.sh
# ==============================================================================
# HTCondor execution wrapper for Full 2024 Generation Chain (Gridpack -> NanoAOD).
# Arguments:
#   $1: Proxy file name (x509up)
#   $2: Cluster ID
#   $3: Process ID
#   $4: Fragment path
#   $5: Target EOS output directory
#   $6: Apply patch flag (1 or 0)
#   $7: Events per job (default: 200)
# ==============================================================================

set -e

PROXY_FILE=$1
CLUSTER=$2
PROCESS=$3
FRAGMENT_PATH=$4
EOS_DIR=$5
APPLY_PATCH=${6:-1}
EVENTS=${7:-200}

echo "[CONDOR WORKER] Starting Full Chain 2024 Job: Cluster $CLUSTER, Process $PROCESS"
echo "[CONDOR WORKER] Hostname: $(hostname)"
echo "[CONDOR WORKER] Timestamp: $(date)"

export X509_USER_PROXY="$(pwd)/$PROXY_FILE"
if [ -f "$X509_USER_PROXY" ]; then
    voms-proxy-info -file "$X509_USER_PROXY"
fi

chmod +x scripts/run_full_chain_2024.sh
chmod +x scripts/run_mini_to_nano.sh

# Compute unique random seed per Condor job
JOB_SEED=$((CLUSTER * 1000 + PROCESS + 1))

LOCAL_OUT_DIR="$(pwd)/output_job_${CLUSTER}_${PROCESS}"
mkdir -p "$LOCAL_OUT_DIR"

PATCH_ARG=""
if [ "$APPLY_PATCH" -eq 1 ]; then
    PATCH_ARG="--apply-patch"
fi

./scripts/run_full_chain_2024.sh \
    --fragment "$FRAGMENT_PATH" \
    --events "$EVENTS" \
    --seed "$JOB_SEED" \
    --threads 4 \
    --output-dir "$LOCAL_OUT_DIR" \
    $PATCH_ARG

# Copy final NanoAOD (and MiniAOD) to EOS
if [ -n "$EOS_DIR" ]; then
    mkdir -p "$EOS_DIR"
    FINAL_NANO="$LOCAL_OUT_DIR/final_NANOAODSIM.root"
    if [ -f "$FINAL_NANO" ]; then
        DEST="${EOS_DIR}/nanoaod_2024_seed${JOB_SEED}_${CLUSTER}_${PROCESS}.root"
        echo "[CONDOR WORKER] Transferring NanoAOD to $DEST..."
        cp "$FINAL_NANO" "$DEST"
    fi
    FINAL_MINI="$LOCAL_OUT_DIR/step3_MINIAODSIM.root"
    if [ -f "$FINAL_MINI" ]; then
        DEST_MINI="${EOS_DIR}/miniaod_2024_seed${JOB_SEED}_${CLUSTER}_${PROCESS}.root"
        echo "[CONDOR WORKER] Transferring MiniAOD to $DEST_MINI..."
        cp "$FINAL_MINI" "$DEST_MINI"
    fi
fi

# Clean local scratch
rm -rf "$LOCAL_OUT_DIR"
echo "[CONDOR WORKER] Finished job at $(date)."

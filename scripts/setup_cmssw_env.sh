#!/bin/bash
# ==============================================================================
# setup_cmssw_env.sh
# ==============================================================================
# Helper to set up or bootstrap a CMSSW release area on lxplus.
# Default architecture: el9_amd64_gcc12 (RHEL9 native).
#
# Usage:
#   source scripts/setup_cmssw_env.sh [CMSSW_RELEASE] [BASE_DIR]
# Example:
#   source scripts/setup_cmssw_env.sh CMSSW_15_0_2
# ==============================================================================

RELEASE=${1:-"CMSSW_15_0_2"}
BASE_DIR=${2:-$(pwd)}
SCRAM_ARCH_DEFAULT="el9_amd64_gcc12"

# Detect OS and set SCRAM_ARCH
if grep -q "release 9" /etc/redhat-release 2>/dev/null; then
    export SCRAM_ARCH=${SCRAM_ARCH:-$SCRAM_ARCH_DEFAULT}
elif grep -q "release 8" /etc/redhat-release 2>/dev/null; then
    export SCRAM_ARCH="el8_amd64_gcc12"
else
    export SCRAM_ARCH=${SCRAM_ARCH:-$SCRAM_ARCH_DEFAULT}
fi

echo "[setup_cmssw_env] SCRAM_ARCH: $SCRAM_ARCH"
echo "[setup_cmssw_env] Initializing CVMFS environment..."

source /cvmfs/cms.cern.ch/cmsset_default.sh

cd "$BASE_DIR" || exit 1

if [ -d "$RELEASE/.SCRAM" ]; then
    echo "[setup_cmssw_env] Found existing area: $BASE_DIR/$RELEASE"

else
    echo "[setup_cmssw_env] Creating new project: $RELEASE under $BASE_DIR"
    scram project CMSSW "$RELEASE" || {
        echo "[ERROR] Failed to create CMSSW project $RELEASE. Check release availability on CVMFS."
        return 1 2>/dev/null || exit 1
    }
fi

cd "$BASE_DIR/$RELEASE/src" || exit 1
eval "$(scramv1 runtime -sh)"

echo "[setup_cmssw_env] CMSSW_BASE: $CMSSW_BASE"
echo "[setup_cmssw_env] Ready."

#!/bin/bash
# ==============================================================================
# run_full_chain_2024.sh
# ==============================================================================
# Full 4-step generation chain for CMS Run 3 (2024) NanoAODv15:
#   Step 1: wmLHEGS  (CMSSW_14_0_19) -> GEN-SIM,LHE.root
#   Step 2: DRPremix (CMSSW_14_0_20) -> AODSIM.root
#   Step 3: MiniAODv6(CMSSW_15_0_2)  -> MINIAODSIM.root
#   Step 4: NanoAODv15(CMSSW_15_0_2) -> NANOAODSIM.root (with optional patch)
#
# Matched to official McM Chained Request:
#   HIG-chain_RunIII2024Summer24wmLHEGS_flowRunIII2024Summer24DRPremix_flowRunIII2024Summer24MiniAODv6_flowRunIII2024Summer24NanoAODv15-00064
#
# Examples:
#   # 1. Dry run: generate all configurations without running simulation:
#   ./scripts/run_full_chain_2024.sh --no-exec
#
#   # 2. Generate 100 events end-to-end with the HTXS patch:
#   ./scripts/run_full_chain_2024.sh --events 100 --seed 42 --apply-patch --output-dir ./output_2024
# ==============================================================================

set -e

# Default settings
EVENTS=100
SEED=$(($(date +%s) % 10000 + RANDOM + 1))
THREADS=4
APPLY_PATCH=0
CLEAN_INTERMEDIATES=1
NO_EXEC=0
OUTPUT_DIR="$(pwd)/output_2024"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

FRAGMENT_FILE="$REPO_DIR/configs/fragments/WplusH_Hto2B_WtoLNu_13p6TeV_powhegMINLO_fragment.py"
PREMIX_DATASET="dbs:/Neutrino_E-10_gun/RunIIISummer24PrePremix-Premixlib2024_140X_mcRun3_2024_realistic_v26-v1/PREMIX"

# CMSSW Releases (from McM)
REL_STEP1="CMSSW_14_0_19"
COND_STEP1="140X_mcRun3_2024_realistic_v26"

REL_STEP2="CMSSW_14_0_20"
COND_STEP2="140X_mcRun3_2024_realistic_v26"

REL_STEP3="CMSSW_15_0_2"
COND_STEP3="150X_mcRun3_2024_realistic_v2"

REL_STEP4="CMSSW_15_0_2"
COND_STEP4="150X_mcRun3_2024_realistic_v2"

print_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --fragment, -f      Path to generator fragment (default: 2024 WplusH fragment)"
    echo "  --events, -n        Number of events to generate (default: 100)"
    echo "  --seed, -s          Random seed for LHE/Pythia (default: dynamic)"
    echo "  --threads, -t       Number of CPU threads (default: 4)"
    echo "  --output-dir, -o    Directory to store output files (default: ./output_2024)"
    echo "  --apply-patch       Apply HTXSRivetProducer patch in Step 4"
    echo "  --keep-all          Do not delete intermediate large files (GEN-SIM, PREMIX, AOD)"
    echo "  --no-exec           Generate cmsDriver configurations only; do not run cmsRun"
    echo "  --help, -h          Show this help message"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fragment|-f)
            FRAGMENT_FILE="$2"; shift 2 ;;
        --events|-n)
            EVENTS="$2"; shift 2 ;;
        --seed|-s)
            SEED="$2"; shift 2 ;;
        --threads|-t)
            THREADS="$2"; shift 2 ;;
        --output-dir|-o)
            OUTPUT_DIR="$2"; shift 2 ;;
        --apply-patch)
            APPLY_PATCH=1; shift ;;
        --keep-all)
            CLEAN_INTERMEDIATES=0; shift ;;
        --no-exec)
            NO_EXEC=1; shift ;;
        --help|-h)
            print_help ;;
        *)
            echo "Unknown argument: $1" >&2
            print_help ;;
    esac
done

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
WORK_DIR="$OUTPUT_DIR/work"
mkdir -p "$WORK_DIR"

echo "========================================================================"
echo " 2024 Full Generation Chain: Gridpack -> NanoAODv15"
echo "========================================================================"
echo " Fragment:            $FRAGMENT_FILE"
echo " Events:              $EVENTS"
echo " Random Seed:         $SEED"
echo " Output Directory:    $OUTPUT_DIR"
echo " Apply HTXS Patch:    $([ "$APPLY_PATCH" -eq 1 ] && echo 'YES' || echo 'NO')"
echo " Clean Intermediates: $([ "$CLEAN_INTERMEDIATES" -eq 1 ] && echo 'YES' || echo 'NO')"
echo "========================================================================"

# Check fragment existence
if [ ! -f "$FRAGMENT_FILE" ]; then
    echo "[ERROR] Generator fragment not found at: $FRAGMENT_FILE" >&2
    exit 1
fi

# ------------------------------------------------------------------------------
# STEP 1: wmLHEGS (LHE, GEN, SIM)
# ------------------------------------------------------------------------------
echo ""
echo ">>> [STEP 1/4] Starting wmLHEGS in $REL_STEP1..."
source "$SCRIPT_DIR/setup_cmssw_env.sh" "$REL_STEP1" "$WORK_DIR"

# Copy fragment into CMSSW Configuration/GenProduction/python
mkdir -p "$CMSSW_BASE/src/Configuration/GenProduction/python"
FRAGMENT_NAME=$(basename "$FRAGMENT_FILE")
cp "$FRAGMENT_FILE" "$CMSSW_BASE/src/Configuration/GenProduction/python/$FRAGMENT_NAME"
cd "$CMSSW_BASE/src"
scram b -j "$THREADS"

STEP1_OUT="$OUTPUT_DIR/step1_GENSIM.root"
STEP1_CFG="$OUTPUT_DIR/step1_wmLHEGS_cfg.py"

cmsDriver.py Configuration/GenProduction/python/"$FRAGMENT_NAME" \
    --era Run3_2024 \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --beamspot DBrealistic \
    --step LHE,GEN,SIM \
    --geometry DB:Extended \
    --conditions "$COND_STEP1" \
    --customise_commands "process.RandomNumberGeneratorService.externalLHEProducer.initialSeed=int(${SEED})\nprocess.source.numberEventsInLuminosityBlock=cms.untracked.uint32(100)" \
    --datatier GEN-SIM,LHE \
    --eventcontent RAWSIM,LHE \
    --python_filename "$STEP1_CFG" \
    --fileout "file:$STEP1_OUT" \
    --number "$EVENTS" \
    --nThreads "$THREADS" \
    --no_exec \
    --mc

if [ "$NO_EXEC" -eq 0 ]; then
    echo "[INFO] Running cmsRun for Step 1..."
    cmsRun -e -j "$OUTPUT_DIR/step1_report.xml" "$STEP1_CFG"
fi

# ------------------------------------------------------------------------------
# STEP 2: DRPremix (DIGI, DATAMIX, L1, DIGI2RAW, HLT -> RECO -> AODSIM)
# ------------------------------------------------------------------------------
echo ""
echo ">>> [STEP 2/4] Starting DRPremix in $REL_STEP2..."
source "$SCRIPT_DIR/setup_cmssw_env.sh" "$REL_STEP2" "$WORK_DIR"
cd "$CMSSW_BASE/src"

STEP2_PREMIX_OUT="$OUTPUT_DIR/step2_PREMIXRAW.root"
STEP2_AOD_OUT="$OUTPUT_DIR/step2_AODSIM.root"
STEP2_CFG1="$OUTPUT_DIR/step2_DRPremix_seq1_cfg.py"
STEP2_CFG2="$OUTPUT_DIR/step2_DRPremix_seq2_cfg.py"

# Sequence 1: Premix DIGI + HLT
cmsDriver.py step2_seq1 \
    --era Run3_2024 \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --procModifiers premix_stage2 \
    --datamix PreMix \
    --step DIGI,DATAMIX,L1,DIGI2RAW,HLT:2024v14 \
    --geometry DB:Extended \
    --conditions "$COND_STEP2" \
    --datatier GEN-SIM-RAW \
    --eventcontent PREMIXRAW \
    --python_filename "$STEP2_CFG1" \
    --fileout "file:$STEP2_PREMIX_OUT" \
    --filein "file:$STEP1_OUT" \
    --number "$EVENTS" \
    --nThreads "$THREADS" \
    --pileup_input "$PREMIX_DATASET" \
    --no_exec \
    --mc

# Sequence 2: Reconstruction to AODSIM
cmsDriver.py step2_seq2 \
    --era Run3_2024 \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --step RAW2DIGI,L1Reco,RECO,RECOSIM \
    --geometry DB:Extended \
    --conditions "$COND_STEP2" \
    --datatier AODSIM \
    --eventcontent AODSIM \
    --python_filename "$STEP2_CFG2" \
    --fileout "file:$STEP2_AOD_OUT" \
    --filein "file:$STEP2_PREMIX_OUT" \
    --number "$EVENTS" \
    --nThreads "$THREADS" \
    --no_exec \
    --mc

if [ "$NO_EXEC" -eq 0 ]; then
    echo "[INFO] Running cmsRun for Step 2 (Sequence 1: DIGI/HLT)..."
    cmsRun -e -j "$OUTPUT_DIR/step2_seq1_report.xml" "$STEP2_CFG1"
    echo "[INFO] Running cmsRun for Step 2 (Sequence 2: RECO/AOD)..."
    cmsRun -e -j "$OUTPUT_DIR/step2_seq2_report.xml" "$STEP2_CFG2"
fi

# ------------------------------------------------------------------------------
# STEP 3: MiniAODv6 (PAT)
# ------------------------------------------------------------------------------
echo ""
echo ">>> [STEP 3/4] Starting MiniAODv6 in $REL_STEP3..."
source "$SCRIPT_DIR/setup_cmssw_env.sh" "$REL_STEP3" "$WORK_DIR"
cd "$CMSSW_BASE/src"

STEP3_OUT="$OUTPUT_DIR/step3_MINIAODSIM.root"
STEP3_CFG="$OUTPUT_DIR/step3_MiniAODv6_cfg.py"

cmsDriver.py step3_pat \
    --era Run3_2024 \
    --customise Configuration/DataProcessing/Utils.addMonitoring \
    --step PAT \
    --geometry DB:Extended \
    --conditions "$COND_STEP3" \
    --datatier MINIAODSIM \
    --eventcontent MINIAODSIM1 \
    --python_filename "$STEP3_CFG" \
    --fileout "file:$STEP3_OUT" \
    --filein "file:$STEP2_AOD_OUT" \
    --number "$EVENTS" \
    --nThreads "$THREADS" \
    --no_exec \
    --mc

if [ "$NO_EXEC" -eq 0 ]; then
    echo "[INFO] Running cmsRun for Step 3 (MiniAOD)..."
    cmsRun -e -j "$OUTPUT_DIR/step3_report.xml" "$STEP3_CFG"
fi

# ------------------------------------------------------------------------------
# STEP 4: NanoAODv15 (NANO)
# ------------------------------------------------------------------------------
echo ""
echo ">>> [STEP 4/4] Starting NanoAODv15 (via run_mini_to_nano.sh)..."
FINAL_NANO_OUT="$OUTPUT_DIR/final_NANOAODSIM.root"

PATCH_FLAG=""
if [ "$APPLY_PATCH" -eq 1 ]; then
    PATCH_FLAG="--apply-patch"
fi

NO_EXEC_FLAG=""
if [ "$NO_EXEC" -eq 1 ]; then
    NO_EXEC_FLAG="--no-exec"
fi

"$SCRIPT_DIR/run_mini_to_nano.sh" \
    --input "$STEP3_OUT" \
    --output "$FINAL_NANO_OUT" \
    --events "$EVENTS" \
    --threads "$THREADS" \
    --cmssw "$REL_STEP4" \
    --conditions "$COND_STEP4" \
    $PATCH_FLAG \
    $NO_EXEC_FLAG

# ------------------------------------------------------------------------------
# Optional Cleanup of Intermediate Files
# ------------------------------------------------------------------------------
if [ "$NO_EXEC" -eq 0 ] && [ "$CLEAN_INTERMEDIATES" -eq 1 ]; then
    echo "[INFO] Cleaning up intermediate large files to save disk space..."
    rm -f "$STEP1_OUT" "$STEP2_PREMIX_OUT" "$STEP2_AOD_OUT"
    echo "[INFO] Kept final MiniAOD ($STEP3_OUT) and NanoAOD ($FINAL_NANO_OUT)."
fi

echo "========================================================================"
echo " Full 2024 Simulation Chain Finished Successfully!"
echo " Final Output: $FINAL_NANO_OUT"
echo "========================================================================"

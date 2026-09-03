#!/usr/bin/env python3
"""
inspect_nanov15_htxs.py
======================
Standalone verification script to inspect HTXS (Higgs Template Cross Section)
branches in CMS Run 3 Summer24 NanoAODv15 Monte Carlo samples.

Demonstrates and verifies:
1. The missing/unpopulated HTXS sentinel problem in WH samples across various decay modes:
   - W(lnu) H(bb) [W+ and W-]
   - W(qq) H(bb)  [hadronic W]
   - W(lnu) H(cc)
   - W(lnu) H(tautau)
   - W(lnu) H(ZZ->4l)
   - W(lnu) H(WW->2l2nu)
   - W(lnu) H(mumu)
2. The working exception:
   - W(lnu) H(gamma gamma)
3. The control samples where HTXS is properly populated:
   - qq -> ZH, Z(ll) H(bb)
   - gg -> ZH, Z(ll) H(bb)

Usage:
  # Using an environment with uproot and awkward (e.g. PocketCoffea or LCG release):
  python3 inspect_nanov15_htxs.py [--entries N] [--verbose] [--process NAME]

Requires:
  - Valid grid proxy (voms-proxy-init -voms cms)
  - uproot, awkward, numpy
"""

import argparse
import sys
import numpy as np

# Sample registry: mapping from clean label to (dataset, example_file_path, category)
SAMPLES = {
    "WplusH_Hto2B_WtoLNu": {
        "title": "W+H, W->lnu, H->bb",
        "category": "WH (Signal)",
        "dataset": "/WplusH-WtoLNu-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/WplusH-WtoLNu-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/120000/07ce3cf9-a0ee-4f30-a31c-1cd00205bb77.root",
    },
    "WminusH_Hto2B_WtoLNu": {
        "title": "W-H, W->lnu, H->bb",
        "category": "WH (Signal)",
        "dataset": "/WminusH-WtoLNu-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/WminusH-WtoLNu-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/2560000/ecb24314-a6a7-4949-833f-e6d3cea38a07.root",
    },
    "WplusH_Hto2B_Wto2Q": {
        "title": "W+H, W->qq, H->bb (hadronic W)",
        "category": "WH (Decay mode scan)",
        "dataset": "/WplusH-Wto2Q-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/WplusH-Wto2Q-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/2560000/5048f06b-de47-4643-adcb-8a79bbb2daa5.root",
    },
    "WplusH_Hto2C_WtoLNu": {
        "title": "W+H, W->lnu, H->cc",
        "category": "WH (Decay mode scan)",
        "dataset": "/WplusH-WtoLNu-Hto2C_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/WplusH-WtoLNu-Hto2C_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/120000/7bf3cc1a-bf20-47ba-8426-2233abf268e3.root",
    },
    "WplusH_Hto2Tau": {
        "title": "W+H, H->tautau",
        "category": "WH (Decay mode scan)",
        "dataset": "/WplusH-Hto2TauUncorrelatedDecay_Par-M-125_TuneCP5_13p6TeV_powhegMINNLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/WplusH-Hto2TauUncorrelatedDecay_Par-M-125_TuneCP5_13p6TeV_powhegMINNLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/120000/80ca192d-aebe-47dd-921b-166ed80db5bc.root",
    },
    "WplusH_Hto2Zto4L": {
        "title": "W+H, H->ZZ->4l",
        "category": "WH (Decay mode scan)",
        "dataset": "/WplusH-Hto2Zto4L_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-jhugen-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/WplusH-Hto2Zto4L_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-jhugen-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/120000/00499adb-f282-42a8-aeab-662231976df0.root",
    },
    "WplusH_Hto2Wto2L2Nu": {
        "title": "W+H, W->lnu, H->WW->2l2nu",
        "category": "WH (Decay mode scan)",
        "dataset": "/WplusH-WtoLNu-Hto2Wto2L2Nu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-jhugen-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/WplusH-WtoLNu-Hto2Wto2L2Nu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-jhugen-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/2550000/2f66f9db-1ce0-4a2f-bbcc-6211f77898f9.root",
    },
    "WplusH_Hto2Mu": {
        "title": "W+H, H->mumu",
        "category": "WH (Decay mode scan)",
        "dataset": "/WplusH-Hto2Mu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v3/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/WplusH-Hto2Mu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v3/2810000/aab75a2d-4c20-4b8f-8021-75c2fc60b96c.root",
    },
    "WplusH_Hto2G_WtoLNu": {
        "title": "W+H, W->lnu, H->gamma gamma",
        "category": "WH (Working Exception)",
        "dataset": "/WplusH-Hto2G-WtoLNu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/WplusH-Hto2G-WtoLNu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/2550000/cc6787f6-7076-4838-90de-86cc3c5be3cf.root",
    },
    "ZH_Hto2B_Zto2L": {
        "title": "qq -> ZH, Z->ll, H->bb",
        "category": "Control (Working)",
        "dataset": "/ZH-Zto2L-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/ZH-Zto2L-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/140000/3f1aaaee-242f-44e4-a3d6-56bc2f6fb19b.root",
    },
    "ggZH_Hto2B_Zto2L": {
        "title": "gg -> ZH, Z->ll, H->bb",
        "category": "Control (Working)",
        "dataset": "/GluGluZH-Zto2L-Hto2B_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "file": "/store/mc/RunIII2024Summer24NanoAODv15/GluGluZH-Zto2L-Hto2B_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/140000/f2b12277-a685-47fb-9ada-e67a5da4c4b9.root",
    },
}

BRANCHES = [
    "HTXS_V_pt",
    "HTXS_Higgs_y",
    "HTXS_Higgs_pt",
    "HTXS_njets30",
    "HTXS_stage1_2_cat_pTjet30GeV",
    "HTXS_stage1_2_fine_cat_pTjet30GeV",
]


def check_sample(key, info, redirector, n_entries, verbose=False):
    import uproot

    # Ensure double slash for XRootD global redirectors: root://host//store/...
    base = redirector.split("//")[0] + "//" + redirector.split("//")[1].split("/")[0] + "//"
    url = base + info["file"].lstrip("/")
    result = {
        "key": key,
        "title": info["title"],
        "category": info["category"],
        "status": "UNKNOWN",
        "v_pt": None,
        "higgs_y": None,
        "higgs_pt": None,
        "njets30": None,
        "stage1_2": None,
        "error": None,
    }

    try:
        with uproot.open(url, timeout=35) as f:
            if "Events" not in f:
                result["status"] = "ERROR (No Events tree)"
                return result
            tree = f["Events"]
            avail = [b for b in BRANCHES if b in tree]
            if not avail:
                result["status"] = "ERROR (No HTXS branches)"
                return result

            arrays = tree.arrays(avail, entry_stop=n_entries)
            v_pt = arrays["HTXS_V_pt"].to_numpy() if "HTXS_V_pt" in arrays.fields else np.array([])
            higgs_y = arrays["HTXS_Higgs_y"].to_numpy() if "HTXS_Higgs_y" in arrays.fields else np.array([])
            higgs_pt = arrays["HTXS_Higgs_pt"].to_numpy() if "HTXS_Higgs_pt" in arrays.fields else np.array([])
            njets30 = arrays["HTXS_njets30"].to_numpy() if "HTXS_njets30" in arrays.fields else np.array([])
            stage1_2 = arrays["HTXS_stage1_2_cat_pTjet30GeV"].to_numpy() if "HTXS_stage1_2_cat_pTjet30GeV" in arrays.fields else np.array([])

            result["v_pt"] = v_pt
            result["higgs_y"] = higgs_y
            result["higgs_pt"] = higgs_pt
            result["njets30"] = njets30
            result["stage1_2"] = stage1_2

            # Check if values are sentinel
            is_sentinel_vpt = np.all(v_pt == 0.0)
            is_sentinel_hy = np.all(np.isnan(higgs_y) | (higgs_y == 0.0))
            is_sentinel_codes = np.all(stage1_2 == 0)

            if is_sentinel_vpt and is_sentinel_hy and is_sentinel_codes:
                result["status"] = "BROKEN (Sentinel 0 / NaN)"
            else:
                result["status"] = "POPULATED & VALID"

    except Exception as e:
        result["status"] = f"ERROR ({type(e).__name__})"
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Inspect HTXS in NanoAODv15 samples")
    parser.add_argument("--redirector", default="root://cms-xrd-global.cern.ch//", help="XRootD redirector")
    parser.add_argument("--entries", type=int, default=5, help="Number of entries to inspect per file")
    parser.add_argument("--process", choices=list(SAMPLES.keys()), default=None, help="Inspect only a specific process")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-event array values")
    args = parser.parse_args()

    try:
        import uproot
    except ImportError:
        print("Error: 'uproot' package is required. Run this script in an environment with uproot.", file=sys.stderr)
        sys.exit(1)

    samples_to_check = {args.process: SAMPLES[args.process]} if args.process else SAMPLES

    print("=" * 110)
    print("CMS Run 3 Summer24 NanoAODv15 HTXS Branch Inspection Report")
    print(f"XRootD Redirector: {args.redirector}")
    print(f"Inspecting first {args.entries} events per sample")
    print("=" * 110)
    print()

    results = []
    for key, info in samples_to_check.items():
        print(f"-> Inspecting {key} ({info['title']})...", end="", flush=True)
        res = check_sample(key, info, args.redirector, args.entries, args.verbose)
        results.append(res)
        print(f" [{res['status']}]")

    print()
    print("=" * 110)
    print(f"{'Sample Key':<24} | {'Process / Channel':<30} | {'HTXS Status':<25} | {'Stage1.2 Codes':<18}")
    print("-" * 110)
    for r in results:
        codes_str = str(r["stage1_2"].tolist()) if r["stage1_2"] is not None else "N/A"
        if len(codes_str) > 18:
            codes_str = codes_str[:15] + "..."
        print(f"{r['key']:<24} | {r['title']:<30} | {r['status']:<25} | {codes_str:<18}")
    print("=" * 110)
    print()

    if args.verbose:
        print("\n" + "=" * 110)
        print("Detailed Per-Sample Inspection Dumps:")
        print("=" * 110)
        for r in results:
            print(f"\n--- {r['key']} ({r['title']}) ---")
            print(f"  Dataset: {SAMPLES[r['key']]['dataset']}")
            print(f"  File:    {SAMPLES[r['key']]['file']}")
            print(f"  Status:  {r['status']}")
            if r["error"]:
                print(f"  Error:   {r['error']}")
            if r["v_pt"] is not None:
                print(f"  HTXS_V_pt:                    {r['v_pt']}")
                print(f"  HTXS_Higgs_y:                 {r['higgs_y']}")
                print(f"  HTXS_Higgs_pt:                {r['higgs_pt']}")
                print(f"  HTXS_njets30:                 {r['njets30']}")
                print(f"  HTXS_stage1_2_cat_pTjet30GeV: {r['stage1_2']}")


if __name__ == "__main__":
    main()

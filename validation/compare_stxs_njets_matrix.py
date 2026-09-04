#!/usr/bin/env python3
"""
compare_stxs_njets_matrix.py
============================
Computes and compares the Njet30 migration/confusion matrices:
  Self-defined Njet (GenJet R=0.6 cleaning proxy) vs. Official HTXS_njets30 (Rivet)
for both:
  1. NanoAODv12 (Run 3 2022 postEE baseline)
  2. 2024 Patched NanoAODv15 (100k generated test sample on EOS)

Evaluated specifically in the two critical STXS pT(V) intervals:
  - Bin 1: 150 <= pT(V) < 250 GeV (PTV_150_250)
  - Bin 2: 250 <= pT(V) < 400 GeV (PTV_250_400)

Evaluated under both:
  A) Official Rivet STXS Stage 1.2 Fine Category definition
  B) Truth GenPart pT(V) Kinematic definition
"""

import sys
import os
import glob
import numpy as np
import uproot
import awkward as ak
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Add CMSRun3VHbbSTXS to path for official workflow truth logic
STXS_REPO = "/afs/cern.ch/work/l/lichengz/private/VHbb/CMSRun3VHbbSTXS"
if STXS_REPO not in sys.path:
    sys.path.insert(0, STXS_REPO)

from workflow.stxs_truth import (
    classify_self_stxs,
    ProductionMode,
    DecayMode,
    WH_SELF_NJET_CLEANING_RADIUS,
)

BASE_BRANCHES = [
    "GenPart_pt", "GenPart_eta", "GenPart_phi", "GenPart_mass",
    "GenPart_pdgId", "GenPart_statusFlags", "GenPart_genPartIdxMother",
    "GenJet_pt", "GenJet_eta", "GenJet_phi", "GenJet_mass",
    "HTXS_njets30", "HTXS_Higgs_y",
    "HTXS_stage1_2_cat_pTjet30GeV", "HTXS_stage1_2_fine_cat_pTjet30GeV",
]

OPTIONAL_BRANCHES = [
    "HTXS_V_pt", "HTXS_Higgs_pt"
]

NJET_LABELS = ["0J", "1J", ">=2J"]
NJET_COLLAPSED_LABELS = ["0J", ">=1J"]


def group_njet(arr):
    """Groups raw integer njet into 0: 0J, 1: 1J, 2: >=2J."""
    arr = np.asarray(arr, dtype=int)
    grouped = np.zeros_like(arr)
    grouped[arr == 1] = 1
    grouped[arr >= 2] = 2
    return grouped


def collapse_njet(arr):
    """Collapses raw integer njet into 0: 0J, 1: >=1J."""
    arr = np.asarray(arr, dtype=int)
    collapsed = np.zeros_like(arr)
    collapsed[arr >= 1] = 1
    return collapsed


def process_file_list(file_list, max_events=100000, label=""):
    print(f"[{label}] Processing up to {max_events} events across {len(file_list)} files...")
    
    htxs_vpt_all = []
    htxs_hy_all = []
    htxs_njet_all = []
    htxs_cat_all = []
    htxs_fine_all = []
    self_vpt_all = []
    self_hy_all = []
    self_njet_all = []
    
    events_read = 0
    for fpath in file_list:
        if events_read >= max_events:
            break
        try:
            with uproot.open(fpath) as f:
                tree = f["Events"]
                n_avail = tree.num_entries
                n_to_read = min(n_avail, max_events - events_read)
                if n_to_read <= 0:
                    break
                
                avail_keys = set(tree.keys())
                branches_to_read = [b for b in BASE_BRANCHES if b in avail_keys]
                for ob in OPTIONAL_BRANCHES:
                    if ob in avail_keys:
                        branches_to_read.append(ob)
                        
                data = tree.arrays(branches_to_read, entry_stop=n_to_read)
                
                # Check for HTXS branches validity
                h_njet = ak.to_numpy(data["HTXS_njets30"])
                h_hy = ak.to_numpy(data["HTXS_Higgs_y"])
                h_cat = ak.to_numpy(data["HTXS_stage1_2_cat_pTjet30GeV"])
                h_fine = ak.to_numpy(data["HTXS_stage1_2_fine_cat_pTjet30GeV"])
                
                if "HTXS_V_pt" in data.fields:
                    h_vpt = ak.to_numpy(data["HTXS_V_pt"])
                else:
                    h_vpt = np.full(len(h_njet), np.nan)
                
                # Filter out unpopulated events (if any sentinel exists)
                valid_mask = np.isfinite(h_hy) & (h_njet >= 0)
                if not np.any(valid_mask):
                    continue
                
                # Zip into awkward record for classify_self_stxs
                events = ak.zip({
                    "GenPart": ak.zip({k.replace("GenPart_", ""): data[k] for k in branches_to_read if k.startswith("GenPart_")}),
                    "GenJet": ak.zip({k.replace("GenJet_", ""): data[k] for k in branches_to_read if k.startswith("GenJet_")}),
                }, depth_limit=1)
                
                self_res = classify_self_stxs(
                    events,
                    ProductionMode.QQWH,
                    DecayMode.WLNU,
                    cleaning_radius=WH_SELF_NJET_CLEANING_RADIUS
                )
                
                s_njet = ak.to_numpy(self_res.njet30_raw)
                s_vpt = ak.to_numpy(self_res.v_pt)
                s_hy = ak.to_numpy(self_res.h_y)
                
                htxs_vpt_all.append(h_vpt)
                htxs_hy_all.append(h_hy)
                htxs_njet_all.append(h_njet)
                htxs_cat_all.append(h_cat)
                htxs_fine_all.append(h_fine)
                self_vpt_all.append(s_vpt)
                self_hy_all.append(s_hy)
                self_njet_all.append(s_njet)
                
                events_read += n_to_read
                print(f"  Processed {events_read}/{max_events} events (+{n_to_read} from {os.path.basename(fpath)})")
        except Exception as e:
            print(f"  [WARNING] Error reading {fpath}: {e}")
            continue

    return {
        "htxs_vpt": np.concatenate(htxs_vpt_all),
        "htxs_hy": np.concatenate(htxs_hy_all),
        "htxs_njet": np.concatenate(htxs_njet_all),
        "htxs_cat": np.concatenate(htxs_cat_all),
        "htxs_fine": np.concatenate(htxs_fine_all),
        "self_vpt": np.concatenate(self_vpt_all),
        "self_hy": np.concatenate(self_hy_all),
        "self_njet": np.concatenate(self_njet_all),
        "total_events": events_read
    }


def compute_matrices_from_mask(h_njet_sel, s_njet_sel, bin_name):
    """
    Computes 3x3 and 2x2 migration matrices for selected events.
    Rows = Self-defined Njet, Cols = Official HTXS Njet
    """
    n_sel = len(h_njet_sel)
    
    # 3x3 matrix: rows = Self, cols = HTXS
    h_grp = group_njet(h_njet_sel)
    s_grp = group_njet(s_njet_sel)
    mat3x3 = np.zeros((3, 3), dtype=int)
    for s in range(3):
        for h in range(3):
            mat3x3[s, h] = np.sum((s_grp == s) & (h_grp == h))
            
    # 2x2 collapsed matrix: rows = Self, cols = HTXS
    h_col = collapse_njet(h_njet_sel)
    s_col = collapse_njet(s_njet_sel)
    mat2x2 = np.zeros((2, 2), dtype=int)
    for s in range(2):
        for h in range(2):
            mat2x2[s, h] = np.sum((s_col == s) & (h_col == h))
            
    return {
        "bin": bin_name,
        "n_events": n_sel,
        "mat3x3": mat3x3,
        "mat2x2": mat2x2,
        "acc3x3": np.trace(mat3x3) / n_sel if n_sel > 0 else 0.0,
        "acc2x2": np.trace(mat2x2) / n_sel if n_sel > 0 else 0.0,
    }


def format_matrix_table(mat, row_labels, col_labels, title=""):
    lines = []
    lines.append(f"--- {title} (Raw Counts) ---")
    lbl_sh = "Self \\ HTXS"
    header = f"{lbl_sh:<14} | " + " | ".join(f"{c:>8}" for c in col_labels) + " | " + f"{'Total':>8}"

    lines.append(header)
    lines.append("-" * len(header))
    
    col_sums = np.sum(mat, axis=0)
    for r_idx, r_label in enumerate(row_labels):
        r_sum = np.sum(mat[r_idx, :])
        row_str = f"{r_label:<14} | " + " | ".join(f"{mat[r_idx, c]:>8d}" for c in range(len(col_labels))) + f" | {r_sum:>8d}"
        lines.append(row_str)
    lines.append("-" * len(header))
    total = np.sum(mat)
    lines.append(f"{'Total':<14} | " + " | ".join(f"{col_sums[c]:>8d}" for c in range(len(col_labels))) + f" | {total:>8d}")
    
    # Column-normalized (Purity / Fraction of HTXS bin)
    lines.append(f"\n--- {title} (Column-Normalized: P(Self | HTXS) %) ---")
    lines.append(header)
    lines.append("-" * len(header))
    for r_idx, r_label in enumerate(row_labels):
        pcts = [
            (mat[r_idx, c] / col_sums[c] * 100) if col_sums[c] > 0 else 0.0
            for c in range(len(col_labels))
        ]
        row_str = f"{r_label:<14} | " + " | ".join(f"{p:>7.2f}%" for p in pcts) + " | "
        lines.append(row_str)
    lines.append("-" * len(header))
    return "\n".join(lines)


def plot_heatmaps_side_by_side(m_v12, m_v15, bin_name, out_dir, mode_name="Rivet"):
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. 3x3 Heatmap
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, m, camp in zip(axes, [m_v12, m_v15], ["NanoAODv12 (2022 postEE)", "2024 Patched NanoAODv15"]):
        mat = m["mat3x3"]
        col_sums = np.sum(mat, axis=0, keepdims=True)
        norm_mat = np.divide(mat, col_sums, where=(col_sums > 0), out=np.zeros_like(mat, dtype=float))
        
        im = ax.imshow(norm_mat, cmap="Blues", vmin=0.0, vmax=1.0, origin="lower")
        ax.set_xticks([0, 1, 2])
        ax.set_yticks([0, 1, 2])
        ax.set_xticklabels(NJET_LABELS, fontsize=12)
        ax.set_yticklabels(NJET_LABELS, fontsize=12)
        ax.set_xlabel("Official HTXS $N_{\\rm jets}^{30}$ (Rivet)", fontsize=12)
        ax.set_ylabel("Self-Derived $N_{\\rm jets}^{30}$ ($R_{\\rm clean}=0.6$)", fontsize=12)
        ax.set_title(f"{camp}\n{bin_name} [N={m['n_events']}] (Diag Agree: {m['acc3x3']*100:.2f}%)", fontsize=12, fontweight="bold")
        
        for r in range(3):
            for c in range(3):
                cnt = mat[r, c]
                pct = norm_mat[r, c] * 100
                color = "white" if norm_mat[r, c] > 0.55 else "black"
                ax.text(c, r, f"{cnt:,}\n({pct:.1f}%)", ha="center", va="center", color=color, fontsize=11, fontweight="bold")
                
    fig.subplots_adjust(right=0.88)
    cbar_ax = fig.add_axes([0.90, 0.15, 0.02, 0.7])
    fig.colorbar(im, cax=cbar_ax, label="Column Fraction: P(Self | HTXS)")
    plt.suptitle(f"STXS Njet Migration Matrix: {bin_name} ({mode_name} STXS Selection)", fontsize=14, y=0.98)
    
    clean_bin = bin_name.replace(" ", "_").replace("~", "_").replace("<=", "").replace("<", "")
    stem = f"{out_dir}/matrix_3x3_{clean_bin}_{mode_name.lower()}"
    plt.savefig(f"{stem}.png", dpi=200, bbox_inches="tight")
    plt.savefig(f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"[PLOT] Saved {stem}.png and {stem}.pdf")

    # 2. 2x2 Collapsed Heatmap
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, m, camp in zip(axes, [m_v12, m_v15], ["NanoAODv12 (2022 postEE)", "2024 Patched NanoAODv15"]):
        mat = m["mat2x2"]
        col_sums = np.sum(mat, axis=0, keepdims=True)
        norm_mat = np.divide(mat, col_sums, where=(col_sums > 0), out=np.zeros_like(mat, dtype=float))
        
        im = ax.imshow(norm_mat, cmap="Blues", vmin=0.0, vmax=1.0, origin="lower")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(NJET_COLLAPSED_LABELS, fontsize=12)
        ax.set_yticklabels(NJET_COLLAPSED_LABELS, fontsize=12)
        ax.set_xlabel("Official HTXS $N_{\\rm jets}^{30}$ (Rivet)", fontsize=12)
        ax.set_ylabel("Self-Derived $N_{\\rm jets}^{30}$ ($R_{\\rm clean}=0.6$)", fontsize=12)
        ax.set_title(f"{camp}\n{bin_name} [N={m['n_events']}] (Diag Agree: {m['acc2x2']*100:.2f}%)", fontsize=12, fontweight="bold")
        
        for r in range(2):
            for c in range(2):
                cnt = mat[r, c]
                pct = norm_mat[r, c] * 100
                color = "white" if norm_mat[r, c] > 0.55 else "black"
                ax.text(c, r, f"{cnt:,}\n({pct:.1f}%)", ha="center", va="center", color=color, fontsize=12, fontweight="bold")
                
    fig.subplots_adjust(right=0.88)
    cbar_ax = fig.add_axes([0.90, 0.15, 0.02, 0.7])
    fig.colorbar(im, cax=cbar_ax, label="Column Fraction: P(Self | HTXS)")
    plt.suptitle(f"STXS Njet Collapsed (0J vs >=1J): {bin_name} ({mode_name} STXS Selection)", fontsize=14, y=0.98)
    
    stem = f"{out_dir}/matrix_2x2_{clean_bin}_{mode_name.lower()}"
    plt.savefig(f"{stem}.png", dpi=200, bbox_inches="tight")
    plt.savefig(f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"[PLOT] Saved {stem}.png and {stem}.pdf")


def main():
    print("=" * 90)
    print(" STXS Njet Migration Comparison: NanoAODv12 vs. 2024 Patched NanoAODv15")
    print("=" * 90)
    print()
    
    # 1. Gather 2024 Patched NanoAODv15 files (from /eos/user/l/lichengz/VHBBBOX/nano-test/)
    v15_files = sorted(glob.glob("/eos/user/l/lichengz/VHBBBOX/nano-test/NanoAODv15_*_job*.root"))
    print(f"Found {len(v15_files)} 2024 Patched NanoAODv15 files (100k events).")
    
    # 2. Gather NanoAODv12 files (from /eos/cms/)
    v12_wplus = sorted(glob.glob("/eos/cms/store/mc/Run3Summer22EENanoAODv12/WplusH_Hto2B_WtoLNu_M-125_TuneCP5_13p6TeV_powheg-pythia8/NANOAODSIM/130X_mcRun3_2022_realistic_postEE_v6-v2/*/*.root"))
    v12_wminus = sorted(glob.glob("/eos/cms/store/mc/Run3Summer22EENanoAODv12/WminusH_Hto2B_WtoLNu_M-125_TuneCP5_13p6TeV_powheg-pythia8/NANOAODSIM/130X_mcRun3_2022_realistic_postEE_v6-v2/*/*.root"))
    
    # Interleave W+ and W- files to get 100k balanced events (50k W+, 50k W-)
    v12_files = []
    for p, m in zip(v12_wplus[:6], v12_wminus[:6]):
        v12_files.extend([p, m])
    print(f"Sampled {len(v12_files)} NanoAODv12 files for 2022 postEE comparison.\n")
    
    # Process both datasets (100,000 events each)
    data_v15 = process_file_list(v15_files, max_events=100000, label="2024 Patched NanoAODv15")
    data_v12 = process_file_list(v12_files, max_events=100000, label="Run 3 NanoAODv12")
    
    out_plot_dir = "/eos/user/l/lichengz/VHBBBOX/nano-test/matrix_plots"
    os.makedirs(out_plot_dir, exist_ok=True)

    # We evaluate two definitions of the pT(V) intervals:
    # Definition 1: Official Rivet STXS Stage 1.2 Fine Bins
    #   - 150 <= pT(V) < 250: fine codes {303 (0J), 308 (1J), 313 (>=2J)}
    #   - 250 <= pT(V) < 400: fine codes {304 (0J), 309 (1J), 314 (>=2J)}
    # Definition 2: Truth GenPart pT(V) Kinematic Bins
    #   - 150 <= pT(V) < 250: 150 <= self_v_pt < 250 and |self_h_y| < 2.5
    #   - 250 <= pT(V) < 400: 250 <= self_v_pt < 400 and |self_h_y| < 2.5
    
    modes = [
        ("Rivet_STXS_Bins", "Official Rivet STXS Classification", {
            "PTV_150_250": lambda d: np.isin(d["htxs_fine"], [303, 308, 313]),
            "PTV_250_400": lambda d: np.isin(d["htxs_fine"], [304, 309, 314]),
        }),
        ("Truth_pTV_Bins", "Truth GenPart pT(V) Kinematic Intervals", {
            "PTV_150_250": lambda d: (d["self_vpt"] >= 150.0) & (d["self_vpt"] < 250.0) & (np.abs(d["self_hy"]) < 2.5),
            "PTV_250_400": lambda d: (d["self_vpt"] >= 250.0) & (d["self_vpt"] < 400.0) & (np.abs(d["self_hy"]) < 2.5),
        })
    ]

    for mode_key, mode_title, bin_filters in modes:
        print("\n" + "#" * 90)
        print(f" SELECTION REGIME: {mode_title}")
        print("#" * 90)
        
        for bin_name, filter_func in bin_filters.items():
            print("\n" + "=" * 90)
            print(f" >>> INTERVAL: {bin_name} [{mode_title}] <<<")
            print("=" * 90)
            
            mask_v12 = filter_func(data_v12)
            mask_v15 = filter_func(data_v15)
            
            m_v12 = compute_matrices_from_mask(data_v12["htxs_njet"][mask_v12], data_v12["self_njet"][mask_v12], bin_name)
            m_v15 = compute_matrices_from_mask(data_v15["htxs_njet"][mask_v15], data_v15["self_njet"][mask_v15], bin_name)
            
            print(f"\nEvents selected in {bin_name}:")
            print(f"  NanoAODv12:               {m_v12['n_events']:,} events")
            print(f"  2024 Patched NanoAODv15:  {m_v15['n_events']:,} events")
            print(f"\nExact 3x3 Diagonal Agreement (0J, 1J, >=2J):")
            print(f"  NanoAODv12:              {m_v12['acc3x3']*100:.2f}%")
            print(f"  2024 Patched NanoAODv15: {m_v15['acc3x3']*100:.2f}%")
            print(f"\nOfficial 2x2 Split Agreement (0J vs. >=1J):")
            print(f"  NanoAODv12:              {m_v12['acc2x2']*100:.2f}%")
            print(f"  2024 Patched NanoAODv15: {m_v15['acc2x2']*100:.2f}%")
            
            print("\n" + "-" * 40 + f" NanoAODv12: {bin_name} (3x3) " + "-" * 40)
            print(format_matrix_table(m_v12["mat3x3"], NJET_LABELS, NJET_LABELS, title=f"NanoAODv12 {bin_name} (3x3)"))
            print("\n" + "-" * 40 + f" NanoAODv12: {bin_name} (2x2 Collapsed) " + "-" * 40)
            print(format_matrix_table(m_v12["mat2x2"], NJET_COLLAPSED_LABELS, NJET_COLLAPSED_LABELS, title=f"NanoAODv12 {bin_name} (2x2 Collapsed)"))
            
            print("\n" + "-" * 40 + f" 2024 Patched NanoAODv15: {bin_name} (3x3) " + "-" * 40)
            print(format_matrix_table(m_v15["mat3x3"], NJET_LABELS, NJET_LABELS, title=f"2024 Patched NanoAODv15 {bin_name} (3x3)"))
            print("\n" + "-" * 40 + f" 2024 Patched NanoAODv15: {bin_name} (2x2 Collapsed) " + "-" * 40)
            print(format_matrix_table(m_v15["mat2x2"], NJET_COLLAPSED_LABELS, NJET_COLLAPSED_LABELS, title=f"2024 Patched NanoAODv15 {bin_name} (2x2 Collapsed)"))
            
            # Plot side-by-side heatmaps
            plot_heatmaps_side_by_side(m_v12, m_v15, bin_name, out_plot_dir, mode_name=mode_key)

    print("\n" + "=" * 90)
    print(f" Analysis complete! Plots saved to: {out_plot_dir}/")
    print("=" * 90)


if __name__ == "__main__":
    main()

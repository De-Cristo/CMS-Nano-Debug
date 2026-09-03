#!/usr/bin/env python3
"""
compare_htxs_results.py
=======================
Side-by-side verification and benchmark tool for NanoAOD HTXS branches.
Compares:
1. Unpatched NanoAOD (demonstrating the bug: 0s, NaNs).
2. Patched NanoAOD (demonstrating the fix: physical kinematics, 300 series).
3. Rivet HTXS_njets30 vs. our Analysis R=0.6 GenJet cleaning proxy!
"""

import argparse
import sys
import numpy as np
import uproot
import awkward as ak


def delta_r(eta1, phi1, eta2, phi2):
    deta = eta1 - eta2
    dphi = np.remainder(phi1 - phi2 + np.pi, 2 * np.pi) - np.pi
    return np.sqrt(deta**2 + dphi**2)


def calculate_r06_proxy(events):
    """
    Computes our analysis GenJet cleaning proxy (R_clean = 0.6) on the event array.
    """
    # Find Higgs daughter b quarks (pdgId == 5 or -5, status == 23 or isLastCopy)
    gen_pdg = events["GenPart_pdgId"]
    gen_flags = events["GenPart_statusFlags"]
    gen_eta = events["GenPart_eta"]
    gen_phi = events["GenPart_phi"]

    is_b = (np.abs(gen_pdg) == 5) & ((gen_flags & (1 << 13)) > 0)  # isLastCopy

    b_eta = gen_eta[is_b]
    b_phi = gen_phi[is_b]

    # GenJets with pt > 30, |eta| < 2.5
    jet_pt = events["GenJet_pt"]
    jet_eta = events["GenJet_eta"]
    jet_phi = events["GenJet_phi"]

    pt_cut = jet_pt > 30.0

    # Count additional jets after R = 0.6 cleaning
    njets_proxy = []
    for ievt in range(len(events)):
        be = b_eta[ievt]
        bp = b_phi[ievt]
        je = jet_eta[ievt][pt_cut[ievt]]
        jp = jet_phi[ievt][pt_cut[ievt]]

        clean_count = 0
        for j_idx in range(len(je)):
            # Check delta R to each b
            dr_min = 999.0
            for b_idx in range(len(be)):
                dr = delta_r(je[j_idx], jp[j_idx], be[b_idx], bp[b_idx])
                if dr < dr_min:
                    dr_min = dr
            if dr_min >= 0.6:
                clean_count += 1
        njets_proxy.append(clean_count)

    return np.array(njets_proxy)


def inspect_file(filepath, max_entries=10):
    with uproot.open(filepath) as f:
        tree = f["Events"]
        branches = [
            "HTXS_V_pt",
            "HTXS_Higgs_pt",
            "HTXS_Higgs_y",
            "HTXS_njets30",
            "HTXS_stage1_2_cat_pTjet30GeV",
            "HTXS_stage1_2_fine_cat_pTjet30GeV"
        ]
        available = [b for b in branches if b in tree]
        data = tree.arrays(available, entry_stop=max_entries)
        
        has_gen = all(k in tree for k in ["GenPart_pdgId", "GenJet_pt"])
        gen_data = None
        if has_gen:
            gen_data = tree.arrays(["GenPart_pdgId", "GenPart_statusFlags", "GenPart_eta", "GenPart_phi", "GenJet_pt", "GenJet_eta", "GenJet_phi"], entry_stop=max_entries)
            
        return data, gen_data, tree.num_entries


def main():
    parser = argparse.ArgumentParser(description="Side-by-side NanoAOD HTXS comparator")
    parser.add_argument("--unpatched", "-u", required=True, help="Path to unpatched NanoAOD ROOT file")
    parser.add_argument("--patched", "-p", required=True, help="Path to patched NanoAOD ROOT file")
    parser.add_argument("--entries", "-n", type=int, default=10, help="Number of entries to display in detail")
    args = parser.parse_args()

    print("==========================================================================================")
    print(" CMS Run 3 NanoAODv15 WH HTXS Fix: Side-by-Side Verification Report")
    print("==========================================================================================")
    print(f" Unpatched File: {args.unpatched}")
    print(f" Patched File:   {args.patched}")
    print("==========================================================================================\n")

    unp_data, unp_gen, unp_n = inspect_file(args.unpatched, max_entries=args.entries)
    pat_data, pat_gen, pat_n = inspect_file(args.patched, max_entries=args.entries)

    n_compare = min(args.entries, len(unp_data["HTXS_V_pt"]), len(pat_data["HTXS_V_pt"]))

    print(f"--- Event-by-Event Comparison (First {n_compare} Events) ---")
    header = (
        f"{'Evt':<4} | "
        f"{'Unpatched (V_pt, njets, Cat)':<30} | "
        f"{'Patched (V_pt, njets, Cat)':<30} | "
        f"{'Fix Status':<12}"
    )
    print(header)
    print("-" * len(header))

    patched_valid_count = 0
    for i in range(n_compare):
        u_vpt = unp_data["HTXS_V_pt"][i]
        u_njet = unp_data["HTXS_njets30"][i]
        u_cat = unp_data["HTXS_stage1_2_cat_pTjet30GeV"][i]

        p_vpt = pat_data["HTXS_V_pt"][i]
        p_njet = pat_data["HTXS_njets30"][i]
        p_cat = pat_data["HTXS_stage1_2_cat_pTjet30GeV"][i]

        u_str = f"({u_vpt:.1f}, {u_njet}, {u_cat})"
        p_str = f"({p_vpt:.1f}, {p_njet}, {p_cat})"

        is_fixed = (u_cat == 0 and p_cat >= 300)
        if is_fixed:
            status = "FIXED OK"
            patched_valid_count += 1
        else:
            status = "VERIFY"

        print(f"{i:<4} | {u_str:<30} | {p_str:<30} | {status:<12}")

    print("-" * len(header))
    print(f"\nSummary: {patched_valid_count} / {n_compare} events successfully recovered from dummy (0) to QQ2HLNU (300 series).\n")

    # Benchmark against Analysis R=0.6 GenJet Proxy
    if pat_gen is not None:
        print("--- Benchmark: Patched Rivet HTXS_njets30 vs. Our Analysis R=0.6 Proxy ---")
        proxy_njets = calculate_r06_proxy(pat_gen)
        rivet_njets = np.array(pat_data["HTXS_njets30"])

        exact_match = np.sum(proxy_njets[:n_compare] == rivet_njets[:n_compare])
        match_pct = (exact_match / n_compare) * 100

        print(f"  Exact Multiplicity Agreement: {exact_match}/{n_compare} ({match_pct:.1f}%)\n")
        print(f"{'Evt':<4} | {'Rivet HTXS_njets30':<20} | {'Analysis R=0.6 Proxy':<22} | {'Agreement'}")
        print("-" * 65)
        for i in range(n_compare):
            r_val = rivet_njets[i]
            p_val = proxy_njets[i]
            match_str = "MATCH" if r_val == p_val else "MIGRATION"
            print(f"{i:<4} | {r_val:<20} | {p_val:<22} | {match_str}")
        print("-" * 65)


if __name__ == "__main__":
    main()

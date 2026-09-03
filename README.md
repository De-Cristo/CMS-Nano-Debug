# Technical Investigation Report: Missing HTXS Information in CMS Run 3 NanoAODv15 WH Samples

- **Date:** September 2026
- **Analysis Scope:** CMS VH(bb) STXS Stage 1.3 Measurement (Run 3)
- **Target Campaign:** `RunIII2024Summer24NanoAODv15` (150X realistic v2)
- **Target Software:** CMSSW (`GeneratorInterface/RivetInterface/plugins/HTXSRivetProducer.cc`)
- **Author/Contact:** CMS VHbb Analysis Team

---

## 1. Executive Summary

During the integration and validation of the 2024 CMS Run 3 simulation (`RunIII2024Summer24NanoAODv15`), an anomaly was uncovered in the Simplified Template Cross Sections (STXS / HTXS) data products for associated Higgs production with a $W$ boson ($WH$):

1. **Unpopulated HTXS Branches for WH:** In standard $WH$ samples ($W^\pm H, W \to \ell\nu, H \to b\bar{b}$), all `HTXS_*` branches are completely unpopulated, holding non-physical dummy/sentinel values ($p_{\mathrm{T}}(\mathrm{V}) = 0$, $y_{\mathrm{H}} = \mathrm{NaN}$, $N_{\mathrm{jet}}^{30} = 0$, Stage 1.2 Category Code $= 0$).
2. **Contrast with ZH:** Under the identical NanoAODv15 campaign schema, $ZH$ samples ($q\bar{q} \to ZH$ and $gg \to ZH$) are populated with valid, physical HTXS kinematics and correct Stage 1.2 category codes.
3. **Decay Mode Survey:** A systematic survey across 8 different $WH$ decay modes reveals that this failure is **general across almost all $WH$ decay topologies** ($H \to b\bar{b}$, $H \to c\bar{c}$, $H \to \tau\tau$, $H \to ZZ \to 4\ell$, $H \to WW \to 2\ell 2\nu$, $H \to \mu\mu$, and hadronic $W \to 2q, H \to b\bar{b}$). The only working exception is $W(\to \ell\nu)H(\to \gamma\gamma)$.
4. **Root Cause in CMSSW:** The failure is traced directly to CMSSW's `HTXSRivetProducer.cc`. When `ProductionMode = "AUTO"`, the run-level LHE header parser matches `"HZJ"` for $ZH$, but completely lacks a check for `"HWJ"` for $WH$. The code then falls back to an event-level heuristic that counts outgoing particles at the first vertex with a Higgs child. This heuristic fails for hadronic $W$ decays and multi-particle/showered Higgs decays, setting the production mode to `UNKNOWN` ($0$) and producing dummy outputs.
5. **Mitigation in VH(bb) Analysis:** The analysis isolates this failure via an explicit sentinel tag (`v15_qqwh_htxs_reference_unusable`), employs an independently calibrated geometric GenJet cleaning proxy ($R_{\text{clean}} = 0.6$) across both Run 3 campaigns (`v12_qqwh_direct`), and covers residual migrations with a dedicated systematic variation (`truthNjet_migration`).

---

## 2. Background and Physics Context

### 2.1 The STXS Stage 1.3 Framework for VH
The Simplified Template Cross Section (STXS) framework partitions the Standard Model Higgs boson production phase space into mutually exclusive kinematic bins to measure cross sections with minimal model dependence. For $VH$ ($V = W, Z$), Stage 1.3 defines eight physical bins:

| Bin Name | $p_{\mathrm{T}}(\mathrm{V})$ Interval [GeV] | Additional Jet Multiplicity ($N_{\text{jet}}^{30}$) |
|---|---|---|
| `PTV_0_75` | $[0, 75)$ | Inclusive |
| `PTV_75_150` | $[75, 150)$ | Inclusive |
| `PTV_150_250_0J` | $[150, 250)$ | $N_{\text{jet}}^{30} = 0$ |
| `PTV_150_250_GE1J` | $[150, 250)$ | $N_{\text{jet}}^{30} \ge 1$ |
| `PTV_250_400_0J` | $[250, 400)$ | $N_{\text{jet}}^{30} = 0$ |
| `PTV_250_400_GE1J` | $[250, 400)$ | $N_{\text{jet}}^{30} \ge 1$ |
| `PTV_400_600` | $[400, 600)$ | Inclusive |
| `PTV_GE600` | $[600, \infty)$ | Inclusive |

### 2.2 Official Rivet / HTXS Definition of $N_{\text{jet}}^{30}$
In the official Rivet routine (`HiggsTemplateCrossSections.cc`), the additional-jet multiplicity is calculated by clustering final-state generator particles after **removing all particles descending from the Higgs boson** by traversing the particle ancestry tree (`originateFrom`).
* In **NanoAOD**, generator-particle constituent links and full ancestry graphs are removed to save disk space. As a result, the exact Rivet ancestry-removal algorithm **cannot be run directly on NanoAOD**.
* The analysis depends on the pre-computed `HTXS_njets30` branch stored in NanoAOD. When this branch is unpopulated, the $0\mathrm{J}$ versus $\ge 1\mathrm{J}$ split in the fit-critical $[150, 400)\,\text{GeV}$ window cannot be obtained from official branches.

---

## 3. Empirical Survey Across Decay Topologies

We conducted a live survey of `RunIII2024Summer24NanoAODv15` samples accessing events directly via the CMS global XRootD redirector (`root://cms-xrd-global.cern.ch//`).

### 3.1 Survey Summary Table

| Process Key | Channel / Topology | CMS DAS Dataset Name | Example NanoAOD File (LFN) | HTXS Status | Stage 1.2 Codes |
|---|---|---|---|---|---|
| `WplusH_Hto2B_WtoLNu` | $W^+ \to \ell\nu, H \to b\bar{b}$ | `/WplusH-WtoLNu-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/WplusH-WtoLNu-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/120000/07ce3cf9-a0ee-4f30-a31c-1cd00205bb77.root` | **BROKEN (Sentinel)** | `[0, 0, 0, 0, 0]` |
| `WminusH_Hto2B_WtoLNu` | $W^- \to \ell\nu, H \to b\bar{b}$ | `/WminusH-WtoLNu-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/WminusH-WtoLNu-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/2560000/ecb24314-a6a7-4949-833f-e6d3cea38a07.root` | **BROKEN (Sentinel)** | `[0, 0, 0, 0, 0]` |
| `WplusH_Hto2B_Wto2Q` | $W^+ \to 2q, H \to b\bar{b}$ (Hadronic $W$) | `/WplusH-Wto2Q-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/WplusH-Wto2Q-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/2560000/5048f06b-de47-4643-adcb-8a79bbb2daa5.root` | **BROKEN (Sentinel)** | `[0, 0, 0, 0, 0]` |
| `WplusH_Hto2C_WtoLNu` | $W^+ \to \ell\nu, H \to c\bar{c}$ | `/WplusH-WtoLNu-Hto2C_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/WplusH-WtoLNu-Hto2C_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/120000/7bf3cc1a-bf20-47ba-8426-2233abf268e3.root` | **BROKEN (Sentinel)** | `[0, 0, 0, 0, 0]` |
| `WplusH_Hto2Tau` | $W^+ \to \text{incl}, H \to \tau\tau$ | `/WplusH-Hto2TauUncorrelatedDecay_Par-M-125_TuneCP5_13p6TeV_powhegMINNLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/WplusH-Hto2TauUncorrelatedDecay_Par-M-125_TuneCP5_13p6TeV_powhegMINNLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/120000/80ca192d-aebe-47dd-921b-166ed80db5bc.root` | **BROKEN (Sentinel)** | `[0, 0, 0, 0, 0]` |
| `WplusH_Hto2Zto4L` | $W^+ \to \text{incl}, H \to ZZ \to 4\ell$ | `/WplusH-Hto2Zto4L_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-jhugen-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/WplusH-Hto2Zto4L_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-jhugen-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/2810000/5a51d8ac-3602-47b2-9dc1-6198f9096131.root` | **BROKEN (Sentinel)** | `[0, 0, 0, 0, 0]` |
| `WplusH_Hto2Wto2L2Nu` | $W^+ \to \ell\nu, H \to WW \to 2\ell 2\nu$ | `/WplusH-WtoLNu-Hto2Wto2L2Nu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-jhugen-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/WplusH-WtoLNu-Hto2Wto2L2Nu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-jhugen-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/2550000/2f66f9db-1ce0-4a2f-bbcc-6211f77898f9.root` | **BROKEN (Sentinel)** | `[0, 0, 0, 0, 0]` |
| `WplusH_Hto2Mu` | $W^+ \to \text{incl}, H \to \mu\mu$ | `/WplusH-Hto2Mu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v3/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/WplusH-Hto2Mu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v3/2810000/aab75a2d-4c20-4b8f-8021-75c2fc60b96c.root` | **BROKEN (Sentinel)** | `[0, 0, 0, 0, 0]` |
| `WplusH_Hto2G_WtoLNu` | $W^+ \to \ell\nu, H \to \gamma\gamma$ | `/WplusH-Hto2G-WtoLNu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/WplusH-Hto2G-WtoLNu_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/2550000/cc6787f6-7076-4838-90de-86cc3c5be3cf.root` | **POPULATED & VALID** | `[300, 304, 301, 300, 301]` |
| `ZH_Hto2B_Zto2L` (Control) | $q\bar{q} \to ZH, Z \to 2\ell, H \to b\bar{b}$ | `/ZH-Zto2L-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/ZH-Zto2L-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/140000/3f1aaaee-242f-44e4-a3d6-56bc2f6fb19b.root` | **POPULATED & VALID** | `[402, 400, 401, 402, 402]` |
| `ggZH_Hto2B_Zto2L` (Control) | $gg \to ZH, Z \to 2\ell, H \to b\bar{b}$ | `/GluGluZH-Zto2L-Hto2B_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` | `/store/mc/RunIII2024Summer24NanoAODv15/GluGluZH-Zto2L-Hto2B_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8/NANOAODSIM/150X_mcRun3_2024_realistic_v2-v2/140000/f2b12277-a685-47fb-9ada-e67a5da4c4b9.root` | **POPULATED & VALID** | `[502, 502, 500, 501, 502]` |

### 3.2 Observed Values in Broken vs. Working Samples

#### Broken Case ($W^+H, H \to b\bar{b}$):
```text
HTXS_V_pt:                    [0.0, 0.0, 0.0, 0.0, 0.0]
HTXS_Higgs_y:                 [nan, nan, nan, nan, nan]
HTXS_Higgs_pt:                [0.0, 0.0, 0.0, 0.0, 0.0]
HTXS_njets30:                 [0, 0, 0, 0, 0]
HTXS_stage1_2_cat_pTjet30GeV: [0, 0, 0, 0, 0]
```

#### Working Exception Case ($W^+H, H \to \gamma\gamma$):
```text
HTXS_V_pt:                    [24.8, 211.0, 32.5, 8.9, 40.7]
HTXS_Higgs_y:                 [-3.73, 0.36, -1.28, -3.02, -0.48]
HTXS_Higgs_pt:                [23.6, 64.9, 68.6, 8.9, 152.9]
HTXS_njets30:                 [0, 1, 2, 0, 1]
HTXS_stage1_2_cat_pTjet30GeV: [300, 304, 301, 300, 301]  <-- 300 series = QQ2HLNU
```

---

## 4. Root Cause Analysis in CMSSW

The producer responsible for generating the `HTXS` table is `rivetProducerHTXS` defined in `PhysicsTools/NanoAOD/python/particlelevel_cff.py`:
```python
rivetProducerHTXS = cms.EDProducer('HTXSRivetProducer',
    HepMCCollection = cms.InputTag('genParticles2HepMCHiggsVtx', 'unsmeared'),
    LHERunInfo = cms.InputTag('externalLHEProducer'),
    ProductionMode = cms.string('AUTO'),
)
```
The C++ implementation is located at [`GeneratorInterface/RivetInterface/plugins/HTXSRivetProducer.cc`](https://github.com/cms-sw/cmssw/blob/master/GeneratorInterface/RivetInterface/plugins/HTXSRivetProducer.cc).

### 4.1 Flaw #1: Omission of $WH$ in `beginRun()` LHE Parsing
When `ProductionMode` is set to `"AUTO"`, the producer executes `beginRun()` once per run to read generator headers from `LHERunInfoProduct`:

```cpp
void HTXSRivetProducer::beginRun(edm::Run const& iRun, edm::EventSetup const& es) {
  if (_prodMode == "AUTO") {
    edm::Handle<LHERunInfoProduct> run;
    bool product_exists = iRun.getByLabel(edm::InputTag("externalLHEProducer"), run);
    if (product_exists) {
      ...
      for (headers_const_iterator iter = ...; iter != ...; iter++) {
        for (unsigned int iLine = 0; iLine < lines.size(); iLine++) {
          const std::string& line = lines.at(iLine);
          // POWHEG
          if (line.find("gg_H_quark-mass-effects") != std::string::npos) { m_HiggsProdMode = HTXS::GGF; break; }
          if (line.find("Process: HJ") != std::string::npos)              { m_HiggsProdMode = HTXS::GGF; break; }
          if (line.find("Process: HJJ") != std::string::npos)             { m_HiggsProdMode = HTXS::GGF; break; }
          if (line.find("VBF_H") != std::string::npos)                    { m_HiggsProdMode = HTXS::VBF; break; }
          if (line.find("HZJ") != std::string::npos)                      { m_HiggsProdMode = HTXS::QQ2ZH; break; } // <--- MATCHES ZH!
          if (line.find("ggHZ") != std::string::npos)                     { m_HiggsProdMode = HTXS::GG2ZH; break; }
          ...
```

* **The Problem:** The string matching contains `"HZJ"` for $ZH$, but **`"HWJ"` (or `"HW"`) is completely absent**.
* **Effect:** For all POWHEG $ZH$ samples, `m_HiggsProdMode` is resolved immediately as `HTXS::QQ2ZH` ($4$). But for all POWHEG $WH$ samples, `m_HiggsProdMode` remains `HTXS::UNKNOWN` ($0$).

### 4.2 Flaw #2: The Fragile Event-Level Fallback Heuristic in `produce()`
Because `m_HiggsProdMode == UNKNOWN`, the code enters a fallback heuristic inside `produce()`:

```cpp
// Find Higgs production vertex automatically
ConstGenVertexPtr HSvtx = nullptr;
int totlv = int(myGenEvent->vertices().size());
for (auto i = 0; i < totlv; i++) {
  ConstGenVertexPtr vtx = myGenEvent->vertices()[i];
  for (const auto& ptcl : HepMCUtils::particles(vtx, Relatives::CHILDREN)) {
    if (ptcl->pdg_id() == 25) {  // Higgs found as outgoing
      HSvtx = vtx;
      break;
    }
  }
  if (HSvtx) break;
}

if (HSvtx) {
  for (const auto& ptcl : HepMCUtils::particles(HSvtx, Relatives::CHILDREN)) {
    if (std::abs(ptcl->pdg_id()) == 24) ++nWs;
    if (ptcl->pdg_id() == 23)           ++nZs;
    if (abs(ptcl->pdg_id()) == 6)       ++nTs;
    if (abs(ptcl->pdg_id()) == 5)       ++nBs;
    if (ptcl->pdg_id() == 25)           ++nHs;
  }
}

if (nZs == 1 && nHs == 1 && (nWs + nTs) == 0) {
  m_HiggsProdMode = HTXS::QQ2ZH;
} else if (nWs == 1 && nHs == 1 && (nZs + nTs) == 0) {
  m_HiggsProdMode = HTXS::WH;
}
```

This event-level logic makes fragile assumptions about the event graph converted by `GenParticles2HepMCConverter`:
1. **Hadronic $W$ ($W \to 2q$):** The $W$ boson is decayed into quarks at the matrix-element level; there is no outgoing $W$ boson ($nWs = 0$). Condition `nWs == 1` fails.
2. **$H \to WW$:** The Higgs decays into two $W$ bosons at or near the vertex ($nWs = 3$). Condition `nWs == 1` fails.
3. **$H \to ZZ$:** The Higgs decays into two $Z$ bosons ($nZs = 2$). Condition `nZs == 0` fails.
4. **$H \to b\bar{b}, c\bar{c}, \tau\tau, \mu\mu$:** In the reconstructed HepMC graph from Pythia shower histories, the vertex outgoing list includes intermediate shower/decay copies or fails the simple 2-body association.
5. **Why $H \to \gamma\gamma$ worked:** Photons carry no color or weak charge and do not increment $nWs, nZs, nTs$, or $nBs$. The vertex cleanly contained $1 \times W$ and $1 \times H$, satisfying `nWs == 1 && nHs == 1 && nZs == 0 && nTs == 0`.

When this check fails, `m_HiggsProdMode` remains `HTXS::UNKNOWN` ($0$). The Rivet analyzer:
```cpp
Rivet::HiggsClassification rivet_cat = _HTXS->classifyEvent(event, m_HiggsProdMode);
```
cannot classify the event and produces default values ($p_{\mathrm{T}}(\mathrm{V}) = 0$, $y_{\mathrm{H}} = \mathrm{NaN}$, Category $= 0$).

---

## 5. Impact and Mitigation in the VH(bb) STXS Analysis

### 5.1 Isolating the Failure
In [`workflow/stxs_truth_source_validation.py`](../../../CMSRun3VHbbSTXS/workflow/stxs_truth_source_validation.py), the framework recognizes this state as a known sentinel and rejects any silent per-event fallback:
```python
# Accept unavailable NanoAODv15 WH sentinel without silent fallback
all_default = (
    (v_pt == 0.0)
    & ((higgs_y == 0.0) | np.isnan(higgs_y))
    & (njets30 == 0.0)
    & (stage1p2 == 0.0)
    & (stage1p2_fine == 0.0)
)
```
In truth-cleaning and response diagnostics, the policy registers:
```python
"v15_qqwh_htxs_reference_unusable"
```

### 5.2 Self-Defined Geometric Truth Proxy ($R = 0.6$)
To measure $N_{\text{jet}}^{30}$ without Rivet ancestry information, GenJets ($p_{\mathrm{T}} > 30\,\text{GeV}$) are cleaned geometrically:
$$\Delta R(\text{GenJet}, b_1) < R_{\text{clean}} \quad\text{or}\quad \Delta R(\text{GenJet}, b_2) < R_{\text{clean}}$$
where $b_1, b_2$ are the last-copy Higgs daughter quarks.
* An empirical calibration across $R \in \{0.4, 0.5, 0.6, 0.8\}$ in 2022 postEE showed that **$R = 0.6$** optimizes agreement with the true Rivet oracle ($\sim 90\%$ in $[150, 250)\,\text{GeV}$ and $\sim 92.2\%$ in $[250, 400)\,\text{GeV}$).
* To preserve cross-campaign uniformity, the self-defined $R=0.6$ classification is adopted for WH across both Run 3 campaigns (`v12_qqwh_direct`).

### 5.3 Systematic Migration Uncertainty
Because the geometric proxy has residual $2\text{--}4\%$ migration relative to the Rivet routine, an owner-approved systematic uncertainty—the **WH truth-$N_{\text{jet}}$ migration variation**—is applied to the two split bins (`PTV_150_250` and `PTV_250_400`).

---

## 6. Production Chain Context: Where the Bug Occurs

### 6.1 The CMS Monte Carlo Production Tiers

To understand where the bug is introduced, we trace the full simulation chain from matrix element generation to analysis ntuples:

| Production Tier | Software & Release | Operations Performed | HTXS Status |
|---|---|---|---|
| **1. wmLHEGS** (`GEN-SIM`) | `CMSSW_14_0_19` | POWHEG-BOX-RES (HWJ MiNLO) + Pythia8 + Geant4 detector simulation. Produces `RAWSIM,LHE`. | **Untouched.** Stores raw LHE weights & generator particles. |
| **2. DRPremix** (`AODSIM`) | `CMSSW_14_0_20` | Electronic digitization, pileup mixing (`premix_stage2`), HLT simulation, full tracking & reconstruction. Produces `AODSIM`. | **Untouched.** Does not evaluate HTXS. |
| **3. MiniAODv6** (`MINIAODSIM`) | `CMSSW_15_0_2` | High-level candidate pruning, jet clustering, candidate slimming. Produces `MINIAODSIM1`. | **Untouched.** HTXS information is **NOT stored in MiniAOD**. |
| **4. NanoAODv15** (`NANOAODSIM`) | `CMSSW_15_0_2` | Runs `nanoSequenceMC` (`cmsDriver.py -s NANO`). Schedules `particleLevelTask` (`rivetProducerHTXS`). | 💥 **THE BUG HAPPENS HERE.** |

### 6.2 Why HTXS is Absent in MiniAOD
Direct inspection of the official `RunIII2024Summer24MiniAODv6` file reveals **756 branches** and **zero HTXS data products**:
* MiniAOD only stores `recoGenParticles_prunedGenParticles__PAT` and `LHERunInfoProduct`.
* `rivetProducerHTXS` runs **dynamically on the fly** during the MiniAOD $\to$ NanoAOD step (`PhysicsTools/NanoAOD/python/particlelevel_cff.py`), reading `prunedGenParticles` through an in-memory `HepMC` converter.
* Therefore, the upstream datasets (`GEN-SIM`, `AODSIM`, `MINIAODSIM`) are **completely intact and uncorrupted**. The bug is strictly confined to the `NANO` step.

---

## 7. Recommended CMSSW Patch

The patch [`patches/cmssw_htxs_hwj.patch`](patches/cmssw_htxs_hwj.patch) corrects `GeneratorInterface/RivetInterface/plugins/HTXSRivetProducer.cc`:
1. Adds `"HWJ"`, `"HW_"`, and `"Process: HW"` to the run-level POWHEG parser in `beginRun()`.
2. Adds `"wh012j"` and `"whj"` to the MC@NLO / MadGraph parser in `beginRun()`.
3. Ensures that if `m_HiggsProdMode` was positively identified in `beginRun()`, the event-level fallback heuristic in `produce()` does not overwrite it:

```diff
--- a/GeneratorInterface/RivetInterface/plugins/HTXSRivetProducer.cc
+++ b/GeneratorInterface/RivetInterface/plugins/HTXSRivetProducer.cc
@@ -74,7 +74,7 @@ void HTXSRivetProducer::produce(edm::Event& iEvent, const edm::EventSetup&) {
 
     if (_prodMode == "AUTO") {
       // for these prod modes, don't change what is set in BeginRun
-      if (m_HiggsProdMode != HTXS::GGF && m_HiggsProdMode != HTXS::VBF && m_HiggsProdMode != HTXS::GG2ZH) {
+      if (m_HiggsProdMode == HTXS::UNKNOWN) {
         unsigned nWs = 0;
         unsigned nZs = 0;
@@ -213,6 +213,11 @@ void HTXSRivetProducer::beginRun(edm::Run const& iRun, edm::EventSetup const& es
             m_HiggsProdMode = HTXS::QQ2ZH;
             break;
           }
+          if (line.find("HWJ") != std::string::npos || line.find("HW_") != std::string::npos || line.find("Process: HW") != std::string::npos) {
+            edm::LogInfo("HTXSRivetProducer") << iLine << " " << line << std::endl;
+            m_HiggsProdMode = HTXS::WH;
+            break;
+          }
           if (line.find("ggHZ") != std::string::npos) {
             edm::LogInfo("HTXSRivetProducer") << iLine << " " << line << std::endl;
             m_HiggsProdMode = HTXS::GG2ZH;
```

---

## 8. The 2024 Generation & Validation Suite

This directory provides an automated, production-grade suite extending the `HH4WBoosted` simulation framework to 2024 (`NanoAODv15`):

```text
nanov15-wh-htxs-investigation/
├── patches/
│   └── cmssw_htxs_hwj.patch            # The HTXSRivetProducer C++ fix
├── configs/
│   ├── fragments/                      # 2024 Pythia8 generator fragments (W+H, ZH)
│   └── pileup/                         # Official 2024 PreMix dataset configuration
├── scripts/
│   ├── setup_cmssw_env.sh              # Environment & release bootstrapper
│   ├── run_mini_to_nano.sh             # [MODE 1] Standalone MiniAOD -> NanoAOD driver
│   └── run_full_chain_2024.sh          # [MODE 2] Full 4-step chain: Gridpack -> NanoAODv15
├── condor/
│   ├── submit_mini_to_nano.sub         # HTCondor submit file for MiniAOD -> NanoAOD
│   ├── submit_full_chain_2024.sub      # HTCondor submit file for Full Chain
│   ├── condor_mini_to_nano_wrapper.sh  # Condor worker script for Mini -> Nano
│   ├── condor_full_chain_wrapper.sh    # Condor worker script for Full Chain
│   └── launch_condor.sh                # Interactive Condor job launcher
└── validation/
    ├── test_patch_validation.sh        # Side-by-side automated proof script
    └── compare_htxs_results.py         # Event-by-event verification & R=0.6 benchmark tool
```

### 8.1 Mode 1: Standalone MiniAOD $\to$ NanoAOD (`run_mini_to_nano.sh`)
Processes existing 2024 MiniAOD files directly into NanoAODv15 with or without the patch:
```bash
# Dry run: generate cmsDriver python configuration without executing:
./scripts/run_mini_to_nano.sh --input /path/to/miniaod.root --no-exec

# Produce 200 events with the patch compiled on the fly:
./scripts/run_mini_to_nano.sh \
    --input /store/mc/RunIII2024Summer24MiniAODv6/.../sample.root \
    --events 200 \
    --apply-patch \
    --output nanoaod_patched.root
```

### 8.2 Mode 2: Full 4-Step Chain (`run_full_chain_2024.sh`)
Executes the full chain from gridpack to NanoAODv15 in one command:
```bash
# Dry run:
./scripts/run_full_chain_2024.sh --no-exec

# Run 100 events end-to-end:
./scripts/run_full_chain_2024.sh \
    --fragment configs/fragments/WplusH_Hto2B_WtoLNu_13p6TeV_powhegMINLO_fragment.py \
    --events 100 \
    --seed 12345 \
    --output-dir ./output_2024 \
    --apply-patch
```

### 8.3 Mode 3: Automated Side-by-Side Proof (`test_patch_validation.sh`)
Generates 50 events unpatched, 50 events patched, and runs `compare_htxs_results.py`:
```bash
# Dry run:
./validation/test_patch_validation.sh --no-exec

# Full execution:
./validation/test_patch_validation.sh --events 50
```

### 8.4 Mode 4: HTCondor Batch Submission (`condor/launch_condor.sh`)
```bash
# Test submission preparation (dry run):
./condor/launch_condor.sh --dry-run

# Submit 10 parallel MiniAOD -> NanoAOD jobs (500 events each):
./condor/launch_condor.sh --mode mini2nano --input-file "<MINIAOD_LFN>" --njobs 10 --events 500
```

---

## 9. Verification & Diagnostics Tooling

The standalone Python tool [`inspect_nanov15_htxs.py`](inspect_nanov15_htxs.py) inspects any NanoAOD sample:
```bash
# Verify all 11 survey processes:
./inspect_nanov15_htxs.py --entries 5

# Inspect specific sample:
./inspect_nanov15_htxs.py --process WplusH_Hto2B_WtoLNu --verbose
```

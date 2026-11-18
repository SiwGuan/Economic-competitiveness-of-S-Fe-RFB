# Economic competitiveness of polysulfide–ferrocyanide

Python code for the techno-economic assessment (TEA) of polysulfide–ferrocyanide (S–Fe) redox flow batteries. The model estimates energy- and power-related capital costs, financing, component replacement, maintenance, lifetime delivered energy and levelized cost of storage (LCOS).

## Scope and provenance

The author's original `Fe-SRFB TEA.py` is preserved byte-for-byte in `original/`. `SOURCE_PROVENANCE.json` records its SHA-256 checksum. The eight calculation functions in `tea_model.py` retain the original function source text. The separate `run_tea.py` adds configuration loading, explicit execution and CSV/JSON export; it does not change the equations.

The original script saves **OCV = 1.77 V and energy = 8,000 kWh**, which is a prospective scenario, not the 0.97 V baseline. Its original entry point also runs a 1,000-point efficiency sweep and writes `all_results.csv` in the current directory. Use the portable runner below instead. It needs no third-party libraries and refuses to overwrite an existing output directory.

This repository covers the supplied **S–Fe TEA model**. It does not contain the VRFB benchmark code, SimaPro/ecoinvent data, LCA calculations, experimental records or a complete regeneration pipeline for all manuscript figures. Higher-voltage scenarios are modelling scenarios, not demonstrated cell measurements.

## Quick start

Python 3.10 or newer is recommended. No package installation is required for `run_tea.py`.

```bash
python run_tea.py --config configs/baseline_4h.json --output results/baseline_4h --daily
python run_tea.py --config configs/baseline_8h.json --output results/baseline_8h
python run_tea.py --config configs/source_defaults.json --output results/source_defaults
```

Each run writes `parameters.json`, `summary.json` and `summary.csv`. `--daily` also writes daily delivered energy, discounted delivered energy and discounted charging-loss costs for the modelled operating period. Use a new output-directory name for each run.

## Reproduction checks

| Configuration | Power | Energy | OCV | Capital cost (EUR/kWh) | LCOS (EUR/MWh) |
|---|---:|---:|---:|---:|---:|
| `baseline_4h.json` | 1 MW | 4 MWh | 0.97 V | 349.103433 | 344.425517 |
| `baseline_8h.json` | 1 MW | 8 MWh | 0.97 V | 220.507294 | 291.234485 |
| `source_defaults.json` | 1 MW | 8 MWh | 1.77 V | 153.423460 | 265.982252 |

All three configurations use `eta_rt = 0.81`. The first two change only `OCV` and/or `E_b_nom` relative to the supplied source; every other model input is retained. The 1.77 V configuration does not incorporate the additional performance changes in a combined improvement scenario.

The checked example outputs are in `examples/`. Currency labels follow the manuscript's EUR convention; this packaging step performs no currency conversion, price-year adjustment or independent price validation.

Run the verification suite:

```bash
python -m unittest discover -s tests -v
```

The suite verifies source integrity, identical calculation-function syntax, numerical agreement with the archived source and the configuration/export workflow. Numerical reproduction verifies the software packaging, not the scientific validity of every modelling assumption.

## Sensitivity analysis

The following reproduces the type of efficiency scan configured in the supplied script:

```bash
python run_tea.py --config configs/source_defaults.json --output results/efficiency_scan --sweep eta_rt --start 0.6 --stop 1.0 --points 1000
```

It adds `sensitivity.csv` to the output directory. The endpoints and number of points are explicit. Other scalar inputs can be scanned by changing `--sweep`. A scan of either `DoD_max` or `DOD_max` updates both names together.

These are one-at-a-time deterministic sensitivities. Other parameters remain fixed. The scan does not impose a coupled relation between current density, resistance and round-trip efficiency, and its ranges are not confidence intervals. Select ranges appropriate to the intended scenario; an invalid discharge voltage or mass balance is rejected.

## Inputs and units

Every configuration contains the complete scalar input set. Key conventions are:

| Input | Meaning and unit |
|---|---|
| `P_b_nom`, `E_b_nom` | Rated power in kW and energy in kWh; duration is energy/power |
| `OCV`, `i_d`, `ASR` | Open-circuit voltage (V), current density (mA/cm²), area-specific resistance (ohm cm²) |
| `eta_rt`, `eta_sys_d` | Round-trip efficiency and auxiliary discharge efficiency, as fractions |
| `DoD_max`, `DOD_max` | Depth-of-discharge fraction; the source uses two names and the runner requires equality |
| `conc_act_anode`, `conc_act_catholyte` | Active-species concentrations in mol/L, retaining the source's species basis |
| `MW_active_anode`, `MW_active_Catholyte` | Source model molecular weights in kg/mol; not bare-element molar masses |
| `rho_el_anode`, `rho_el_catholyte` | Electrolyte densities in kg/L |
| `c_active_anode`, `c_active_Catholyte`, `c_SE_anode`, `c_SE_Catholyte` | Mass-specific material costs in EUR/kg |
| `C_fabr_sol`, `C_tank_vol` | Fabrication and tank costs in EUR/L |
| `c_m`, `c_BP`, `c_felt`, `c_frame`, `c_EP`, `c_IP`, `c_CC` | Area-related component costs in EUR/m² |
| BOP and assembly `c_*` terms | Power-specific costs in EUR/kW, as in the source |
| `N` | Number of cells used in the source's stack-cost equation |
| `N_y`, `t_rep_P`, `n_rep_P` | Operating years, replacement interval in years and number of replacement events |
| `f_d`, `d_r`, `r_d_y`, `r_i_y` | Debt fraction, annual debt interest, annual discount and annual electricity-price inflation, as fractions |
| `r_CO`, `r_ED`, `r_time` | Crossover and electrolyte decay per modelled equivalent cycle, and calendar fade per day, as fractions rather than percent |
| `cyc_day`, `cap_lim` | Nominal cycles per day and maintenance-trigger capacity fraction |
| `c_el` | Electricity price in EUR/kWh; 0.125 corresponds to 125 EUR/MWh |
| `O_cost` | Energy-specific servicing-cost input in EUR/kWh of rated capacity |

## Retained implementation conventions

To preserve the supplied results, the following source behaviours are unchanged:

- Daily degradation-cycle counters increase by `DOD_max * cyc_day`; daily delivered energy is `E_b_nom * cyc_day * available_capacity`.
- The routine contains both servicing and rebalancing branches and assigns a charging factor of 1.5 on a triggered maintenance day. These are retained implementation conventions; the repository does not independently establish their physical applicability to an asymmetric chemistry.
- Fixed annual O&M is hard-coded as `13 * P_b_nom` in the original function. The original `OM_power_fixed`, `OM_energy_fixed` and `om` arguments are retained, but are not active controls of that term.
- The original discounting, electricity-price escalation and indexing conventions are retained, including the indexing in `levelized_cost`.
- Source parameter values are not automatically reconciled with every SI table. The JSON files are the authoritative inputs for the numerical outputs in this repository.

These details are documented for reproducibility. No unapproved equation or parameter correction has been introduced during repository preparation.

## Methodological reference

Cremoncini, D. et al. *Techno-economic analysis of Aqueous Organic Redox Flow Batteries: Stochastic investigation of capital cost and levelized cost of storage*. Applied Energy **360**, 122738 (2024). https://doi.org/10.1016/j.apenergy.2024.122738

The accompanying manuscript and Supplementary Information describe the study assumptions and other sources. This repository documents the author-supplied implementation; it is not represented as the original software from the cited publication.

## Reuse

No open-source licence has been assigned in this initial deposit. Public accessibility does not by itself grant a software reuse licence. A licence can be added by the rights holders in a subsequent release.

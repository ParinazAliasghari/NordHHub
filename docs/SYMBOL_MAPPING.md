# SYMBOL MAPPING (GAMS ↔ Python)

## Introduction
This guide maps core model symbols between the original GAMS implementation (`src/MGET.gms`, `src/load_input_from_Excel.gms`) and the Python/Pyomo implementation (`scr/model.py`, `scr/data_loading.py`).

Scenario data in this repository is loaded from CSV files equivalent to the original Excel sheets:
- `arcs.csv` (Sheet A)
- `nodes.csv` (Sheet N)
- `consumption.csv` (Sheet C)
- `production.csv` (Sheet P)
- `regasification.csv` (Sheet R)
- `storage.csv` (Sheet W)
- `other.csv` (Sheet O)
- `timeseries.csv` (scaleUp / planning data)

Notes:
- Mapping is based on code inspection, not only on external tables.
- If a GAMS symbol has no active Python equivalent in `scr/model.py`, Python is marked `—`.
- Units below use the project unit convention provided in your unit consistency table.

## Sets

| Gams | Python | Discription | Unit |
|---|---|---|---|
| `A` | `model.A` | Arcs | 1 |
| `CN` | `model.CN` | Countries | 1 |
| `F` | `model.E` | Fuels / energy carriers | 1 |
| `N` | `model.N` | Nodes (NUTS3 level) | 1 |
| `NUTS2` | `model.NUTS2` | NUTS2 regions | 1 |
| `RGN` | `model.RGN` | Regions | 1 |
| `Z` | `model.Z` | Deficit/surplus penalty classes | 1 |
| `Y` | `model.Y` | Planning years | year label |
| `H` | `model.H` | Operational slices | hour-slice label |
| `yrep` | — | Reporting-year helper set in GAMS loader | 1 |
| `aux_tot`, `aux_rep`, `aux_rep_c` | — | Auxiliary/report label sets (GAMS only) | 1 |

## Parameters

| Gams | Python | Discription | Unit |
|---|---|---|---|
| `bigM` | `model.bigM` | Global big-M scalar | 1 |
| `YearStep` (from `dat_o`) | `model.yearstep` | Years per planning step | year/step |
| `DiscRate` (from `dat_o`) | `model.discRate` | Discount rate | 1/year |
| `r(y)` | `model.r[y]` | Discount factor by year | 1 |
| `EOH(y)` | `model.EOH[y]` | End-of-horizon multiplier | 1 |
| `ypred(y,y)` | `model.ypred[y2,y]` | Immediate predecessor mapping | 1 |
| `yscai(y,y)` | `model.yscai[y2,y]` | Successor mapping | 1 |
| `scaleUp(h)` | `model.scaleUp[h]` | Hours represented by slice | h |
| `vola2(e)` | `model.vola2[e]` | Arc-capacity usage multiplier | 1 |
| `vols2(e)` | `model.vols2[e]` | Storage-capacity usage multiplier | 1 |
| `c_z(z,e)` | `model.c_z[z,e]` | Penalty cost coefficients | €/GWh |
| `c_bl(e,f)` | `model.c_bl[e,f]` | Blending variable cost | €/GWh |
| `ub_bl(e,f)` | `model.ub_bl[e,f]` | Max blending fraction | 1 |
| `is_g(e)` | `model.is_g[e]` | Gas classifier | 1 |
| `is_h(e)` | `model.is_h[e]` | Hydrogen classifier | 1 |
| `not_g(e)` | `model.not_g[e]` | Not-gas classifier | 1 |
| `not_h(e)` | `model.not_h[e]` | Not-hydrogen classifier | 1 |
| `n_in_c(n,c)` | `model.n_in_c[n,cn]` | Node-to-country mapping | 1 |
| `n_in_2(n,nuts2)` | `model.n_in_2[n,nuts2]` | Node-to-NUTS2 mapping | 1 |
| `n_in_r(n,rgn)` | `model.n_in_r[n,rgn]` | Node-to-region mapping | 1 |
| `dmd(n,e,y,h)` | `model.dmd[n,e,y,h]` | Nodal demand | GWh |
| `dmd2(nuts2,e,y,h)` | `model.dmd2[g,e,y,h]` | NUTS2 hydrogen demand | GWh |
| `cap_p(n,e,y,h)` | `model.cap_p[n,e,y,h]` | Production capacity upper bound | GWh |
| `lb_p(n,e,y,h)` | `model.lb_p[n,e,y,h]` | Production lower bound | GWh |
| `c_p(n,e,y)` | `model.c_p[n,e,y]` | Production marginal cost | €/GWh |
| `c_lr(n,e)` | `model.c_lr[n,e]` | Regasification variable cost | €/GWh |
| `ub_r(n,e)` / `dat_r(...,'ub')` | `model.ub_r[n,e]` | Regasification capacity bound | GWh |
| `a_s(a,n)` | `model.a_s[a,n]` | Arc-start incidence | 1 |
| `a_e(a,n)` | `model.a_e[a,n]` | Arc-end incidence | 1 |
| `opp(ai,ao)` | `model.opp[ai,ao]` | Opposite-arc mapping | 1 |
| `is_bid(a)` | `model.is_bid[a]` | Arc already bidirectional flag | 1 |
| `cap_a(a,e,y)` | `model.cap_a[a,e,y]` | Arc base capacity | GWh-capacity |
| `c_a(a,e,y)` | `model.c_a[a,e,y]` | Arc flow unit cost | €/GWh |
| `c_ax(a,e,y)` | `model.c_ax[a,e,y]` | Arc expansion investment cost | €/GWh-capacity (per step) |
| `c_ab(a,e,y)` | `model.c_ab[a,e,y]` | Bidirectional variable investment cost | €/GWh-capacity (per step) |
| `f_ab(a,y)` | `model.f_ab[a,y]` | Bidirectional fixed investment cost | € (per step) |
| `c_ar(a,e,f,y)` | `model.c_ar[a,e,f,y]` | Arc repurposing variable cost | €/GWh-capacity (per step) |
| `f_ar(a,e,f,y)` | `model.f_ar[a,e,f,y]` | Arc repurposing fixed cost | € (per step) |
| `e_a(a,e)` | `model.e_a[a,e]` | Arc efficiency (1-loss) | 1 |
| `cap_we(n,e,y)` | `model.cap_we[n,e,y]` | Storage extraction cap | GWh |
| `cap_wi(n,e,y)` | `model.cap_wi[n,e,y]` | Storage injection cap | GWh |
| `cap_ww(n,e,y)` | `model.cap_ww[n,e,y]` | Storage working capacity | GWh-capacity |
| `c_we(n,e)` | `model.c_we[n,e]` | Storage extraction variable cost | €/GWh |
| `e_w(n,e)` | `model.e_w[n,e]` | Storage cycle efficiency | 1 |
| `dat_w(n,e,'H2-ready')` | `model.h2_ready[n,e]` | Storage H2-ready indicator | 1 |
| `LossMax` (from `dat_o`) | `model.lossMax` | Max loss floor in efficiency formula | 1 |
| `anm(a,n,m)` | — | Arc existence helper used in GAMS loader | 1 |
| `c_az` | — | Arc-expansion feasibility penalty coefficient | €/GWh (penalty-like) |
| `lb_ax(a,e,y)` | — | Expansion lower bound (GAMS loader/reporting) | GWh-capacity |
| `ub_ax(a,y)` | — | Expansion upper bound (GAMS loader/reporting) | GWh-capacity |
| `stor_i`, `stor_x` | — | Storage bound helper tables (GAMS comments/reporting) | GWh |
| `dat_o`, `dat_a`, `dat_c`, `dat_p`, `dat_r`, `dat_w`, `dat_n` | `loaded_inputs[...]` (loader stage) | Raw input tables before model params | source table |

## Variables

| Gams | Python | Discription | Unit |
|---|---|---|---|
| `TC` (Free Variable) | `model.TC` | Total system cost linking variable | € |
| `F_A(a,e,y,h)` | `model.F_A[a,e,y,h]` | Arc flow | GWh |
| `Q_P(n,e,y,h)` | `model.Q_P[n,e,y,h]` | Production | GWh |
| `Q_S(n,e,y,h)` | `model.Q_S[n,e,y,h]` | Served demand (sales) | GWh |
| `Q_I(n,e,y,h)` | `model.Q_I[n,e,y,h]` | Storage injection | GWh |
| `Q_E(n,e,y,h)` | `model.Q_E[n,e,y,h]` | Storage extraction | GWh |
| `Q_R(n,e,y,h)` | `model.Q_R[n,e,y,h]` | Regasification flow | GWh |
| `Q_B(n,e,f,y,h)` | `model.Q_B[n,e,f,y,h]` | Blending flow from `e` into `f` | GWh |
| `ZDS(z,n,e,y,h)` | `model.ZDS[z,n,e,y,h]` | Nodal deficit/surplus slack | GWh |
| `ZN2(nuts2,e,y,h)` | `model.ZN2[g,e,y,h]` | NUTS2 hydrogen shortage | GWh |
| `K_A(a,e,y)` | `model.K_A[a,e,y]` | Arc capacity stock | GWh-capacity |
| `K_OPP(a,e,y)` | `model.K_OPP[a,e,y]` | Opposite-direction usable capacity | GWh-capacity |
| `X_A(a,e,y)` | `model.X_A[a,e,y]` | Arc expansion decision | GWh-capacity |
| `K_BD(a,e,y)` | `model.K_BD[a,e,y]` | Capacity priced by bidirectional variable cost | GWh-capacity |
| `K_RA(a,e,f,y)` | `model.K_RA[a,e,f,y]` | Repurposed arc capacity from `e` to `f` | GWh-capacity |
| `K_W(n,e,y)` | `model.K_W[n,e,y]` | Storage working capacity | GWh-capacity |
| `K_RW(n,e,f,y)` | `model.K_RW[n,e,f,y]` | Repurposed storage capacity from `e` to `f` | GWh-capacity |
| `BD(a,y)` | `model.BD[a,y]` | Bidirectional state indicator (continuous 0..1) | 1 |
| `B_BD(a,y)` (binary) | `model.B_BD[a,y]` | Bidirectional investment binary | 1 |
| `B_AR(a,e,f,y)` (binary) | `model.B_AR[a,e,f,y]` | Arc repurposing binary | 1 |
| `B_WR(n,e,f,y)` (binary) | `model.B_WR[n,e,f,y]` | Storage repurposing binary | 1 |
| Objective `obj` equation | `model.obj_total_cost` | Min-cost objective expression | € |
| `ZXA_FS(a,y)` (commented in GAMS) | — | Feasibility slack for expansion upper limit (not active) | GWh-capacity |

## Scope reminder
This table reflects the active Python model in `scr/core/model.py` and the active GAMS model equations in `src/MGET.gms`. Historical backup files may contain additional symbols not listed here.

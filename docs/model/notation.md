## Index sets

- `A` : set of directed arcs (pipelines). Each arc can have capacity for multiple fuels.
- `rev[a]` : reverse arc mapping; if `a = (i, j)` then `rev[a] = (j, i)` (when the reverse exists). 
- `C` : set of countries.
- `E` : set of fuels (energy carriers), e.g. NG, H2, CO2.
- `N` : set of nodes.
- `N_c ⊆ N` : nodes in country `c`.
- `N_EU ⊆ N` : nodes in the European Union.
- `Y` : set of investment periods (e.g. every fifth year).
- `H` : set of operational periods (representative hours).
- `H_y ⊆ H` : operational periods belonging to investment period `y`.
- `pred[y]` : immediate predecessor of investment period `y`.
- `succ[y]` : successor periods of `y` including itself.
## Parameters

Unless otherwise stated, parameters may depend on investment period `y` and fuel `e`, and many also depend on operational period `h`. 

- `bigM` [1]  
  Large constant used in several constraints (e.g., McCormick reformulations).

### Costs
- `c_a[a,e,y]` [€/MWh] : variable transport/usage cost on arc `a`.
- `c_b[a,e,y]` [€ or €/capacity] : cost of making an arc bidirectional (see also fixed part).
- `f_b[a,y]` [€] : fixed cost of making arc bidirectional.
- `c_r[a,e,f,y]` [€/MWh] : repurposing cost from fuel `e` to fuel `f` on arc `a`.
- `f_r[a,e,f,y]` [€] : fixed repurposing cost.
- `c_x[a,e,y]` [€/MWh] : expansion cost of arc capacity.
- `c_p[n,e,y]` [€/MWh] : supply cost (production/import) at node `n`.
- `c_dz[e]` [€/MWh] : penalty for demand deficit.
- `c_pz[e]` [€/MWh] : penalty for supply deficit. 

### Capacities, potentials, demand
- `cap_a[a,e,y]` [bcm/h] : exogenous initial arc capacity.
- `cap_p[n,e,y,h]` [GWh/h] : supply potential.
- `dmd[n,e,y,h]` [GWh/h] : demand (or export) at node `n`. 

### Efficiencies and scaling
- `eta_a[e,a]` [%] : arc efficiency (1 − loss rate).
- `scale[h]` [1] : number of hours represented by operational hour `h`.

### Storage bounds (exogenous operation limits)
- `stor_i[n,e,y,h,lo]`, `stor_i[n,e,y,h,ub]` [GWh/h] : injection bounds.
- `stor_e[n,e,y,h,lo]`, `stor_e[n,e,y,h,ub]` [GWh/h] : extraction bounds.

### Expansion bounds and discounting
- `lb_x[a,e,y]` [GWh/h] : minimum expansion (planned expansion).
- `ub_x[a,y]` [GWh/h] : maximum expansion.
- `r[y]` [1] : discount factor. 
### Unit conversions
- `vol2_a[e]` [TWh/bcm] : volume→energy conversion for arcs.
- `vol2_w[e]` [TWh/bcm] : volume→energy conversion for storages. 

### Blending
- `blend_ub[...]` : upper bound on blending share (define exact indices used).
- ## Decision variables

All variables are nonnegative unless stated otherwise. `B_B` and `B_R` are binary. `BD` is binary but can be implemented as continuous with upper bound 1. 

### Binary / indicator variables
- `B_B[a,y] ∈ {0,1}` : invest to make arc `a` bidirectional.
- `BD[a,y] ∈ [0,1]` (or `{0,1}`) : directional traversability indicator.
- `B_R[a,e,f,y] ∈ {0,1}` : repurpose arc `a` from fuel `e` to fuel `f`.
- `B_W[w,e,f,y] ∈ {0,1}` : repurpose storage `w` from fuel `e` to fuel `f`.

### Continuous variables (flows and capacities)
- `F_A[a,e,y,h]` [GWh/h] : flow on arc `a`.
- `K_A[a,e,y]` [GWh/h] : fuel-specific transport capacity.
- `K_OPP[a,e,y]` [GWh/h] : usable capacity in opposite direction.
- `X_A[a,e,y]` [GWh/h] : capacity expansion.

- `Q_P[n,e,y,h]` [GWh/h] : supply (production/import).
- `Q_S[n,e,y,h]` [GWh/h] : deliveries (sales: demand/export).

- `Q_W_inj[n,e,y,h]` [GWh/h] : storage injection.
- `Q_W_ext[n,e,y,h]` [GWh/h] : storage extraction.

- `K_W[w,f,y]` [GWh] : storage working gas capacity.
- `K_I[w,f,y]` [GWh/h] : injection capacity.
- `K_E[w,f,y]` [GWh/h] : extraction capacity.

- `H2_blend[...]` [GWh/h] : hydrogen blended into natural gas (define indices used). 

### Slack variables (feasibility)
- `Z_D[n,e,y,h]` [GWh/h] : demand deficit.
- `Z_L[n,e,y,h]` [GWh/h] : supply deficit due to lower bound.
- `Z_U[n,e,y,h]` [GWh/h] : supply surplus due to upper bound. 

## Implementation note (Python)

# In the Python implementation, sets are stored as Python containers (lists/sets), and parameters are stored as dictionaries keyed by tuples, e.g. `cap_p[(n,e,y,h)]`. Arc incidence is represented via `in_arcs[n]` and `out_arcs[n]`, and the reverse-arc mapping is represented by `rev[a]`. 



# Demo 04 — Arc Repurposing (G→H)

Scenario: `demo04_repurpose`  
Folder: [data/demo04_repurpose](../../data/demo04_repurpose)

---

## Purpose

This scenario demonstrates arc capacity repurposing from natural gas (G) to hydrogen (H) between time periods, activating repurposing cost variables `B_AR` and `K_RA`.

---

## How to run

From repository root:

```bash
python -m scr.core.solve_pipeline data/demo04_repurpose/other.csv
```

---

## Input Data

### nodes.csv

| n | cn | nuts2 | G | H |
|---|---|---|---|---|
| N1 | C1 | R1 | 1 | 1 |
| N2 | C2 | R2 | 1 | 1 |

Interpretation:

- Both nodes support both carriers (G=1, H=1)
- **Critical:** N2 is in different NUTS2 region (R2) to enforce node-level hydrogen demand

---

### arcs.csv

| a | start | end | f | len | off | cal_r | cap |
|---|---|---|---|---:|---:|---:|---:|
| N1_N2 | N1 | N2 | G | 160 | 0 | 1 | 6 |
| N1_N2_H | N1 | N2 | H | 160 | 0 | 0 | 0 |

Interpretation:

- N1_N2: Initially carries G with capacity=6, cal_r=1 allows repurposing
- N1_N2_H: Defined for H but cap=0 (provides expansion option, not used)

---

### production.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 6 | 6 |
| N1 | G | 2030 | 0 | 0 |
| N1 | H | 2025 | 0 | 0 |
| N1 | H | 2030 | 6 | 6 |
| N2 | G | 2025-2030 | 0 | 0 |
| N2 | H | 2025-2030 | 0 | 0 |

Interpretation:

- N1 produces G in 2025, switches to H in 2030

---

### consumption.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N1 | G,H | 2025-2030 | 0 | 0 |
| N2 | G | 2025 | 6 | 6 |
| N2 | G | 2030 | 0 | 0 |
| N2 | H | 2025 | 0 | 0 |
| N2 | H | 2030 | 6 | 6 |

Interpretation:

- N2 consumes G in 2025, switches to H in 2030

---

### timeseries.csv

| y | h | scaleup |
|---:|---:|---:|
| 2025 | 1 | 1 |
| 2025 | 2 | 1 |
| 2030 | 1 | 1 |
| 2030 | 2 | 1 |

---

### other.csv

| param | indx1 | indx2 | value |
|---|---|---|---:|
| BFPipe |  |  | 1 |
| BIPipe |  |  | 3 |
| BIPipe | G |  | 3 |
| BIPipe | H |  | 3 |
| RepurpArc |  |  | 1 |
| RepurpArc | G | H | 1 |
| RepurpArc | Fix |  | 0.5 |
| RepurpArc | Fix | G | 0.5 |
| RepurpArc | Fix | H | 0.5 |
| Vola2 | G |  | 1 |
| Vola2 | H |  | 1 |
| Pipe | Len | Std | 80 |
| OffshMult |  |  | 20 |
| YearStep |  |  | 5 |

Only parameters relevant for this demo:

- Production cost parameters
- Slack penalties (`ZDS`, `ZN2`)
- Transport cost parameters
- Expansion cost parameters
- Repurposing cost parameters

Arc flow cost coefficient (`c_a`) is computed as:

$$
 c_a = \text{BFPipe} \cdot \text{Vola2}(f) \cdot \frac{(\text{len} + \text{offsh\_mult} \cdot \text{off}) \cdot \text{cal\_c}}{\text{PipeLenStd}}
$$

Arc expansion cost coefficient (`c_{ax}`) is computed as:

$$
 c_{ax} = \text{BIPipe}(f) \cdot \frac{(\text{len} + \text{offsh\_mult} \cdot \text{off}) \cdot \text{cal\_x}}{\text{PipeLenStd} \cdot \text{YearStep}}
$$

Repurposing variable cost coefficient (`c_{ar}`) is computed as:

$$
 c_{ar} = \text{RepurpArc}(e,f) \cdot \frac{(\text{len} + \text{off}) \cdot \text{cal\_r}}{\text{PipeLenStd} \cdot \text{YearStep}}
$$

Repurposing fixed cost coefficient (`f_{ar}`) is computed as:

$$
 f_{ar} = \text{RepurpArc\_Fix}(f) \cdot \text{Vola2}(e) \cdot \frac{(\text{len} + \text{off}) \cdot \text{cal\_r}}{\text{PipeLenStd} \cdot \text{YearStep}}
$$

With demo04 inputs:

$$
 c_a = 1 \cdot 1 \cdot \frac{(160 + 20 \cdot 0) \cdot 1}{80} = 2.0
$$

$$
 c_{ax} = 3 \cdot \frac{(160 + 20 \cdot 0) \cdot 1}{80 \cdot 5} = 1.2
$$

$$
 c_{ar} = 1 \cdot \frac{(160 + 0) \cdot 1}{80 \cdot 5} = 0.4
$$

$$
 f_{ar} = 0.5 \cdot 1 \cdot \frac{(160 + 0) \cdot 1}{80 \cdot 5} = 0.2
$$

---

## Results Summary

- objective = 53.66
- production_cost = 22.87
- arc_flow_cost = 24.00
- repurpose_fixed_cost = 0.27
- repurpose_variable_cost = 6.52
- total_reconstructed = 53.66
- sum_ZDS = 0.0
- sum_ZN2 = 0.0

---

## Arc Flows

| a | f | y | total_flow |
|---|---|---:|---:|
| N1_N2 | G | 2025 | 12.0 |
| N1_N2 | H | 2030 | 12.0 |

---

## Arc Repurposing

| metric | a | e | f | y | value |
|---|---|---|---|---:|---:|
| B_AR | N1_N2 | G | H | 2030 | 1.0 |
| K_RA | N1_N2 | G | H | 2030 | 6.0 |

Interpretation:

- Binary decision B_AR = 1: Arc N1_N2 is repurposed from G to H in 2030
- Continuous capacity K_RA = 6.0: All 6 units of G capacity converted to H capacity

---

## Arc Capacity Evolution

| a | f | y | K_A (capacity) | Source |
|---|---|---:|---:|---|
| N1_N2 | G | 2025 | 6.0 | Initial cap |
| N1_N2 | H | 2030 | 6.0 | K_RA[N1_N2,G,H,2030] |

Capacity mechanism:

```
K_A[a,f,y] = sum_e K_RA[a,e,f,y] + X_A[a,f,y-1]

For N1_N2, H, 2030:
K_A[N1_N2,H,2030] = K_RA[N1_N2,G,H,2030] + X_A[N1_N2,H,2025]
                   = 6.0 + 0
                   = 6.0
```

---

## Node Mass Balance

Model balance structure:

Residual(n,f,y,h) =
Production(n,f,y,h)
+ Σ inflow
− Σ outflow
− Consumption(n,f,y,h)
− SlackTerms

Since demo04 has no storage / regasification activity:

Residual = Production + inflow − outflow − Consumption

---

### Hourly Balance Check

| y | h | n | f | Production | Inflow | Outflow | Consumption | Residual |
|---:|---:|---|---|---:|---:|---:|---:|---:|
| 2025 | 1 | N1 | G | 6 | 0 | 6 | 0 | 0 |
| 2025 | 1 | N2 | G | 0 | 6 | 0 | 6 | 0 |
| 2025 | 2 | N1 | G | 6 | 0 | 6 | 0 | 0 |
| 2025 | 2 | N2 | G | 0 | 6 | 0 | 6 | 0 |
| 2030 | 1 | N1 | H | 6 | 0 | 6 | 0 | 0 |
| 2030 | 1 | N2 | H | 0 | 6 | 0 | 6 | 0 |
| 2030 | 2 | N1 | H | 6 | 0 | 6 | 0 | 0 |
| 2030 | 2 | N2 | H | 0 | 6 | 0 | 6 | 0 |

---

## What this demo confirms

✔ Arc capacity can be repurposed from one carrier to another  
✔ Repurposing costs (fixed + variable) activate correctly  
✔ B_AR and K_RA variables function as expected  
✔ Model prefers repurposing over new investment when costs favor it  
✔ Multi-carrier network with temporal transitions works correctly  
✔ No shortages or slack usage


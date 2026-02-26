# Demo 05 — LNG Regasification

Scenario: `demo05_regas`  
Folder: [data/demo05_regas](../../data/demo05_regas)

---

## Purpose

This scenario demonstrates LNG regasification by activating the regasification variable `Q_R` to supply demand through imported LNG at a terminal node.

---

## How to run

From repository root:

```bash
python -m scr.core.solve_pipeline data/demo05_regas/other.csv
```

---

## Input Data

### nodes.csv

| n | cn | nuts2 | G | H |
|---|---|---|---|---|
| N1 | C1 | R1 | 1 | 0 |
| N2 | C1 | R1 | 1 | 0 |

Interpretation:

- Both nodes support gas carrier
- N1 represents LNG import terminal

---

### arcs.csv

| a | start | end | f | len | off | cal_c | cap |
|---|---|---|---|---:|---:|---:|---:|
| N1_N2 | N1 | N2 | G | 160 | 0 | 0 | 10 |

Interpretation:

- Flow allowed from N1 (terminal) to N2 (consumption)
- Capacity = 10 to accommodate peak demand

---

### production.csv

| n | f | y | 1 | 2 | MC |
|---|---|---:|---:|---:|---:|
| N1 | G | 2025 | 0 | 0 | 100 |
| N2 | G | 2025 | 0 | 0 | 1 |

Interpretation:

- N1 has no domestic production (or very expensive MC=100)
- N2 has no production available
- Force use of regasification at N1

---

### consumption.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 0 | 0 |
| N2 | G | 2025 | 6 | 8 |

Interpretation:

- N2 has demand varying by hour (6, 8)
- N1 has no local demand

---

### regasification.csv

| n | f | y | cal_c | ub |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 1 | 10 |

Interpretation:

- **Critical:** N1 has regasification capacity with ub=10
- cal_c=1: unit cost calibration factor
- ub defines hourly regasification upper bound

---

### timeseries.csv

| y | h | scaleup |
|---:|---:|---:|
| 2025 | 1 | 1 |
| 2025 | 2 | 1 |

---

### other.csv

| param | indx1 | indx2 | value |
|---|---|---|---:|
| BFPipe |  |  | 1 |
| Vola2 | G |  | 1 |
| Pipe | Len | Std | 80 |
| OffshMult |  |  | 20 |
| YearStep |  |  | 1 |

Only parameters relevant for this demo:

- Transport cost parameters
- Regasification cost (c_lr defaults to 1 for gas)

Arc flow cost coefficient (`c_a`) is computed as:

$$
 c_a = \text{BFPipe} \cdot \text{Vola2}(G) \cdot \frac{(\text{len} + \text{offsh\_mult} \cdot \text{off}) \cdot \text{cal\_c}}{\text{PipeLenStd}}
$$

With demo05 inputs:

$$
 c_a = 1 \cdot 1 \cdot \frac{(160 + 20 \cdot 0) \cdot 1}{80} = 2.0
$$

Regasification cost per unit: c_lr = 1.0 (default for gas)

---

## Results Summary

- objective = 42.00
- production_cost = 0.00
- arc_flow_cost = 28.00
- regas_cost = 14.00
- total_reconstructed = 42.00
- sum_ZDS = 0.0
- sum_ZN2 = 0.0

---

## Regasification Volumes

| n | f | y | h | Q_R |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 1 | 6.0 |
| N1 | G | 2025 | 2 | 8.0 |

Interpretation:

- N1 regasifies LNG to meet downstream demand
- Total regasification = 6 + 8 = 14 units

---

## Arc Flows

| a | f | y | total_flow |
|---|---|---:|---:|
| N1_N2 | G | 2025 | 14.0 |

Interpretation:

- All regasified gas transported from N1 to N2
- Flow matches regasification volume (14 = 6 + 8)

---

## Node Mass Balance

Model balance structure:

Residual(n,f,y,h) =
Production(n,f,y,h)
+ Regasification(n,f,y,h)
+ Σ inflow
− Σ outflow
− Consumption(n,f,y,h)
− SlackTerms

Since demo05 has no storage / blending activity:

Residual = Production + Q_R + inflow − outflow − Consumption

---

### Hourly Balance Check

| y | h | n | Production | Q_R | Inflow | Outflow | Consumption | Residual |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 2025 | 1 | N1 | 0 | 6 | 0 | 6 | 0 | 0 |
| 2025 | 1 | N2 | 0 | 0 | 6 | 0 | 6 | 0 |
| 2025 | 2 | N1 | 0 | 8 | 0 | 8 | 0 | 0 |
| 2025 | 2 | N2 | 0 | 0 | 8 | 0 | 8 | 0 |

---

## What this demo confirms

✔ LNG regasification (Q_R) activates correctly  
✔ Regasification supplies demand when local production unavailable  
✔ Regasification cost included in objective  
✔ Arc flow transports regasified LNG to consumption node  
✔ No shortages or slack usage  
✔ Mass balance satisfied with regasification term

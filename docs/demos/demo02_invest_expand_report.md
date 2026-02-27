# Demo 02 — Investment and Expansion

Scenario: `demo02_invest_expand`  
Folder: [data/demo02_invest_expand](data/demo02_invest_expand)

---

## Purpose

This scenario extends the base flow case with a second year (2030) and demonstrates arc expansion when demand exceeds base arc capacity.

---

## How to run

From repository root:

python -m scr.core.run --scenario demo02_invest_expand

---

## Input Data

### nodes.csv

| n | cn | nuts2 |
|---|---|---|
| N1 | C1 | N1 |
| N2 | C1 | N2 |

---

### arcs.csv

| a | start | end | f | len | off | cal_c | cal_x | cap | bidir |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| N1_N2 | N1 | N2 | G | 160 | 0 | 0 | 1 | 6 | 0 |

Interpretation:

- Flow allowed from `start → end`
- Carrier defined by column `f`
- No reverse flow (`bidir = 0`)
- `cal_c = 0` is treated as `1.0` in the loader

---

### production.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 6 | 6 |
| N1 | G | 2030 | 4 | 8 |
| N2 | G | 2025 | 0 | 0 |
| N2 | G | 2030 | 0 | 0 |

Interpretation:

- Hourly production profile at node `n` (year-specific)

---

### consumption.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 0 | 0 |
| N1 | G | 2030 | 0 | 0 |
| N2 | G | 2025 | 4 | 6 |
| N2 | G | 2030 | 4 | 8 |

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
| BIPipe |  |  | 1 |
| BIPipe | G |  | 1 |
| Vola2 | G |  | 1 |
| Pipe | Len | Std | 80 |
| OffshMult |  |  | 20 |
| YearStep |  |  | 5 |

Only parameters relevant for this demo:

- Production cost parameters
- Slack penalties (`ZDS`, `ZN2`)
- Transport cost parameters
- Expansion cost parameters

Arc flow cost coefficient (`c_a`) is computed as:

$$
 c_a = \text{BFPipe} \cdot \text{Vola2}(G) \cdot \frac{(\text{len} + \text{offsh\_mult} \cdot \text{off}) \cdot \text{cal\_c}}{\text{PipeLenStd}}
$$

Arc expansion cost coefficient (`c_{ax}`) is computed as:

$$
 c_{ax} = \text{BIPipe}(G) \cdot \frac{(\text{len} + \text{offsh\_mult} \cdot \text{off}) \cdot \text{cal\_x}}{\text{PipeLenStd} \cdot \text{YearStep}}
$$

With demo02 inputs:

$$
 c_a = 1 \cdot 1 \cdot \frac{(160 + 19 \cdot 0) \cdot 1}{80} = 2.0
$$

$$
 c_{ax} = 1 \cdot \frac{(160 + 19 \cdot 0) \cdot 1}{80 \cdot 5} = 0.4
$$

---

## Results Summary

- objective = 69.3
- production_cost = 21.8
- arc_flow_cost = 43.5
- arc_investment_cost = 4.0
- total_reconstructed = 69.3
- sum_ZDS = 0.0
- sum_ZN2 = 0.0

---

## Arc Flows

| a | f | y | total_flow |
|---|---|---:|---:|
| N1_N2 | G | 2025 | 10.0 |
| N1_N2 | G | 2030 | 12.0 |

---

## Arc Expansion

| a | f | y | expansion_total |
|---|---|---:|---:|
| N1_N2 | G | 2025 | 2.0 |

---

## Node Mass Balance

Model balance structure:

Residual(n,f,y,h) =
Production(n,f,y,h)
+ Σ inflow
− Σ outflow
− Consumption(n,f,y,h)
− SlackTerms

Since demo02 has no storage / regasification activity:

Residual = Production + inflow − outflow − Consumption

---

### Hourly Balance Check

| y | h | n | Production | Inflow | Outflow | Consumption | Residual |
|---:|---:|---|---:|---:|---:|---:|---:|
| 2025 | 1 | N1 | 4 | 0 | 4 | 0 | 0 |
| 2025 | 1 | N2 | 0 | 4 | 0 | 4 | 0 |
| 2025 | 2 | N1 | 6 | 0 | 6 | 0 | 0 |
| 2025 | 2 | N2 | 0 | 6 | 0 | 6 | 0 |
| 2030 | 1 | N1 | 4 | 0 | 4 | 0 | 0 |
| 2030 | 1 | N2 | 0 | 4 | 0 | 4 | 0 |
| 2030 | 2 | N1 | 8 | 0 | 8 | 0 | 0 |
| 2030 | 2 | N2 | 0 | 8 | 0 | 8 | 0 |

---

## What this demo confirms

✔ Network flow logic across multiple years  
✔ Mass balance constraints satisfied  
✔ Slack variables unused  
✔ Expansion cost is activated 
✔ Cost calculation reflects updated arc flow cost   

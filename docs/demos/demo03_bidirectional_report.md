# Demo 03 — Bidirectional Flow (B_BD and K_BD Active)

Scenario: `demo03_bidirectional`  
Folder: [data/demo03_bidirectional](data/demo03_bidirectional)

---

## Purpose

This scenario activates bidirectional costs by forcing reverse-direction flow above the base capacity of the reverse arc, which triggers `K_OPP`, `B_BD`, and `K_BD` while keeping scale factors small.

---

## How to run

From repository root:

python -m scr.core.run --scenario data/demo03_bidirectional

---

## Input Data

### nodes.csv

| n | cn | nuts2 |
|---|---|---|
# Demo 03 — Bidirectional Flow (B_BD and K_BD Active)

Scenario: `demo03_bidirectional`  
Folder: [data/demo03_bidirectional](data/demo03_bidirectional)

---

## Purpose

This scenario activates bidirectional costs by forcing reverse-direction flow above the base capacity of the reverse arc, which triggers `K_OPP`, `B_BD`, and `K_BD` while keeping scale factors small.

---

## How to run

From repository root:

python -m scr.core.run --scenario data/demo03_bidirectional

---

## Input Data

### nodes.csv

| n | cn | nuts2 |
|---|---|---|
| N1 | C1 | R1 |
| N2 | C1 | R1 |

---

### arcs.csv

| a | start | end | f | len | off | cal_c | cal_b | cap | bidir |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| N1_N2 | N1 | N2 | G | 160 | 0 | 0 | 0 | 6 | 0 |
| N2_N1 | N2 | N1 | G | 160 | 0 | 0 | 0 | 2 | 0 |

Interpretation:

- Flow allowed from `start → end` for each arc.
- Reverse direction is constrained by the lower capacity on `N2_N1` (`cap = 2`).
- `bidir = 0` ensures `is_bid = 0`, so `B_BD`/`K_BD` are not fixed to zero.
- `cal_c = 0` and `cal_b = 0` are treated as `1.0` in the loader.

---

### production.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 6 | 0 |
| N2 | G | 2025 | 0 | 6 |
| N1 | G | 2030 | 6 | 0 |
| N2 | G | 2030 | 0 | 6 |

Interpretation:

- N1 produces at `h=1`, N2 produces at `h=2` in both years.

---

### consumption.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 0 | 6 |
| N2 | G | 2025 | 6 | 0 |
| N1 | G | 2030 | 0 | 6 |
| N2 | G | 2030 | 6 | 0 |

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
| Bidir | Fix |  | 1 |
| Bidir | Var |  | 1 |
| Vola2 | G |  | 1 |
| Pipe | Len | Std | 80 |
| OffshMult |  |  | 20 |
| YearStep |  |  | 1 |

Only parameters relevant for this demo:

- Production cost parameters
- Slack penalties (`ZDS`, `ZN2`)
- Transport cost parameters
- Bidirectional cost parameters

Arc flow cost coefficient (`c_a`) is computed as:

$$
 c_a = \text{BFPipe} \cdot \text{Vola2}(G) \cdot \frac{(\text{len} + \text{offsh\_mult} \cdot \text{off}) \cdot \text{cal\_c}}{\text{PipeLenStd}}
$$

Bidirectional variable cost coefficient (`c_{ab}`) is computed as:

$$
 c_{ab} = \text{BidirVar}(G) \cdot \frac{(\text{len} + \text{off}) \cdot \text{cal\_b}}{\text{PipeLenStd} \cdot \text{YearStep}}
$$

With demo03 inputs:

$$
 c_a = 1 \cdot 1 \cdot \frac{(160 + 19 \cdot 0) \cdot 1}{80} = 2.0
$$

$$
 c_{ab} = 1 \cdot \frac{(160 + 0) \cdot 1}{80 \cdot 1} = 2.0
$$

---

## Results Summary


- objective = 80.29411764705883
- production_cost = 23.764705882352942
- arc_flow_cost = 47.529411764705884
- bidir_fixed_cost = 1.0
- bidir_variable_cost = 8.0
- total_reconstructed = 80.29411764705883
- sum_ZDS = 0.0
- sum_ZN2 = 0.0

---

## Arc Flows

| a | f | y | total_flow |
|---|---|---:|---:|
| N1_N2 | G | 2025 | 6.0 |
| N1_N2 | G | 2030 | 6.0 |
| N2_N1 | G | 2025 | 6.0 |
| N2_N1 | G | 2030 | 6.0 |

---

## Bidirectional Activation

| metric | a | y | value |
|---|---|---:|---:|
| BD | N2_N1 | 2025 | 1.0 |
| BD | N2_N1 | 2030 | 0.004 |
| B_BD | N2_N1 | 2025 | 1.0 |
| K_OPP | N2_N1 | 2025 | 4.0 |
| K_OPP | N2_N1 | 2030 | 4.0 |
| K_BD | N2_N1 | 2025 | 4.0 |

---

## Node Mass Balance

Model balance structure:

Residual(n,f,y,h) =
Production(n,f,y,h)
+ Σ inflow
− Σ outflow
− Consumption(n,f,y,h)
− SlackTerms

Since demo03 has no storage / regasification activity:

Residual = Production + inflow − outflow − Consumption

---

### Hourly Balance Check

| y | h | n | Production | Inflow | Outflow | Consumption | Residual |
|---:|---:|---|---:|---:|---:|---:|---:|
| 2025 | 1 | N1 | 6 | 0 | 6 | 0 | 0 |
| 2025 | 1 | N2 | 0 | 6 | 0 | 6 | 0 |
| 2025 | 2 | N1 | 0 | 6 | 0 | 6 | 0 |
| 2025 | 2 | N2 | 6 | 0 | 6 | 0 | 0 |
| 2030 | 1 | N1 | 6 | 0 | 6 | 0 | 0 |
| 2030 | 1 | N2 | 0 | 6 | 0 | 6 | 0 |
| 2030 | 2 | N1 | 0 | 6 | 0 | 6 | 0 |
| 2030 | 2 | N2 | 6 | 0 | 6 | 0 | 0 |

---

## What this demo confirms

✔ Bidirectional costs activate 
✔ Reverse-direction capacity is borrowed
✔ No shortages or slack usage  
✔ Multi-year balance and flow switching are consistent  

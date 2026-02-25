# Demo 01 — Base Flow

Scenario: `demo01_base_flow`  
Folder: `data/demo01_base_flow/`

---

## Purpose

This scenario validates the minimal feasible configuration of the model:

- Single energy carrier (`f = G`)
- One production node
- One consumption node
- One transport arc
- No shortages (`ZDS = 0`, `ZN2 = 0`)
- No investments or expansions

---

## How to run

From repository root:

python -m scr.run --scenario demo01_base_flow

---

## Input Data

### nodes.csv

| n | cn | nuts2 |
|---|---|---|
| N1 | ... | ... |
| N2 | ... | ... |

---

### arcs.csv

| a | start | end | f | cap | bidir |
|---|---|---|---|---:|---|
| N1_N2 | N1 | N2 | G | 10 | 0 |

Interpretation:

- Flow allowed from `start → end`
- Carrier defined by column `f`
- No reverse flow (`bidir = 0`)

---

### production.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 4 | 6 |

Interpretation:

- Hourly production profile at node `n`

---

### consumption.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N2 | G | 2025 | 4 | 6 |

---

### timeseries.csv

| h | scaleup |
|---:|---:|
| 1 | 1 |
| 2 | 1 |

---

### other.csv

| param | indx1 | indx2 | value |
|---|---|---|---:|
| ... | ... | ... | ... |

Only parameters relevant for this demo:

- Production cost parameters
- Slack penalties (`ZDS`, `ZN2`)
- Transport cost parameters (if defined)

---

## Results Summary

Key values extracted from `summary_*.csv`:

- objective = 10.0
- sum_ZDS = 0.0
- sum_ZN2 = 0.0

---

## Arc Flows

| a | f | y | total_flow |
|---|---|---:|---:|
| N1_N2 | G | 2025 | 10.0 |

---

## Node Mass Balance

Model balance structure:

Residual(n,f,y,h) =
Production(n,f,y,h)
+ Σ inflow
− Σ outflow
− Consumption(n,f,y,h)
− SlackTerms

Since demo01 has no storage / regasification activity:

Residual = Production + inflow − outflow − Consumption

---

### Hourly Balance Check

| y | h | n | Production | Inflow | Outflow | Consumption | Residual |
|---:|---:|---|---:|---:|---:|---:|---:|
| 2025 | 1 | N1 | 4 | 0 | 4 | 0 | 0 |
| 2025 | 1 | N2 | 0 | 4 | 0 | 4 | 0 |
| 2025 | 2 | N1 | 6 | 0 | 6 | 0 | 0 |
| 2025 | 2 | N2 | 0 | 6 | 0 | 6 | 0 |

---

## What this demo confirms

✔ Network flow logic is correct  
✔ Mass balance constraints satisfied  
✔ Slack variables unused  
✔ Cost calculation behaves as expected  
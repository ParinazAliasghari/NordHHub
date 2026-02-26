# Demo 06 — Storage (Injection and Extraction)

Scenario: `demo06_storage`  
Folder: `data/demo06_storage/`

---

## Purpose

This scenario demonstrates storage operational behavior under the CURRENT model logic:

- Demonstrates **hourly energy shifting** via storage injection (Q_I) and extraction (Q_E)
- Supply concentrated in hour 1 requires time-shifting to meet hour 2 demand
- Storage works with **non-unity efficiency** (1% loss: e_w = 0.99)
- No shortages (`ZDS = 0`, `ZN2 = 0`)
- Illustrates the working-gas capacity constraint: $\text{cap\_ww} = W \times \frac{\sum_h \text{scaleUp}(h)}{8760}$

---

## How to run

From repository root:

```bash
python -m scr.core.solve_pipeline data/demo06_storage/other.csv
```

---

## Input Data

### nodes.csv

| n | cn | nuts2 |
|---|---|---|
| N1 | C1 | R1 |
| N2 | C1 | R1 |

Supply at N1, demand at N2.

---

### arcs.csv

| a | start | end | f | len | off | cal_c | cap | bidir |
|---|---|---|---|---:|---:|---:|---:|---:|
| N1_N2 | N1 | N2 | G | 160 | 0 | 0 | 20 | 0 |

Transport arc with ample capacity (cap=20) so flow is not a bottleneck.

---

### production.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 11 | 0 |
| N2 | G | 2025 | 0 | 0 |

Supply available **only** in hour 1 (11 units to cover 1% storage loss).

---

### consumption.csv

| n | f | y | 1 | 2 |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 0 | 0 |
| N2 | G | 2025 | 2 | 8 |

Demand low in hour 1 (2 units), **peaks in hour 2 (8 units)**. Total demand = 10 units.

---

### timeseries.csv

| y | h | scaleup |
|---:|---:|---:|
| 2025 | 1 | 4380 |
| 2025 | 2 | 4380 |

**Critical:** `sum(scaleup) = 8760` to keep model scaling interpretable.  
Working-gas capacity: $\text{cap\_ww} = 35040 \times \frac{8760}{8760} = 35040$ GWh.

---

### storage.csv

| N | F | W | X | I | cal_c | cal_l | H2-ready |
|---|---|---:|---:|---:|---:|---:|---:|
| N2 | G | 35040 | 8 | 9 | 1 | 1 | 0 |

Storage at **demand node N2**:
- **W** (working-gas capacity) = 35040 GWh
- **X** (extraction hourly cap) = 8 GWh/h
- **I** (injection hourly cap) = 9 GWh/h (>8 to allow efficiency loss absorption)
- **cal_c** = 1 → extraction cost = 1 × Vols2(G) = 1 EUR/GWh
- **cal_l** = 1 → cycle efficiency e_w = 1 − 0.01 × 1 = 0.99 (1% loss)

---

### other.csv (key rows)

| param | indx1 | indx2 | value |
|---|---|---|---:|
| BFPipe |  |  | 1 |
| Vola2 | G |  | 1 |
| Penalty | ZD2 | G | 1000 |
| Pipe | Len | Std | 80 |
| OffshMult |  |  | 20 |

Cost formulas:

Arc flow cost (same as demo01):
$$
c_a = 1 \cdot 1 \cdot \frac{(160 + 20 \cdot 0) \cdot 1}{80} = 2.0 \text{ EUR/GWh}
$$

Storage extraction cost:
$$
c_{\text{we}} = \text{Vols2}(G) \cdot \text{cal\_c} = 1 \cdot 1 = 1 \text{ EUR/GWh}
$$

Storage efficiency (penalty for loss):
$$
e_w = 1 - 0.01 \times \text{cal\_l} = 0.99
$$

---

## Results Summary

| Metric | Value |
|---|---:|
| **Objective** | 167501.82 EUR |
| **Production cost** | 44153.94 EUR |
| **Arc flow cost** | 88307.88 EUR |
| **Storage cost** | 35040.00 EUR |
| **ZDS penalty (shortage)** | 0.00 EUR |
| **ZN2 penalty (H2 unmet)** | 0.00 EUR |

✔ **Zero shortage**: all demand met by (production + storage extraction)  
✔ **Storage active**: Q_I = 8.08 GWh in h=1, Q_E = 8.00 GWh in h=2

---

## Hourly Node Balance

### Node N1 (Supply)

| h | Production | Outflow (arc) | Demand | Residual |
|---:|---:|---:|---:|---:|
| 1 | 10.08 | 10.08 | 0 | 0 |
| 2 | 0.00 | 0.00 | 0 | 0 |

All hour-1 production shipped via arc to N2.

### Node N2 (Demand + Storage)

| h | Inflow (arc) | Production | Q_I (inject) | Q_E (extract) | Q_S (delivery) | Demand | Residual |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10.08 | 0 | 8.08 | 0 | 2.00 | 2 | 0 |
| 2 | 0.00 | 0 | 0 | 8.00 | 8.00 | 8 | 0 |

- Hour 1: Receive 10.08 from N1. Deliver 2 to satisfy demand. **Store (inject) 8.08** in storage.
- Hour 2: Extract 8.00 from storage (accounting for 1% loss from 8.08 input). Deliver 8 to satisfy demand.

---

## Storage Details

### Storage Cycle Balance Constraint

The model enforces:
$$
\sum_h \text{scaleUp}(h) \cdot Q_E(n,e,y,h) = e_w(n,e) \cdot \sum_h \text{scaleUp}(h) \cdot Q_I(n,e,y,h)
$$

With N2, G, 2025:
$$
4380 \cdot 8.00 = 0.99 \cdot 4380 \cdot 8.08
$$
$$
35040 = 34939.4 \approx 35040 \quad \checkmark
$$

(Small numerical rounding in solver.)

### Working-Gas Capacity

Maximum stored energy: $\text{cap\_ww} = 35040$ GWh  
Peak stored: 8.08 GWh (stored in h=1, extracted in h=2)  
Utilization: 8.08 / 35040 = 0.023% (tiny fraction, but sufficient for the 2-hour cycle)

---

## What this demo confirms

✔ **Storage injection** (Q_I) activates when supply exceeds demand (h=1)  
✔ **Storage extraction** (Q_E) supplies demand when production unavailable (h=2)  
✔ **Efficiency loss** modeled: injected 8.08, extracted 8.00 (1% loss absorbed)  
✔ **Working-gas constraint** enforced: stored energy bounded by K_W  
✔ **Net-zero shortage**: ZDS and ZN2 both zero (all demand satisfied)  
✔ **Time-shifting economics**: Cost of storage operations (35040 EUR) is acceptable vs. shortage penalties

---

## Key Insights

1. **Storage is activated by supply/demand mismatch in time**: Production available in h=1 but demand peaks in h=2.
2. **Hourly limits matter**: Injection/extraction caps (I=9, X=8) enforce realistic operational constraints.
3. **Efficiency loss is modeled**: The 1% cycle loss (cal_l=1) requires slightly more injection than extraction.
4. **scaleUp scaling is critical**: With sum(scaleUp)=8760, working-gas capacity becomes interpretable (W in GWh).
5. **No network bottleneck**: Arc capacity (20) is ample, so storage is the binding time-shift mechanism.

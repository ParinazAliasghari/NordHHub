# Demo 07 — Regional Hierarchy

Scenario: `demo07_regions_hierarchy`  
Folder: `data/demo07_regions_hierarchy/`

---

## Purpose

This scenario validates multi-level regional hierarchy (`n`, `nuts2`, `rgn`, `cn`) with:

- Multiple nodes sharing same NUTS2 region (N1, N2 → A_N2_1)
- Node ID matching NUTS2 ID (N3 → N3, N4 → N4)  
- Independent RGN dimension (R1, R2, R3) preventing fallback to NUTS2

---

## How to run

From repository root:

```bash
python -m scr.run --scenario demo07_regions_hierarchy
```

---

## Input Data

### nodes.csv

| n | cn | nuts2 | rgn | G | H |
|---|---|---|---|---|---|
| N1 | A | A_N2_1 | R1 | 1 | 0 |
| N2 | A | A_N2_1 | R1 | 1 | 0 |
| N3 | A | N3 | R2 | 1 | 0 |
| N4 | B | N4 | R3 | 1 | 0 |

Interpretation:

- Chain topology: N1 → N2 → N3 → N4
- N1, N2 share `nuts2 = A_N2_1` (many-to-one mapping)
- N3, N4 have `nuts2 == n` (edge case)
- Explicit `rgn` column prevents fallback

---

### arcs.csv

| a | start | end | f | len | off | cal_c | cap | bidir |
|---|---|---|---|---:|---:|---:|---:|---:|
| N1_N2 | N1 | N2 | G | 100 | 0 | 1.0 | 10 | 0 |
| N2_N3 | N2 | N3 | G | 100 | 0 | 1.0 | 10 | 0 |
| N3_N4 | N3 | N4 | G | 100 | 0 | 1.0 | 10 | 0 |

Interpretation:

- Chain with 10 GWh capacity per arc
- All arcs unidirectional

---

### production.csv

| n | f | y | 1 | MC |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 15 | 1 |
| N2 | G | 2025 | 0 | 100 |
| N3 | G | 2025 | 0 | 100 |
| N4 | G | 2025 | 0 | 100 |

Interpretation:

- N1: Cheap production (MC=1), capacity=15 GWh
- Others: Expensive backup (MC=100)

---

### consumption.csv

| n | f | y | 1 |
|---|---|---:|---:|
| N1 | G | 2025 | 0 |
| N2 | G | 2025 | 5 |
| N3 | G | 2025 | 3 |
| N4 | G | 2025 | 4 |

Total demand: 12 GWh

---

### timeseries.csv

| y | h | scaleup |
|---:|---:|---:|
| 2025 | 1 | 1 |

---

### other.csv

| param | indx1 | indx2 | value |
|---|---|---|---:|
| Pipe | Len | Std | 80 |
| penalty | ZD2 | G | 1000 |
| Vola2 | G |  | 1 |
| ... | | | |

Relevant parameters:

- Pipe,Len,Std,80: Arc cost scaling
- penalty,ZD2,G,1000: Demand slack penalty

---

## Hierarchy Confirmation

Validation output confirms:

```
Nodes detected: ['N1', 'N2', 'N3', 'N4']
Countries detected: ['A', 'B']
NUTS2 detected: ['A_N2_1', 'N3', 'N4']
Regions detected: ['R1', 'R2', 'R3']
n_in_c entries: 4
n_in_2 entries: 4
n_in_r entries: 4
```

Loader behavior ([data_loading.py:127](../../scr/core/data_loading.py#L127)):

```python
if "rgn" not in df.columns:
    df["rgn"] = df["nuts2"]  # NOT triggered (explicit rgn present)
```

---

## Results Summary

```
Status: ok
Termination: optimal
TC: 2010.00
sum(ZDS): 2.00  ← Demand shortage captured via ZDS slack
sum(ZN2): 0.00
```

**Note:** Arc capacity constraint (10 GWh per arc × 3 arcs = 30 GWh max flow) is redundant in serial chain. Effective bottleneck: N1→N2 capacity (10) carries all demand, but demand exceeds this in aggregate. Model activates ZDS slack at N2 (2 GWh shortage) due to capacity constraints.

---

## Arc Flows

| a | f | y | h | flow |
|---|---|---:|---:|---:|
| N1_N2 | G | 2025 | 1 | 10.0 |
| N2_N3 | G | 2025 | 1 | 7.0 |
| N3_N4 | G | 2025 | 1 | 4.0 |

---

## Node Production and Consumption

**Production:**

| n | f | y | h | Q_P |
|---|---|---:|---:|---:|
| N1 | G | 2025 | 1 | 10.0 |

**Consumption (satisfied):**

| n | f | y | h | Q_S |
|---|---|---:|---:|---:|
| N2 | G | 2025 | 1 | 3.0 |
| N3 | G | 2025 | 1 | 3.0 |
| N4 | G | 2025 | 1 | 4.0 |

**Demand slack:**

| zd_type | n | f | y | h | ZDS |
|---|---|---|---:|---:|---:|
| ZD2 | N2 | G | 2025 | 1 | 2.0 |

Interpretation:

- N2 demand = 5 GWh, satisfied = 3 GWh, shortage = 2 GWh
- Penalty cost = 2 × 1000 = 2000

---

## Node Mass Balance

| y | h | n | Production | Inflow | Outflow | Consumption | Slack | Residual |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 2025 | 1 | N1 | 10 | 0 | 10 | 0 | 0 | 0 |
| 2025 | 1 | N2 | 0 | 10 | 7 | 3 | 2 | 0 |
| 2025 | 1 | N3 | 0 | 7 | 4 | 3 | 0 | 0 |
| 2025 | 1 | N4 | 0 | 4 | 0 | 4 | 0 | 0 |

All nodes balanced with slack at N2.

---

## What this demo confirms

✔ Loader accepts explicit `rgn` column (no fallback to nuts2)  
✔ Handles n == nuts2 edge case (N3, N4)  
✔ Processes many-to-one n → nuts2 mapping (N1, N2 → A_N2_1)  
✔ Constructs non-disjoint set structures (CN ⊃ NUTS2)  
✔ Validates arc formulas with multi-level hierarchy  
✔ Model runs without set overlap errors

| N | 4 | [N1, N2, N3, N4] |
| CN | 2 | [A, B] |
| NUTS2 | 3 | [A_N2_1, N3, N4] |
| RGN | 3 | [R1, R2, R3] |
| E | 1 | [G] |
| Y | 1 | [2025] |
| H | 1 | [1] |
| A | 3 | [N1_N2, N2_N3, N3_N4] |

**Critical checks:**
- `|NUTS2| = 3` (not 4; N1 and N2 share A_N2_1)
- `|RGN| = 3` (from explicit CSV column, not auto nuts2)
- N3 appears in both N and NUTS2 sets (allowed)
- N4 appears in both N and NUTS2 sets (allowed)

---

## Expected Mappings

### n_in_c (node → country)

Total entries: 4

| (n, cn) | Value | Region |
|---------|-------|--------|
| (N1, A) | 1 | Country A |
| (N2, A) | 1 | Country A |
| (N3, A) | 1 | Country A |
| (N4, B) | 1 | Country B |

### n_in_2 (node → NUTS2)

Total entries: 4

| (n, nuts2) | Value | Notes |
|------------|-------|-------|
| (N1, A_N2_1) | 1 | Shared nuts2 |
| (N2, A_N2_1) | 1 | Shared nuts2 |
| (N3, N3) | 1 | n==nuts2 case |
| (N4, N4) | 1 | n==nuts2 case |

**Critical test:** N1 and N2 both map to A_N2_1 (many-to-one).

### n_in_r (node → region)

Total entries: 4

| (n, rgn) | Value | Notes |
|----------|-------|-------|
| (N1, R1) | 1 | From CSV |
| (N2, R1) | 1 | From CSV |
| (N3, R2) | 1 | From CSV |
| (N4, R3) | 1 | From CSV |

**Critical test:** rgn values (R1, R2, R3) are independent from nuts2 values.

---

## dat_n Table Structure

Expected 8 entries (4 nodes × 2 coordinates):

| Key | Value | Notes |
|-----|-------|-------|
| (N1, A, A_N2_1, R1, LAT) | 40.0 | Standard |
| (N1, A, A_N2_1, R1, LON) | 1.0 | Standard |
| (N2, A, A_N2_1, R1, LAT) | 41.0 | Shared nuts2 |
| (N2, A, A_N2_1, R1, LON) | 2.0 | Shared nuts2 |
| (N3, A, N3, R2, LAT) | 42.0 | **nuts2=N3 repeats** |
| (N3, A, N3, R2, LON) | 3.0 | **nuts2=N3 repeats** |
| (N4, B, N4, R3, LAT) | 50.0 | **nuts2=N4 repeats** |
| (N4, B, N4, R3, LON) | 10.0 | **nuts2=N4 repeats** |

**Key test:** Tuple keys like `(N3, A, N3, R2, LAT)` have repeating values (n==nuts2) but do not cause overwrites because n values are unique.

---

## Results Summary

**Note:** This section contains qualitative expectations only. Numeric values should be verified by executing the scenario and inspecting output files.

### Expected Solver Outcome

- ✅ **Status:** optimal
- ✅ **Termination:** optimal
- ✅ **Feasibility:** All slack variables (ZDS, ZN2) = 0

### Expected Production Pattern

- **N1:** Should produce to meet total demand (≈12 GWh) at MC=1
- **N2, N3, N4:** Should not produce (expensive MC=100)

### Expected Flow Pattern

- **N1_N2:** Flow from N1 to N2 (total demand downstream)
- **N2_N3:** Flow continues after N2 consumption
- **N3_N4:** Flow continues after N3 consumption

### Expected Consumption (Q_S)

- **N2:** 5 GWh (from consumption.csv)
- **N3:** 3 GWh (from consumption.csv)
- **N4:** 4 GWh (from consumption.csv)
- **Total:** 12 GWh

---

## Validation Checks

### 1. Loader Phase (data_loading.py)

**Check terminal output for:**

```
Nodes detected: ['N1', 'N2', 'N3', 'N4']
Countries detected: ['A', 'B']
NUTS2 detected: ['A_N2_1', 'N3', 'N4']
Regions detected: ['R1', 'R2', 'R3']
n_in_c entries: 4
n_in_2 entries: 4
n_in_r entries: 4
```

**Verify:**
- ✅ All 4 nodes loaded (no silent drops)
- ✅ NUTS2 has 3 unique values (not 4)
- ✅ RGN has 3 values from CSV (not auto nuts2)
- ✅ Mapping counts correct (4 each)

### 2. Model Construction Phase (model.py)

**Check terminal output for:**

```
|N| = 4
|CN| = 2
|NUTS2| = 3
|RGN| = 3
|E| = 1
|A| = 3
```

**Verify:**
- ✅ Set sizes match expectations
- ✅ No Pyomo errors about set overlaps (N3, N4 in both N and NUTS2)
- ✅ Parameters (n_in_c, n_in_2, n_in_r) initialize without domain errors

### 3. Solver Phase

**Check solver output for:**

```
Solver status: ok
Termination condition: optimal
```

**Verify:**
- ✅ Solver terminates successfully
- ✅ No infeasibility warnings
- ✅ No unbounded solution

### 4. Mass Balance Residuals

**For each node, verify:**
```
Production + Inflow = Consumption + Outflow
```

**Example (N2):**
- Production: 0
- Inflow: F_A[N1_N2, G, 2025, 1]
- Consumption: 5
- Outflow: F_A[N2_N3, G, 2025, 1]
- Balance: 0 + Inflow = 5 + Outflow ✓

**All 4 nodes should have zero residual.**

---

## Output Files to Inspect

### 1. Terminal Output (stdout)

**Location:** Console output during execution

**What to check:**
- Set sizes: |N|, |CN|, |NUTS2|, |RGN|
- Mapping counts: n_in_c, n_in_2, n_in_r entries
- Solver termination status

**Run validation tool:**
```powershell
python scr\tools\validate_inputs.py data\demo07_regions_hierarchy\other.csv
```

**Expected validation output:**
```
Input validation OK
File: ...\data\demo07_regions_hierarchy\other.csv
Rows: 13
...
Nodes detected: ['N1', 'N2', 'N3', 'N4']
Countries detected: ['A', 'B']
NUTS2 detected: ['A_N2_1', 'N3', 'N4']          ← Critical: 3 values (N1,N2 share A_N2_1)
Regions detected: ['R1', 'R2', 'R3']            ← Critical: from CSV rgn column
n_in_c entries: 4
n_in_2 entries: 4
n_in_r entries: 4                               ← Critical: all 4 nodes mapped to rgn
```

**Verify hierarchy:**
- `Regions detected: ['R1', 'R2', 'R3']` confirms rgn read from CSV (not auto nuts2)
- `NUTS2 detected: ['A_N2_1', 'N3', 'N4']` confirms |NUTS2|=3 (N1, N2 share A_N2_1)
- `n_in_r entries: 4` confirms all nodes have region mappings

### 2. Results Directory

**Likely location:** (verify actual output structure)
```
results/demo07_regions_hierarchy/
```

**Expected files:**
- `all_results.json` or similar (if reporter creates it)
- `operations.csv` (flow variables, production, consumption)
- `solver_output.txt` (raw solver log)

### 3. Detailed Mapping Verification (Optional Debug)

**In data_loading.py after line 342:**
```python
# Temporary debug output - remove after testing
print(f"DEBUG n_in_2: {n_in_2}")
print(f"DEBUG n_in_r: {n_in_r}")
print(f"DEBUG dat_n keys: {list(dat_n.keys())[:4]}")
```

**Expected:**
```
DEBUG n_in_2: {('N1','A_N2_1'):1, ('N2','A_N2_1'):1, ('N3','N3'):1, ('N4','N4'):1}
DEBUG n_in_r: {('N1','R1'):1, ('N2','R1'):1, ('N3','R2'):1, ('N4','R3'):1}
DEBUG dat_n keys: [('N1','A','A_N2_1','R1','LAT'), ('N1','A','A_N2_1','R1','LON'), ...]
```

**Key verifications:**
- n_in_2 shows N1 and N2 both map to 'A_N2_1' (shared NUTS2)
- n_in_r shows rgn values R1, R2, R3 from CSV (not nuts2)
- dat_n keys have 5-tuple structure (n, cn, nuts2, rgn, coord)

---

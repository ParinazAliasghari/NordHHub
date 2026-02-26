# Demo 07 — Regional Hierarchy Testing (cn, nuts2, rgn)

## Purpose

Test GAMS-like multi-level regional hierarchy semantics:
- **n** (node): NUTS3-level fine granularity
- **nuts2** (NUTS2): Mid-level grouping
- **rgn** (region): Macro-region (independent from nuts2 in GAMS)
- **cn** (country): Top-level grouping

This demo validates:
1. **n ≠ nuts2** case (N1, N2 share nuts2=A_N2_1)
2. **n == nuts2** case (N3, N4 where nuts2 equals node id)
3. **rgn as independent grouping** (not auto-derived from nuts2)
4. **Multi-country structure** (2 countries A, B)

---

## Scenario Structure

### Hierarchical Topology

```
Country A (cn=A):
  Region R1 (rgn=R1):
    NUTS2 = A_N2_1:
      ├─ N1 (production=15 GWh, MC=1)
      └─ N2 (demand=5 GWh)
  
  Region R2 (rgn=R2):
    NUTS2 = N3 (n==nuts2 case):
      └─ N3 (demand=3 GWh)

Country B (cn=B):
  Region R3 (rgn=R3):
    NUTS2 = N4 (n==nuts2 case):
      └─ N4 (demand=4 GWh)
```

### Network Flow Topology

```
N1 --[N1_N2]--> N2 --[N2_N3]--> N3 --[N3_N4]--> N4
│                │                │                │
prod=15         dmd=5           dmd=3           dmd=4
(MC=1)
```

**Flow solution:** N1 produces 12 GWh → flows through chain to meet all demand (5+3+4=12)

---

## Expected Set Sizes

| Set | Expected Size | Elements |
|-----|---------------|----------|
| N | 4 | [N1, N2, N3, N4] |
| CN | 2 | [A, B] |
| NUTS2 | 3 | [A_N2_1, N3, N4] |
| RGN | 3 | [R1, R2, R3] |
| E | 1 | [G] |
| Y | 1 | [2025] |
| H | 1 | [1] |
| A | 3 | [N1_N2, N2_N3, N3_N4] |

---

## Expected Mappings

### n_in_c (node → country)

| (n, cn) | Value |
|---------|-------|
| (N1, A) | 1 |
| (N2, A) | 1 |
| (N3, A) | 1 |
| (N4, B) | 1 |

**Total entries:** 4

### n_in_2 (node → NUTS2)

| (n, nuts2) | Value |
|------------|-------|
| (N1, A_N2_1) | 1 |
| (N2, A_N2_1) | 1 |
| (N3, N3) | 1 |
| (N4, N4) | 1 |

**Total entries:** 4  
**Critical test:** N1 and N2 share the same nuts2 (A_N2_1)

### n_in_r (node → region)

| (n, rgn) | Value |
|----------|-------|
| (N1, R1) | 1 |
| (N2, R1) | 1 |
| (N3, R2) | 1 |
| (N4, R3) | 1 |

**Total entries:** 4  
**Critical test:** rgn values (R1, R2, R3) are independent from nuts2 values

---

## dat_n Table Structure

The `dat_n` table should have keys like:

```
(n, cn, nuts2, rgn, 'LAT'|'LON')
```

Expected entries (8 rows for LAT/LON):

| Key | Value |
|-----|-------|
| (N1, A, A_N2_1, R1, LAT) | 40.0 |
| (N1, A, A_N2_1, R1, LON) | 1.0 |
| (N2, A, A_N2_1, R1, LAT) | 41.0 |
| (N2, A, A_N2_1, R1, LON) | 2.0 |
| (N3, A, N3, R2, LAT) | 42.0 |
| (N3, A, N3, R2, LON) | 3.0 |
| (N4, B, N4, R3, LAT) | 50.0 |
| (N4, B, N4, R3, LON) | 10.0 |

**Critical test:** When nuts2=n (N3, N4), the key has repeating values like `(N3, A, N3, R2, LAT)`

---

## How Python Loader Handles This

### Stage 1: data_loading.py (_extract_node_structures)

**File:** [scr/core/data_loading.py](../../scr/core/data_loading.py) lines 310-342

**What happens:**
1. **Reads nodes.csv** with explicit rgn column → no fallback triggered
2. **Extracts unique sets:**
   - `n_values = ['N1', 'N2', 'N3', 'N4']`
   - `cn_values = ['A', 'B']`
   - `nuts2_values = ['A_N2_1', 'N3', 'N4']` (sorted unique from column)
   - `rgn_values = ['R1', 'R2', 'R3']` (sorted unique from column)

3. **Builds mappings:**
   ```python
   n_in_c = {('N1','A'):1, ('N2','A'):1, ('N3','A'):1, ('N4','B'):1}
   n_in_2 = {('N1','A_N2_1'):1, ('N2','A_N2_1'):1, ('N3','N3'):1, ('N4','N4'):1}
   n_in_r = {('N1','R1'):1, ('N2','R1'):1, ('N3','R2'):1, ('N4','R3'):1}
   ```

4. **Populates dat_n table:**
   ```python
   for each row in nodes.csv:
       dat_n[(r.n, r.cn, r.nuts2, r.rgn, 'LAT')] = lat
       dat_n[(r.n, r.cn, r.nuts2, r.rgn, 'LON')] = lon
   ```

**No fallback triggered** because rgn column exists!

### Stage 2: model.py (set/param initialization)

**File:** [scr/core/model.py](../../scr/core/model.py) lines 100-230

**What happens:**
1. **Sets created:**
   ```python
   model.N = pyo.Set(initialize=['N1','N2','N3','N4'])
   model.CN = pyo.Set(initialize=['A','B'])
   model.NUTS2 = pyo.Set(initialize=['A_N2_1','N3','N4'])
   model.RGN = pyo.Set(initialize=['R1','R2','R3'])
   ```

2. **Mapping parameters:**
   ```python
   model.n_in_c = pyo.Param(model.N, model.CN, ...)  # 4×2=8 domain, 4 valued
   model.n_in_2 = pyo.Param(model.N, model.NUTS2, ...)  # 4×3=12 domain, 4 valued
   model.n_in_r = pyo.Param(model.N, model.RGN, ...)  # 4×3=12 domain, 4 valued
   ```

3. **Constraint indexing:**
   - Mass balance: `model.N × model.E × model.Y × model.H` (4×1×1×1=4 constraints)
   - Arc capacity: `model.A × model.E × model.Y × model.H` (3×1×1×1=3 constraints)
   - **No constraints indexed by RGN** (rgn is unused in optimization!)

---

## Potential Failure Points

### 1. **Loader Schema Assumptions**

**Location:** [data_loading.py](../../scr/core/data_loading.py#L314-L321)

**Risk:** Code assumes all columns (n, cn, nuts2, rgn) are non-empty strings after loading.

**Test:** Line 321 filters out empty strings:
```python
clean = clean[
    (clean["n"] != "")
    & (clean["cn"] != "")
    & (clean["nuts2"] != "")
    & (clean["rgn"] != "")
]
```

**Failure mode:** If any row has missing cn/nuts2/rgn, that row silently drops → set sizes mismatch.

**Check:** Validate that `len(loaded['n_values']) == 4` (all nodes preserved).

### 2. **Duplicate dat_n Keys**

**Location:** [data_loading.py](../../scr/core/data_loading.py#L334-L340)

**Risk:** If two nodes have identical (n, cn, nuts2, rgn) tuple, they overwrite LAT/LON entries.

**Test scenario:** If N1 and N2 had nuts2=A_N2_1 AND rgn=R1 AND n=N1 (same node id), keys collide.

**This demo:** Safe because n values are unique (N1 ≠ N2).

**Failure mode:** Last row wins → coordinates silently wrong.

**Check:** Ensure dat_n has exactly 8 entries (4 nodes × 2 coords).

### 3. **Domain Size Explosion**

**Location:** [model.py](../../scr/core/model.py#L222-L229)

**Risk:** Pyomo creates `n_in_r` param with domain `N × RGN` = 4×3=12 possible indices.

**Memory:** For large scenarios (1000 nodes × 100 regions = 100k domain), most are zero.

**This demo:** Tiny (12 indices), but check param initialization doesn't error on out-of-domain keys.

**Check:** `model.n_in_r` should have default=0, only 4 non-zero values.

### 4. **Reporting/Validation Grouping**

**Location:** [validate_inputs.py](../../scr/tools/validate_inputs.py#L39-L42)

**Risk:** Validation prints rgn_values but doesn't verify regional aggregation consistency.

**Test:** What if n_in_r says (N1, R1) but NUTS2 aggregation expects N1 in different region?

**This demo:** No cross-validation between nuts2 grouping and rgn grouping.

**Failure mode:** Silent inconsistency (user assigns conflicting hierarchies).

**Check:** Validation output should show:
```
Regions detected: ['R1', 'R2', 'R3']
NUTS2 detected: ['A_N2_1', 'N3', 'N4']
n_in_r entries: 4
n_in_2 entries: 4
```

### 5. **n==nuts2 Edge Case**

**Location:** Throughout (set extraction, dat_n key generation)

**Risk:** When nuts2=N3 (column value equals another column), no semantic issue but code must handle non-unique labels across different semantic levels.

**Test:** N3 has nuts2='N3', ensuring 'N3' appears in both `n_values` and `nuts2_values`.

**Failure mode:** Set intersection confusion (if code wrongly assumes n ∩ nuts2 = ∅).

**Check:** 
```
'N3' in model.N → True
'N3' in model.NUTS2 → True
```

Both should be allowed (sets represent different semantic domains).

---

## How to Run

### Command

```powershell
cd c:\Users\parinaza\NordHHub\NordHHub
python scr/run.py data/demo07_regions_hierarchy/other.csv
```

### Expected Terminal Output

```
Input validation OK
...
Nodes detected: ['N1', 'N2', 'N3', 'N4']
Countries detected: ['A', 'B']
NUTS2 detected: ['A_N2_1', 'N3', 'N4']
Regions detected: ['R1', 'R2', 'R3']
n_in_c entries: 4
n_in_2 entries: 4
n_in_r entries: 4
...
|N| = 4
|CN| = 2
|NUTS2| = 3
|RGN| = 3
|E| = 1
|A| = 3
...
Solver status: ok
Termination condition: optimal
```

---

## What to Check in Outputs

### 1. Feasibility & Optimality

**File:** Terminal output or `results/demo07_regions_hierarchy/solver_status.json` (if exists)

**Check:**
- ✅ `Solver status: ok`
- ✅ `Termination condition: optimal`
- ✅ No infeasibility warnings
- ✅ All ZDS (slack variables) = 0

### 2. Set Sizes

**File:** Terminal output (model construction phase)

**Expected:**
```
|N| = 4
|CN| = 2
|NUTS2| = 3
|RGN| = 3
```

**Failure:** If `|RGN| = 4` → loader mistakenly auto-generated rgn from nuts2 (but shouldn't happen with explicit column).

### 3. Mapping Validation

**Method:** Add temporary debugging in [validate_inputs.py](../../scr/tools/validate_inputs.py) (but don't commit):

```python
# After line 42:
print(f"n_in_c mappings: {loaded['n_in_c']}")
print(f"n_in_2 mappings: {loaded['n_in_2']}")
print(f"n_in_r mappings: {loaded['n_in_r']}")
```

**Expected:**
```
n_in_c mappings: {('N1','A'):1, ('N2','A'):1, ('N3','A'):1, ('N4','B'):1}
n_in_2 mappings: {('N1','A_N2_1'):1, ('N2','A_N2_1'):1, ('N3','N3'):1, ('N4','N4'):1}
n_in_r mappings: {('N1','R1'):1, ('N2','R1'):1, ('N3','R2'):1, ('N4','R3'):1}
```

**Critical:** N1 and N2 both map to A_N2_1 (shared NUTS2).

### 4. dat_n Table Keys

**Method:** Add debugging after [data_loading.py](../../scr/core/data_loading.py#L342):

```python
# Temporary:
print(f"dat_n keys sample: {list(dat_n.keys())[:4]}")
```

**Expected keys like:**
```
('N1', 'A', 'A_N2_1', 'R1', 'LAT')
('N3', 'A', 'N3', 'R2', 'LAT')  # Note nuts2=N3 repeats
('N4', 'B', 'N4', 'R3', 'LON')  # Note nuts2=N4 repeats
```

**Check:** 8 total keys (4 nodes × 2 coords), no duplicates.

### 5. Optimization Solution

**File:** `results/demo07_regions_hierarchy/operations.csv` (if exists) or terminal output

**Expected flows:**
- F_A[N1_N2, G, 2025, 1] = 12 GWh (all demand flows from N1)
- F_A[N2_N3, G, 2025, 1] = 7 GWh (12 - 5 consumed at N2)
- F_A[N3_N4, G, 2025, 1] = 4 GWh (7 - 3 consumed at N3)

**Expected production:**
- Q_P[N1, G, 2025, 1] = 12 GWh (feasible: cap=15, MC=1)
- Q_P[N2, G, 2025, 1] = 0 (expensive MC=100)
- Q_P[N3, G, 2025, 1] = 0
- Q_P[N4, G, 2025, 1] = 0

**Expected consumption (Q_S):**
- Q_S[N1, G, 2025, 1] = 0
- Q_S[N2, G, 2025, 1] = 5
- Q_S[N3, G, 2025, 1] = 3
- Q_S[N4, G, 2025, 1] = 4

**Total cost:** ≈ 12 GWh × 1 $/GWh (production) + arc transport costs

### 6. Residual Check (Mass Balance)

**Method:** For each node, verify:
```
Production + Inflow + Storage_Extract = Consumption + Outflow + Storage_Inject
```

**Node N2 example:**
- Production: 0
- Inflow: F_A[N1_N2] = 12
- Outflow: F_A[N2_N3] = 7
- Consumption: 5
- Balance: 0 + 12 = 5 + 7 ✓

**Check all 4 nodes** have zero residual.

---

## Expected Behavior vs Potential Issues

### Region Mapping in Constraints

**Current Python model:** [model.py](../../scr/core/model.py)

**Uses NUTS2 (not RGN) for hydrogen demand aggregation:**
```python
# Line ~927: dmd_n2 constraint
model.dmd_n2 = pyo.Constraint(
    model.NUTS2, model.E, model.Y, model.H,
    rule=lambda mm, g, e, y, h: (
        sum(mm.Q_S[n, e, y, h] for n in mm.N if mm.n_in_2[n, g] > 0)
        == mm.dmd2[g, e, y, h] - mm.ZN2[g, e, y, h]
    ) if (str(e) == 'H' and mm.dmd2[g, e, y, h] > 0) else pyo.Constraint.Skip
)
```

**Observation:** This constraint uses `n_in_2` (NUTS2 mapping), not `n_in_r` (region mapping).

**Impact on this demo:**
- If dmd2 specified at NUTS2 level (e.g., demand at A_N2_1 aggregating N1+N2), it uses NUTS2.
- If dmd2 specified at rgn level (e.g., R1 grouping), **it won't work** (no dmd_rgn constraint exists).

**This demo:** Uses node-level demand (dmd, not dmd2), so no regional aggregation tested.

**Potential issue:** If GAMS uses rgn for aggregation but Python uses NUTS2, results differ.

### No RGN-Specific Constraints

**Confirmed:** Searching [model.py](../../scr/core/model.py) for "RGN":
- Line 106: Set definition only
- Line 224: n_in_r parameter (unused in constraints)
- Line 1088: Debug print

**Conclusion:** RGN is a "dead" set in Python (matches GAMS behavior from earlier analysis).

**Implication:** Even if rgn values differ between GAMS/Python, optimization is unaffected.

---

## Diagnosis: Fixes That Might Be Required Later

### 1. **Loader: n==nuts2 Assumption**

**Location:** [data_loading.py](../../scr/core/data_loading.py#L127)

**Current code:**
```python
if "rgn" not in df.columns:
    df["rgn"] = df["nuts2"]  # Fallback
```

**Issue:** Assumes nuts2 never equals n (but N3, N4 prove this wrong).

**Fix needed:** None (code handles it fine), but **documentation** should clarify:
- nuts2 can equal n (NUTS3==NUTS2 for small regions)
- rgn can equal nuts2 (1-to-1 mapping)
- rgn should be independent grouping in multi-level hierarchies

**Action:** Add docstring example showing n==nuts2 case.

### 2. **Validation: Region Hierarchy Consistency**

**Location:** [validate_inputs.py](../../scr/tools/validate_inputs.py)

**Missing check:** No validation that rgn grouping is consistent with cn/nuts2 hierarchy.

**Example inconsistency:**
```
N1: cn=A, nuts2=A_N2_1, rgn=R1
N2: cn=A, nuts2=A_N2_1, rgn=R2  # BUG: same nuts2, different rgn?
```

**Fix needed:** Add optional validation:
```python
# Check: all nodes in same nuts2 should have same rgn (if hierarchical)
for nuts2_val in loaded['nuts2_values']:
    nodes_in_nuts2 = [n for n, g in loaded['n_in_2'].items() if g == nuts2_val]
    regions = {loaded['n_in_r'][n] for n in nodes_in_nuts2}
    if len(regions) > 1:
        warnings.warn(f"NUTS2 {nuts2_val} spans multiple regions: {regions}")
```

**Caveat:** This assumes hierarchical nesting (nuts2 ⊆ rgn), which may not be intended design.

**Action:** Clarify if rgn is hierarchical or cross-cutting dimension.

### 3. **Reporting: Regional Aggregation**

**Location:** [report.py](../../scr/core/report.py)

**Current:** No regional aggregation reported (only node-level results).

**Fix needed:** Add optional regional summaries:
```python
# Group production by region
for rgn in model.RGN:
    nodes_in_rgn = [n for n in model.N if model.n_in_r[n, rgn] > 0]
    total_prod = sum(model.Q_P[n, e, y, h].value for n in nodes_in_rgn ...)
    print(f"Region {rgn} total production: {total_prod}")
```

**Action:** Add regional aggregation to report if GAMS outputs include it.

### 4. **Model: NUTS2 vs RGN in dmd_n2**

**Location:** [model.py](../../scr/core/model.py#L927)

**Current:** Hydrogen demand aggregates by NUTS2 (not RGN).

**GAMS equivalent:** [MGET.gms](../../scr/MGET.gms#L126) also uses NUTS2 (dmd_n2).

**Observation:** Both models use NUTS2 for demand aggregation, not RGN.

**Potential confusion:** If user expects rgn to matter for constraints, document that it's unused.

**Action:** Add model.py docstring: "RGN set defined for data compatibility; not used in constraints (NUTS2 used for aggregation)."

### 5. **dat_n Table: Repeating Keys**

**Location:** [data_loading.py](../../scr/core/data_loading.py#L338-L340)

**Current:** Keys like `(N3, A, N3, R2, LAT)` have nuts2=n repeating.

**Issue:** Not a bug, but may confuse users expecting distinct values.

**Fix needed:** None (semantically correct).

**Action:** Document in nodes.csv schema: "nuts2 may equal n for small regions."

### 6. **Set Intersection: n ∩ nuts2 ≠ ∅**

**Location:** Pyomo set definitions in [model.py](../../scr/core/model.py#L100-L106)

**Current:** Sets are independent:
```python
model.N = pyo.Set(...)      # Contains N1, N2, N3, N4
model.NUTS2 = pyo.Set(...)  # Contains A_N2_1, N3, N4
```

**Observation:** 'N3' and 'N4' appear in both sets.

**Pyomo behavior:** Allowed (sets represent different semantic domains).

**Potential issue:** If code assumes `model.N & model.NUTS2 == set()`, fails.

**This demo:** Tests that overlapping values (N3, N4) don't break anything.

**Action:** If any validation code checks set intersection, remove that assumption.

---

## Summary: What This Demo Tests

| Test Case | Validates |
|-----------|-----------|
| N1, N2 share nuts2=A_N2_1 | Many-to-one n→nuts2 mapping works |
| N3 has nuts2=N3 | n==nuts2 edge case handled |
| N4 has nuts2=N4 | Another n==nuts2 case in different country |
| rgn independent (R1, R2, R3) | rgn not auto-derived from nuts2 |
| 2 countries (A, B) | Multi-country structure works |
| 3 NUTS2 regions | NUTS2 set correctly sized |
| 4 nodes, 3 arcs | Minimal feasible network solves |
| Explicit rgn column | No fallback to nuts2 triggered |
| dat_n with repeating coords | (N3, A, N3, R2, LAT) keys work |

---

## Expected Diagnosis After Running

### If solver terminates successfully:
✅ **Loader pipeline separation preserved**
- data_loading.py built sets/params correctly
- model.py constructed math without errors
- Solver found optimal solution

### If validation passes:
✅ **Set sizes match expectations**
- No silent row drops
- No domain explosions
- Mappings have expected cardinality

### If mass balance residuals = 0:
✅ **Constraint logic correct**
- Node-level balance works
- Arc flows conserve energy
- No phantom production/consumption

### Likely conclusion:
🟢 **Python loader handles GAMS-like hierarchy correctly**
- No code fixes needed for basic hierarchy
- Optional: Add validation for consistency checks
- Optional: Add regional aggregation reporting

### If anything fails, probable causes:
🔴 **Schema assumption violated**
- Empty strings not filtered correctly
- Duplicate keys overwriting data
- Domain size mismatch in param initialization

---

## Pipeline Verification Checklist

Run this demo and check:

- [ ] Loader completes without errors
- [ ] Set sizes: |N|=4, |CN|=2, |NUTS2|=3, |RGN|=3
- [ ] Mapping counts: n_in_c=4, n_in_2=4, n_in_r=4
- [ ] Model builds without Pyomo errors
- [ ] Solver returns optimal status
- [ ] Total cost > 0 (production cost incurred)
- [ ] All ZDS slack variables = 0 (feasible)
- [ ] F_A[N1_N2] + F_A[N2_N3] + F_A[N3_N4] = 12+7+4 (flows consistent)
- [ ] Q_S totals = 5+3+4 = 12 (demand met)
- [ ] Q_P[N1] = 12, others = 0 (cheapest source used)
- [ ] No warnings about missing/duplicate data

If all pass → **No fixes required**, hierarchy works as designed.

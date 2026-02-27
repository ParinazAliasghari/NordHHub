# Multigas Energy Transition Model
**Data Loading · Model Builder · Validation · Reporting · Documentation**

---

## 📁 Project Structure

---

## 1. `data/` — Input Scenarios

This folder contains structured CSV scenario inputs.

Each scenario has its own subfolder:

```
demo01_base_flow/
demo02_invest_expand/
demo03_bidirectional/
demo04_repurpose/
demo05_regas/
demo06_storage/
demo07_regions_hierarchy/
demo08_full_min/
...
```

Each scenario folder includes:

- `nodes.csv` – Node definitions (country, region, carrier availability)  
- `arcs.csv` – Network connections and capacities  
- `production.csv` – Hourly supply profiles  
- `consumption.csv` – Hourly demand profiles  
- `storage.csv` – Storage facilities and parameters  
- `regasification.csv` – Regasification/conversion capacities  
- `timeseries.csv` – Representative hours and scale factors  
- `other.csv` – Global parameters and penalty settings  

---

## 2. `scr/` — Python Source Code

Core model logic is implemented inside `scr/core/`.

| File | Description |
|------|------------|
| `run.py` | Command-line entry point for running scenarios |
| `data_loading.py` | Reads scenario CSV files and constructs sets, mappings, and parameter dictionaries |
| `param_table.py` | Processes `other.csv` and builds scalar parameters and penalty matrices |
| `model.py` | Defines sets, parameters, variables, constraints, and objective function (Pyomo) |
| `solver.py` | Configures and executes the optimization solver |
| `validate.py` | Performs structural checks (mass balance, bidirectional logic, repurposing consistency) |
| `report.py` | Generates structured CSV and JSON result outputs |
| `solve_pipeline.py` | Orchestrates the workflow: load → build → solve → validate → report |

---

## 3. `results/` — Auto-Generated Output

Each scenario gets its own results folder:

```
results/demo01_base_flow/
results/demo02_invest_expand/
results/demo03_bidirectional/
results/demo04_repurpose/
results/demo05_regas/
results/demo06_storage/
results/demo07_regions_hierarchy/
results/demo08_full_min/
...
```

Each model run generates timestamped files:

- `summary_<scenario>_<timestamp>.csv`  
  High-level results (objective value, slack totals, balance checks)

- `operations_<scenario>_<timestamp>.csv`  
  Detailed operational results (flows, production, storage, regasification, investments)

Additionally:

- `runs_<scenario>.csv`  
  Maintains a cumulative history of all executed runs for that scenario

## 4. `docs/` — Documentation

This folder contains project documentation, reports, and technical notes.

```
docs/
├── demos/
│   ├── demo01_base_flow_report.md
│   ├── demo02_invest_expand_report.md
│   ├── demo03_bidirectional_report.md
│   ├── demo04_repurpose_report.md
│   ├── demo05_regas_report.md
│   ├── demo06_storage_report.md
│   ├── demo07_regions_hierarchy_report.md
│   └── demo08_full_min_report.md
│
├── input_files/
├── javascripts/
├── model/
├── introduction.md
└── load_module.md
```

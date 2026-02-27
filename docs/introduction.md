# MGET – Multi-Gas Energy Transition Model

The **Multigas Energy Transition (MGET)** model is an open-source Python optimization framework
for analyzing, planning, and transforming gas and multi-energy networks.

It supports energy transition studies by representing multiple fuels, long-term
infrastructure investment, storage, repurposing, and hourly operational dynamics
within a single integrated optimization model.

This documentation describes the open-source Python implementation of MGET, based on the original GAMS formulation developed by Ruud Egging (NTNU). MGET is implemented in **Python using Pyomo** and formulated as a
**linear or mixed-integer linear optimization problem**.


## Code Structure
All main scripts are located in the `scr/` directory,
with core model logic implemented inside `scr/core/`.

The framework follows a transparent, modular pipeline:

- **Data Loading Layer (`scr/core/data_loading.py`)**  
  Reads structured CSV scenario files (nodes, arcs, production, consumption,
  storage, regasification, parameters, time series) and constructs sets,
  mappings, and parameter dictionaries.

- **Parameter Processing Layer (`scr/core/param_table.py`)**  
  Builds scalar parameters and penalty matrices from `other.csv`,
  including fallback logic consistent with the original GAMS formulation.

- **Model Builder (`scr/core/model.py`)**  
  Defines all sets, parameters, variables, constraints, and the objective function
  using Pyomo.

- **Solver Layer (`scr/core/solver.py`)**  
  Configures and executes the optimization solver (e.g., Gurobi).

- **Validation Layer (`scr/core/validate.py`)**  
  Performs structural checks such as node–arc mass balance,
  bidirectional consistency, and repurposing validation.

- **Reporting Layer (`scr/core/report.py`)**  
  Extracts results and exports structured CSV and JSON outputs
  for flows, production, investments, costs, and slack variables.

- **Execution Orchestration (`scr/core/solve_pipeline.py`)**  
  Connects all modules into a reproducible end-to-end workflow:
  load → build → solve → validate → report.

The model is designed to be:

- Modular and extensible  
- Transparent and reproducible  
- Aligned with the original GAMS assumptions  
- Suitable for research, scenario exploration, and open-access energy system analysis

---

## Data Structure

All model input data are stored in the `data/` directory.

Each scenario has its own subfolder:

    data/
    ├── demo01_base_flow/
    ├── demo02_invest_expand/
    ├── demo03_bidirectional/
    ├── demo04_repurpose/
    ├── demo05_regas/
    ├── demo06_storage/
    ├── demo07_regions_hierarchy/
    ├── demo08_full_min/
    └── ...

Each scenario folder contains:

    data/<scenario_name>/
    ├── nodes.csv
    ├── arcs.csv
    ├── production.csv
    ├── consumption.csv
    ├── storage.csv
    ├── regasification.csv
    ├── timeseries.csv
    └── other.csv

---

## Results Structure

Model outputs are stored in the `results/` directory.

Each scenario has a separate results folder:

    results/
    ├── demo01_base_flow/
    ├── demo02_invest_expand/
    ├── demo03_bidirectional/
    ├── demo04_repurpose/
    ├── demo05_regas/
    ├── demo06_storage/
    ├── demo07_regions_hierarchy/
    ├── demo08_full_min/
    └── ...

### Per-Run Output Files

Each time a scenario is executed, the model generates timestamped result files:

    summary_<scenario>_<timestamp>.csv
    operations_<scenario>_<timestamp>.csv

- `summary_<scenario>_<timestamp>.csv`  
  High-level summary of the run (objective value, slack totals, balance checks, key aggregates).

- `operations_<scenario>_<timestamp>.csv`  
  Detailed operational results (flows, production, storage activity, regasification, investments).

The timestamp ensures that multiple runs of the same scenario do not overwrite each other and remain fully reproducible.

### Run Log

Each scenario folder also contains:

    runs_<scenario>.csv

This file records all runs of the scenario and acts as a cumulative execution history,
tracking timestamps and key indicators for each run.    

# NordHHub
Multigas Network Optimization Model (Python) – Data Loader, Model Builder, and Documentation:

NordHHub/
│
├── data/               # Input Excel scenarios
│    └── mget_input_scenario.xlsx
│
├── src/                # All Python source code
│    ├── mget_load_data.py     # Data loader (reads the Excel scenario)
│    ├── mget_main_model.py    # Main model: build + solve + call reporting
│    └── report.py             # Reporting and export tools
│
├── results/            # Auto-created output files
│    └── results_<scenario>/
│         ├── summary_<timestamp>.csv
│         ├── flows_<timestamp>.csv
│         ├── production_<timestamp>.csv
│         ├── ... etc
│         └── <scenario>_runs_log.csv
│
└── README.md


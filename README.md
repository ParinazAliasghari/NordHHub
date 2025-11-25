NordHHub/
│
├── data/ # Input Excel scenarios
│ └── mget_input_scenario.xlsx
│
├── src/ # All Python source code
│ ├── mget_load_data.py # Data loader (reads the Excel scenario)
│ ├── mget_main_model.py # Main model: build + solve + call reporting
│ └── report.py # Reporting and CSV export tools
│
├── results/ # Auto-created output files (one folder per scenario)
│ └── results_<scenario>/ # Example: results_mget_input_scenario/
│ ├── summary_<timestamp>.csv
│ ├── flows_<timestamp>.csv
│ ├── production_<timestamp>.csv
│ ├── expansion_<timestamp>.csv
│ ├── borrowed_<timestamp>.csv
│ ├── deficits_<timestamp>.csv
│ └── <scenario>_runs_log.csv # Cumulative log of all runs
│
└── README.md


# Data loading module `my_load_all.py`

## 1. Purpose

The module `my_load_all.py` is responsible for:

- Reading the Excel scenario file (`nodes`, `arcs`, `supplys`, `demands`, `other`, etc.)
- Cleaning raw columns (trimming whitespace, removing illegal characters)
- Converting Excel cells into numeric values
- Determining topology (nodes, arcs, start/end)
- Constructing time structure (years, hours, discount, scaling)
- Parsing scalar parameters used by the optimization model

It is the **single source of truth** for converting Excel input into Python
data structures for the MGET optimization model.

---

## 2. High-Level Structure

```text
my_load_all.py
├─ imports + PATH setup (INPUT_XLSX)
├─ helper functions:
│   - _is_nan, _clean_str
│   - _infer_endpoints_from_name
│   - _endpoints_for_row
│   - _num  (parse numeric or percent inputs)
├─ Excel readers:
│   - read_network_excel(...)   # nodes, arcs, supply, demand
│   - read_other_params(...)    # scalar costs, YearStep, scale, etc.
├─ main builder:
│   - prepare_mget_data(xlsx_path) -> dict
│       Part 1: topology
│       Part 2: time structure
│       Part 3: scalar parameters
└─ __main__ self-test

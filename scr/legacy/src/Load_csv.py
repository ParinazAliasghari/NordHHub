"""
load_csv.py

Data loading and preprocessing utilities for the MGET network model
using **CSV** input files instead of Excel.

Responsibilities
----------------
- Read the CSV files in one scenario directory:
    nodes.csv
    arcs.csv
    production.csv   (supply)
    consumption.csv  (demand)
    other.csv        (scalar parameters)
    discount.csv     (optional: year → discount factor)
    timeseries.csv   (optional: hour → scale factor)

- Do very light cleaning:
    * lower-case column names
    * strip whitespace from string columns

- Build plain Python data structures (lists + dicts) that the Pyomo
  model can consume to define Sets and Params.

The model file can do:

    from load_csv import DATA_DIR, prepare_mget_data_from_csv

    data = prepare_mget_data_from_csv(DATA_DIR)

and then use `data` to populate Pyomo Sets/Params.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, List, Optional

import math
import pandas as pd

# ---------------------------------------------------------------------------
# Scenario directory
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent

# Default scenario folder:  <repo_root>/data/scenario1
DATA_DIR = HERE / "data" / "scenario1"

# Allow overriding from command line:
#   python load_csv.py path/to/other_scenario
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        DATA_DIR = Path(sys.argv[1]).expanduser().resolve()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _read_csv_if_exists(data_dir: Path, filename: str) -> pd.DataFrame:
    """
    Read `data_dir/filename` as CSV if it exists, otherwise return empty DF.

    We explicitly use encoding="cp1252" to avoid the UnicodeDecodeError that
    happens when files are saved by Excel with Windows-1252 characters.

    If you later re-save all CSVs as UTF-8, you can change this to:
        pd.read_csv(path)  # without encoding=
    """
    path = data_dir / filename
    if not path.exists():
        print(f"Warning: CSV not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path, encoding="cp1252")
    # normalise column names: lower case, no leading/trailing spaces
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _is_nan(x) -> bool:
    try:
        return x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x)
    except Exception:
        return False


def _clean_str(x) -> Optional[str]:
    """
    Convert a value to a stripped string, or return None if it's NaN-like.
    """
    if _is_nan(x):
        return None
    return str(x).strip()


# ---------------------------------------------------------------------------
# Reading all CSVs
# ---------------------------------------------------------------------------

def read_network_csvs(data_dir: Path):
    """
    Read all relevant CSVs in `data_dir`.

    Expected filenames (all optional; missing files → empty DataFrame):

        nodes.csv
        arcs.csv
        production.csv
        consumption.csv
        other.csv
        discount.csv
        timeseries.csv

    Returns:
        (nodes_df, arcs_df, prod_df, cons_df, other_df, disc_df, ts_df)
    """
    print(f"Data directory: {data_dir}")

    nodes_df = _read_csv_if_exists(data_dir, "nodes.csv")
    arcs_df  = _read_csv_if_exists(data_dir, "arcs.csv")
    prod_df  = _read_csv_if_exists(data_dir, "production.csv")
    cons_df  = _read_csv_if_exists(data_dir, "consumption.csv")
    other_df = _read_csv_if_exists(data_dir, "other.csv")
    disc_df  = _read_csv_if_exists(data_dir, "discount.csv")
    ts_df    = _read_csv_if_exists(data_dir, "timeseries.csv")

    return nodes_df, arcs_df, prod_df, cons_df, other_df, disc_df, ts_df


# ---------------------------------------------------------------------------
# Simple reader for other.csv (scalar parameters)
# ---------------------------------------------------------------------------

def read_other_simple(other_df: pd.DataFrame) -> dict:
    """
    Build a very compact dictionary from other.csv.

    Expected columns (all lower-case after normalisation):
        scalar, name_id, fuel, value, ...

    Returns a dict with keys:
        'c_a', 'f_ab', 'c_ab', 'c_x', 'c_r', 'f_r'  ->  fuel -> value
        'yearstep'                                ->  float or None
        'vola2'                                   ->  (name_id, fuel) -> value
        'scale'                                   ->  name_id -> value
        'c_bl'                                    ->  name_id -> value
    """
    if other_df.empty:
        return {}

    df = other_df.copy()

    def _num(x):
        return float(x) if pd.notna(x) else None

    out: dict = {}

    # 1) fuel-based parameters
    for pname in ["c_a", "f_ab", "c_ab", "c_x", "c_r", "f_r"]:
        rows = df[df["scalar"] == pname]
        out[pname] = {
            str(r["fuel"]).strip(): _num(r["value"])
            for _, r in rows.iterrows()
            if pd.notna(r.get("fuel"))
        }

    # 2) YearStep: a single scalar
    ys = df[df["scalar"] == "yearstep"]
    out["yearstep"] = _num(ys["value"].iloc[0]) if not ys.empty else None

    # 3) Vola2: (name_id, fuel) -> value
    rows = df[df["scalar"] == "vola2"]
    out["vola2"] = {
        (str(r["name_id"]).strip(), str(r["fuel"]).strip()): _num(r["value"])
        for _, r in rows.iterrows()
        if pd.notna(r.get("name_id")) and pd.notna(r.get("fuel"))
    }

    # 4) scale: name_id -> value
    rows = df[df["scalar"] == "scale"]
    out["scale"] = {
        str(r["name_id"]).strip(): _num(r["value"])
        for _, r in rows.iterrows()
        if pd.notna(r.get("name_id"))
    }

    # 5) c_bl: name_id -> value
    rows = df[df["scalar"] == "c_bl"]
    out["c_bl"] = {
        str(r["name_id"]).strip(): _num(r["value"])
        for _, r in rows.iterrows()
        if pd.notna(r.get("name_id"))
    }

    return out


# ---------------------------------------------------------------------------
# Main data-prep function from CSVs
# ---------------------------------------------------------------------------

def prepare_mget_data_from_csv(data_dir: Path) -> dict:
    """
    High-level helper:

    1. Read all CSVs in `data_dir`.
    2. Build plain Python lists/dicts that are easy to feed into Pyomo.

    The focus is on the *test system* you set up:
        - nodes.csv with a few nodes
        - arcs.csv with gas pipeline connections
        - production.csv / consumption.csv for gas
        - other.csv for scalar parameters
    """
    (
        nodes_df,
        arcs_df,
        prod_df,
        cons_df,
        other_df,
        disc_df,
        ts_df,
    ) = read_network_csvs(data_dir)

    # ----------------- Nodes -----------------------------------------------
    if nodes_df.empty:
        raise ValueError("nodes.csv is empty or missing – cannot build model.")

    # We assume node_id column exists
    if "node_id" not in nodes_df.columns:
        raise ValueError("nodes.csv must have a 'node_id' column.")

    node_names = (
        nodes_df["node_id"].astype(str).map(str.strip).unique().tolist()
    )

    # ----------------- Arcs ------------------------------------------------
    if arcs_df.empty:
        raise ValueError("arcs.csv is empty or missing – cannot build model.")

    required_arc_cols = {"arc_id", "start_node", "end_node"}
    if not required_arc_cols.issubset(arcs_df.columns):
        raise ValueError(
            f"arcs.csv must contain columns: {sorted(required_arc_cols)}"
        )

    arc_ids: List[str] = []
    start_of: Dict[str, str] = {}
    end_of: Dict[str, str] = {}

    for _, row in arcs_df.iterrows():
        a = str(row["arc_id"]).strip()
        i = str(row["start_node"]).strip()
        j = str(row["end_node"]).strip()
        arc_ids.append(a)
        start_of[a] = i
        end_of[a] = j

    # Fuels: from prod/cons and/or arcs
    fuels = set()
    for df in (prod_df, cons_df, arcs_df):
        if "fuel" in df.columns:
            fuels.update(
                _clean_str(v) for v in df["fuel"].dropna().unique()
            )
    fuels.discard(None)
    fuels = sorted(fuels) or ["gas"]  # default to gas

    # ----------------- Years & hours --------------------------------------
    years = set()
    hours = set()

    for df in (prod_df, cons_df):
        if "year" in df.columns:
            years.update(int(y) for y in df["year"].dropna().unique())
        if "hour" in df.columns:
            hours.update(int(h) for h in df["hour"].dropna().unique())

    Y = sorted(years) or [2025]
    H = sorted(hours) or [1]

    # ----------------- Discount (r_param[y]) -------------------------------
    r_param: Dict[int, float] = {y: 1.0 for y in Y}
    if not disc_df.empty and {"year", "r"}.issubset(disc_df.columns):
        for _, row in disc_df.iterrows():
            y = int(row["year"])
            r_param[y] = float(row["r"])

    # ----------------- Scale (scale_param[h]) ------------------------------
    scale_param: Dict[int, float] = {h: 1.0 for h in H}
    if not ts_df.empty and {"hour", "scale"}.issubset(ts_df.columns):
        for _, row in ts_df.iterrows():
            h = int(row["hour"])
            scale_param[h] = float(row["scale"])

    # ----------------- Production (cap_p, c_p) -----------------------------
    cap_p: Dict[Tuple[str, str, int, int], float] = {}
    c_p: Dict[Tuple[str, str, int, int], float] = {}

    if not prod_df.empty:
        for _, row in prod_df.iterrows():
            n = str(row["node_id"]).strip()
            f = _clean_str(row.get("fuel"))
            if not f:
                continue
            y = int(row["year"]) if "year" in prod_df.columns else Y[0]
            h = int(row["hour"]) if "hour" in prod_df.columns else H[0]

            cap = row.get("capacity")
            cost = row.get("marginal_cost")

            if not _is_nan(cap):
                cap_p[(n, f, y, h)] = float(cap)
            if not _is_nan(cost):
                c_p[(n, f, y, h)] = float(cost)

    # ----------------- Consumption (dmd, c_dz) -----------------------------
    dmd: Dict[Tuple[str, str, int, int], float] = {}
    c_dz: Dict[str, float] = {}

    if not cons_df.empty:
        for _, row in cons_df.iterrows():
            n = str(row["node_id"]).strip()
            f = _clean_str(row.get("fuel"))
            if not f:
                continue
            y = int(row["year"]) if "year" in cons_df.columns else Y[0]
            h = int(row["hour"]) if "hour" in cons_df.columns else H[0]

            demand = row.get("demand")
            penalty = row.get("penalty_cost")

            if not _is_nan(demand):
                dmd[(n, f, y, h)] = float(demand)
            if not _is_nan(penalty):
                c_dz[f] = float(penalty)

    # ----------------- Arc capacity & cost (c_a, cap_a) --------------------
    c_a: Dict[Tuple[str, str, int], float] = {}
    cap_a: Dict[Tuple[str, str, int], float] = {}

    col_cap = "capacity" if "capacity" in arcs_df.columns else None
    col_len = "length_km" if "length_km" in arcs_df.columns else None

    for _, row in arcs_df.iterrows():
        a = str(row["arc_id"]).strip()
        f = _clean_str(row.get("fuel"))
        if not f:
            # if fuel missing, apply to all fuels
            arc_fuels = fuels
        else:
            arc_fuels = [f]
        y = Y[0]  # test case: one set of arc data

        # For now we only use capacity; you can extend with costs (c_a) later
        cap_val = row.get(col_cap) if col_cap else None
        cost_val = row.get("cal_c") if "cal_c" in arcs_df.columns else None

        for fuel in arc_fuels:
            if not _is_nan(cap_val):
                cap_a[(a, fuel, y)] = float(cap_val)
            if not _is_nan(cost_val):
                c_a[(a, fuel, y)] = float(cost_val)

    # Expansion & binary costs – leave empty for now, but keep keys
    c_x_dict: Dict[Tuple[str, str, int], float] = {}
    c_b_dict: Dict[Tuple[str, int], float] = {}

    # ----------------- Scalar parameters from other.csv --------------------
    other_simple = read_other_simple(other_df)

    # For now we do not build an efficiency matrix; assume 1.0 for all
    eff: Dict[Tuple[str, str], float] = {}
    for a in arc_ids:
        for f in fuels:
            eff[(f, a)] = 1.0

    # ----------------- Final dictionary -----------------------------------
    return {
        "node_names": node_names,
        "arc_ids": arc_ids,
        "start_of": start_of,
        "end_of": end_of,
        "fuels": fuels,
        "Y": Y,
        "H": H,
        "r_param": r_param,
        "scale_param": scale_param,
        "cap_p": cap_p,
        "c_p": c_p,
        "dmd": dmd,
        "c_dz": c_dz,
        "c_a": c_a,
        "cap_a": cap_a,
        "c_x": c_x_dict,
        "c_b": c_b_dict,
        "eff": eff,
        # scalar parameters from other.csv
        "c_a_base": other_simple.get("c_a", {}),
        "f_ab_base": other_simple.get("f_ab", {}),
        "c_ab_base": other_simple.get("c_ab", {}),
        "c_x_base": other_simple.get("c_x", {}),
        "c_r_base": other_simple.get("c_r", {}),
        "f_r_base": other_simple.get("f_r", {}),
        "YearStep": other_simple.get("yearstep"),
        "Vola2": other_simple.get("vola2", {}),
        "scale2": other_simple.get("scale", {}),
        "c_bl": other_simple.get("c_bl", {}),
    }


# ---------------------------------------------------------------------------
# Simple CLI / self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Using data directory:", DATA_DIR)
    data = prepare_mget_data_from_csv(DATA_DIR)

    print("\n=== Summary ===")
    print("nodes:", data["node_names"])
    print("arcs :", data["arc_ids"])
    print("fuels:", data["fuels"])
    print("Y (years):", data["Y"])
    print("H (hours):", data["H"])
    print("\nPrepared data keys:", list(data.keys()))

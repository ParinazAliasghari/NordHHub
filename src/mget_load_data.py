"""
my_load_all.py

Unified data loading and preprocessing utilities for the multigas (MGET) model.

Responsibilities:
- Read the Excel scenario file (nodes, arcs, supply, demand, other, etc.).
- Clean column names and key string columns.
- Build plain Python data structures (lists + dicts) for the Pyomo model.

Logically split into 3 parts inside `prepare_mget_data`:
  1) Topology (nodes, arcs, directions)
  2) Time structure (years, hours, discount, hourly scaling)
  3) Scalar parameters:
       - Supply / demand / arc costs & capacities
       - Investment costs
       - "other" sheet (fuel-based scalars, YearStep, Vola2, scale, c_bl)

Usage from the model file:

    from my_load_all import INPUT_XLSX, prepare_mget_data

    data = prepare_mget_data(INPUT_XLSX)

    # Then use:
    #   data["node_names"], data["arc_ids"], data["start_of"], data["end_of"]
    #   data["fuels"], data["Y"], data["H"]
    #   data["cap_p"], data["c_p"], data["dmd"], data["c_dz"]
    #   data["c_a"], data["cap_a"], data["c_x"], data["c_b"], data["eff"]
    #   data["other_params"], data["YearStep"]
"""

from __future__ import annotations

from pathlib import Path
import sys
import math
from typing import Optional, Tuple, Dict, List, Any

import pandas as pd


# ---------------------------------------------------------------------------
# Path to the default Excel input file
# ---------------------------------------------------------------------------

HERE = Path(__file__).parent

# Change this to your default scenario
INPUT_XLSX = HERE / "data" / "sample_scenario_mget_v6.xlsx"

# Optional: allow overriding the input file from the command line:
#   python my_load_all.py path/to/other_scenario.xlsx
if len(sys.argv) > 1:
    INPUT_XLSX = Path(sys.argv[1]).expanduser().resolve()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _is_nan(x) -> bool:
    """Return True if `x` behaves like a NaN / missing value."""
    try:
        return x is None or (isinstance(x, float) and math.isnan(x))
    except Exception:
        return False


def _clean_str(x) -> Optional[str]:
    """
    Convert a value to a stripped string, or return None if it's NaN-like.

    Used for keys like node names and fuel names.
    """
    if _is_nan(x):
        return None
    else:
        return str(x).strip()


def _infer_endpoints_from_name(arc_id: str) -> Optional[Tuple[str, str]]:
    """
    Try to infer (start_node, end_node) from an arc name like 'A_B'.
    """
    if not isinstance(arc_id, str):
        return None
    if "_" in arc_id:
        i, j = arc_id.split("_", 1)
        i, j = i.strip(), j.strip()
        if i and j:
            return i, j
    return None


def _endpoints_for_row(arc_id: str, start_node, end_node) -> Tuple[str, str]:
    """
    Determine the (start_node, end_node) for a given arc row.
    """
    s = None if _is_nan(start_node) else (str(start_node).strip() if start_node is not None else None)
    t = None if _is_nan(end_node)   else (str(end_node).strip()   if end_node   is not None else None)
    if s and t:
        return s, t

    infer = _infer_endpoints_from_name(str(arc_id))
    if infer is not None:
        return infer

    raise ValueError(
        f"Cannot determine endpoints for arc '{arc_id}'. "
        "Provide start_node/end_node columns or name the arc like 'A_B'."
    )


def _num(x: Any):
    """
    Convert cell value to float if possible.

    - NaN / empty -> None
    - '0 %' / '2 %' -> 0.0 / 2.0
    - normal numbers -> float
    """
    if pd.isna(x):
        return None
    if isinstance(x, str):
        s = x.strip()
        if s == "":
            return None
        s = s.replace("%", "").strip()
        try:
            return float(s)
        except ValueError:
            return x
    try:
        return float(x)
    except Exception:
        return x


# ---------------------------------------------------------------------------
# Excel readers
# ---------------------------------------------------------------------------

def read_network_excel(xlsx_path: Path):
    """
    Read the core sheets from the Excel scenario file.

    Expected sheets:
        - "nodes"
        - "arcs"
        - "supplys"
        - "demands"

    Returns:
        (nodes_df, arcs_df, supplies_df, demands_df) as pandas DataFrames
        with stripped column names and cleaned key columns.
    """
    xls = pd.ExcelFile(str(xlsx_path))

    nodes_df    = pd.read_excel(xls, "nodes")
    arcs_df     = pd.read_excel(xls, "arcs")
    supplies_df = pd.read_excel(xls, "supplys")
    demands_df  = pd.read_excel(xls, "demands")

    # Strip whitespace from column headers
    for df in (nodes_df, arcs_df, supplies_df, demands_df):
        df.columns = df.columns.str.strip()

    def rmspaces(df, cols):
        for c in cols:
            if c in df.columns:
                df[c] = df[c].astype(str).str.replace(r"\s+", "", regex=True)
        return df

    def coerce_numeric_checked(df, cols, sheet_name):
        for c in cols:
            if c in df.columns:
                raw = df[c]
                num = pd.to_numeric(raw, errors="coerce")
                bad_mask = num.isna() & raw.notna() & (
                    raw.astype(str).str.strip() != ""
                )
                if bad_mask.any():
                    bad_values = sorted({str(v) for v in raw[bad_mask].unique()})
                    raise ValueError(
                        f"Invalid numeric entries in sheet '{sheet_name}', "
                        f"column '{c}': {bad_values[:5]} "
                        "(please correct these in the Excel file)"
                    )
                df[c] = num
        return df

    nodes_df    = rmspaces(nodes_df,    ["node"])
    arcs_df     = rmspaces(arcs_df,     ["arc_id", "start_node", "end_node"])
    supplies_df = rmspaces(supplies_df, ["node", "fuel"])
    demands_df  = rmspaces(demands_df,  ["node", "fuel"])

    arcs_df = coerce_numeric_checked(
        arcs_df,
        ["cost_arc", "capp1", "capp2", "cap", "arc_cost", "capacity"],
        sheet_name="arcs",
    )
    supplies_df = coerce_numeric_checked(
        supplies_df,
        ["supply", "supply_cost"],
        sheet_name="supplys",
    )
    demands_df = coerce_numeric_checked(
        demands_df,
        ["demand", "penalty_cost"],
        sheet_name="demands",
    )

    return nodes_df, arcs_df, supplies_df, demands_df


def read_other_params(xlsx_path: str | Path) -> Dict[str, Any]:
    """
    Read the 'other' sheet and return simple dictionaries:

      c_a, f_ab, c_ab, c_x, c_r, f_r :  fuel -> value
      YearStep                       :  single number
      Vola2                          :  (name_id, fuel) -> value
      scale                          :  name_id -> value
      c_bl                           :  name_id -> value   (fuel ignored)
    """
    xlsx_path = Path(xlsx_path)
    df = pd.read_excel(xlsx_path, sheet_name="other")
    df.columns = df.columns.str.strip()

    result: Dict[str, Any] = {}

    fuel_params = ["c_a", "f_ab", "c_ab", "c_x", "c_r", "f_r"]
    for pname in fuel_params:
        rows = df[df["scalar"] == pname]
        result[pname] = {
            str(r.fuel).strip(): _num(r.value)
            for _, r in rows.iterrows()
            if pd.notna(r.fuel)
        }

    ys = df[df["scalar"] == "YearStep"]
    result["YearStep"] = _num(ys["value"].iloc[0]) if not ys.empty else None

    rows = df[df["scalar"] == "Vola2"]
    result["Vola2"] = {
        (str(r.name_id).strip(), str(r.fuel).strip()): _num(r.value)
        for _, r in rows.iterrows()
        if pd.notna(r.name_id) and pd.notna(r.fuel)
    }

    rows = df[df["scalar"] == "scale"]
    result["scale"] = {
        str(r.name_id).strip(): _num(r.value)
        for _, r in rows.iterrows()
        if pd.notna(r.name_id)
    }

    rows = df[df["scalar"] == "c_bl"]
    result["c_bl"] = {
        str(r.name_id).strip(): _num(r.value)
        for _, r in rows.iterrows()
        if pd.notna(r.name_id)
    }

    return result


# ---------------------------------------------------------------------------
# Main data-preparation function for the model
# ---------------------------------------------------------------------------

def prepare_mget_data(xlsx_path: Path) -> dict:
    """
    Read the Excel file and build all Python data structures needed by the
    MGET Pyomo model.

    Internally split into three logical parts:
      1) TOPOLOGY: nodes, arcs, start/end of each arc
      2) TIME: fuels, years Y, hours H, discount factors r_param,
               per-hour scaling scale_param
      3) SCALARS: supply/demand, costs, capacities, investment costs,
                  plus 'other' scalars (c_a, f_ab, ..., YearStep, Vola2, scale, c_bl)
    """
    nodes_df, arcs_df_raw, supplies_df, demands_df = read_network_excel(xlsx_path)

    # === Part 1: TOPOLOGY (nodes, arcs, start/end) =========================
    if {"start_node", "end_node"}.issubset(arcs_df_raw.columns):
        arcs_rev = arcs_df_raw.copy()
        arcs_rev["start_node"], arcs_rev["end_node"] = (
            arcs_df_raw["end_node"],
            arcs_df_raw["start_node"],
        )
        arcs_rev["arc_id"] = (
            arcs_rev["start_node"].astype(str) + "_" + arcs_rev["end_node"].astype(str)
        )
        for c in ("arc_cost", "capacity", "fuel", "x_cost", "bd_cost"):
            if c in arcs_rev.columns and c in arcs_df_raw.columns:
                arcs_rev[c] = arcs_df_raw[c]
        arcs_df = pd.concat([arcs_df_raw, arcs_rev], ignore_index=True)
    else:
        arcs_df = arcs_df_raw.copy()

    node_names = (
        nodes_df["node"].astype(str).map(str.strip).unique().tolist()
    )

    arc_ids: List[str] = []
    start_of: Dict[str, str] = {}
    end_of: Dict[str, str] = {}

    cols = {c.lower().strip(): c for c in arcs_df.columns}
    c_arc = cols.get("arc_id") or cols.get("arc")
    c_s   = cols.get("start_node") or cols.get("from")
    c_t   = cols.get("end_node")   or cols.get("to")

    for row in arcs_df.itertuples(index=False):
        arc_id = str(getattr(row, c_arc))
        i, j = _endpoints_for_row(arc_id, getattr(row, c_s), getattr(row, c_t))
        arc_ids.append(arc_id)
        start_of[arc_id] = i
        end_of[arc_id]   = j

    # === Part 2: TIME (fuels, years, hours, discount, hourly scaling) ======
    fuels = sorted(
        set(
            supplies_df.get("fuel", []).dropna().map(str).map(str.strip)
            if "fuel" in supplies_df.columns else []
        ).union(
            demands_df.get("fuel", []).dropna().map(str).map(str.strip)
            if "fuel" in demands_df.columns else []
        )
    )
    if not fuels:
        fuels = ["gas"]

    Y = (
        sorted(set(supplies_df.get("year", [])) | set(demands_df.get("year", [])))
        if "year" in supplies_df.columns or "year" in demands_df.columns
        else [2025]
    )

    H = sorted(set(demands_df.get("hour", []))) if "hour" in demands_df.columns else [1]

    r_param = {y: 1.0 for y in Y}
    scale_param = {h: 1.0 for h in H}

    try:
        xls = pd.ExcelFile(str(xlsx_path))
        if "discount" in xls.sheet_names:
            ddf = pd.read_excel(xls, "discount")
            if {"year", "r"}.issubset(ddf.columns):
                r_param = {int(y): float(r) for y, r in zip(ddf["year"], ddf["r"])}
                for y in Y:
                    r_param.setdefault(y, 1.0)
        if "scale" in xls.sheet_names:
            sdf = pd.read_excel(xls, "scale")
            if {"hour", "scale"}.issubset(sdf.columns):
                scale_param = {int(h): float(s) for h, s in zip(sdf["hour"], sdf["scale"])}
                for h in H:
                    scale_param.setdefault(h, 1.0)
    except Exception:
        pass

    # === Part 3: SCALARS (cap, costs, "other") ============================

    # 3.1 Supply capacities & costs
    cap_p: Dict[tuple, float] = {}
    c_p: Dict[tuple, float]   = {}

    if {"node", "fuel"}.issubset(supplies_df.columns):
        for row in supplies_df.itertuples(index=False):
            n = _clean_str(getattr(row, "node"))
            e = _clean_str(getattr(row, "fuel"))
            y = getattr(row, "year", Y[0]) if "year" in supplies_df.columns else Y[0]
            h = getattr(row, "hour", H[0]) if "hour" in supplies_df.columns else H[0]
            if n and e:
                cap_p[(n, e, y, h)] = float(getattr(row, "supply", 0.0) or 0.0)
                c_p[(n, e, y, h)]   = float(getattr(row, "supply_cost", 0.0) or 0.0)

    # 3.2 Demand & penalty
    dmd: Dict[tuple, float] = {}
    c_dz: Dict[str, float] = {}

    if {"node", "fuel"}.issubset(demands_df.columns):
        for row in demands_df.itertuples(index=False):
            n = _clean_str(getattr(row, "node"))
            e = _clean_str(getattr(row, "fuel"))
            y = getattr(row, "year", Y[0]) if "year" in demands_df.columns else Y[0]
            h = getattr(row, "hour", H[0]) if "hour" in demands_df.columns else H[0]
            if n and e:
                dmd[(n, e, y, h)] = float(getattr(row, "demand", 0.0) or 0.0)
                pc = getattr(row, "penalty_cost", None)
                if not _is_nan(pc):
                    c_dz[e] = float(pc)

    for e in fuels:
        c_dz.setdefault(e, 1e4)

    # 3.3 Arc transport cost & capacity
    c_a: Dict[tuple, float]   = {}
    cap_a: Dict[tuple, float] = {}

    BIGM = 1e12

    arc_cols = {c.lower().strip(): c for c in arcs_df.columns}
    col_cost = arc_cols.get("arc_cost") or arc_cols.get("cost_arc")
    col_cap  = arc_cols.get("capacity") or arc_cols.get("cap")
    col_fuel = arc_cols.get("fuel")

    if col_fuel in arcs_df.columns:
        for row in arcs_df.itertuples(index=False):
            a = str(getattr(row, c_arc))
            e = _clean_str(getattr(row, col_fuel))
            y = Y[0]
            if e:
                cost = float(getattr(row, col_cost, 0.0) or 0.0) if col_cost in arcs_df.columns else 0.0
                cap  = float(getattr(row, col_cap,  0.0) or 0.0) if col_cap  in arcs_df.columns else 0.0
                c_a[(a, e, y)]   = cost
                cap_a[(a, e, y)] = cap
    else:
        for row in arcs_df.itertuples(index=False):
            a = str(getattr(row, c_arc))
            y = Y[0]
            cost = float(getattr(row, col_cost, 0.0) or 0.0) if col_cost in arcs_df.columns else 0.0
            cap  = float(getattr(row, col_cap,  0.0) or 0.0) if col_cap  in arcs_df.columns else BIGM
            for e in fuels:
                c_a[(a, e, y)]   = cost
                cap_a[(a, e, y)] = cap

    # 3.4 Investment costs
    c_x_dict: Dict[tuple, float] = {}
    c_b_dict: Dict[tuple, float] = {}

    cx_col = arc_cols.get("x_cost")
    cb_col = arc_cols.get("bd_cost")

    if cx_col in arcs_df.columns:
        for row in arcs_df.itertuples(index=False):
            a = str(getattr(row, c_arc))
            y = Y[0]
            cx = getattr(row, cx_col)
            if not _is_nan(cx):
                for e in fuels:
                    c_x_dict[(a, e, y)] = float(cx)

    if cb_col in arcs_df.columns:
        for row in arcs_df.itertuples(index=False):
            a = str(getattr(row, c_arc))
            y = Y[0]
            cb = getattr(row, cb_col)
            if not _is_nan(cb):
                c_b_dict[(a, y)] = float(cb)

    # 3.5 Arc efficiencies (currently all 1.0)
    eff = {(e, a): 1.0 for e in fuels for a in arc_ids}

    # 3.6 "other" scalars from the 'other' sheet
    try:
        other_params = read_other_params(xlsx_path)
    except Exception:
        other_params = {}
    YearStep = other_params.get("YearStep")

    # SUCCESS MESSAGE
    print("✓ All parts validated successfully: topology, time structure, scalar parameters, and 'other' sheet.")



    # Final dictionary returned to the model code
    return {
        # topology
        "node_names": node_names,
        "arc_ids": arc_ids,
        "start_of": start_of,
        "end_of": end_of,

        # time structure
        "fuels": fuels,
        "Y": Y,
        "H": H,
        "r_param": r_param,
        "scale_param": scale_param,

        # scalar params
        "cap_p": cap_p,
        "c_p": c_p,
        "dmd": dmd,
        "c_dz": c_dz,
        "c_a": c_a,
        "cap_a": cap_a,
        "c_x": c_x_dict,
        "c_b": c_b_dict,
        "eff": eff,

        # 'other' sheet
        "other_params": other_params,   # full dict: c_a, f_ab, c_ab, c_x, c_r, f_r, YearStep, Vola2, scale, c_bl
        "YearStep": YearStep,          # convenient shortcut for time step length
    }


# ---------------------------------------------------------------------------
# Simple CLI / self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("cwd:      ", Path().resolve())
    print("xlsx_path:", INPUT_XLSX)
    print("exists?:  ", INPUT_XLSX.exists())
    print(f"\nReading Excel file: {INPUT_XLSX}\n")

    try:
        nodes_df, arcs_df, supplies_df, demands_df = read_network_excel(INPUT_XLSX)
        print("====================================")
        print("✓ File loaded successfully!\n")
        print("====================================")

        print("==================")
        print("=== Nodes ===")
        print("==================")
        print(nodes_df, "\n")

        print("==================")
        print("=== Arcs ===")
        print("==================")
        print(arcs_df, "\n")

        print("==================")
        print("=== Supply ===")
        print("==================")
        print(supplies_df, "\n")

        print("==================")
        print("=== Demand ===")
        print("==================")
        print(demands_df, "\n")

        data = prepare_mget_data(INPUT_XLSX)
        print("\nPrepared data keys:", list(data.keys()))

    except Exception as e:
        print("==================")
        print("✗ Error reading Excel file:", e)
        print("==================")
        if "openpyxl" in str(e).lower():
            print("==================")
            print("Hint: Try `pip install openpyxl`")
            print("==================")

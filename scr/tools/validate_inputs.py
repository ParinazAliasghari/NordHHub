from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

from scr.core.data_loading import load_inputs


DEFAULT_OTHER_CSV = Path(__file__).resolve().parents[2] / "data" / "scenario1" / "other.csv"


def main() -> None:
    other_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OTHER_CSV
    loaded = load_inputs(other_path=other_path)
    df = loaded["dat_o"]

    param_series = df["param"].astype(str).str.strip().str.lower()
    param_series = param_series[~param_series.isin(["", "nan", "none", "null"])]
    param_counts = param_series.value_counts().sort_index()
    has_bigm = (param_series == "bigm").any()

    print("Input validation OK")
    print(f"File: {other_path}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print(f"Unique params: {len(param_counts)}")
    for param, count in param_counts.items():
        print(f"  {param}: {int(count)}")
    print(f"Has bigM row: {bool(has_bigm)}")
    print(f"Timeseries file: {loaded['timeseries_path']}")
    print(f"Years detected: {loaded['y_values']}")
    print(f"Hours detected: {loaded['h_values']}")
    print(f"Nodes file: {loaded['nodes_path']}")
    print(f"Nodes detected: {loaded['n_values']}")
    print(f"Countries detected: {loaded['cn_values']}")
    print(f"NUTS2 detected: {loaded['nuts2_values']}")
    print(f"Regions detected: {loaded['rgn_values']}")
    print(f"n_in_c entries: {len(loaded['n_in_c'])}")
    print(f"n_in_2 entries: {len(loaded['n_in_2'])}")
    print(f"n_in_r entries: {len(loaded['n_in_r'])}")
    print(f"Consumption file: {loaded['consumption_path']}")
    print(f"Production file: {loaded['production_path']}")
    print(f"Regasification file: {loaded['regas_path']}")
    print(f"Storage file: {loaded['storage_path']}")
    print(f"Arcs file: {loaded['arcs_path']}")
    print(f"Consumption rows: {len(loaded['dat_consumption'])}")
    print(f"Production rows: {len(loaded['dat_production'])}")
    print(f"Regasification rows: {len(loaded['dat_regas'])}")
    print(f"Storage rows: {len(loaded['dat_storage'])}")
    print(f"Arcs rows: {len(loaded['dat_arcs'])}")
    if loaded.get("regas_warnings"):
        print("Regasification warnings:")
        for msg in loaded["regas_warnings"]:
            print(f"  - {msg}")
    if loaded.get("storage_warnings"):
        print("Storage warnings:")
        for msg in loaded["storage_warnings"]:
            print(f"  - {msg}")
    print(f"dmd entries: {len(loaded['dmd'])}")
    print(f"dmd2 entries: {len(loaded['dmd2'])}")
    print(f"cap_p entries: {len(loaded['cap_p'])}")
    print(f"c_p entries: {len(loaded['c_p'])}")
    print(f"c_lr entries: {len(loaded['c_lr'])}")
    print(f"ub_r entries: {len(loaded['ub_r'])}")
    print(f"cap_we entries: {len(loaded['cap_we'])}")
    print(f"cap_wi entries: {len(loaded['cap_wi'])}")
    print(f"cap_ww entries: {len(loaded['cap_ww'])}")
    print(f"c_we entries: {len(loaded['c_we'])}")
    print(f"e_w entries: {len(loaded['e_w'])}")
    print(f"a_values entries: {len(loaded['a_values'])}")
    print(f"a_s entries: {len(loaded['a_s'])}")
    print(f"a_e entries: {len(loaded['a_e'])}")
    print(f"cap_a entries: {len(loaded['cap_a'])}")
    print(f"c_a entries: {len(loaded['c_a'])}")
    print(f"e_a entries: {len(loaded['e_a'])}")

    # Arc validation checks
    dat_arcs = loaded.get("dat_arcs", pd.DataFrame())
    if not dat_arcs.empty:
        work = dat_arcs.copy()
        work["a"] = work["a"].astype(str).str.strip()
        work["start"] = work["start"].astype(str).str.strip()
        work["end"] = work["end"].astype(str).str.strip()

        duplicate_endpoint_arcs = 0
        for arc_id, grp in work.groupby("a"):
            if arc_id in {"", "nan", "none", "null"}:
                continue
            starts = set(grp["start"].tolist())
            ends = set(grp["end"].tolist())
            if len(starts) != 1 or len(ends) != 1:
                duplicate_endpoint_arcs += 1
        print(f"Arc endpoint consistency violations: {duplicate_endpoint_arcs}")

        nodes_from_nodes_csv = set(
            loaded.get("dat_nodes", pd.DataFrame()).get("n", pd.Series(dtype=str)).astype(str).str.strip().tolist()
        )
        arc_nodes = set(work["start"].tolist()) | set(work["end"].tolist())
        unknown_arc_nodes = sorted([n for n in arc_nodes if n and n not in nodes_from_nodes_csv])
        print(f"Arc nodes missing in nodes.csv: {len(unknown_arc_nodes)}")
        if unknown_arc_nodes:
            print(f"  Missing nodes sample: {unknown_arc_nodes[:10]}")

    cap_a_negative = sum(1 for v in loaded.get("cap_a", {}).values() if float(v) < -1e-9)
    c_a_negative = sum(1 for v in loaded.get("c_a", {}).values() if float(v) < -1e-9)
    e_a_out_of_range = sum(1 for v in loaded.get("e_a", {}).values() if float(v) < -1e-9 or float(v) > 1.0 + 1e-9)
    print(f"cap_a negative entries: {cap_a_negative}")
    print(f"c_a negative entries: {c_a_negative}")
    print(f"e_a out-of-range entries (<0 or >1): {e_a_out_of_range}")

    arc_fail_count = cap_a_negative + c_a_negative + e_a_out_of_range
    if not dat_arcs.empty:
        arc_fail_count += duplicate_endpoint_arcs + len(unknown_arc_nodes)
    print(f"ARC VALIDATION SUMMARY: {'PASS' if arc_fail_count == 0 else 'FAIL'} (issues={arc_fail_count})")


if __name__ == "__main__":
    main()

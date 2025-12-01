# ======================================================================
# report.py
# ----------------------------------------------------------------------
# Reporting utilities for the MGET model:
#   - summarize_solve_status : turn Pyomo results into a short message
#   - print_text_report      : print nonzero variables to the console
#   - export_results         : write CSV files into a per-scenario
#                              results folder and update a per-scenario
#                              run log (runs_log.csv).
#
# NOTE: This version is compatible with
#   * Excel-based workflows (scenario is an .xlsx file), and
#   * CSV-based workflows (scenario is a directory with CSV files).
#
# In both cases, the third argument to export_results is treated as the
# "scenario path". If it is a directory, its name is used as the scenario
# name. If it is a file, the stem (filename without extension) is used.
# ======================================================================

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import TerminationCondition, SolverStatus


# ----------------------------------------------------------------------
# User-facing formatting choices for the run log
# ----------------------------------------------------------------------
RUNLOG_DATE_FMT = "%d/%m/%Y %H:%M"  # e.g. 20/10/2025 13:21
SUCCESS_FLAG = "YES"
FAIL_FLAG = "NO"
PLACEHOLDER = "none"

# Canonical columns for runs_log.csv (order matters)
_LOG_COLUMNS = [
    "timestamp",
    "feasiblity",   # note the spelling, kept to match your existing example
    "error",
    "error stage",
    "total_cost",
    "demand",
    "solver",
    "build_s",
    "solve_s",
    "total_s",
]


# ----------------------------------------------------------------------
# Helper: append one row to runs_log.csv
# ----------------------------------------------------------------------
def _append_run_log(out_dir: Path, row: Dict[str, Any]) -> Path:
    """
    Append one row to runs_log.csv in 'out_dir', using _LOG_COLUMNS order
    and PLACEHOLDER for missing/None values.
    """
    import csv
    log_path = Path(out_dir) / "runs_log.csv"
    write_header = not log_path.exists()

    values = []
    for col in _LOG_COLUMNS:
        v = row.get(col, PLACEHOLDER)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            v = PLACEHOLDER
        values.append(v)

    with log_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(_LOG_COLUMNS)
        w.writerow(values)

    return log_path


# ----------------------------------------------------------------------
# Helper: summarize solver status
# ----------------------------------------------------------------------
def summarize_solve_status(results) -> str:
    """
    Convert the Pyomo 'results' object into a short human-readable string.
    """
    if results is None:
        return "Solve not run."

    stat = getattr(results.solver, "status", None)
    term = getattr(results.solver, "termination_condition", None)

    if stat == SolverStatus.ok:
        if term == TerminationCondition.optimal:
            return "Optimal solution found."
        if term == TerminationCondition.locallyOptimal:
            return "Locally optimal solution found."
        if term == TerminationCondition.feasible:
            return "Feasible solution found (not proven optimal)."
        if term == TerminationCondition.maxTimeLimit:
            return "Time limit reached; best available solution reported."
        if term == TerminationCondition.maxIterations:
            return "Iteration limit reached; best available solution reported."
        if term == TerminationCondition.unbounded:
            return "Model is unbounded."
        if term == TerminationCondition.infeasible:
            return "Model is infeasible."
        if term == TerminationCondition.infeasibleOrUnbounded:
            return "Model is infeasible or unbounded."
        if term == TerminationCondition.noSolution:
            return "No solution reported."
        if term == TerminationCondition.solverFailure:
            return "Solver failed."
        return f"Solve ended with status OK and termination '{term}'."

    if stat == SolverStatus.warning:
        return f"Solver warning: termination '{term}'."
    if stat == SolverStatus.error:
        return f"Solver error: termination '{term}'."
    if stat == SolverStatus.aborted:
        return f"Solver aborted: termination '{term}'."

    return f"Solve ended with status '{stat}' and termination '{term}'."


# ----------------------------------------------------------------------
# Helper: safe value() wrapper
# ----------------------------------------------------------------------
def _val(x, default=None):
    """
    Safely extract the numeric value of a Pyomo expression/variable.

    If value() fails (e.g. no solution assigned), return 'default' instead
    of raising an exception.
    """
    try:
        return pyo.value(x)
    except Exception:
        return default


# ======================================================================
# Text report (console printing)
# ======================================================================
def print_text_report(model: pyo.ConcreteModel, results, tol: float = 1e-9) -> None:
    """
    Print a human-readable report of the solution to the console.
    """
    val = _val

    # ---- Objective value
    print("\n=== Objective ===")
    objv = val(model.TotalCost)
    print("Total cost =", f"{objv:.6g}" if objv is not None else "(unavailable)")

    # ---- Production Q_P
    print("\n=== Nonzero production Q_P (any y,h) ===")
    for n in model.n:
        for e in model.F:
            for y in model.Y:
                for h in model.H:
                    v = val(model.Q_P[n, e, y, h], 0.0)
                    if v and v > tol:
                        print(f"Q_P[{n},{e}] y={y} h={h}: {v:g}")

    # ---- Flows F_A
    print("\n=== Nonzero flows F_A (any y,h) ===")
    for a in model.A:
        i = val(model.start_node[a])
        j = val(model.end_node[a])
        for e in model.F:
            for y in model.Y:
                for h in model.H:
                    v = val(model.F_A[a, e, y, h], 0.0)
                    if v and v > tol:
                        c = val(model.c_a[a, e, y], 0.0)
                        print(f"{a} ({i}->{j}) {e} y={y} h={h}: {v:g}  (cost {c})")

    # ---- Expansion X_A
    print("\n=== Nonzero expansion X_A ===")
    for a in model.A:
        for e in model.F:
            for y in model.Y:
                v = val(model.X_A[a, e, y], 0.0)
                if v and v > tol:
                    print(f"X_A[{a},{e},{y}] = {v:g}")

    # ---- BD decisions
    print("\n=== BD decisions (if any) ===")
    for a in model.A:
        for y in model.Y:
            v = val(model.BD[a, y])
            if v is not None and v > tol:
                print(f"BD[{a},{y}] = {v:.4f}")

    # ---- Borrowed opposite capacity K_OPP
    print("\n=== Nonzero borrowed opposite capacity K_OPP ===")
    for a in model.A:
        arev = model._a_rev_map[a]  # set in the main model file
        for e in model.F:
            for y in model.Y:
                v = val(model.K_OPP[a, e, y], 0.0)
                if v and v > tol:
                    print(f"K_OPP[{a},{e},{y}] = {v:g}  (borrowed from reverse arc '{arev}')")

    # ---- Deficits Z_D
    print("\n=== Nonzero deficits Z_D ===")
    for n in model.n:
        for e in model.F:
            for y in model.Y:
                for h in model.H:
                    v = val(model.Z_D[n, e, y, h], 0.0)
                    if v and v > tol:
                        print(f"Z_D[{n},{e},y={y},h={h}] = {v:g}")

    # ---- Solve status
    print("\n=== Solve note ===")
    note = summarize_solve_status(results)
    print(note)


# ======================================================================
# CSV exporter + per-scenario run log
# ======================================================================
def export_results(
    model: pyo.ConcreteModel,
    results,
    scenario_path: Path,
    outdir: Optional[Path] = None,
    tol: float = 1e-9,
    *,
    solver_name: Optional[str] = None,
    build_s: Optional[float] = None,
    solve_s: Optional[float] = None,
    total_s: Optional[float] = None,
) -> None:
    """
    Export solution results to CSV files AND append one row to a run log
    for this scenario.

    The third argument 'scenario_path' can be:
      - an Excel file (old workflow), or
      - a directory containing CSV input files (new workflow).

    In both cases the scenario name is derived from the last path
    component (file stem or directory name), and a folder named
    'results_<scenario_name>' is created inside the base results dir.
    """
    val = _val

    # ------------------------------------------------------------------
    # 1) Prepare timestamp and scenario-specific output folder
    # ------------------------------------------------------------------
    scenario_path = Path(scenario_path)

    # Distinguish between file and directory
    if scenario_path.is_dir():
        # CSV-based workflow: scenario_path = .../data/scenario1
        scenario_stem = scenario_path.name
        data_dir = scenario_path
        project_root = data_dir.parent
    else:
        # Excel-based workflow: scenario_path = .../data/my_scenario.xlsx
        scenario_stem = scenario_path.stem
        data_dir = scenario_path.parent
        project_root = data_dir.parent

    # timestamp string for filenames and human-readable log
    now = datetime.now()
    ts_stamp = now.strftime("%Y%m%d_%H%M%S")
    ts_human = now.strftime(RUNLOG_DATE_FMT)

    # Base directory for results
    if outdir is None:
        base_dir = project_root / "results"
    else:
        base_dir = Path(outdir)

    # Scenario folder with no time in its name
    scenario_dir = base_dir / f"results_{scenario_stem}"
    scenario_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 2) Summary info (used for both CSV and log)
    # ------------------------------------------------------------------
    total_cost = val(model.TotalCost)
    solve_note = summarize_solve_status(results)

    # Determine feasibility flag from solver status / termination
    feasiblity = FAIL_FLAG
    error_stage = "solve"
    if results is not None:
        stat = getattr(results.solver, "status", None)
        term = getattr(results.solver, "termination_condition", None)
        if stat == SolverStatus.ok and term not in (
            TerminationCondition.infeasible,
            TerminationCondition.infeasibleOrUnbounded,
            TerminationCondition.unbounded,
            TerminationCondition.noSolution,
        ):
            feasiblity = SUCCESS_FLAG
            error_stage = PLACEHOLDER
    else:
        error_stage = "solve"

    # If caller didn't pass solver_name, try to infer from results
    if solver_name is None and results is not None:
        solver_name = getattr(results.solver, "name", None)
    if solver_name is None:
        solver_name = PLACEHOLDER

    # Compute total demand (sum over all n,e,y,h)
    total_demand = 0.0
    try:
        for n in model.n:
            for e in model.F:
                for y in model.Y:
                    for h in model.H:
                        dv = val(model.dmd[n, e, y, h], 0.0)
                        if dv is not None:
                            total_demand += dv
    except Exception:
        total_demand = None

    # ------------------------------------------------------------------
    # 3) Write per-run CSV files into the scenario folder
    # ------------------------------------------------------------------
    prefix = f"{scenario_stem}_{ts_stamp}"

    # ---- Summary file: one row with objective and solve status
    summary = pd.DataFrame([{
        "scenario": scenario_stem,
        "input_path": str(scenario_path),
        "objective": total_cost,
        "solve_note": solve_note,
        "timestamp": ts_human,
    }])
    summary.to_csv(scenario_dir / f"summary_{prefix}.csv", index=False)

    # ---- Production Q_P
    rows = []
    for n in model.n:
        for e in model.F:
            for y in model.Y:
                for h in model.H:
                    v = val(model.Q_P[n, e, y, h])
                    if v is not None and v > tol:
                        rows.append({
                            "node": n,
                            "fuel": e,
                            "year": int(y),
                            "hour": int(h),
                            "value": float(v),
                            "unit_cost": float(val(model.c_p[n, e, y, h])),
                        })
    pd.DataFrame(rows).to_csv(
        scenario_dir / f"production_{prefix}.csv", index=False
    )

    # ---- Flows F_A
    rows = []
    for a in model.A:
        i = val(model.start_node[a])
        j = val(model.end_node[a])
        for e in model.F:
            for y in model.Y:
                for h in model.H:
                    v = val(model.F_A[a, e, y, h])
                    if v is not None and v > tol:
                        rows.append({
                            "arc": a,
                            "from": i,
                            "to": j,
                            "fuel": e,
                            "year": int(y),
                            "hour": int(h),
                            "value": float(v),
                            "unit_cost": float(val(model.c_a[a, e, y])),
                        })
    pd.DataFrame(rows).to_csv(
        scenario_dir / f"flows_{prefix}.csv", index=False
    )

    # ---- Expansion X_A
    rows = []
    for a in model.A:
        for e in model.F:
            for y in model.Y:
                v = val(model.X_A[a, e, y])
                if v is not None and v > tol:
                    rows.append({
                        "arc": a,
                        "fuel": e,
                        "year": int(y),
                        "value": float(v),
                        "unit_cost": float(val(model.c_x[a, e, y])),
                    })
    pd.DataFrame(rows).to_csv(
        scenario_dir / f"expansion_{prefix}.csv", index=False
    )

    # ---- Binary investment decisions BD
    rows = []
    for a in model.A:
        for y in model.Y:
            v = val(model.BD[a, y])
            if v is not None and v > tol:
                rows.append({
                    "arc": a,
                    "year": int(y),
                    "value": float(v),
                    "unit_cost": float(val(model.c_b[a, y])),
                })
    pd.DataFrame(rows).to_csv(
        scenario_dir / f"bd_{prefix}.csv", index=False
    )

    # ---- Borrowed opposite capacity K_OPP
    rows = []
    for a in model.A:
        arev = model._a_rev_map[a]  # reverse arc, set in main model
        for e in model.F:
            for y in model.Y:
                v = val(model.K_OPP[a, e, y])
                if v is not None and v > tol:
                    rows.append({
                        "arc": a,
                        "reverse_arc": arev,
                        "fuel": e,
                        "year": int(y),
                        "value": float(v),
                    })
    pd.DataFrame(rows).to_csv(
        scenario_dir / f"borrowed_{prefix}.csv", index=False
    )

    # ---- Deficits Z_D
    rows = []
    for n in model.n:
        for e in model.F:
            for y in model.Y:
                for h in model.H:
                    v = val(model.Z_D[n, e, y, h])
                    if v is not None and v > tol:
                        rows.append({
                            "node": n,
                            "fuel": e,
                            "year": int(y),
                            "hour": int(h),
                            "value": float(v),
                            "penalty": float(val(model.c_dz[e])),
                        })
    pd.DataFrame(rows).to_csv(
        scenario_dir / f"deficits_{prefix}.csv", index=False
    )

    print(f"\nCSV results written to: {scenario_dir.resolve()}")

    # ------------------------------------------------------------------
    # 4) Append to per-scenario run log (one row per run)
    # ------------------------------------------------------------------
    row: Dict[str, Any] = {
        "timestamp": ts_human,
        "feasiblity": feasiblity,
        "error": solve_note if feasiblity == FAIL_FLAG else PLACEHOLDER,
        "error stage": error_stage if feasiblity == FAIL_FLAG else PLACEHOLDER,
        "total_cost": total_cost if total_cost is not None else PLACEHOLDER,
        "demand": total_demand if total_demand is not None else PLACEHOLDER,
        "solver": solver_name,
        "build_s": build_s if build_s is not None else PLACEHOLDER,
        "solve_s": solve_s if solve_s is not None else PLACEHOLDER,
        "total_s": total_s if total_s is not None else PLACEHOLDER,
    }

    log_path = _append_run_log(scenario_dir, row)
    print(f"Run log updated: {log_path.resolve()}")

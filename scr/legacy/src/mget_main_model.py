# ======================================================================
# my_model_mget_v2.py
# ----------------------------------------------------------------------
# Multi-gas network investment and operation model (Pyomo).
#
# This script defines:
#   1. The mathematical optimization model (build_model_mget)
#   2. How data is loaded (via prepare_mget_data in mget_load_data.py)
#   3. How the model is solved (Gurobi)
#   4. How results are printed and exported (via report.py)
#
# The structure intentionally separates:
#   - model logic  (this file)
#   - data loading (mget_load_data.py)
#   - reporting    (report.py)
#
# to make the project clean and easy to understand.
# ======================================================================

from __future__ import annotations
from pathlib import Path
from typing import Optional
import sys

import pyomo.environ as pyo

# Data loader (preprocesses Excel to Python dictionaries)
from mget_load_data import INPUT_XLSX, prepare_mget_data

# Reporting utilities (printing + CSV export)
from report import summarize_solve_status, print_text_report, export_results
import time



# ======================================================================
# Model builder
# ======================================================================
def build_model_mget(xlsx_path: Path | None = None) -> pyo.ConcreteModel:
    """
    Build and return a fully constructed Pyomo model.

    Parameters
    ----------
    xlsx_path : Path or None
        Path to the scenario Excel file.
        If None, defaults to INPUT_XLSX defined in mget_load_data.py.

    Returns
    -------
    ConcreteModel
        A fully defined Pyomo model ready to solve.

    Notes
    -----
    The function:
      • loads all data using prepare_mget_data()
      • defines sets, parameters, variables, constraints, and objective
      • does NOT solve the model (solving happens in __main__)
    """
    # Use default Excel unless overridden
    data_path = Path(xlsx_path) if xlsx_path is not None else INPUT_XLSX

    # ------------------------------------------------------------------
    # STEP 1: Load all data (already converted into Python structures)
    # ------------------------------------------------------------------
    # prepare_mget_data() returns a dictionary with:
    #   node_names, arc_ids, fuels, Y, H, cost parameters, efficiencies, etc.
    # This keeps the model script clean and focused only on mathematics.
    data = prepare_mget_data(data_path)

    node_names  = data["node_names"]    # list of nodes
    arc_ids     = data["arc_ids"]       # list of arcs
    start_of    = data["start_of"]      # arc -> start node
    end_of      = data["end_of"]        # arc -> end node
    fuels       = data["fuels"]         # fuel set F
    Y           = data["Y"]             # years
    H           = data["H"]             # hours
    r_param     = data["r_param"]       # discount factor r[y]
    scale_param = data["scale_param"]   # hour scaling factor Scale[h]
    cap_p       = data["cap_p"]         # production capacity
    c_p         = data["c_p"]           # production cost
    dmd         = data["dmd"]           # demand
    c_dz        = data["c_dz"]          # deficit penalty cost
    c_a         = data["c_a"]           # arc transport cost
    cap_a       = data["cap_a"]         # arc transport capacity
    c_x_dict    = data["c_x"]           # investment cost for expansions
    c_b_dict    = data["c_b"]           # binary investment cost
    eff         = data["eff"]           # conversion efficiency on arcs

    # ------------------------------------------------------------------
    # STEP 2: Create the Pyomo model and declare sets
    # ------------------------------------------------------------------
    m = pyo.ConcreteModel()

    # Basic sets
    m.n = pyo.Set(initialize=sorted(node_names))  # nodes
    m.A = pyo.Set(initialize=sorted(arc_ids))     # arcs
    m.F = pyo.Set(initialize=fuels)               # fuels
    m.Y = pyo.Set(initialize=Y, ordered=True)     # years
    m.H = pyo.Set(initialize=H, ordered=True)     # hours

    # Reverse arc map: needed for K_OPP borrowing capacity
    by_ij = {(start_of[a], end_of[a]): a for a in arc_ids}
    a_rev = {a: by_ij.get((end_of[a], start_of[a]), a) for a in arc_ids}

    # Outgoing and incoming arcs of each node
    def _delta_out(mm, n): return [a for a in mm.A if start_of[a] == n]
    def _delta_in(mm, n):  return [a for a in mm.A if end_of[a]   == n]
    m.delta_out = pyo.Set(m.n, initialize=_delta_out)
    m.delta_in  = pyo.Set(m.n, initialize=_delta_in)

    # Node-attribution for arcs
    m.start_node = pyo.Param(m.A, initialize=start_of)
    m.end_node   = pyo.Param(m.A, initialize=end_of)

    # ------------------------------------------------------------------
    # STEP 3: Declare scalar parameters
    # ------------------------------------------------------------------
    # Discount factor r[y] and hour scaling Scale[h]
    m.r     = pyo.Param(m.Y, initialize=r_param,     within=pyo.NonNegativeReals, default=1.0)
    m.Scale = pyo.Param(m.H, initialize=scale_param, within=pyo.NonNegativeReals, default=1.0)

    # ------------------------------------------------------------------
    # STEP 4: Declare technical and cost parameters
    # ------------------------------------------------------------------
    # Production capacity, cost, and demand
    m.cap_p = pyo.Param(m.n, m.F, m.Y, m.H,
                        initialize=lambda mm,n,e,y,h: cap_p.get((n,e,y,h), 0.0))
    m.c_p   = pyo.Param(m.n, m.F, m.Y, m.H,
                        initialize=lambda mm,n,e,y,h: c_p.get((n,e,y,h), 0.0))
    m.dmd   = pyo.Param(m.n, m.F, m.Y, m.H,
                        initialize=lambda mm,n,e,y,h: dmd.get((n,e,y,h), 0.0))

    # Deficit penalty cost (per fuel)
    m.c_dz  = pyo.Param(m.F, initialize=lambda mm,e: c_dz.get(e, 1e4))

    # Arc transport cost and capacity
    m.c_a   = pyo.Param(m.A, m.F, m.Y, initialize=lambda mm,a,e,y: c_a.get((a,e,y), 0.0))
    m.cap_a = pyo.Param(m.A, m.F, m.Y, initialize=lambda mm,a,e,y: cap_a.get((a,e,y), 0.0))

    # Efficiency: fraction of fuel preserved across arc conversions
    m.eff   = pyo.Param(m.F, m.A, initialize=lambda mm,e,a: eff.get((e,a), 1.0))

    # Investment cost for capacity expansion + binary cost
    m.c_x = pyo.Param(m.A, m.F, m.Y, initialize=lambda mm,a,e,y: c_x_dict.get((a,e,y), 0.0))
    m.c_b = pyo.Param(m.A, m.Y,     initialize=lambda mm,a,y: c_b_dict.get((a,y), 0.0))

    # ------------------------------------------------------------------
    # STEP 5: Decision variables
    # ------------------------------------------------------------------
    m.Q_P   = pyo.Var(m.n, m.F, m.Y, m.H, domain=pyo.NonNegativeReals)  # production
    m.F_A   = pyo.Var(m.A, m.F, m.Y, m.H, domain=pyo.NonNegativeReals)  # flows on arcs
    m.Z_D   = pyo.Var(m.n, m.F, m.Y, m.H, domain=pyo.NonNegativeReals)  # unmet demand
    m.X_A   = pyo.Var(m.A, m.F, m.Y, domain=pyo.NonNegativeReals)       # expansion
    m.BD    = pyo.Var(m.A, m.Y, domain=pyo.UnitInterval)                # binary decision
    m.K_OPP = pyo.Var(m.A, m.F, m.Y, domain=pyo.NonNegativeReals)       # borrowed capacity

    # ------------------------------------------------------------------
    # STEP 6: Constraints
    # ------------------------------------------------------------------

    # Production cannot exceed installed capacity
    m.SupplyCap = pyo.Constraint(
        m.n, m.F, m.Y, m.H,
        rule=lambda mm,n,e,y,h: mm.Q_P[n,e,y,h] <= mm.cap_p[n,e,y,h]
    )

    # Node balance: production + inflow = outflow + demand - deficit
    def _bal(mm, n, e, y, h):
        inflow  = sum(mm.eff[e,a] * mm.F_A[a,e,y,h] for a in mm.delta_in[n])
        outflow = sum(mm.F_A[a,e,y,h]               for a in mm.delta_out[n])
        return mm.Q_P[n,e,y,h] + inflow == outflow + mm.dmd[n,e,y,h] - mm.Z_D[n,e,y,h]
    m.Balance = pyo.Constraint(m.n, m.F, m.Y, m.H, rule=_bal)

    # Transport capacity along arcs
    m.Capacity = pyo.Constraint(
        m.A, m.F, m.Y, m.H,
        rule=lambda mm,a,e,y,h: mm.F_A[a,e,y,h] <= (
            mm.cap_a[a,e,y] + mm.X_A[a,e,y] + mm.K_OPP[a,e,y]
        )
    )

    # Borrow opposite-arc capacity if the reverse arc is activated
    def _opp_cap(mm, a, e, y):
        arev = a_rev[a]
        return mm.K_OPP[a,e,y] <= mm.BD[arev,y] * (
            mm.cap_a[arev,e,y] + mm.X_A[arev,e,y]
        )
    m.OppCapacity = pyo.Constraint(m.A, m.F, m.Y, rule=_opp_cap)

    # Only include arcs with nonzero c_b in the binary-cost term
    CbIndex = [(a,y) for (a,y), val in c_b_dict.items() if val and val != 0]
    m.CbIndex = pyo.Set(initialize=CbIndex, dimen=2)

    # ------------------------------------------------------------------
    # STEP 7: Objective function
    # ------------------------------------------------------------------
    # Total cost = discounted investment + discounted operating cost

    def _investment_cost(mm):
        """
        Investment costs:
          - c_x[a,e,y] * X_A[a,e,y] : continuous capacity expansion
          - c_b[a,y]   * BD[a,y]    : binary cost to enable an arc
        """
        return sum(
            mm.r[y] * (
                sum(mm.c_x[a,e,y] * mm.X_A[a,e,y] for a in mm.A for e in mm.F) +
                sum(mm.c_b[a,y]   * mm.BD[a,y]    for (a,y) in mm.CbIndex)
            )
            for y in mm.Y
        )

    def _operating_cost(mm):
        """
        Operating cost:
          - production cost     c_p[n,e,y,h] * Q_P[n,e,y,h]
          - transport cost      c_a[a,e,y]   * F_A[a,e,y,h]
          - deficit penalty     c_dz[e]      * Z_D[n,e,y,h]
        """
        return sum(
            mm.r[y] * mm.Scale[h] * (
                sum(mm.c_p[n,e,y,h] * mm.Q_P[n,e,y,h] for n in mm.n for e in mm.F) +
                sum(mm.c_a[a,e,y]   * mm.F_A[a,e,y,h] for a in mm.A for e in mm.F) +
                sum(mm.c_dz[e]      * mm.Z_D[n,e,y,h] for n in mm.n for e in mm.F)
            )
            for y in mm.Y for h in mm.H
        )

    m.TotalCost = pyo.Objective(
        expr=_investment_cost(m) + _operating_cost(m),
        sense=pyo.minimize
    )

    # Needed by the reporter to identify reverse arcs
    m._a_rev_map = a_rev

    return m


# ======================================================================
# CLI / Solve / Report
# ======================================================================
if __name__ == "__main__":
    """
    Command-line usage:
        python mget_main_model.py [excel_path] [results_root]

    Arguments
    ---------
    excel_path   (optional)
        Path to the scenario Excel file.
        If omitted, the default INPUT_XLSX (from mget_load_data.py) is used.

    results_root (optional)
        Root folder where results will be stored.
        If omitted, results are written under '<project_root>/results/'.

    For a scenario file like:
        <project_root>/data/my_scenario.xlsx

    The report.py exporter will create (by default):
        <project_root>/results/results_my_scenario/
    and place timestamped CSV files + a runs_log.csv there.
    """

    import time  # timing for build/solve

    # Parse optional command-line arguments
    xlsx_override: Optional[Path] = None
    outdir_override: Optional[Path] = None
    if len(sys.argv) > 1:
        xlsx_override = Path(sys.argv[1]).expanduser().resolve()
    if len(sys.argv) > 2:
        outdir_override = Path(sys.argv[2]).expanduser().resolve()

    # Decide which Excel scenario file to use
    excel_path = xlsx_override if xlsx_override is not None else INPUT_XLSX
    excel_path = Path(excel_path).resolve()

    # ------------------------------------------------------------------
    # Build model (timed)
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    build_s = None
    solve_s = None
    total_s = None

    model = build_model_mget(excel_path)
    t1 = time.perf_counter()
    build_s = t1 - t0

    # ------------------------------------------------------------------
    # Solve model (timed)
    # ------------------------------------------------------------------
    results = None
    solver_name = "gurobi"

    try:
        opt = pyo.SolverFactory(solver_name)
        if opt is not None and opt.available():
            # some solvers (like Gurobi) need this for nonconvex models
            opt.options["NonConvex"] = 2

            t_solve_start = time.perf_counter()
            results = opt.solve(model, tee=True)
            t_solve_end = time.perf_counter()

            solve_s = t_solve_end - t_solve_start
            total_s = t_solve_end - t0

            # Optional: print raw solver status line
            print(getattr(results.solver, "status", None),
                  getattr(results.solver, "termination_condition", None))
        else:
            print(f"{solver_name} not found/available; model built but not solved.")
    except Exception as e:
        print("Solver error:", e)
        # solve_s and total_s remain None; report.py will log them as 'none'

    # ------------------------------------------------------------------
    # Human-readable console report
    # ------------------------------------------------------------------
    print_text_report(model, results)

    # ------------------------------------------------------------------
    # CSV export + per-scenario run log
    # ------------------------------------------------------------------
    export_results(
        model,
        results,
        excel_path,
        outdir_override,      # can be None -> defaults to <project_root>/results
        solver_name=solver_name,
        build_s=build_s,
        solve_s=solve_s,
        total_s=total_s,
    )

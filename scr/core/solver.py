from __future__ import annotations

import sys

import pyomo.environ as pyo


DEFAULT_SOLVER_NAME = "gurobi"
DEFAULT_TOL = 1e-6


def get_solver_defaults() -> tuple[str, float]:
    return DEFAULT_SOLVER_NAME, DEFAULT_TOL


def create_solver(solver_name: str):
    solver = pyo.SolverFactory(solver_name)
    if solver is None or not solver.available(False):
        print(f"ERROR: Solver '{solver_name}' is not available in this environment.")
        print("Install/activate Gurobi and ensure Pyomo can find it (e.g., gurobipy + license).")
        sys.exit(2)
    return solver


def solve_model(solver, model: pyo.ConcreteModel, tee: bool, solver_name: str):
    try:
        return solver.solve(model, tee=tee)
    except Exception as exc:
        print(f"ERROR: Solver '{solver_name}' failed to run: {exc}")
        if "license" in str(exc).lower() or "version" in str(exc).lower():
            print("Hint: Your Gurobi runtime and license versions likely do not match.")
            print("Fix by installing the Gurobi version that matches your license, or renewing/upgrading the license.")
        sys.exit(5)

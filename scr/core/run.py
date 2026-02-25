from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

from scr.core.solver import DEFAULT_SOLVER_NAME, DEFAULT_TOL
from scr.core.solve_pipeline import main as solve_main


def _derive_scenario_name(other_csv_path: str) -> str:
    if not other_csv_path:
        return "scenario"
    parent_name = Path(other_csv_path).resolve().parent.name.strip()
    return parent_name if parent_name else "scenario"


def _resolve_scenario_arg(scenario_arg: str) -> str:
    if not scenario_arg:
        return ""

    scenario_path = Path(scenario_arg)
    if scenario_path.exists():
        resolved = scenario_path.resolve()
        if resolved.is_dir():
            return str((resolved / "other.csv").resolve())
        return str(resolved)

    if scenario_path.suffix.lower() == ".csv":
        return str(scenario_path)

    return str((Path(__file__).resolve().parents[1] / "data" / scenario_arg / "other.csv").resolve())


def _timestamp_yyyymmdd_hhmmss() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Official CLI wrapper for scenario solve/validation.",
    )
    parser.add_argument(
        "--scenario",
        default="",
        help="Path to scenario other.csv (equivalent to solve_pipeline positional other_csv).",
    )
    parser.add_argument("--solver", default=None, help=f"Pyomo solver name (default: {DEFAULT_SOLVER_NAME})")
    parser.add_argument("--tol", type=float, default=None, help=f"Constraint feasibility tolerance (default: {DEFAULT_TOL})")
    parser.add_argument("--top-n", type=int, default=10, help="Top nonzero entries to print per key variable")
    parser.add_argument("--tee", action="store_true", help="Show solver log")
    parser.add_argument("--output-json", default="", help="Optional path to write JSON report")
    parser.add_argument(
        "--export-all-dir",
        default="",
        help="Optional folder to export full variable tables including zero values",
    )
    parser.add_argument(
        "--combined-csv",
        default="",
        help="Optional single CSV export for combined key results",
    )
    parser.add_argument(
        "--compare-scenario",
        default="",
        help="Optional baseline other.csv path for metric comparison",
    )

    args = parser.parse_args()

    forwarded_argv: list[str] = ["scr.core.solve_pipeline"]
    resolved_scenario = _resolve_scenario_arg(args.scenario)
    if resolved_scenario:
        forwarded_argv.append(resolved_scenario)

    if not args.output_json and not args.combined_csv and not args.export_all_dir:
        scenario_name = _derive_scenario_name(resolved_scenario)
        ts = _timestamp_yyyymmdd_hhmmss()
        default_base = Path(__file__).resolve().parents[1] / "results" / scenario_name / f"{scenario_name}_{ts}"
        default_base.mkdir(parents=True, exist_ok=True)
        args.output_json = str(default_base / "report.json")
        args.combined_csv = str(default_base / "combined_results.csv")
        args.export_all_dir = str(default_base / "all_results")

    if args.solver is not None:
        forwarded_argv.extend(["--solver", args.solver])
    if args.tol is not None:
        forwarded_argv.extend(["--tol", str(args.tol)])
    forwarded_argv.extend(["--top-n", str(args.top_n)])

    if args.tee:
        forwarded_argv.append("--tee")
    if args.output_json:
        forwarded_argv.extend(["--output-json", args.output_json])
    if args.export_all_dir:
        forwarded_argv.extend(["--export-all-dir", args.export_all_dir])
    if args.combined_csv:
        forwarded_argv.extend(["--combined-csv", args.combined_csv])
    if args.compare_scenario:
        forwarded_argv.extend(["--compare-other-csv", args.compare_scenario])

    original_argv = sys.argv
    try:
        sys.argv = forwarded_argv
        solve_main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main()

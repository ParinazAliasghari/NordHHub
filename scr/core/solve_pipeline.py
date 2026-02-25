from __future__ import annotations

from pathlib import Path
import argparse
from datetime import datetime
import math
import re
import sys

from .data_loading import load_inputs
from .model import build_base_model_with_cz
from .report import (
    append_run_log,
    collect_arc_expansion_totals,
    collect_arc_flow_totals,
    collect_bidir_totals,
    collect_cost_breakdown,
    collect_qb_totals,
    collect_repurpose_totals,
    collect_top_variable_values,
    export_all_results,
    export_combined_results_csv,
    summarize_a_lim_binding,
    summarize_max_bl_binding,
    summarize_slacks,
    write_per_run_result_csvs,
    write_json_report,
)
from .solver import (
    DEFAULT_SOLVER_NAME,
    DEFAULT_TOL,
    create_solver,
    solve_model,
)
from .validate import (
    _safe_value,
    validate_bidirectional_logic,
    validate_constraints,
    validate_node_arc_balance,
    validate_repurposing_logic,
)


DEFAULT_OTHER_CSV = Path(__file__).resolve().parents[2] / "data" / "scenario5" / "other.csv"


def _derive_scenario_name(other_csv_path: Path) -> str:
    parent_name = other_csv_path.parent.name.strip() if other_csv_path.parent is not None else ""
    return parent_name if parent_name else "scenario"


def _timestamp_yyyymmdd_hhmmss() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _is_legacy_wrapper_default_paths(
    *,
    output_json: str,
    combined_csv: str,
    export_all_dir: str,
    results_root: Path,
    scenario_name: str,
) -> tuple[bool, Path | None]:
    if not output_json or not combined_csv or not export_all_dir:
        return False, None

    p_json = Path(output_json).resolve()
    p_combined = Path(combined_csv).resolve()
    p_export = Path(export_all_dir).resolve()

    if p_json.name != "report.json" or p_combined.name != "combined_results.csv" or p_export.name != "all_results":
        return False, None

    run_dir = p_json.parent
    if p_combined.parent != run_dir or p_export.parent != run_dir:
        return False, None

    expected_parent = (results_root / scenario_name).resolve()
    if run_dir.parent != expected_parent:
        return False, None

    if not re.fullmatch(rf"{re.escape(scenario_name)}_\d{{8}}_\d{{6}}", run_dir.name):
        return False, None

    return True, run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve model with Gurobi and validate optimality/feasibility.")
    parser.add_argument("other_csv", nargs="?", default=str(DEFAULT_OTHER_CSV), help="Path to other.csv")
    parser.add_argument("--solver", default=None, help=f"Pyomo solver name (default: {DEFAULT_SOLVER_NAME})")
    parser.add_argument("--tol", type=float, default=None, help=f"Constraint feasibility tolerance (default: {DEFAULT_TOL})")
    parser.add_argument("--top-n", type=int, default=10, help="Top nonzero entries to print per key variable")
    parser.add_argument("--tee", action="store_true", help="Show solver log")
    parser.add_argument("--output-json", default="", help="Optional path to write JSON report")
    parser.add_argument(
        "--export-all-dir",
        default="",
        help="Optional folder to export full variable tables including zero values (Q_P,Q_S,ZDS,ZN2)",
    )
    parser.add_argument(
        "--combined-csv",
        default="",
        help="Optional single CSV export with columns for Q_P,Q_S,ZDS_*,ZN2_* (including zeros)",
    )
    parser.add_argument(
        "--compare-other-csv",
        default="",
        help="Optional baseline other.csv path for metric comparison (objective, total ZDS, total F_A)",
    )
    parser.add_argument(
        "--compare-o-csv",
        default="",
        help="DEPRECATED alias for --compare-other-csv",
    )
    args = parser.parse_args()
    effective_solver = args.solver if args.solver is not None else DEFAULT_SOLVER_NAME
    effective_tol = args.tol if args.tol is not None else DEFAULT_TOL

    other_path = Path(args.other_csv).resolve()
    scenario_name = _derive_scenario_name(other_path)
    run_timestamp = _timestamp_yyyymmdd_hhmmss()
    results_root = Path(__file__).resolve().parents[2] / "results"
    scenario_dir = results_root / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    is_legacy_defaults, legacy_run_dir = _is_legacy_wrapper_default_paths(
        output_json=args.output_json,
        combined_csv=args.combined_csv,
        export_all_dir=args.export_all_dir,
        results_root=results_root,
        scenario_name=scenario_name,
    )
    if is_legacy_defaults:
        args.output_json = ""
        args.combined_csv = ""
        args.export_all_dir = ""

    default_operations_path = (scenario_dir / f"operations_{scenario_name}_{run_timestamp}.csv").resolve()
    default_json_path = (scenario_dir / f"report_{scenario_name}_{run_timestamp}.json").resolve()

    loaded = load_inputs(other_path=other_path)
    model = build_base_model_with_cz(loaded)

    solver = create_solver(effective_solver)
    solve_started = datetime.now()
    result = solve_model(solver, model, tee=args.tee, solver_name=effective_solver)
    solve_seconds = (datetime.now() - solve_started).total_seconds()

    status = str(result.solver.status)
    term = str(result.solver.termination_condition)
    is_optimal = term.lower() == "optimal"

    obj_value = _safe_value(model.obj_total_cost)
    tc_value = _safe_value(model.TC)

    con_report = validate_constraints(model, tol=effective_tol)
    cost_report = collect_cost_breakdown(model)
    slack_report = summarize_slacks(model, tol=effective_tol)
    top_vars = collect_top_variable_values(model, tol=effective_tol, top_n=max(1, args.top_n))
    arc_flow_totals = collect_arc_flow_totals(model, tol=effective_tol)
    arc_expansion_totals = collect_arc_expansion_totals(model, tol=effective_tol)
    bidir_totals = collect_bidir_totals(model, tol=effective_tol)
    repurpose_totals = collect_repurpose_totals(model, tol=effective_tol)
    a_lim_binding = summarize_a_lim_binding(model, tol=effective_tol)
    qb_totals = collect_qb_totals(model, tol=effective_tol)
    blend_binding = summarize_max_bl_binding(model, tol=effective_tol)
    node_arc_balance = validate_node_arc_balance(model, tol=effective_tol)
    bidir_checks = validate_bidirectional_logic(model, tol=effective_tol)
    repurpose_checks = validate_repurposing_logic(model, tol=effective_tol)

    report = {
        "input": str(other_path),
        "solver": effective_solver,
        "solver_status": status,
        "termination_condition": term,
        "optimal": is_optimal,
        "objective": obj_value,
        "tc_value": tc_value,
        "objective_tc_gap": abs(obj_value - tc_value) if not (math.isnan(obj_value) or math.isnan(tc_value)) else math.nan,
        "constraint_check": con_report,
        "cost_breakdown": cost_report,
        "slack_summary": slack_report,
        "top_variables": top_vars,
        "arc_flow_totals": arc_flow_totals,
        "arc_expansion_totals": arc_expansion_totals,
        "bidir_totals": bidir_totals,
        "repurpose_totals": repurpose_totals,
        "a_lim_binding": a_lim_binding,
        "qb_totals": qb_totals,
        "max_bl_binding": blend_binding,
        "node_arc_balance_check": node_arc_balance,
        "bidirectional_checks": bidir_checks,
        "repurposing_checks": repurpose_checks,
    }

    export_all_requested = bool(args.export_all_dir)
    if export_all_requested:
        export_dir = (scenario_dir / f"all_results_{run_timestamp}").resolve()
        report["all_variable_exports"] = export_all_results(model, export_dir)

    report["operations_csv_export_default"] = export_combined_results_csv(
        model,
        default_operations_path,
        scenario_name=scenario_name,
        timestamp=run_timestamp,
    )
    if args.combined_csv:
        combined_path = Path(args.combined_csv).resolve()
        if combined_path != default_operations_path:
            report["combined_csv_export"] = export_combined_results_csv(
                model,
                combined_path,
                scenario_name=scenario_name,
                timestamp=run_timestamp,
            )
        else:
            report["combined_csv_export"] = report["operations_csv_export_default"]

    compare_other_csv = args.compare_other_csv if args.compare_other_csv else args.compare_o_csv
    if compare_other_csv:
        compare_path = Path(compare_other_csv).resolve()
        loaded_ref = load_inputs(other_path=compare_path)
        model_ref = build_base_model_with_cz(loaded_ref)
        result_ref = solver.solve(model_ref, tee=False)
        ref_term = str(result_ref.solver.termination_condition)
        if ref_term.lower() == "optimal":
            ref_obj = _safe_value(model_ref.obj_total_cost)
            ref_slack = summarize_slacks(model_ref, tol=effective_tol)
            ref_arc_flow_totals = collect_arc_flow_totals(model_ref, tol=effective_tol)
            cur_total_fa = float(sum(float(row["flow_sum_h"]) for row in arc_flow_totals))
            ref_total_fa = float(sum(float(row["flow_sum_h"]) for row in ref_arc_flow_totals))
            report["comparison"] = {
                "baseline_input": str(compare_path),
                "baseline_objective": ref_obj,
                "baseline_sum_ZDS": float(ref_slack["sum_ZDS"]),
                "baseline_total_F_A": ref_total_fa,
                "current_objective": obj_value,
                "current_sum_ZDS": float(slack_report["sum_ZDS"]),
                "current_total_F_A": cur_total_fa,
                "delta_objective": float(obj_value - ref_obj),
                "delta_sum_ZDS": float(slack_report["sum_ZDS"] - ref_slack["sum_ZDS"]),
                "delta_total_F_A": float(cur_total_fa - ref_total_fa),
            }
        else:
            report["comparison"] = {
                "baseline_input": str(compare_path),
                "error": f"Baseline solve not optimal (termination={ref_term})",
            }

    report["summary_csv_export_default"] = write_per_run_result_csvs(
        report=report,
        results_root=results_root,
        scenario_name=scenario_name,
        timestamp=run_timestamp,
    )
    append_run_log(
        results_root=results_root,
        scenario_name=scenario_name,
        timestamp=run_timestamp,
        solver=str(effective_solver),
        termination_condition=str(term),
        objective=float(obj_value),
        tc_value=float(tc_value),
        solve_seconds=float(solve_seconds),
        violated_constraints=int(con_report.get("violated_constraints", 0)),
        max_violation=float(con_report.get("max_violation", math.nan)),
        sum_ZDS=float(slack_report.get("sum_ZDS", 0.0)),
        sum_ZN2=float(slack_report.get("sum_ZN2", 0.0)),
    )

    if is_legacy_defaults and legacy_run_dir is not None and legacy_run_dir.exists():
        try:
            legacy_run_dir.rmdir()
        except OSError:
            pass

    print("=== Solve Report ===")
    print(f"Input: {report['input']}")
    print(f"Solver: {report['solver']}")
    print(f"Status: {status}")
    print(f"Termination: {term}")
    print(f"Optimal: {is_optimal}")
    print(f"Objective: {obj_value:.8f}")
    print(f"TC: {tc_value:.8f}")
    print(f"|Objective-TC|: {report['objective_tc_gap']:.8e}")

    print("\n=== Feasibility Check ===")
    print(f"Total constraints: {con_report['total_constraints']}")
    print(f"Violated constraints (> {effective_tol}): {con_report['violated_constraints']}")
    print(f"Max violation: {con_report['max_violation']:.8e}")
    print(f"Feasible by tolerance: {con_report['feasible_by_tolerance']}")

    worst = con_report.get("worst_constraint")
    if worst is not None:
        print("Worst constraint:")
        print(
            f"  {worst['name']}[{worst['index']}] body={worst['body']:.8f} "
            f"lb={worst['lower']:.8f} ub={worst['upper']:.8f} viol={worst['violation']:.8e}"
        )

    print("\n=== Cost Breakdown ===")
    print(f"Production cost: {cost_report['production_cost']:.8f}")
    print(f"Arc investment cost: {cost_report['arc_investment_cost']:.8f}")
    print(f"Bidir fixed cost: {cost_report['bidir_fixed_cost']:.8f}")
    print(f"Bidir variable cost: {cost_report['bidir_variable_cost']:.8f}")
    print(f"Repurpose fixed cost: {cost_report['repurpose_fixed_cost']:.8f}")
    print(f"Repurpose variable cost: {cost_report['repurpose_variable_cost']:.8f}")
    print(f"Arc flow cost: {cost_report['arc_flow_cost']:.8f}")
    print(f"Blending cost: {cost_report['blending_cost']:.8f}")
    print(f"Regas cost: {cost_report['regas_cost']:.8f}")
    print(f"Storage cost: {cost_report['storage_cost']:.8f}")
    print(f"ZDS penalty cost: {cost_report['zds_penalty_cost']:.8f}")
    print(f"ZN2 penalty cost: {cost_report['zn2_penalty_cost']:.8f}")
    print(f"Reconstructed total: {cost_report['total_reconstructed']:.8f}")

    print("\n=== Slack Summary ===")
    print(f"sum(ZDS): {slack_report['sum_ZDS']:.8f} | nonzero entries: {slack_report['nonzero_ZDS']}")
    print(f"sum(ZN2): {slack_report['sum_ZN2']:.8f} | nonzero entries: {slack_report['nonzero_ZN2']}")

    print("\n=== Top Nonzero Variables ===")
    for var_name, entries in top_vars.items():
        print(f"{var_name}: {len(entries)} shown")
        for row in entries:
            print(f"  {var_name}[{row['index']}] = {row['value']:.8f}")

    print("\n=== Arc Flow Totals (sum_h scaleUp*F_A) ===")
    if len(arc_flow_totals) == 0:
        print("No nonzero arc flows.")
    else:
        for row in arc_flow_totals:
            print(f"  F_A_total[{row['a']},{row['e']},{row['y']}] = {row['flow_sum_h']:.8f}")

    print("\n=== Arc Expansion Totals (X_A) ===")
    if len(arc_expansion_totals) == 0:
        print("No nonzero arc expansions.")
    else:
        for row in arc_expansion_totals:
            print(f"  X_A[{row['a']},{row['e']},{row['y']}] = {row['x_a']:.8f}")

    print("\n=== Arc Capacity Binding (a_lim) ===")
    print(f"active a_lim constraints: {a_lim_binding['active_constraints']}")
    print(f"binding a_lim constraints: {a_lim_binding['binding_constraints']}")
    print(f"any binding after investment: {a_lim_binding['binding_constraints'] > 0}")
    for row in a_lim_binding["binding_rows"]:
        print(
            f"  a_lim[{row['index']}] body={row['body']:.8f} "
            f"upper={row['upper']:.8f} util={row['utilization']:.6f}"
        )

    print("\n=== Bidirectional Totals ===")
    for key in ["BD", "B_BD", "K_OPP", "K_BD"]:
        rows = bidir_totals[key]
        if len(rows) == 0:
            print(f"{key}: none")
            continue
        print(f"{key}: {len(rows)}")
        for row in rows[:25]:
            if key in ["BD", "B_BD"]:
                print(f"  {key}[{row['a']},{row['y']}] = {row[key]:.8f}")
            else:
                print(f"  {key}[{row['a']},{row['e']},{row['y']}] = {row[key]:.8f}")

    print("\n=== Repurposing Totals ===")
    for key in ["B_AR", "K_RA", "B_WR", "K_RW"]:
        rows = repurpose_totals[key]
        if len(rows) == 0:
            print(f"{key}: none")
            continue
        print(f"{key}: {len(rows)}")
        for row in rows[:25]:
            if key in ["B_AR", "K_RA"]:
                print(f"  {key}[{row['a']},{row['e']},{row['f']},{row['y']}] = {row[key]:.8f}")
            else:
                print(f"  {key}[{row['n']},{row['e']},{row['f']},{row['y']}] = {row[key]:.8f}")

    print("\n=== Blending Totals (sum_h scaleUp*Q_B) ===")
    if len(qb_totals) == 0:
        print("No nonzero blending flows.")
    else:
        for row in qb_totals:
            print(f"  Q_B_total[{row['n']},{row['f']},{row['e']},{row['y']}] = {row['qb_sum_h']:.8f}")

    print("\n=== Blending Constraint Binding (max_bl) ===")
    print(f"active max_bl constraints: {blend_binding['active_constraints']}")
    print(f"binding max_bl constraints: {blend_binding['binding_constraints']}")
    for row in blend_binding["binding_rows"]:
        print(f"  max_bl[{row['index']}] body={row['body']:.8f} upper={row['upper']:.8f}")

    print("\n=== Node Arc-Balance Check (aggregated over h) ===")
    print(f"max |lhs-rhs|: {node_arc_balance['max_abs_residual']:.8e}")
    print(f"violations (> {effective_tol}): {node_arc_balance['violation_count']}")
    worst_bal = node_arc_balance.get("worst")
    if worst_bal is not None:
        print(
            "worst residual: "
            f"({worst_bal['n']},{worst_bal['e']},{worst_bal['y']}) "
            f"lhs={float(worst_bal['lhs_total']):.8f} rhs={float(worst_bal['rhs_total']):.8f} "
            f"res={float(worst_bal['residual']):.8e}"
        )

    print("\n=== Bidirectional Debug Checks ===")
    print(f"total violations: {bidir_checks['violation_count']}")
    print(f"no-opp K_OPP violations: {len(bidir_checks['no_opp_kopp_violations'])}")
    print(f"BD=0 with K_OPP>0 violations: {len(bidir_checks['bd_zero_kopp_violations'])}")
    print(f"K_OPP<=opp-cap violations: {len(bidir_checks['opp_capacity_violations'])}")
    print(f"is_bid -> BD=1 violations: {len(bidir_checks['is_bid_bd_fix_violations'])}")

    print("\n=== Repurposing Debug Checks ===")
    print(f"total violations: {repurpose_checks['violation_count']}")
    print(f"ar_cap violations: {len(repurpose_checks['ar_cap_violations'])}")
    print(f"wr_cap violations: {len(repurpose_checks['wr_cap_violations'])}")
    print(f"sos_a violations: {len(repurpose_checks['sos_a_violations'])}")
    print(f"sos_w violations: {len(repurpose_checks['sos_w_violations'])}")
    print(f"bil_a1 violations: {len(repurpose_checks['bil_a1_violations'])}")
    print(f"bil_w1 violations: {len(repurpose_checks['bil_w1_violations'])}")
    print(f"bil_a2 violations: {len(repurpose_checks['bil_a2_violations'])}")
    print(f"bil_w2 violations: {len(repurpose_checks['bil_w2_violations'])}")

    if "all_variable_exports" in report:
        print("\n=== Full Result Exports (Including Zeros) ===")
        for name, meta in report["all_variable_exports"].items():
            print(f"{name}: {meta['rows']} rows -> {meta['file']}")

    if "operations_csv_export_default" in report:
        print("\n=== Default Operations Export ===")
        print(f"rows: {report['operations_csv_export_default']['rows']} -> {report['operations_csv_export_default']['file']}")

    if "summary_csv_export_default" in report:
        print("\n=== Default Summary Export ===")
        print(f"rows: {report['summary_csv_export_default']['rows']} -> {report['summary_csv_export_default']['summary']}")

    if "combined_csv_export" in report:
        print("\n=== Combined Result Export ===")
        print(f"rows: {report['combined_csv_export']['rows']} -> {report['combined_csv_export']['file']}")

    if "comparison" in report:
        print("\n=== Baseline Comparison ===")
        cmp = report["comparison"]
        if "error" in cmp:
            print(f"{cmp['error']}")
        else:
            print(f"baseline: {cmp['baseline_input']}")
            print(f"objective: current={cmp['current_objective']:.8f} baseline={cmp['baseline_objective']:.8f} delta={cmp['delta_objective']:.8f}")
            print(f"sum(ZDS): current={cmp['current_sum_ZDS']:.8f} baseline={cmp['baseline_sum_ZDS']:.8f} delta={cmp['delta_sum_ZDS']:.8f}")
            print(f"total F_A: current={cmp['current_total_F_A']:.8f} baseline={cmp['baseline_total_F_A']:.8f} delta={cmp['delta_total_F_A']:.8f}")

    output_json_requested = bool(args.output_json)
    if output_json_requested:
        out_path = Path(args.output_json).resolve()
        if is_legacy_defaults:
            out_path = default_json_path
        write_json_report(report, out_path)
        print(f"\nJSON report written: {out_path}")

    if not is_optimal:
        sys.exit(3)
    if not con_report["feasible_by_tolerance"]:
        sys.exit(4)


if __name__ == "__main__":
    main()

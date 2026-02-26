from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyomo.environ as pyo
from pyomo.opt import SolverFactory

from scr.core.data_loading import load_inputs
from scr.core.model import build_base_model_with_cz


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    scenario_folder: str
    expectation: str


DEFAULT_SCENARIOS: list[ScenarioSpec] = [
    ScenarioSpec("baseline", "scenario13", "KRA=0 and KRW=0"),
    ScenarioSpec("testF2", "scenario13_testF2", "KRA>0 or KRW>0"),
    ScenarioSpec("testJ2", "scenario13_testJ2", "KRA=0"),
    ScenarioSpec("testK2a", "scenario13_testK2a", "KRA>0"),
    ScenarioSpec("testK2b", "scenario13_testK2b", "KRA=0"),
]


def _safe_value(v: Any) -> float:
    try:
        return float(pyo.value(v))
    except Exception:
        return 0.0


def _evaluate_expectation(name: str, kra: float, krw: float, tol: float) -> tuple[bool, str]:
    if name == "baseline":
        ok = abs(kra) <= tol and abs(krw) <= tol
        return ok, "expect KRA=0 and KRW=0"
    if name == "testF2":
        ok = (kra > tol) or (krw > tol)
        return ok, "expect KRA>0 or KRW>0"
    if name == "testJ2":
        ok = abs(kra) <= tol
        return ok, "expect KRA=0"
    if name == "testK2a":
        ok = kra > tol
        return ok, "expect KRA>0"
    if name == "testK2b":
        ok = abs(kra) <= tol
        return ok, "expect KRA=0"
    return False, "unknown expectation"


def _top_nonzero_kra_krw(model: pyo.ConcreteModel, tol: float, top_n: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kra_rows: list[dict[str, Any]] = []
    for a in model.A:
        for e in model.E:
            for f in model.E:
                if str(e) == str(f):
                    continue
                for y in model.Y:
                    val = _safe_value(model.K_RA[a, e, f, y])
                    if abs(val) > tol:
                        kra_rows.append(
                            {"a": str(a), "e": str(e), "f": str(f), "y": int(y), "value": float(val)}
                        )
    kra_rows.sort(key=lambda row: abs(float(row["value"])), reverse=True)

    krw_rows: list[dict[str, Any]] = []
    for n in model.N:
        for e in model.E:
            for f in model.E:
                if str(e) == str(f):
                    continue
                for y in model.Y:
                    val = _safe_value(model.K_RW[n, e, f, y])
                    if abs(val) > tol:
                        krw_rows.append(
                            {"n": str(n), "e": str(e), "f": str(f), "y": int(y), "value": float(val)}
                        )
    krw_rows.sort(key=lambda row: abs(float(row["value"])), reverse=True)

    return kra_rows[:top_n], krw_rows[:top_n]


def run_one_scenario(
    other_csv: Path,
    *,
    solver: str,
    mip_gap: float | None,
    seed: int | None,
    tol: float,
    top_n: int,
) -> dict[str, Any]:
    loaded = load_inputs(other_path=other_csv)
    model = build_base_model_with_cz(loaded)

    opt = SolverFactory(solver)
    if mip_gap is not None:
        opt.options["MIPGap"] = float(mip_gap)
    if seed is not None:
        opt.options["Seed"] = int(seed)

    res = opt.solve(model, tee=False)
    status = str(res.solver.status)
    termination = str(res.solver.termination_condition)
    optimal = status.lower() == "ok" and termination.lower() == "optimal"

    out: dict[str, Any] = {
        "status": status,
        "termination": termination,
        "optimal": optimal,
    }
    if not optimal:
        return out

    objective = _safe_value(model.obj_total_cost)
    repurpose_fixed_cost = _safe_value(
        sum(
            model.r[y] * model.EOH[y] * model.f_ar[a, e, f, y] * model.B_AR[a, e, f, y]
            for a in model.A
            for e in model.E
            for f in model.E
            for y in model.Y
        )
    )
    repurpose_variable_cost = _safe_value(
        sum(
            model.r[y] * model.EOH[y] * model.c_ar[a, e, f, y] * model.K_RA[a, e, f, y]
            for a in model.A
            for e in model.E
            for f in model.E
            for y in model.Y
        )
    )

    kra_eneqf = float(
        sum(
            _safe_value(model.K_RA[a, e, f, y])
            for a in model.A
            for e in model.E
            for f in model.E
            for y in model.Y
            if str(e) != str(f)
        )
    )
    krw_eneqf = float(
        sum(
            _safe_value(model.K_RW[n, e, f, y])
            for n in model.N
            for e in model.E
            for f in model.E
            for y in model.Y
            if str(e) != str(f)
        )
    )

    top_kra, top_krw = _top_nonzero_kra_krw(model, tol=tol, top_n=top_n)

    out.update(
        {
            "objective": float(objective),
            "repurpose_fixed_cost": float(repurpose_fixed_cost),
            "repurpose_variable_cost": float(repurpose_variable_cost),
            "KRA_eNeqF": float(kra_eneqf),
            "KRW_eNeqF": float(krw_eneqf),
            "top_K_RA_eNeqF": top_kra,
            "top_K_RW_eNeqF": top_krw,
        }
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Permanent repurposing regression suite for Scenario13 derivatives.")
    parser.add_argument(
        "--mode",
        choices=["strict", "fast"],
        default="strict",
        help="strict: MIPGap<=1e-6 with fixed seed, fast: looser gap for quick checks",
    )
    parser.add_argument("--solver", default="gurobi", help="Pyomo solver name")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed in strict mode")
    parser.add_argument("--strict-gap", type=float, default=1e-6, help="MIPGap for strict mode")
    parser.add_argument("--fast-gap", type=float, default=1e-3, help="MIPGap for fast mode")
    parser.add_argument("--tol", type=float, default=1e-9, help="Numerical tolerance for zero checks")
    parser.add_argument("--top-n", type=int, default=10, help="Top nonzero K_RA/K_RW rows per scenario")
    parser.add_argument(
        "--output-prefix",
        default="repurpose_regression",
        help="Output file prefix under results/",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    data_root = root / "data"
    results_root = root / "results"
    results_root.mkdir(exist_ok=True)

    if args.mode == "strict":
        mip_gap = args.strict_gap
        seed = args.seed
    else:
        mip_gap = args.fast_gap
        seed = None

    payload: dict[str, Any] = {
        "mode": args.mode,
        "solver": args.solver,
        "mip_gap": mip_gap,
        "seed": seed,
        "scenarios": {},
    }

    compact_rows: list[dict[str, Any]] = []
    for spec in DEFAULT_SCENARIOS:
        other_csv = (data_root / spec.scenario_folder / "other.csv").resolve()
        result = run_one_scenario(
            other_csv,
            solver=args.solver,
            mip_gap=mip_gap,
            seed=seed,
            tol=args.tol,
            top_n=args.top_n,
        )
        kra = float(result.get("KRA_eNeqF", 0.0))
        krw = float(result.get("KRW_eNeqF", 0.0))
        expected_ok, expected_note = _evaluate_expectation(spec.name, kra, krw, tol=args.tol)

        result["expectation"] = spec.expectation
        result["expectation_pass"] = expected_ok
        result["expectation_check"] = expected_note
        result["scenario_folder"] = spec.scenario_folder
        payload["scenarios"][spec.name] = result

        compact_rows.append(
            {
                "scenario": spec.name,
                "folder": spec.scenario_folder,
                "optimal": result.get("optimal"),
                "objective": result.get("objective"),
                "repurpose_fixed_cost": result.get("repurpose_fixed_cost"),
                "repurpose_variable_cost": result.get("repurpose_variable_cost"),
                "KRA_eNeqF": result.get("KRA_eNeqF"),
                "KRW_eNeqF": result.get("KRW_eNeqF"),
                "expectation": spec.expectation,
                "expectation_pass": expected_ok,
            }
        )

    payload["all_expectations_pass"] = all(bool(r["expectation_pass"]) for r in compact_rows)

    prefix = f"{args.output_prefix}_{args.mode}"
    json_path = results_root / f"{prefix}.json"
    csv_path = results_root / f"{prefix}.csv"
    top_path = results_root / f"{prefix}_top_nonzero.csv"

    json_path.write_text(json.dumps(payload, indent=2))

    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(compact_rows[0].keys()))
        writer.writeheader()
        writer.writerows(compact_rows)

    top_rows: list[dict[str, Any]] = []
    for scenario_name, scenario_result in payload["scenarios"].items():
        for row in scenario_result.get("top_K_RA_eNeqF", []):
            top_rows.append(
                {
                    "scenario": scenario_name,
                    "var": "K_RA",
                    "a": row.get("a", ""),
                    "n": "",
                    "e": row.get("e", ""),
                    "f": row.get("f", ""),
                    "y": row.get("y", ""),
                    "value": row.get("value", 0.0),
                }
            )
        for row in scenario_result.get("top_K_RW_eNeqF", []):
            top_rows.append(
                {
                    "scenario": scenario_name,
                    "var": "K_RW",
                    "a": "",
                    "n": row.get("n", ""),
                    "e": row.get("e", ""),
                    "f": row.get("f", ""),
                    "y": row.get("y", ""),
                    "value": row.get("value", 0.0),
                }
            )

    with open(top_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["scenario", "var", "a", "n", "e", "f", "y", "value"])
        writer.writeheader()
        writer.writerows(top_rows)

    print("=== Repurpose Regression Suite ===")
    print(f"Mode: {args.mode} | solver={args.solver} | mip_gap={mip_gap} | seed={seed}")
    for row in compact_rows:
        print(
            f"{row['scenario']}: optimal={row['optimal']} "
            f"KRA_eNeqF={row['KRA_eNeqF']} KRW_eNeqF={row['KRW_eNeqF']} "
            f"expectation_pass={row['expectation_pass']}"
        )
    print(f"All expectations pass: {payload['all_expectations_pass']}")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    print(f"Top rows CSV: {top_path}")


if __name__ == "__main__":
    main()

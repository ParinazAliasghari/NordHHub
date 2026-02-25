from __future__ import annotations

from pathlib import Path
import argparse
import sys

import pyomo.environ as pyo

from scr.core.data_loading import load_inputs
from scr.core.model import build_base_model_with_cz


DEFAULT_OTHER_CSV = Path(__file__).resolve().parents[2] / "data" / "scenario1" / "other.csv"


def _iter_param_names(model: pyo.ConcreteModel) -> list[str]:
    return sorted(param.local_name for param in model.component_objects(pyo.Param, active=True))


def _print_param_summary(model: pyo.ConcreteModel, param_name: str, sample_limit: int) -> bool:
    if not hasattr(model, param_name):
        print(f"[MISSING] {param_name}")
        return False

    component = getattr(model, param_name)
    if not isinstance(component, pyo.Param):
        print(f"[NOT_PARAM] {param_name}: component exists but is not a Pyomo Param")
        return False

    dim = component.dim()
    size = len(component)
    print(f"[OK] {param_name} | dim={dim} | entries={size}")

    printed = 0
    for idx in component:
        print(f"  {param_name}[{idx}] = {pyo.value(component[idx])}")
        printed += 1
        if printed >= sample_limit:
            break

    if size > sample_limit:
        print(f"  ... ({size - sample_limit} more entries)")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check Pyomo Param components on the scaffold model."
    )
    parser.add_argument(
        "other_csv",
        nargs="?",
        default=str(DEFAULT_OTHER_CSV),
        help="Path to other.csv (default: data/scenario1/other.csv)",
    )
    parser.add_argument(
        "--params",
        nargs="*",
        default=None,
        help="Param names to check. If omitted, all model Params are checked.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all Pyomo Params found in the model.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="How many entries to print per Param (default: 10)",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit with code 2 if any requested Param is missing or invalid.",
    )
    args = parser.parse_args()

    other_path = Path(args.other_csv).resolve()
    loaded = load_inputs(other_path=other_path)
    model = build_base_model_with_cz(loaded)

    if args.all or not args.params:
        param_names = _iter_param_names(model)
    else:
        param_names = sorted(set(args.params))

    print(f"Input: {other_path}")
    print(f"Model Params found: {_iter_param_names(model)}")

    ok_count = 0
    fail_count = 0
    for name in param_names:
        ok = _print_param_summary(model, name, args.sample)
        if ok:
            ok_count += 1
        else:
            fail_count += 1

    print(f"\nSummary: {ok_count} OK, {fail_count} failed")

    if args.fail_on_missing and fail_count > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()

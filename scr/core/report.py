from __future__ import annotations

from pathlib import Path
import csv
from datetime import datetime
import json
import math

import pyomo.environ as pyo

from .validate import _safe_value


def collect_cost_breakdown(model: pyo.ConcreteModel) -> dict[str, float]:
    z_dmd = "ZD2" if "ZD2" in model.Z else (next(iter(model.Z)) if len(model.Z) > 0 else None)

    prod_cost = 0.0
    arc_investment_cost = 0.0
    bidir_fixed_cost = 0.0
    bidir_variable_cost = 0.0
    repurpose_fixed_cost = 0.0
    repurpose_variable_cost = 0.0
    arc_flow_cost = 0.0
    blending_cost = 0.0
    regas_cost = 0.0
    storage_cost = 0.0
    zds_cost = 0.0
    zn2_cost = 0.0

    for n in model.N:
        for e in model.E:
            for y in model.Y:
                for h in model.H:
                    weight = _safe_value(model.r[y]) * _safe_value(model.scaleUp[h])
                    prod_cost += weight * _safe_value(model.c_p[n, e, y]) * _safe_value(model.Q_P[n, e, y, h])
                    regas_cost += weight * _safe_value(model.c_lr[n, e]) * _safe_value(model.Q_R[n, e, y, h])
                    storage_cost += weight * _safe_value(model.c_we[n, e]) * _safe_value(model.Q_E[n, e, y, h])
                    for z in model.Z:
                        zds_cost += weight * _safe_value(model.c_z[z, e]) * _safe_value(model.ZDS[z, n, e, y, h])

    for a in model.A:
        for e in model.E:
            for y in model.Y:
                arc_investment_cost += (
                    _safe_value(model.r[y])
                    * _safe_value(model.EOH[y])
                    * _safe_value(model.c_ax[a, e, y])
                    * _safe_value(model.X_A[a, e, y])
                )

    for a in model.A:
        for y in model.Y:
            bidir_fixed_cost += (
                _safe_value(model.r[y])
                * _safe_value(model.EOH[y])
                * _safe_value(model.f_ab[a, y])
                * _safe_value(model.B_BD[a, y])
            )

    for a in model.A:
        for e in model.E:
            for y in model.Y:
                bidir_variable_cost += (
                    _safe_value(model.r[y])
                    * _safe_value(model.EOH[y])
                    * _safe_value(model.c_ab[a, e, y])
                    * _safe_value(model.K_BD[a, e, y])
                )

    for a in model.A:
        for e in model.E:
            for f in model.E:
                for y in model.Y:
                    repurpose_fixed_cost += (
                        _safe_value(model.r[y])
                        * _safe_value(model.EOH[y])
                        * _safe_value(model.f_ar[a, e, f, y])
                        * _safe_value(model.B_AR[a, e, f, y])
                    )
                    repurpose_variable_cost += (
                        _safe_value(model.r[y])
                        * _safe_value(model.EOH[y])
                        * _safe_value(model.c_ar[a, e, f, y])
                        * _safe_value(model.K_RA[a, e, f, y])
                    )

    for a in model.A:
        for e in model.E:
            for y in model.Y:
                for h in model.H:
                    weight = _safe_value(model.r[y]) * _safe_value(model.scaleUp[h])
                    arc_flow_cost += weight * _safe_value(model.c_a[a, e, y]) * _safe_value(model.F_A[a, e, y, h])

    for n in model.N:
        for e in model.E:
            for f in model.E:
                for y in model.Y:
                    for h in model.H:
                        weight = _safe_value(model.r[y]) * _safe_value(model.scaleUp[h])
                        blending_cost += weight * _safe_value(model.c_bl[e, f]) * _safe_value(model.Q_B[n, e, f, y, h])

    if z_dmd is not None:
        for g in model.NUTS2:
            for e in model.E:
                for y in model.Y:
                    for h in model.H:
                        weight = _safe_value(model.r[y]) * _safe_value(model.scaleUp[h])
                        zn2_cost += weight * _safe_value(model.c_z[z_dmd, e]) * _safe_value(model.ZN2[g, e, y, h])

    return {
        "production_cost": prod_cost,
        "arc_investment_cost": arc_investment_cost,
        "bidir_fixed_cost": bidir_fixed_cost,
        "bidir_variable_cost": bidir_variable_cost,
        "repurpose_fixed_cost": repurpose_fixed_cost,
        "repurpose_variable_cost": repurpose_variable_cost,
        "arc_flow_cost": arc_flow_cost,
        "blending_cost": blending_cost,
        "regas_cost": regas_cost,
        "storage_cost": storage_cost,
        "zds_penalty_cost": zds_cost,
        "zn2_penalty_cost": zn2_cost,
        "total_reconstructed": (
            prod_cost
            + arc_investment_cost
            + bidir_fixed_cost
            + bidir_variable_cost
            + repurpose_fixed_cost
            + repurpose_variable_cost
            + arc_flow_cost
            + blending_cost
            + regas_cost
            + storage_cost
            + zds_cost
            + zn2_cost
        ),
    }


def collect_qb_totals(model: pyo.ConcreteModel, tol: float) -> list[dict[str, float | str | int]]:
    rows: list[dict[str, float | str | int]] = []
    for n in model.N:
        for f in model.E:
            for e in model.E:
                for y in model.Y:
                    total = 0.0
                    for h in model.H:
                        total += _safe_value(model.scaleUp[h]) * _safe_value(model.Q_B[n, f, e, y, h])
                    if abs(total) <= tol:
                        continue
                    rows.append({"n": str(n), "f": str(f), "e": str(e), "y": int(y), "qb_sum_h": float(total)})
    rows.sort(key=lambda r: (str(r["n"]), str(r["f"]), str(r["e"]), int(r["y"])))
    return rows


def summarize_max_bl_binding(model: pyo.ConcreteModel, tol: float) -> dict[str, object]:
    if not hasattr(model, "max_bl"):
        return {"active_constraints": 0, "binding_constraints": 0, "binding_rows": []}

    active = 0
    binding = 0
    rows: list[dict[str, float | str | int]] = []
    con = model.max_bl
    for idx in con:
        con_data = con[idx]
        active += 1
        body = _safe_value(con_data.body)
        ub = _safe_value(con_data.upper) if con_data.has_ub() else math.inf
        if math.isnan(body) or math.isnan(ub):
            continue
        if abs(ub - body) <= tol:
            binding += 1
            if len(rows) < 25:
                rows.append({"index": str(idx), "body": body, "upper": ub})

    return {
        "active_constraints": active,
        "binding_constraints": binding,
        "binding_rows": rows,
    }


def collect_arc_flow_totals(model: pyo.ConcreteModel, tol: float) -> list[dict[str, float | str | int]]:
    def _arc_endpoints(arc_id: str) -> tuple[str, str]:
        from_node = ""
        to_node = ""
        for n in model.N:
            if from_node == "" and _safe_value(model.a_s[arc_id, n]) >= 0.5:
                from_node = str(n)
            if to_node == "" and _safe_value(model.a_e[arc_id, n]) >= 0.5:
                to_node = str(n)
            if from_node and to_node:
                break
        return from_node, to_node

    rows: list[dict[str, float | str | int]] = []
    for a in model.A:
        from_node, to_node = _arc_endpoints(a)
        for e in model.E:
            for y in model.Y:
                total = 0.0
                for h in model.H:
                    total += _safe_value(model.scaleUp[h]) * _safe_value(model.F_A[a, e, y, h])
                if abs(total) <= tol:
                    continue
                rows.append(
                    {
                        "a": str(a),
                        "e": str(e),
                        "y": int(y),
                        "flow_sum_h": float(total),
                        "from_node": from_node,
                        "to_node": to_node,
                    }
                )

    rows.sort(key=lambda r: (str(r["a"]), str(r["e"]), int(r["y"])))
    return rows


def collect_arc_expansion_totals(model: pyo.ConcreteModel, tol: float) -> list[dict[str, float | str | int]]:
    def _arc_endpoints(arc_id: str) -> tuple[str, str]:
        from_node = ""
        to_node = ""
        for n in model.N:
            if from_node == "" and _safe_value(model.a_s[arc_id, n]) >= 0.5:
                from_node = str(n)
            if to_node == "" and _safe_value(model.a_e[arc_id, n]) >= 0.5:
                to_node = str(n)
            if from_node and to_node:
                break
        return from_node, to_node

    rows: list[dict[str, float | str | int]] = []
    for a in model.A:
        from_node, to_node = _arc_endpoints(a)
        for e in model.E:
            for y in model.Y:
                xa_val = _safe_value(model.X_A[a, e, y])
                if abs(xa_val) <= tol:
                    continue
                rows.append(
                    {
                        "a": str(a),
                        "e": str(e),
                        "y": int(y),
                        "x_a": float(xa_val),
                        "from_node": from_node,
                        "to_node": to_node,
                    }
                )

    rows.sort(key=lambda r: (str(r["a"]), str(r["e"]), int(r["y"])))
    return rows


def collect_bidir_totals(model: pyo.ConcreteModel, tol: float) -> dict[str, list[dict[str, float | str | int]]]:
    bd_rows: list[dict[str, float | str | int]] = []
    bbd_rows: list[dict[str, float | str | int]] = []
    kopp_rows: list[dict[str, float | str | int]] = []
    kbd_rows: list[dict[str, float | str | int]] = []

    for a in model.A:
        for y in model.Y:
            bd_val = _safe_value(model.BD[a, y])
            bbd_val = _safe_value(model.B_BD[a, y])
            if abs(bd_val) > tol:
                bd_rows.append({"a": str(a), "y": int(y), "BD": float(bd_val)})
            if abs(bbd_val) > tol:
                bbd_rows.append({"a": str(a), "y": int(y), "B_BD": float(bbd_val)})

    for a in model.A:
        for e in model.E:
            for y in model.Y:
                kopp_val = _safe_value(model.K_OPP[a, e, y])
                kbd_val = _safe_value(model.K_BD[a, e, y])
                if abs(kopp_val) > tol:
                    kopp_rows.append({"a": str(a), "e": str(e), "y": int(y), "K_OPP": float(kopp_val)})
                if abs(kbd_val) > tol:
                    kbd_rows.append({"a": str(a), "e": str(e), "y": int(y), "K_BD": float(kbd_val)})

    bd_rows.sort(key=lambda r: (str(r["a"]), int(r["y"])))
    bbd_rows.sort(key=lambda r: (str(r["a"]), int(r["y"])))
    kopp_rows.sort(key=lambda r: (str(r["a"]), str(r["e"]), int(r["y"])))
    kbd_rows.sort(key=lambda r: (str(r["a"]), str(r["e"]), int(r["y"])))

    return {"BD": bd_rows, "B_BD": bbd_rows, "K_OPP": kopp_rows, "K_BD": kbd_rows}


def collect_repurpose_totals(model: pyo.ConcreteModel, tol: float) -> dict[str, list[dict[str, float | str | int]]]:
    bar_rows: list[dict[str, float | str | int]] = []
    kra_rows: list[dict[str, float | str | int]] = []
    bwr_rows: list[dict[str, float | str | int]] = []
    krw_rows: list[dict[str, float | str | int]] = []

    for a in model.A:
        for e in model.E:
            for f in model.E:
                for y in model.Y:
                    bar = _safe_value(model.B_AR[a, e, f, y])
                    kra = _safe_value(model.K_RA[a, e, f, y])
                    if abs(bar) > tol:
                        bar_rows.append({"a": str(a), "e": str(e), "f": str(f), "y": int(y), "B_AR": float(bar)})
                    if abs(kra) > tol:
                        kra_rows.append({"a": str(a), "e": str(e), "f": str(f), "y": int(y), "K_RA": float(kra)})

    for n in model.N:
        for e in model.E:
            for f in model.E:
                for y in model.Y:
                    bwr = _safe_value(model.B_WR[n, e, f, y])
                    krw = _safe_value(model.K_RW[n, e, f, y])
                    if abs(bwr) > tol:
                        bwr_rows.append({"n": str(n), "e": str(e), "f": str(f), "y": int(y), "B_WR": float(bwr)})
                    if abs(krw) > tol:
                        krw_rows.append({"n": str(n), "e": str(e), "f": str(f), "y": int(y), "K_RW": float(krw)})

    bar_rows.sort(key=lambda r: (str(r["a"]), str(r["e"]), str(r["f"]), int(r["y"])))
    kra_rows.sort(key=lambda r: (str(r["a"]), str(r["e"]), str(r["f"]), int(r["y"])))
    bwr_rows.sort(key=lambda r: (str(r["n"]), str(r["e"]), str(r["f"]), int(r["y"])))
    krw_rows.sort(key=lambda r: (str(r["n"]), str(r["e"]), str(r["f"]), int(r["y"])))

    return {"B_AR": bar_rows, "K_RA": kra_rows, "B_WR": bwr_rows, "K_RW": krw_rows}


def summarize_a_lim_binding(model: pyo.ConcreteModel, tol: float) -> dict[str, object]:
    if not hasattr(model, "a_lim"):
        return {"active_constraints": 0, "binding_constraints": 0, "binding_rows": []}

    active = 0
    binding = 0
    rows: list[dict[str, float | str | int]] = []
    con = model.a_lim
    for idx in con:
        con_data = con[idx]
        active += 1
        body = _safe_value(con_data.body)
        ub = _safe_value(con_data.upper) if con_data.has_ub() else math.inf
        if math.isnan(body) or math.isnan(ub) or ub <= tol:
            continue
        if abs(ub - body) <= tol:
            binding += 1
            if len(rows) < 25:
                util = body / ub if abs(ub) > tol else math.nan
                rows.append({"index": str(idx), "body": body, "upper": ub, "utilization": util})

    return {
        "active_constraints": active,
        "binding_constraints": binding,
        "binding_rows": rows,
    }


def summarize_slacks(model: pyo.ConcreteModel, tol: float) -> dict[str, float]:
    total_zds = 0.0
    total_zn2 = 0.0
    nz_zds = 0
    nz_zn2 = 0

    for z in model.Z:
        for n in model.N:
            for e in model.E:
                for y in model.Y:
                    for h in model.H:
                        v = _safe_value(model.ZDS[z, n, e, y, h])
                        total_zds += v
                        if v > tol:
                            nz_zds += 1

    for g in model.NUTS2:
        for e in model.E:
            for y in model.Y:
                for h in model.H:
                    v = _safe_value(model.ZN2[g, e, y, h])
                    total_zn2 += v
                    if v > tol:
                        nz_zn2 += 1

    return {
        "sum_ZDS": total_zds,
        "sum_ZN2": total_zn2,
        "nonzero_ZDS": nz_zds,
        "nonzero_ZN2": nz_zn2,
    }


def _top_nonzero_entries(var_component, tol: float, top_n: int) -> list[dict]:
    rows: list[tuple[float, str, float]] = []
    for idx in var_component:
        value = _safe_value(var_component[idx])
        if math.isnan(value) or value <= tol:
            continue
        rows.append((abs(value), str(idx), value))

    rows.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "index": idx,
            "value": value,
        }
        for _, idx, value in rows[:top_n]
    ]


def collect_top_variable_values(model: pyo.ConcreteModel, tol: float, top_n: int) -> dict[str, list[dict]]:
    return {
        "Q_P": _top_nonzero_entries(model.Q_P, tol=tol, top_n=top_n),
        "F_A": _top_nonzero_entries(model.F_A, tol=tol, top_n=top_n),
        "X_A": _top_nonzero_entries(model.X_A, tol=tol, top_n=top_n),
        "K_A": _top_nonzero_entries(model.K_A, tol=tol, top_n=top_n),
        "B_AR": _top_nonzero_entries(model.B_AR, tol=tol, top_n=top_n),
        "K_RA": _top_nonzero_entries(model.K_RA, tol=tol, top_n=top_n),
        "BD": _top_nonzero_entries(model.BD, tol=tol, top_n=top_n),
        "B_BD": _top_nonzero_entries(model.B_BD, tol=tol, top_n=top_n),
        "K_OPP": _top_nonzero_entries(model.K_OPP, tol=tol, top_n=top_n),
        "K_BD": _top_nonzero_entries(model.K_BD, tol=tol, top_n=top_n),
        "K_W": _top_nonzero_entries(model.K_W, tol=tol, top_n=top_n),
        "B_WR": _top_nonzero_entries(model.B_WR, tol=tol, top_n=top_n),
        "K_RW": _top_nonzero_entries(model.K_RW, tol=tol, top_n=top_n),
        "Q_B": _top_nonzero_entries(model.Q_B, tol=tol, top_n=top_n),
        "Q_R": _top_nonzero_entries(model.Q_R, tol=tol, top_n=top_n),
        "Q_E": _top_nonzero_entries(model.Q_E, tol=tol, top_n=top_n),
        "Q_I": _top_nonzero_entries(model.Q_I, tol=tol, top_n=top_n),
        "Q_S": _top_nonzero_entries(model.Q_S, tol=tol, top_n=top_n),
        "ZDS": _top_nonzero_entries(model.ZDS, tol=tol, top_n=top_n),
        "ZN2": _top_nonzero_entries(model.ZN2, tol=tol, top_n=top_n),
    }


def _export_var_to_csv(var_component, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "value"])
        for idx in var_component:
            writer.writerow([str(idx), _safe_value(var_component[idx])])
            count += 1
    return count


def _export_param_to_csv(param_component, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "value"])
        for idx in param_component:
            writer.writerow([str(idx), _safe_value(param_component[idx])])
            count += 1
    return count


def export_all_results(model: pyo.ConcreteModel, output_dir: Path) -> dict[str, dict[str, str | int]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    export_spec = {
        "Q_P": model.Q_P,
        "F_A": model.F_A,
        "X_A": model.X_A,
        "K_A": model.K_A,
        "B_AR": model.B_AR,
        "K_RA": model.K_RA,
        "BD": model.BD,
        "B_BD": model.B_BD,
        "K_OPP": model.K_OPP,
        "K_BD": model.K_BD,
        "K_W": model.K_W,
        "B_WR": model.B_WR,
        "K_RW": model.K_RW,
        "Q_B": model.Q_B,
        "Q_R": model.Q_R,
        "Q_E": model.Q_E,
        "Q_I": model.Q_I,
        "Q_S": model.Q_S,
        "ZDS": model.ZDS,
        "ZN2": model.ZN2,
    }
    exported: dict[str, dict[str, str | int]] = {}
    for name, component in export_spec.items():
        out_file = output_dir / f"{name}.csv"
        rows = _export_var_to_csv(component, out_file)
        exported[name] = {"file": str(out_file), "rows": rows}

    cax_file = output_dir / "c_ax.csv"
    cax_rows = _export_param_to_csv(model.c_ax, cax_file)
    exported["c_ax"] = {"file": str(cax_file), "rows": cax_rows}

    cab_file = output_dir / "c_ab.csv"
    cab_rows = _export_param_to_csv(model.c_ab, cab_file)
    exported["c_ab"] = {"file": str(cab_file), "rows": cab_rows}

    fab_file = output_dir / "f_ab.csv"
    fab_rows = _export_param_to_csv(model.f_ab, fab_file)
    exported["f_ab"] = {"file": str(fab_file), "rows": fab_rows}

    car_file = output_dir / "c_ar.csv"
    car_rows = _export_param_to_csv(model.c_ar, car_file)
    exported["c_ar"] = {"file": str(car_file), "rows": car_rows}

    far_file = output_dir / "f_ar.csv"
    far_rows = _export_param_to_csv(model.f_ar, far_file)
    exported["f_ar"] = {"file": str(far_file), "rows": far_rows}

    opp_file = output_dir / "opp_map.csv"
    with opp_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["a", "opp_arc", "is_bid"])
        for a in model.A:
            opp_arc_val = pyo.value(model.opp_arc[a], exception=False)
            writer.writerow([str(a), "" if opp_arc_val is None else str(opp_arc_val), int(_safe_value(model.is_bid[a]))])
    exported["opp_map"] = {"file": str(opp_file), "rows": len(list(model.A))}

    return exported


def export_combined_results_csv(
    model: pyo.ConcreteModel,
    output_path: Path,
    *,
    scenario_name: str,
    timestamp: str,
) -> dict[str, str | int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp_display = _format_timestamp_display(timestamp)

    z_values = [str(z) for z in model.Z]
    nuts2_values = [str(g) for g in model.NUTS2]

    headers = [
        "scenario",
        "timestamp",
        "n",
        "e",
        "y",
        "h",
        "demand",
        "Q_P",
        "Q_R",
        "Q_E",
        "Q_I",
        "Q_S",
        "FA_in_eff",
        "FA_out",
        "ZDS_sum",
        "ZN2_assigned",
        "ZN2_total",
    ]
    headers.extend([f"ZDS_{z}" for z in z_values])
    headers.extend([f"ZN2_{g}" for g in nuts2_values])

    row_count = 0
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for n in model.N:
            for e in model.E:
                for y in model.Y:
                    for h in model.H:
                        row: dict[str, float | str | int] = {
                            "scenario": str(scenario_name),
                            "timestamp": timestamp_display,
                            "n": str(n),
                            "e": str(e),
                            "y": int(y),
                            "h": int(h),
                            "demand": _safe_value(model.dmd[n, e, y, h]),
                            "Q_P": _safe_value(model.Q_P[n, e, y, h]),
                            "Q_R": _safe_value(model.Q_R[n, e, y, h]),
                            "Q_E": _safe_value(model.Q_E[n, e, y, h]),
                            "Q_I": _safe_value(model.Q_I[n, e, y, h]),
                            "Q_S": _safe_value(model.Q_S[n, e, y, h]),
                        }

                        fa_in_eff = 0.0
                        fa_out = 0.0
                        for a in model.A:
                            fval = _safe_value(model.F_A[a, e, y, h])
                            if _safe_value(model.a_e[a, n]) >= 0.5:
                                fa_in_eff += fval * _safe_value(model.e_a[a, e])
                            if _safe_value(model.a_s[a, n]) >= 0.5:
                                fa_out += fval
                        row["FA_in_eff"] = fa_in_eff
                        row["FA_out"] = fa_out

                        zds_sum = 0.0
                        for z in model.Z:
                            v = _safe_value(model.ZDS[z, n, e, y, h])
                            row[f"ZDS_{z}"] = v
                            zds_sum += v
                        row["ZDS_sum"] = zds_sum

                        zn2_assigned = 0.0
                        zn2_total = 0.0
                        for g in model.NUTS2:
                            v = _safe_value(model.ZN2[g, e, y, h])
                            row[f"ZN2_{g}"] = v
                            zn2_total += v
                            if _safe_value(model.n_in_2[n, g]) >= 0.5:
                                zn2_assigned += v
                        row["ZN2_assigned"] = zn2_assigned
                        row["ZN2_total"] = zn2_total

                        writer.writerow(row)
                        row_count += 1

    return {"file": str(output_path), "rows": row_count}


def write_json_report(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def _format_timestamp_display(timestamp: str) -> str:
    try:
        parsed = datetime.strptime(str(timestamp), "%Y%m%d_%H%M%S")
        return parsed.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(timestamp)


def write_per_run_result_csvs(
    *,
    report: dict,
    results_root: Path,
    scenario_name: str,
    timestamp: str,
) -> dict[str, str]:
    scenario_dir = results_root / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)
    timestamp_display = _format_timestamp_display(timestamp)
    summary_path = scenario_dir / f"summary_{scenario_name}_{timestamp}.csv"

    rows: list[dict[str, str | float | int]] = []

    def add_row(
        *,
        section: str,
        metric: str,
        value: float,
        node: str = "",
        arc: str = "",
        from_node: str = "",
        to_node: str = "",
        carrier: str = "",
        year: str = "",
        hour: str = "",
        z: str = "",
        nuts2: str = "",
    ) -> None:
        rows.append(
            {
                "scenario": str(scenario_name),
                "timestamp": timestamp_display,
                "section": str(section),
                "metric": str(metric),
                "value": float(value),
                "node": str(node),
                "arc": str(arc),
                "from_node": str(from_node),
                "to_node": str(to_node),
                "carrier": str(carrier),
                "year": str(year),
                "hour": str(hour),
                "z": str(z),
                "nuts2": str(nuts2),
            }
        )

    for key, value in report.get("cost_breakdown", {}).items():
        add_row(section="cost_breakdown", metric=str(key), value=float(value))

    slack = report.get("slack_summary", {})
    for key in ["sum_ZDS", "sum_ZN2", "nonzero_ZDS", "nonzero_ZN2"]:
        if key in slack:
            add_row(section="slack_summary", metric=key, value=float(slack[key]))

    con = report.get("constraint_check", {})
    for key in ["total_constraints", "violated_constraints", "max_violation", "feasible_by_tolerance"]:
        if key in con:
            add_row(section="constraint_check", metric=key, value=float(con[key]))

    for key, value in report.get("a_lim_binding", {}).items():
        if isinstance(value, (int, float, bool)):
            add_row(section="a_lim_binding", metric=str(key), value=float(value))

    for key, value in report.get("max_bl_binding", {}).items():
        if isinstance(value, (int, float, bool)):
            add_row(section="max_bl_binding", metric=str(key), value=float(value))

    for key, value in report.get("node_arc_balance_check", {}).items():
        if isinstance(value, (int, float, bool)):
            add_row(section="node_arc_balance_check", metric=str(key), value=float(value))

    add_row(section="scalar", metric="objective", value=float(report.get("objective", math.nan)))
    add_row(section="scalar", metric="tc_value", value=float(report.get("tc_value", math.nan)))
    add_row(section="scalar", metric="objective_tc_gap", value=float(report.get("objective_tc_gap", math.nan)))

    for row in report.get("arc_flow_totals", []):
        add_row(
            section="arc_flow_totals",
            metric="flow_total",
            value=float(row["flow_sum_h"]),
            arc=str(row.get("a", "")),
            from_node=str(row.get("from_node", "")),
            to_node=str(row.get("to_node", "")),
            carrier=str(row.get("e", "")),
            year=str(row.get("y", "")),
        )
    for row in report.get("arc_expansion_totals", []):
        add_row(
            section="arc_expansion_totals",
            metric="expansion_total",
            value=float(row["x_a"]),
            arc=str(row.get("a", "")),
            from_node=str(row.get("from_node", "")),
            to_node=str(row.get("to_node", "")),
            carrier=str(row.get("e", "")),
            year=str(row.get("y", "")),
        )
    for row in report.get("qb_totals", []):
        add_row(
            section="blending_totals",
            metric="qb_sum_h",
            value=float(row["qb_sum_h"]),
            node=str(row.get("n", "")),
            carrier=str(row.get("e", "")),
            year=str(row.get("y", "")),
        )

    for key, entries in report.get("bidir_totals", {}).items():
        for item in entries:
            if key in ["BD", "B_BD"]:
                add_row(
                    section="bidir_totals",
                    metric=key,
                    value=float(item[key]),
                    arc=str(item.get("a", "")),
                    year=str(item.get("y", "")),
                )
            else:
                add_row(
                    section="bidir_totals",
                    metric=key,
                    value=float(item[key]),
                    arc=str(item.get("a", "")),
                    carrier=str(item.get("e", "")),
                    year=str(item.get("y", "")),
                )

    for key, entries in report.get("repurpose_totals", {}).items():
        for item in entries:
            if key in ["B_AR", "K_RA"]:
                add_row(
                    section="repurpose_totals",
                    metric=key,
                    value=float(item[key]),
                    arc=str(item.get("a", "")),
                    carrier=str(item.get("e", "")),
                    year=str(item.get("y", "")),
                )
            else:
                add_row(
                    section="repurpose_totals",
                    metric=key,
                    value=float(item[key]),
                    node=str(item.get("n", "")),
                    carrier=str(item.get("e", "")),
                    year=str(item.get("y", "")),
                )

    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "scenario",
                "timestamp",
                "section",
                "metric",
                "value",
                "node",
                "arc",
                "from_node",
                "to_node",
                "carrier",
                "year",
                "hour",
                "z",
                "nuts2",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    return {"summary": str(summary_path), "rows": str(len(rows))}


def append_run_log(
    *,
    results_root: Path,
    scenario_name: str,
    timestamp: str,
    solver: str,
    termination_condition: str,
    objective: float,
    tc_value: float,
    solve_seconds: float,
    violated_constraints: int,
    max_violation: float,
    sum_ZDS: float,
    sum_ZN2: float,
) -> str:
    scenario_dir = results_root / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)
    log_path = scenario_dir / f"runs_{scenario_name}.csv"
    timestamp_display = _format_timestamp_display(timestamp)

    file_exists = log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "scenario",
                "solver",
                "termination_condition",
                "objective",
                "tc_value",
                "solve_seconds",
                "violated_constraints",
                "max_violation",
                "sum_ZDS",
                "sum_ZN2",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": timestamp_display,
                "scenario": str(scenario_name),
                "solver": str(solver),
                "termination_condition": str(termination_condition),
                "objective": float(objective),
                "tc_value": float(tc_value),
                "solve_seconds": float(solve_seconds),
                "violated_constraints": int(violated_constraints),
                "max_violation": float(max_violation),
                "sum_ZDS": float(sum_ZDS),
                "sum_ZN2": float(sum_ZN2),
            }
        )

    return str(log_path)

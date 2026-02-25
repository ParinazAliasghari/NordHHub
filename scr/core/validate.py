from __future__ import annotations

import math

import pyomo.environ as pyo


def _safe_value(expr) -> float:
    val = pyo.value(expr, exception=False)
    if val is None:
        return math.nan
    try:
        return float(val)
    except (TypeError, ValueError):
        return math.nan


def _constraint_violation(con_data: pyo.ConstraintData) -> tuple[float, float, float, float]:
    body = _safe_value(con_data.body)
    lb = _safe_value(con_data.lower) if con_data.has_lb() else -math.inf
    ub = _safe_value(con_data.upper) if con_data.has_ub() else math.inf

    if math.isnan(body):
        return math.inf, body, lb, ub

    viol_lb = 0.0 if not con_data.has_lb() else max(0.0, lb - body)
    viol_ub = 0.0 if not con_data.has_ub() else max(0.0, body - ub)
    return max(viol_lb, viol_ub), body, lb, ub


def validate_constraints(model: pyo.ConcreteModel, tol: float) -> dict:
    total = 0
    violated = 0
    max_viol = 0.0
    worst = None

    for con_comp in model.component_objects(pyo.Constraint, active=True):
        for idx in con_comp:
            total += 1
            con_data = con_comp[idx]
            viol, body, lb, ub = _constraint_violation(con_data)
            if viol > max_viol:
                max_viol = viol
                worst = {
                    "name": con_comp.name,
                    "index": str(idx),
                    "violation": viol,
                    "body": body,
                    "lower": lb,
                    "upper": ub,
                }
            if viol > tol:
                violated += 1

    return {
        "total_constraints": total,
        "violated_constraints": violated,
        "max_violation": max_viol,
        "feasible_by_tolerance": violated == 0,
        "worst_constraint": worst,
    }


def validate_bidirectional_logic(model: pyo.ConcreteModel, tol: float) -> dict[str, object]:
    no_opp_violations: list[dict[str, float | str | int]] = []
    bd_zero_violations: list[dict[str, float | str | int]] = []
    opp_cap_violations: list[dict[str, float | str | int]] = []
    is_bid_violations: list[dict[str, float | str | int]] = []

    for a in model.A:
        has_opp = any(_safe_value(model.opp[ao, a]) >= 0.5 for ao in model.A)
        for e in model.E:
            for y in model.Y:
                kopp = _safe_value(model.K_OPP[a, e, y])
                bd = _safe_value(model.BD[a, y])

                if not has_opp and abs(kopp) > tol:
                    no_opp_violations.append({"a": str(a), "e": str(e), "y": int(y), "K_OPP": kopp})

                if abs(bd) <= tol and abs(kopp) > tol:
                    bd_zero_violations.append({"a": str(a), "e": str(e), "y": int(y), "BD": bd, "K_OPP": kopp})

                opp_cap = sum(
                    _safe_value(model.opp[ao, a]) * _safe_value(model.K_A[ao, e, y])
                    for ao in model.A
                )
                if kopp - opp_cap > tol:
                    opp_cap_violations.append(
                        {"a": str(a), "e": str(e), "y": int(y), "K_OPP": kopp, "opp_cap": opp_cap, "diff": kopp - opp_cap}
                    )

        if _safe_value(model.is_bid[a]) >= 0.5:
            for y in model.Y:
                bd = _safe_value(model.BD[a, y])
                if abs(bd - 1.0) > tol:
                    is_bid_violations.append({"a": str(a), "y": int(y), "BD": bd})

    return {
        "no_opp_kopp_violations": no_opp_violations,
        "bd_zero_kopp_violations": bd_zero_violations,
        "opp_capacity_violations": opp_cap_violations,
        "is_bid_bd_fix_violations": is_bid_violations,
        "violation_count": len(no_opp_violations) + len(bd_zero_violations) + len(opp_cap_violations) + len(is_bid_violations),
    }


def validate_repurposing_logic(model: pyo.ConcreteModel, tol: float) -> dict[str, object]:
    ar_cap_viol: list[dict[str, float | str | int]] = []
    wr_cap_viol: list[dict[str, float | str | int]] = []
    sos_a_viol: list[dict[str, float | str | int]] = []
    sos_w_viol: list[dict[str, float | str | int]] = []
    bil_a1_viol: list[dict[str, float | str | int]] = []
    bil_w1_viol: list[dict[str, float | str | int]] = []
    bil_a2_viol: list[dict[str, float | str | int]] = []
    bil_w2_viol: list[dict[str, float | str | int]] = []

    first_y = min(int(y) for y in model.Y) if len(list(model.Y)) > 0 else None

    for a in model.A:
        for e in model.E:
            for y in model.Y:
                yi = int(y)
                if first_y is None or yi == first_y:
                    continue

                lhs_ar = _safe_value(model.K_A[a, e, y])
                rhs_ar = sum(_safe_value(model.K_RA[a, f, e, y]) for f in model.E) + sum(
                    _safe_value(model.X_A[a, e, y2]) for y2 in model.Y if _safe_value(model.ypred[y2, y]) >= 0.5
                )
                if abs(lhs_ar - rhs_ar) > tol:
                    ar_cap_viol.append({"a": str(a), "e": str(e), "y": yi, "lhs": lhs_ar, "rhs": rhs_ar, "residual": lhs_ar - rhs_ar})

                lhs_ba1 = sum(_safe_value(model.K_RA[a, e, f, y]) for f in model.E)
                rhs_ba1 = sum(_safe_value(model.K_A[a, e, y2]) for y2 in model.Y if _safe_value(model.ypred[y2, y]) >= 0.5)
                if abs(lhs_ba1 - rhs_ba1) > tol:
                    bil_a1_viol.append({"a": str(a), "e": str(e), "y": yi, "lhs": lhs_ba1, "rhs": rhs_ba1, "residual": lhs_ba1 - rhs_ba1})

                sos_a = sum(_safe_value(model.B_AR[a, e, f, y]) for f in model.E)
                if abs(sos_a - 1.0) > tol:
                    sos_a_viol.append({"a": str(a), "e": str(e), "y": yi, "sum_B_AR": sos_a})

                for f in model.E:
                    lhs_ba2 = _safe_value(model.K_RA[a, e, f, y])
                    rhs_ba2 = _safe_value(model.B_AR[a, e, f, y]) * _safe_value(model.bigM)
                    if lhs_ba2 - rhs_ba2 > tol:
                        bil_a2_viol.append({"a": str(a), "e": str(e), "f": str(f), "y": yi, "lhs": lhs_ba2, "rhs": rhs_ba2, "diff": lhs_ba2 - rhs_ba2})

    for n in model.N:
        for e in model.E:
            for y in model.Y:
                yi = int(y)
                if first_y is None or yi == first_y:
                    continue

                lhs_wr = _safe_value(model.K_W[n, e, y])
                rhs_wr = sum(_safe_value(model.K_RW[n, f, e, y]) for f in model.E)
                if abs(lhs_wr - rhs_wr) > tol:
                    wr_cap_viol.append({"n": str(n), "e": str(e), "y": yi, "lhs": lhs_wr, "rhs": rhs_wr, "residual": lhs_wr - rhs_wr})

                lhs_bw1 = sum(_safe_value(model.K_RW[n, e, f, y]) for f in model.E)
                rhs_bw1 = sum(_safe_value(model.K_W[n, e, y2]) for y2 in model.Y if _safe_value(model.ypred[y2, y]) >= 0.5)
                if abs(lhs_bw1 - rhs_bw1) > tol:
                    bil_w1_viol.append({"n": str(n), "e": str(e), "y": yi, "lhs": lhs_bw1, "rhs": rhs_bw1, "residual": lhs_bw1 - rhs_bw1})

                sos_w = sum(_safe_value(model.B_WR[n, e, f, y]) for f in model.E)
                if abs(sos_w - 1.0) > tol:
                    sos_w_viol.append({"n": str(n), "e": str(e), "y": yi, "sum_B_WR": sos_w})

                for f in model.E:
                    lhs_bw2 = _safe_value(model.K_RW[n, e, f, y])
                    rhs_bw2 = _safe_value(model.B_WR[n, e, f, y]) * _safe_value(model.bigM)
                    if lhs_bw2 - rhs_bw2 > tol:
                        bil_w2_viol.append({"n": str(n), "e": str(e), "f": str(f), "y": yi, "lhs": lhs_bw2, "rhs": rhs_bw2, "diff": lhs_bw2 - rhs_bw2})

    total = (
        len(ar_cap_viol)
        + len(wr_cap_viol)
        + len(sos_a_viol)
        + len(sos_w_viol)
        + len(bil_a1_viol)
        + len(bil_w1_viol)
        + len(bil_a2_viol)
        + len(bil_w2_viol)
    )

    return {
        "ar_cap_violations": ar_cap_viol,
        "wr_cap_violations": wr_cap_viol,
        "sos_a_violations": sos_a_viol,
        "sos_w_violations": sos_w_viol,
        "bil_a1_violations": bil_a1_viol,
        "bil_w1_violations": bil_w1_viol,
        "bil_a2_violations": bil_a2_viol,
        "bil_w2_violations": bil_w2_viol,
        "violation_count": total,
    }


def validate_node_arc_balance(model: pyo.ConcreteModel, tol: float) -> dict[str, object]:
    rows: list[dict[str, float | str | int]] = []
    max_abs = 0.0
    worst: dict[str, float | str | int] | None = None

    for n in model.N:
        for e in model.E:
            for y in model.Y:
                lhs = 0.0
                rhs = 0.0
                for h in model.H:
                    inflow_eff = sum(
                        _safe_value(model.F_A[a, e, y, h]) * _safe_value(model.e_a[a, e])
                        for a in model.A
                        if _safe_value(model.a_e[a, n]) >= 0.5
                    )
                    outflow = sum(
                        _safe_value(model.F_A[a, e, y, h])
                        for a in model.A
                        if _safe_value(model.a_s[a, n]) >= 0.5
                    )
                    blend_in = 0.0
                    if hasattr(model, "Q_B"):
                        blend_in = sum(_safe_value(model.Q_B[n, f, e, y, h]) for f in model.E)
                    lhs += (
                        _safe_value(model.Q_P[n, e, y, h])
                        + inflow_eff
                        + _safe_value(model.Q_E[n, e, y, h])
                        + _safe_value(model.Q_R[n, e, y, h])
                        + blend_in
                    )
                    rhs += (
                        _safe_value(model.Q_S[n, e, y, h])
                        + outflow
                        + _safe_value(model.Q_I[n, e, y, h])
                    )

                residual = lhs - rhs
                abs_res = abs(residual)
                if abs_res > max_abs:
                    max_abs = abs_res
                    worst = {"n": str(n), "e": str(e), "y": int(y), "lhs_total": lhs, "rhs_total": rhs, "residual": residual}
                if abs_res > tol:
                    rows.append({"n": str(n), "e": str(e), "y": int(y), "lhs_total": lhs, "rhs_total": rhs, "residual": residual})

    return {
        "max_abs_residual": float(max_abs),
        "violations": rows,
        "violation_count": len(rows),
        "worst": worst,
    }

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional
import sys

import pyomo.environ as pyo

from .data_loading import load_inputs


# STEP 0: Default input path
DEFAULT_OTHER_CSV = Path(__file__).resolve().parents[2] / "data" / "scenario5" / "other.csv"


def _clean_list(values: Optional[Iterable], *, keep_empty: bool = False) -> list[str]:
    # Utility: unique_sorted({str(v).strip()}) with optional empty-string filtering.
    if values is None:
        return []
    cleaned: list[str] = []
    for value in values:
        s = "" if value is None else str(value).strip()
        if s.lower() in ["nan", "none", "null"]:
            s = ""
        if s == "" and not keep_empty:
            continue
        cleaned.append(s)
    return sorted(set(cleaned))


def build_base_model_with_cz(
    loaded_inputs: dict[str, Any],
    *,
    z_values: Optional[Iterable[str]] = None,
    e_values: Optional[Iterable[str]] = None,
    node_values: Optional[Iterable[str]] = None,
    arc_values: Optional[Iterable[str]] = None,
    y_values: Optional[Iterable[int]] = None,
    h_values: Optional[Iterable[int]] = None,
) -> pyo.ConcreteModel:
    """
    Node-only MGET subset scaffold:
    - sets and parameters loaded from CSV pipeline
    - production + consumption equations aligned with MGET.gms (without arcs/storage/regas/blending)
    """
    model = pyo.ConcreteModel(name="MGET_Python_Scaffold")

    # STEP 1: Read prepared parameters from centralized loader
    c_z_df = loaded_inputs["c_z"]
    bigm_value = loaded_inputs["bigM"]
    yearstep_value = loaded_inputs["yearstep"]
    discrate_value = loaded_inputs["discRate"]
    c_bl_map = loaded_inputs.get("c_bl", {})
    ub_bl_map = loaded_inputs.get("ub_bl", {})
    loss_max_value = loaded_inputs.get("lossMax", 0.0)
    vola2_map = loaded_inputs.get("vola2", {})
    vols2_map = loaded_inputs.get("vols2", {})
    loaded_y_values = loaded_inputs.get("y_values", [])
    loaded_h_values = loaded_inputs.get("h_values", [])
    loaded_e_values = loaded_inputs.get("e_values", [])
    loaded_scaleup = loaded_inputs.get("scaleUp", {})
    loaded_n_values = loaded_inputs.get("n_values", [])
    loaded_cn_values = loaded_inputs.get("cn_values", [])
    loaded_nuts2_values = loaded_inputs.get("nuts2_values", [])
    loaded_rgn_values = loaded_inputs.get("rgn_values", [])
    loaded_n_in_c = loaded_inputs.get("n_in_c", {})
    loaded_n_in_2 = loaded_inputs.get("n_in_2", {})
    loaded_n_in_r = loaded_inputs.get("n_in_r", {})
    loaded_a_values = loaded_inputs.get("a_values", [])
    loaded_a_s = loaded_inputs.get("a_s", {})
    loaded_a_e = loaded_inputs.get("a_e", {})
    loaded_opp = loaded_inputs.get("opp", {})
    loaded_opp_map = loaded_inputs.get("opp_map", {})
    loaded_is_bid = loaded_inputs.get("is_bid", {})
    loaded_dmd = loaded_inputs.get("dmd", {})
    loaded_dmd2 = loaded_inputs.get("dmd2", {})
    loaded_cap_p = loaded_inputs.get("cap_p", {})
    loaded_c_p = loaded_inputs.get("c_p", {})
    loaded_lb_p = loaded_inputs.get("lb_p", {})
    loaded_c_lr = loaded_inputs.get("c_lr", {})
    loaded_ub_r = loaded_inputs.get("ub_r", {})
    loaded_cap_a = loaded_inputs.get("cap_a", {})
    loaded_c_a = loaded_inputs.get("c_a", {})
    loaded_c_ax = loaded_inputs.get("c_ax", {})
    loaded_c_ab = loaded_inputs.get("c_ab", {})
    loaded_c_ar = loaded_inputs.get("c_ar", {})
    loaded_f_ar = loaded_inputs.get("f_ar", {})
    loaded_f_ab = loaded_inputs.get("f_ab", {})
    loaded_e_a = loaded_inputs.get("e_a", {})
    loaded_cap_we = loaded_inputs.get("cap_we", {})
    loaded_cap_wi = loaded_inputs.get("cap_wi", {})
    loaded_cap_ww = loaded_inputs.get("cap_ww", {})
    loaded_c_we = loaded_inputs.get("c_we", {})
    loaded_e_w = loaded_inputs.get("e_w", {})
    loaded_h2_ready = loaded_inputs.get("h2_ready", {})

    # STEP 2: Build set domains
    z_domain = _clean_list(z_values) or sorted(set(c_z_df["z"].astype(str).tolist()))
    e_domain = _clean_list(e_values) or _clean_list(loaded_e_values) or sorted(set(c_z_df["e"].astype(str).tolist()))

    model.Z = pyo.Set(initialize=z_domain, ordered=True, doc="Penalty types")
    model.E = pyo.Set(initialize=e_domain, ordered=True, doc="Fuels / energy carriers")
    model.N = pyo.Set(initialize=_clean_list(node_values) or _clean_list(loaded_n_values), ordered=True, doc="Nodes")
    model.CN = pyo.Set(initialize=_clean_list(loaded_cn_values), ordered=True, doc="Countries")
    model.NUTS2 = pyo.Set(initialize=_clean_list(loaded_nuts2_values), ordered=True, doc="NUTS2 regions")
    model.RGN = pyo.Set(initialize=_clean_list(loaded_rgn_values), ordered=True, doc="Regions")
    model.A = pyo.Set(initialize=_clean_list(arc_values) or _clean_list(loaded_a_values), ordered=True, doc="Arcs")

    final_y_values = sorted(set((list(y_values) if y_values is not None else loaded_y_values)))
    final_h_values = sorted(set((list(h_values) if h_values is not None else loaded_h_values)))
    model.Y = pyo.Set(initialize=final_y_values, ordered=True, doc="Planning years")
    model.H = pyo.Set(initialize=final_h_values, ordered=True, doc="Operational hours")

    z_dmd = "ZD2" if "ZD2" in z_domain else (z_domain[0] if z_domain else None)

    # STEP 3: Define parameters
    # c_z(z,e): feasibility penalty matrix.
    # r(y) = 1 / (1 + DiscRate)^(YearStep * (ord(y)-1)).
    # dmd(n,e,y,h), dmd2(g,e,y,h), cap_p(n,e,y,h), lb_p(n,e,y,h), c_p(n,e,y).
    # c_lr(n,e): regasification unit cost, ub_r(n,e): regasification hourly upper bound.
    # cap_we/cap_wi/cap_ww, c_we, e_w: storage parameters (Sheet-W subset).
    c_z_map = {(str(r.z), str(r.e)): float(r.c_z) for r in c_z_df.itertuples(index=False)}
    model.c_z = pyo.Param(
        model.Z,
        model.E,
        initialize=lambda mm, z, e: float(c_z_map.get((z, e), 0.0)),
        default=0.0,
        mutable=False,
        doc="Feasibility penalty by (z,e)",
    )
    model.c_bl = pyo.Param(
        model.E,
        model.E,
        initialize=lambda mm, e, f: float(c_bl_map.get((str(e), str(f)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Blending cost c_bl(e,f)",
    )
    model.ub_bl = pyo.Param(
        model.E,
        model.E,
        initialize=lambda mm, e, f: float(ub_bl_map.get((str(e), str(f)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Blending upper limit ub_bl(e,f)",
    )
    model.vola2 = pyo.Param(
        model.E,
        initialize=lambda mm, e: float(vola2_map.get(str(e), 1.0)),
        default=1.0,
        mutable=False,
        doc="Energy to arc-volume conversion, relative to gas",
    )
    model.vols2 = pyo.Param(
        model.E,
        initialize=lambda mm, e: float(vols2_map.get(str(e), 1.0)),
        default=1.0,
        mutable=False,
        doc="Energy to storage-volume conversion, relative to gas",
    )
    model.bigM = pyo.Param(initialize=float(bigm_value), mutable=False, doc="Global big-M scalar")
    model.yearstep = pyo.Param(initialize=float(yearstep_value), mutable=False, doc="Year step scalar")
    model.discRate = pyo.Param(initialize=float(discrate_value), mutable=False, doc="Discount rate scalar")
    model.lossMax = pyo.Param(initialize=float(loss_max_value), mutable=False, doc="Maximum loss scalar")

    y_order = list(model.Y)
    y_pos = {y: idx for idx, y in enumerate(y_order)}
    y_last = y_order[-1] if len(y_order) > 0 else None
    model.r = pyo.Param(
        model.Y,
        initialize=lambda mm, y: float(1.0 / pow(1.0 + pyo.value(mm.discRate), pyo.value(mm.yearstep) * y_pos[y])),
        default=1.0,
        mutable=False,
        doc="Discount factor by year: 1/(1+DiscRate)^(YearStep*(ord(y)-1))",
    )
    model.EOH = pyo.Param(
        model.Y,
        initialize=lambda mm, y: 3.0 if (y_last is not None and int(y) == int(y_last)) else 1.0,
        default=1.0,
        mutable=False,
        doc="End-of-horizon correction EOH(y)",
    )
    model.ypred = pyo.Param(
        model.Y,
        model.Y,
        initialize=lambda mm, y2, y: int(y_pos[y] - y_pos[y2] == 1),
        default=0,
        mutable=False,
        doc="Immediate predecessor mapping ypred(y2,y)",
    )
    model.yscai = pyo.Param(
        model.Y,
        model.Y,
        initialize=lambda mm, y2, y: int(y_pos[y] <= y_pos[y2]),
        default=0,
        mutable=False,
        doc="Successor mapping yscai(y2,y)",
    )
    model.scaleUp = pyo.Param(
        model.H,
        initialize=lambda mm, h: float(loaded_scaleup.get(int(h), 1.0)),
        default=1.0,
        mutable=False,
        doc="Representative-hour scaling factor",
    )
    model.n_in_c = pyo.Param(
        model.N,
        model.CN,
        initialize=lambda mm, n, c: int(loaded_n_in_c.get((str(n), str(c)), 0)),
        default=0,
        mutable=False,
        doc="Node in country mapping",
    )
    model.n_in_2 = pyo.Param(
        model.N,
        model.NUTS2,
        initialize=lambda mm, n, g: int(loaded_n_in_2.get((str(n), str(g)), 0)),
        default=0,
        mutable=False,
        doc="Node in NUTS2 mapping",
    )
    model.n_in_r = pyo.Param(
        model.N,
        model.RGN,
        initialize=lambda mm, n, r: int(loaded_n_in_r.get((str(n), str(r)), 0)),
        default=0,
        mutable=False,
        doc="Node in region mapping",
    )
    model.a_s = pyo.Param(
        model.A,
        model.N,
        initialize=lambda mm, a, n: int(loaded_a_s.get((str(a), str(n)), 0)),
        default=0,
        mutable=False,
        doc="Arc-start incidence a_s(a,n)",
    )
    model.a_e = pyo.Param(
        model.A,
        model.N,
        initialize=lambda mm, a, n: int(loaded_a_e.get((str(a), str(n)), 0)),
        default=0,
        mutable=False,
        doc="Arc-end incidence a_e(a,n)",
    )
    model.opp = pyo.Param(
        model.A,
        model.A,
        initialize=lambda mm, ai, ao: int(loaded_opp.get((str(ai), str(ao)), 0)),
        default=0,
        mutable=False,
        doc="Opposite-arc mapping opp(ai,ao)",
    )
    model.is_bid = pyo.Param(
        model.A,
        initialize=lambda mm, a: int(loaded_is_bid.get(str(a), 0)),
        default=0,
        mutable=False,
        doc="Arc already bidirectional flag is_bid(a)",
    )
    model.opp_arc = pyo.Param(
        model.A,
        initialize=lambda mm, a: str(loaded_opp_map.get(str(a), "")),
        default="",
        mutable=False,
        within=pyo.Any,
        doc="Representative opposite arc id for reporting",
    )
    model.is_h = pyo.Param(
        model.E,
        initialize=lambda mm, e: int(str(e).upper() == "H"),
        default=0,
        mutable=False,
        doc="Fuel classifier: hydrogen",
    )
    model.is_g = pyo.Param(
        model.E,
        initialize=lambda mm, e: int(str(e).upper() == "G"),
        default=0,
        mutable=False,
        doc="Fuel classifier: gas",
    )
    model.not_h = pyo.Param(
        model.E,
        initialize=lambda mm, e: 1 - int(str(e).upper() == "H"),
        default=1,
        mutable=False,
        doc="Fuel classifier: not hydrogen",
    )
    model.not_g = pyo.Param(
        model.E,
        initialize=lambda mm, e: 1 - int(str(e).upper() == "G"),
        default=1,
        mutable=False,
        doc="Fuel classifier: not gas",
    )
    model.dmd = pyo.Param(
        model.N,
        model.E,
        model.Y,
        model.H,
        initialize=lambda mm, n, e, y, h: float(loaded_dmd.get((str(n), str(e), int(y), int(h)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Demand dmd(n,e,y,h) loaded directly from consumption.csv",
    )
    model.dmd2 = pyo.Param(
        model.NUTS2,
        model.E,
        model.Y,
        model.H,
        initialize=lambda mm, g, e, y, h: float(loaded_dmd2.get((str(g), str(e), int(y), int(h)), 0.0)),
        default=0.0,
        mutable=False,
        doc="NUTS2 demand dmd2(nuts2,e,y,h), aggregated from dmd via n_in_2",
    )
    model.cap_p = pyo.Param(
        model.N,
        model.E,
        model.Y,
        model.H,
        initialize=lambda mm, n, e, y, h: float(loaded_cap_p.get((str(n), str(e), int(y), int(h)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Production capacity cap_p(n,e,y,h) from production.csv",
    )
    model.c_p = pyo.Param(
        model.N,
        model.E,
        model.Y,
        initialize=lambda mm, n, e, y: float(loaded_c_p.get((str(n), str(e), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Production marginal cost c_p(n,e,y) from production.csv (MC)",
    )
    model.lb_p = pyo.Param(
        model.N,
        model.E,
        model.Y,
        model.H,
        initialize=lambda mm, n, e, y, h: float(loaded_lb_p.get((str(n), str(e), int(y), int(h)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Production lower bound lb_p(n,e,y,h) from production.csv (LB)",
    )
    model.c_lr = pyo.Param(
        model.N,
        model.E,
        initialize=lambda mm, n, e: float(
            loaded_c_lr.get((str(n), str(e)), 1.0 if str(e).upper() == "G" else 9999.0)
        ),
        default=9999.0,
        mutable=False,
        doc="Regasification unit cost c_lr(n,e)",
    )
    model.ub_r = pyo.Param(
        model.N,
        model.E,
        initialize=lambda mm, n, e: float(loaded_ub_r.get((str(n), str(e)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Regasification hourly capacity upper bound ub_r(n,e)",
    )
    model.cap_a = pyo.Param(
        model.A,
        model.E,
        model.Y,
        initialize=lambda mm, a, e, y: float(loaded_cap_a.get((str(a), str(e), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Arc capacity cap_a(a,e,y)",
    )
    model.c_a = pyo.Param(
        model.A,
        model.E,
        model.Y,
        initialize=lambda mm, a, e, y: float(loaded_c_a.get((str(a), str(e), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Arc flow cost c_a(a,e,y)",
    )
    model.c_ax = pyo.Param(
        model.A,
        model.E,
        model.Y,
        initialize=lambda mm, a, e, y: float(loaded_c_ax.get((str(a), str(e), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Arc expansion investment cost c_ax(a,e,y)",
    )
    model.c_ab = pyo.Param(
        model.A,
        model.E,
        model.Y,
        initialize=lambda mm, a, e, y: float(loaded_c_ab.get((str(a), str(e), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Bidirectional variable cost c_ab(a,e,y)",
    )
    model.f_ab = pyo.Param(
        model.A,
        model.Y,
        initialize=lambda mm, a, y: float(loaded_f_ab.get((str(a), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Bidirectional fixed cost f_ab(a,y)",
    )
    model.c_ar = pyo.Param(
        model.A,
        model.E,
        model.E,
        model.Y,
        initialize=lambda mm, a, e, f, y: float(loaded_c_ar.get((str(a), str(e), str(f), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Repurposing variable cost c_ar(a,e,f,y)",
    )
    model.f_ar = pyo.Param(
        model.A,
        model.E,
        model.E,
        model.Y,
        initialize=lambda mm, a, e, f, y: float(loaded_f_ar.get((str(a), str(e), str(f), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Repurposing fixed cost f_ar(a,e,f,y)",
    )
    model.e_a = pyo.Param(
        model.A,
        model.E,
        initialize=lambda mm, a, e: float(loaded_e_a.get((str(a), str(e)), 1.0)),
        default=1.0,
        mutable=False,
        doc="Arc flow efficiency e_a(a,e)",
    )
    model.cap_we = pyo.Param(
        model.N,
        model.E,
        model.Y,
        initialize=lambda mm, n, e, y: float(loaded_cap_we.get((str(n), str(e), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Storage extraction capacity cap_we(n,e,y)",
    )
    model.cap_wi = pyo.Param(
        model.N,
        model.E,
        model.Y,
        initialize=lambda mm, n, e, y: float(loaded_cap_wi.get((str(n), str(e), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Storage injection capacity cap_wi(n,e,y)",
    )
    model.cap_ww = pyo.Param(
        model.N,
        model.E,
        model.Y,
        initialize=lambda mm, n, e, y: float(loaded_cap_ww.get((str(n), str(e), int(y)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Storage working-gas capacity cap_ww(n,e,y)",
    )
    model.c_we = pyo.Param(
        model.N,
        model.E,
        initialize=lambda mm, n, e: float(loaded_c_we.get((str(n), str(e)), float(mm.vols2[e]))),
        default=0.0,
        mutable=False,
        doc="Storage extraction cost c_we(n,e)",
    )
    model.e_w = pyo.Param(
        model.N,
        model.E,
        initialize=lambda mm, n, e: float(loaded_e_w.get((str(n), str(e)), 0.99)),
        default=0.99,
        mutable=False,
        doc="Storage cycle efficiency e_w(n,e)",
    )
    model.h2_ready = pyo.Param(
        model.N,
        model.E,
        initialize=lambda mm, n, e: float(loaded_h2_ready.get((str(n), str(e)), 0.0)),
        default=0.0,
        mutable=False,
        doc="Storage H2-ready flag/value from dat_w(n,e,'H2-ready')",
    )

    # STEP 4: Node-level variables from MGET subset
    # Decision variables:
    # Q_P(n,e,y,h) >= 0      production
    # Q_R(n,e,y,h) >= 0      regasification
    # F_A(a,e,y,h) >= 0      arc flow
    # X_A(a,e,y) >= 0        arc expansion
    # K_A(a,e,y) >= 0        arc capacity stock
    # BD(a,y) in [0,1]       bidirectional state
    # B_BD(a,y) in {0,1}     bidirectional investment decision
    # K_OPP(a,e,y) >= 0      reverse capacity use
    # K_BD(a,e,y) >= 0       capacity for variable bidirectional cost
    # Q_B(n,e,f,y,h) >= 0    energy carrier e blended into f
    # Q_E(n,e,y,h) >= 0      storage extraction
    # Q_I(n,e,y,h) >= 0      storage injection
    # Q_S(n,e,y,h) >= 0      served demand
    # ZDS(z,n,e,y,h) >= 0    nodal slack by penalty class
    # ZN2(g,e,y,h) >= 0      NUTS2 hydrogen shortage
    model.Q_P = pyo.Var(model.N, model.E, model.Y, model.H, domain=pyo.NonNegativeReals, doc="Production Q_P")
    model.Q_R = pyo.Var(model.N, model.E, model.Y, model.H, domain=pyo.NonNegativeReals, doc="Regasification Q_R")
    model.F_A = pyo.Var(model.A, model.E, model.Y, model.H, domain=pyo.NonNegativeReals, doc="Arc flow F_A")
    model.X_A = pyo.Var(model.A, model.E, model.Y, domain=pyo.NonNegativeReals, doc="Arc expansion X_A")
    model.K_A = pyo.Var(model.A, model.E, model.Y, domain=pyo.NonNegativeReals, doc="Arc capacity K_A")
    model.B_AR = pyo.Var(model.A, model.E, model.E, model.Y, domain=pyo.Binary, doc="Arc repurposing decision B_AR")
    model.K_RA = pyo.Var(model.A, model.E, model.E, model.Y, domain=pyo.NonNegativeReals, doc="Repurposed arc capacity K_RA")
    model.BD = pyo.Var(model.A, model.Y, domain=pyo.UnitInterval, doc="Bidirectional state BD")
    model.B_BD = pyo.Var(model.A, model.Y, domain=pyo.Binary, doc="Bidirectional decision B_BD")
    model.K_OPP = pyo.Var(model.A, model.E, model.Y, domain=pyo.NonNegativeReals, doc="Reversed capacity K_OPP")
    model.K_BD = pyo.Var(model.A, model.E, model.Y, domain=pyo.NonNegativeReals, doc="Bidirectional cost volume K_BD")
    model.K_W = pyo.Var(model.N, model.E, model.Y, domain=pyo.NonNegativeReals, doc="Storage working-gas stock K_W")
    model.B_WR = pyo.Var(model.N, model.E, model.E, model.Y, domain=pyo.Binary, doc="Storage repurposing decision B_WR")
    model.K_RW = pyo.Var(model.N, model.E, model.E, model.Y, domain=pyo.NonNegativeReals, doc="Repurposed storage capacity K_RW")
    model.Q_B = pyo.Var(model.N, model.E, model.E, model.Y, model.H, domain=pyo.NonNegativeReals, doc="Blending Q_B")
    model.Q_E = pyo.Var(model.N, model.E, model.Y, model.H, domain=pyo.NonNegativeReals, doc="Storage extraction Q_E")
    model.Q_I = pyo.Var(model.N, model.E, model.Y, model.H, domain=pyo.NonNegativeReals, doc="Storage injection Q_I")
    model.Q_S = pyo.Var(model.N, model.E, model.Y, model.H, domain=pyo.NonNegativeReals, doc="Sales Q_S")
    model.ZDS = pyo.Var(model.Z, model.N, model.E, model.Y, model.H, domain=pyo.NonNegativeReals, doc="Penalty slack ZDS")
    model.ZN2 = pyo.Var(model.NUTS2, model.E, model.Y, model.H, domain=pyo.NonNegativeReals, doc="NUTS2 shortage ZN2")

    # STEP 5: Constraints (node production + consumption only)
    # p_cap(n,e,y,h):
    #   if cap_p(n,e,y,h) <= 0 => Q_P(n,e,y,h) = 0
    #   else                    Q_P(n,e,y,h) + sum_f Q_B(n,e,f,y,h) <= cap_p(n,e,y,h)
    model.p_cap = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, y, h: (
            mm.Q_P[n, e, y, h] + sum(mm.Q_B[n, e, f, y, h] for f in mm.E) == 0.0
            if pyo.value(mm.cap_p[n, e, y, h]) <= 0.0
            else mm.Q_P[n, e, y, h] + sum(mm.Q_B[n, e, f, y, h] for f in mm.E) <= mm.cap_p[n, e, y, h]
        ),
        doc="Production capacity (GAMS p_cap)",
    )
    # p_min(n,e,y,h):
    #   if lb_p(n,e,y,h) > 0 => Q_P(n,e,y,h) + sum_f Q_B(n,e,f,y,h) >= lb_p(n,e,y,h)
    model.p_min = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, y, h: (
            pyo.Constraint.Skip
            if pyo.value(mm.lb_p[n, e, y, h]) <= 0.0
            else mm.Q_P[n, e, y, h] + sum(mm.Q_B[n, e, f, y, h] for f in mm.E) >= mm.lb_p[n, e, y, h]
        ),
        doc="Production lower bound (GAMS p_min)",
    )
    # Regasification hourly bound (GAMS parity subset of Q_R.up):
    #   Q_R(n,e,y,h) <= ub_r(n,e)
    model.r_cap = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, y, h: mm.Q_R[n, e, y, h] <= mm.ub_r[n, e],
        doc="Regasification upper bound (Q_R.up subset)",
    )

    first_y = y_order[0] if len(y_order) > 0 else None
    y_prev_map = {y_order[idx]: y_order[idx - 1] for idx in range(1, len(y_order))}

    # K_A.fx(a,e,y)$(ord(y)=1) = cap_a(a,e,y)
    model.k_a_init = pyo.Constraint(
        model.A,
        model.E,
        model.Y,
        rule=lambda mm, a, e, y: (
            pyo.Constraint.Skip if first_y is None or int(y) != int(first_y) else mm.K_A[a, e, y] == mm.cap_a[a, e, y]
        ),
        doc="Initial arc capacity stock (GAMS K_A.fx ord(y)=1)",
    )

    # K_W.fx(n,e,y)$(ORD(y)=1) = cap_ww(n,e,y)
    model.k_w_init = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        rule=lambda mm, n, e, y: (
            pyo.Constraint.Skip if first_y is None or int(y) != int(first_y) else mm.K_W[n, e, y] == mm.cap_ww[n, e, y]
        ),
        doc="Initial storage working-gas stock (GAMS K_W.fx ord(y)=1)",
    )

    # ar_cap(a,e,y)$(ord(y)>1): K_A(a,e,y) = sum_f K_RA(a,f,e,y) + sum(y2$ypred(y2,y), X_A(a,e,y2))
    model.ar_cap = pyo.Constraint(
        model.A,
        model.E,
        model.Y,
        rule=lambda mm, a, e, y: (
            pyo.Constraint.Skip
            if first_y is None or int(y) == int(first_y)
            else mm.K_A[a, e, y]
            == sum(mm.K_RA[a, f, e, y] for f in mm.E)
            + sum(mm.X_A[a, e, y2] for y2 in mm.Y if pyo.value(mm.ypred[y2, y]) == 1)
        ),
        doc="Arc capacity with repurposing and prior-year expansion (GAMS ar_cap)",
    )
    # wr_cap(n,e,y)$(ord(y)>1): K_W(n,e,y) = sum_f K_RW(n,f,e,y)
    model.wr_cap = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        rule=lambda mm, n, e, y: (
            pyo.Constraint.Skip
            if first_y is None or int(y) == int(first_y)
            else mm.K_W[n, e, y] == sum(mm.K_RW[n, f, e, y] for f in mm.E)
        ),
        doc="Storage capacity with repurposing (GAMS wr_cap)",
    )

    # a_lim(a,e,y,h): F_A(a,e,y,h)*vola2(e) <= K_A(a,e,y) + K_OPP(a,e,y)
    model.a_lim = pyo.Constraint(
        model.A,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, a, e, y, h: mm.F_A[a, e, y, h] * mm.vola2[e] <= mm.K_A[a, e, y] + mm.K_OPP[a, e, y],
        doc="Arc flow capacity (GAMS a_lim with K_A+K_OPP)",
    )
    model.a_opp1 = pyo.Constraint(
        model.A,
        model.E,
        model.Y,
        rule=lambda mm, a, e, y: mm.K_OPP[a, e, y] <= mm.BD[a, y] * mm.bigM,
        doc="Reverse flow allowed only with bidirectional state (GAMS a_opp1)",
    )
    model.a_opp2 = pyo.Constraint(
        model.A,
        model.E,
        model.Y,
        rule=lambda mm, a, e, y: mm.K_OPP[a, e, y] <= sum(mm.opp[ao, a] * mm.K_A[ao, e, y] for ao in mm.A),
        doc="Reverse flow limited by opposite arc capacity (GAMS a_opp2)",
    )
    model.k_bd_fix_is_bid = pyo.Constraint(
        model.A,
        model.E,
        model.Y,
        rule=lambda mm, a, e, y: (
            mm.K_BD[a, e, y] == 0.0 if pyo.value(mm.is_bid[a]) == 1 else pyo.Constraint.Skip
        ),
        doc="Fix K_BD=0 for already bidirectional arcs (GAMS K_BD.fx $is_bid)",
    )
    model.bd_cost = pyo.Constraint(
        model.A,
        model.E,
        model.Y,
        model.Y,
        rule=lambda mm, a, e, y, y2: (
            pyo.Constraint.Skip
            if pyo.value(mm.is_bid[a]) == 1 or pyo.value(mm.yscai[y2, y]) != 1
            else mm.K_BD[a, e, y] >= mm.K_OPP[a, e, y2] - (1.0 - mm.B_BD[a, y]) * mm.bigM
        ),
        doc="Bidirectional variable-cost volume lower bound (GAMS bd_cost)",
    )
    model.bd_fix_is_bid = pyo.Constraint(
        model.A,
        model.Y,
        rule=lambda mm, a, y: (
            mm.BD[a, y] == 1.0 if pyo.value(mm.is_bid[a]) == 1 else pyo.Constraint.Skip
        ),
        doc="Fix BD=1 for already bidirectional arcs (GAMS BD.fx $is_bid)",
    )
    model.bidir = pyo.Constraint(
        model.A,
        model.Y,
        rule=lambda mm, a, y: (
            pyo.Constraint.Skip
            if pyo.value(mm.is_bid[a]) == 1
            else mm.BD[a, y]
            <= mm.B_BD[a, y] + sum(mm.BD[a, y2] for y2 in mm.Y if pyo.value(mm.ypred[y2, y]) == 1)
        ),
        doc="Bidirectional state propagation (GAMS bidir)",
    )
    # sos_a(a,e,y)$(ord(y)>1): sum_f B_AR(a,e,f,y) = 1
    model.sos_a = pyo.Constraint(
        model.A,
        model.E,
        model.Y,
        rule=lambda mm, a, e, y: (
            pyo.Constraint.Skip
            if first_y is None or int(y) == int(first_y)
            else sum(mm.B_AR[a, e, f, y] for f in mm.E) == 1.0
        ),
        doc="Single arc repurposing destination (GAMS sos_a)",
    )
    # sos_w(n,e,y)$(ord(y)>1): sum_f B_WR(n,e,f,y) = 1
    model.sos_w = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        rule=lambda mm, n, e, y: (
            pyo.Constraint.Skip
            if first_y is None or int(y) == int(first_y)
            else sum(mm.B_WR[n, e, f, y] for f in mm.E) == 1.0
        ),
        doc="Single storage repurposing destination (GAMS sos_w)",
    )
    # B_AR.fx(a,e,f,y)$(ORD(y)=1)=0
    model.b_ar_fix_first = pyo.Constraint(
        model.A,
        model.E,
        model.E,
        model.Y,
        rule=lambda mm, a, e, f, y: (
            pyo.Constraint.Skip if first_y is None or int(y) != int(first_y) else mm.B_AR[a, e, f, y] == 0.0
        ),
        doc="Fix B_AR(a,e,f,firstY)=0 to enforce no first-period repurposing",
    )
    # K_RA.fx(a,e,f,y)$(ORD(y)=1)=0
    model.k_ra_fix_first = pyo.Constraint(
        model.A,
        model.E,
        model.E,
        model.Y,
        rule=lambda mm, a, e, f, y: (
            pyo.Constraint.Skip if first_y is None or int(y) != int(first_y) else mm.K_RA[a, e, f, y] == 0.0
        ),
        doc="Fix K_RA(a,e,f,firstY)=0 (GAMS first-period rule)",
    )
    # B_WR.fx(n,e,f,y)$(ORD(y)=1)=0
    model.b_wr_fix_first = pyo.Constraint(
        model.N,
        model.E,
        model.E,
        model.Y,
        rule=lambda mm, n, e, f, y: (
            pyo.Constraint.Skip if first_y is None or int(y) != int(first_y) else mm.B_WR[n, e, f, y] == 0.0
        ),
        doc="Fix B_WR(n,e,f,firstY)=0 to enforce no first-period repurposing",
    )
    # K_RW.fx(n,e,f,y)$(ORD(y)=1)=0
    model.k_rw_fix_first = pyo.Constraint(
        model.N,
        model.E,
        model.E,
        model.Y,
        rule=lambda mm, n, e, f, y: (
            pyo.Constraint.Skip if first_y is None or int(y) != int(first_y) else mm.K_RW[n, e, f, y] == 0.0
        ),
        doc="Fix K_RW(n,e,f,firstY)=0 (GAMS first-period rule)",
    )
    # K_W.fx(n,'G',y)$(dat_w(n,'G','H2-ready')<=0)=cap_ww(n,'G',y)
    model.k_w_fix_h2_ready = pyo.Constraint(
        model.N,
        model.Y,
        rule=lambda mm, n, y: (
            mm.K_W[n, "G", y] == mm.cap_ww[n, "G", y]
            if "G" in mm.E and pyo.value(mm.h2_ready[n, "G"]) <= 0.0
            else pyo.Constraint.Skip
        ),
        doc="Fix gas storage stock when not H2-ready (GAMS K_W.fx by H2-ready)",
    )
    # bil_a1(a,e,y)$(ord(y)>1): sum_f K_RA(a,e,f,y) = sum(y2$ypred(y2,y), K_A(a,e,y2))
    model.bil_a1 = pyo.Constraint(
        model.A,
        model.E,
        model.Y,
        rule=lambda mm, a, e, y: (
            pyo.Constraint.Skip
            if first_y is None or int(y) == int(first_y)
            else sum(mm.K_RA[a, e, f, y] for f in mm.E)
            == sum(mm.K_A[a, e, y2] for y2 in mm.Y if pyo.value(mm.ypred[y2, y]) == 1)
        ),
        doc="Repurposed arc capacity conservation (GAMS bil_a1)",
    )
    # bil_w1(n,e,y)$(ord(y)>1): sum_f K_RW(n,e,f,y) = sum(y2$ypred(y2,y), K_W(n,e,y2))
    model.bil_w1 = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        rule=lambda mm, n, e, y: (
            pyo.Constraint.Skip
            if first_y is None or int(y) == int(first_y)
            else sum(mm.K_RW[n, e, f, y] for f in mm.E)
            == sum(mm.K_W[n, e, y2] for y2 in mm.Y if pyo.value(mm.ypred[y2, y]) == 1)
        ),
        doc="Repurposed storage capacity conservation (GAMS bil_w1)",
    )
    # bil_a2(a,e,f,y)$(ord(y)>1): K_RA(a,e,f,y) <= B_AR(a,e,f,y)*bigM
    model.bil_a2 = pyo.Constraint(
        model.A,
        model.E,
        model.E,
        model.Y,
        rule=lambda mm, a, e, f, y: (
            pyo.Constraint.Skip
            if first_y is None or int(y) == int(first_y)
            else mm.K_RA[a, e, f, y] <= mm.B_AR[a, e, f, y] * mm.bigM
        ),
        doc="Arc repurposing big-M link (GAMS bil_a2)",
    )
    # bil_w2(n,e,f,y)$(ord(y)>1): K_RW(n,e,f,y) <= B_WR(n,e,f,y)*bigM
    model.bil_w2 = pyo.Constraint(
        model.N,
        model.E,
        model.E,
        model.Y,
        rule=lambda mm, n, e, f, y: (
            pyo.Constraint.Skip
            if first_y is None or int(y) == int(first_y)
            else mm.K_RW[n, e, f, y] <= mm.B_WR[n, e, f, y] * mm.bigM
        ),
        doc="Storage repurposing big-M link (GAMS bil_w2)",
    )
    # Storage flow bounds (GAMS subset of Q_E.up / Q_I.up assignments):
    #   Q_E(n,e,y,h) <= cap_we(n,e,y)
    #   Q_I(n,e,y,h) <= cap_wi(n,e,y)
    model.w_extr_cap = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, y, h: mm.Q_E[n, e, y, h] <= mm.cap_we[n, e, y],
        doc="Storage extraction upper bound",
    )
    model.w_inj_cap = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, y, h: mm.Q_I[n, e, y, h] <= mm.cap_wi[n, e, y],
        doc="Storage injection upper bound",
    )
    # dmd_n3(n,e,y,h) for not_h(e) and dmd(n,e,y,h) > 0:
    #   Q_S(n,e,y,h) = dmd(n,e,y,h) - ZDS(ZD2,n,e,y,h)
    model.dmd_n3 = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, y, h: (
            pyo.Constraint.Skip
            if z_dmd is None or pyo.value(mm.not_h[e]) != 1 or pyo.value(mm.dmd[n, e, y, h]) <= 0.0
            else mm.Q_S[n, e, y, h] == mm.dmd[n, e, y, h] - mm.ZDS[z_dmd, n, e, y, h]
        ),
        doc="NUTS3 demand for non-hydrogen (GAMS dmd_n3)",
    )
    # If non-hydrogen demand is zero/non-positive, fix served demand to zero.
    model.qs_zero_nonh = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, y, h: (
            pyo.Constraint.Skip
            if pyo.value(mm.not_h[e]) != 1 or pyo.value(mm.dmd[n, e, y, h]) > 0.0
            else mm.Q_S[n, e, y, h] == 0.0
        ),
        doc="Fix Q_S=0 for non-hydrogen when demand is non-positive",
    )
    # If non-hydrogen demand is zero/non-positive, fix ZDS(ZD2) to zero.
    model.zd2_zero_nonh = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, y, h: (
            pyo.Constraint.Skip
            if z_dmd is None or pyo.value(mm.not_h[e]) != 1 or pyo.value(mm.dmd[n, e, y, h]) > 0.0
            else mm.ZDS[z_dmd, n, e, y, h] == 0.0
        ),
        doc="Fix ZDS(ZD2)=0 for non-hydrogen when demand is non-positive",
    )
    # Q_B.fx(n,e,f,y,h)$(not_h(e) OR not_g(f)) = 0
    model.qb_fix_type = pyo.Constraint(
        model.N,
        model.E,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, f, y, h: (
            mm.Q_B[n, e, f, y, h] == 0.0
            if pyo.value(mm.not_h[e]) == 1 or pyo.value(mm.not_g[f]) == 1
            else pyo.Constraint.Skip
        ),
        doc="Fix Q_B=0 unless hydrogen blended into gas (GAMS Q_B.fx type)",
    )
    # Q_B.fx(n,e,f,y,h)$(cap_p(n,e,y,h)<=0) = 0
    model.qb_fix_cap = pyo.Constraint(
        model.N,
        model.E,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, f, y, h: (
            mm.Q_B[n, e, f, y, h] == 0.0
            if pyo.value(mm.cap_p[n, e, y, h]) <= 0.0
            else pyo.Constraint.Skip
        ),
        doc="Fix Q_B=0 when source production capacity is non-positive (GAMS Q_B.fx cap)",
    )
    # Q_B.fx(n,e,e,y,h) = 0
    model.qb_fix_same = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, y, h: mm.Q_B[n, e, e, y, h] == 0.0,
        doc="Fix Q_B=0 for same carrier blending (GAMS Q_B.fx e=e)",
    )
    # max_bl(n,f,e,y,h)$(is_h(f) AND is_g(e) AND cap_p(n,f,y,h)>0)..
    #   Q_B(n,f,e,y,h) <= ub_bl(f,e)*(Q_S(n,e,y,h)+sum(a$a_s(a,n),F_A(a,e,y,h))+Q_I(n,e,y,h))
    model.max_bl = pyo.Constraint(
        model.N,
        model.E,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, f, e, y, h: (
            pyo.Constraint.Skip
            if pyo.value(mm.is_h[f]) != 1 or pyo.value(mm.is_g[e]) != 1 or pyo.value(mm.cap_p[n, f, y, h]) <= 0.0
            else mm.Q_B[n, f, e, y, h]
            <= mm.ub_bl[f, e]
            * (mm.Q_S[n, e, y, h] + sum(mm.F_A[a, e, y, h] for a in mm.A if pyo.value(mm.a_s[a, n]) == 1) + mm.Q_I[n, e, y, h])
        ),
        doc="Blending upper share limit (GAMS max_bl)",
    )
    # dmd_n2(nuts2,e,y,h) for is_h(e) and dmd2(nuts2,e,y,h) > 0:
    #   sum_{n in N(g)} Q_S(n,e,y,h) = dmd2(g,e,y,h) - ZN2(g,e,y,h)
    model.dmd_n2 = pyo.Constraint(
        model.NUTS2,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, g, e, y, h: (
            pyo.Constraint.Skip
            if pyo.value(mm.is_h[e]) != 1 or pyo.value(mm.dmd2[g, e, y, h]) <= 0.0
            else sum(mm.Q_S[n, e, y, h] for n in mm.N if pyo.value(mm.n_in_2[n, g]) == 1)
            == mm.dmd2[g, e, y, h] - mm.ZN2[g, e, y, h]
        ),
        doc="NUTS2 hydrogen demand (GAMS dmd_n2)",
    )
    # mb(n,e,y,h) flow-only subset with arcs (no blending):
    #   Q_P + sum(a$a_e(a,n),F_A*e_a) + Q_E + Q_R + sum_f Q_B(n,f,e) = Q_S + sum(a$a_s(a,n),F_A) + Q_I
    model.mb_node = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        model.H,
        rule=lambda mm, n, e, y, h: mm.Q_P[n, e, y, h]
        + sum(mm.F_A[a, e, y, h] * mm.e_a[a, e] for a in mm.A if pyo.value(mm.a_e[a, n]) == 1)
        + mm.Q_E[n, e, y, h]
        + mm.Q_R[n, e, y, h]
        + sum(mm.Q_B[n, f, e, y, h] for f in mm.E)
        == mm.Q_S[n, e, y, h]
        + sum(mm.F_A[a, e, y, h] for a in mm.A if pyo.value(mm.a_s[a, n]) == 1)
        + mm.Q_I[n, e, y, h],
        doc="Node balance subset with arc flows and blending",
    )
    # w_lim(n,e,y): sum_h scaleUp(h)*Q_E(n,e,y,h)*vols2(e) <= K_W(n,e,y)
    model.w_lim = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        rule=lambda mm, n, e, y: sum(mm.scaleUp[h] * mm.Q_E[n, e, y, h] for h in mm.H) * mm.vols2[e]
        <= mm.K_W[n, e, y],
        doc="Storage working-gas limit with repurposed stock (GAMS w_lim)",
    )
    # w_cyc(n,e,y): sum_h scaleUp(h)*Q_E = e_w(n,e)*sum_h scaleUp(h)*Q_I
    model.w_cyc = pyo.Constraint(
        model.N,
        model.E,
        model.Y,
        rule=lambda mm, n, e, y: sum(mm.scaleUp[h] * mm.Q_E[n, e, y, h] for h in mm.H)
        == mm.e_w[n, e] * sum(mm.scaleUp[h] * mm.Q_I[n, e, y, h] for h in mm.H),
        doc="Storage cycle balance",
    )

    # STEP 6: Objective (obj.. subset of MGET objective available today)
    # obj..
    #   TC = sum_{n,e,y,h} r(y)*scaleUp(h) * [ c_p(n,e,y)*Q_P(n,e,y,h)
    #                                        + c_lr(n,e)*Q_R(n,e,y,h)
    #                                        + c_we(n,e)*Q_E(n,e,y,h)
    #                                        + c_z('ZD2',e)*ZDS('ZD2',n,e,y,h) ]
    #      + sum_{nuts2,e,y,h} r(y)*scaleUp(h) * c_z('ZD2',e)*ZN2(nuts2,e,y,h)
    model.obj_total_cost = pyo.Objective(
        expr=sum(
            model.r[y] * model.scaleUp[h] * (
                model.c_p[n, e, y] * model.Q_P[n, e, y, h]
                + model.c_lr[n, e] * model.Q_R[n, e, y, h]
                + model.c_we[n, e] * model.Q_E[n, e, y, h]
            )
            for n in model.N
            for e in model.E
            for y in model.Y
            for h in model.H
        )
        + sum(
            model.r[y] * model.scaleUp[h] * model.c_z[z, e] * model.ZDS[z, n, e, y, h]
            for z in model.Z
            for n in model.N
            for e in model.E
            for y in model.Y
            for h in model.H
        )
        + sum(
            model.r[y] * model.EOH[y] * model.c_ax[a, e, y] * model.X_A[a, e, y]
            for a in model.A
            for e in model.E
            for y in model.Y
        )
        + sum(
            model.r[y] * model.EOH[y] * model.f_ab[a, y] * model.B_BD[a, y]
            for a in model.A
            for y in model.Y
        )
        + sum(
            model.r[y] * model.EOH[y] * model.c_ab[a, e, y] * model.K_BD[a, e, y]
            for a in model.A
            for e in model.E
            for y in model.Y
        )
        + sum(
            model.r[y] * model.EOH[y] * model.f_ar[a, e, f, y] * model.B_AR[a, e, f, y]
            for a in model.A
            for e in model.E
            for f in model.E
            for y in model.Y
        )
        + sum(
            model.r[y] * model.EOH[y] * model.c_ar[a, e, f, y] * model.K_RA[a, e, f, y]
            for a in model.A
            for e in model.E
            for f in model.E
            for y in model.Y
        )
        + sum(
            model.r[y] * model.scaleUp[h] * model.c_a[a, e, y] * model.F_A[a, e, y, h]
            for a in model.A
            for e in model.E
            for y in model.Y
            for h in model.H
        )
        + sum(
            model.r[y] * model.scaleUp[h] * model.c_bl[e, f] * model.Q_B[n, e, f, y, h]
            for n in model.N
            for e in model.E
            for f in model.E
            for y in model.Y
            for h in model.H
        )
        + sum(
            model.r[y]
            * model.scaleUp[h]
            * (0.0 if z_dmd is None else model.c_z[z_dmd, e] * model.ZN2[g, e, y, h])
            for g in model.NUTS2
            for e in model.E
            for y in model.Y
            for h in model.H
        ),
        sense=pyo.minimize,
        doc="Total cost from node production/consumption subset",
    )

    # TC linking equation for compatibility with report/check scripts:
    #   TC = objective expression
    model.TC = pyo.Var(domain=pyo.Reals)
    model.tc_link_con = pyo.Constraint(expr=model.TC == model.obj_total_cost.expr)
    model.is_built = pyo.Param(initialize=1)

    return model


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--show-cz"]
    show_cz = "--show-cz" in sys.argv[1:]

    other_path = Path(args[0]).resolve() if len(args) > 0 else DEFAULT_OTHER_CSV
    loaded = load_inputs(other_path=other_path)
    model = build_base_model_with_cz(loaded)

    print("Model created")
    print("|Z| =", len(list(model.Z)))
    print("|E| =", len(list(model.E)))
    print("|Y| =", len(list(model.Y)))
    print("|H| =", len(list(model.H)))
    print("|N| =", len(list(model.N)))
    print("|CN| =", len(list(model.CN)))
    print("|NUTS2| =", len(list(model.NUTS2)))
    print("|RGN| =", len(list(model.RGN)))
    print("bigM =", pyo.value(model.bigM))
    print("yearstep =", pyo.value(model.yearstep))
    print("discRate =", pyo.value(model.discRate))
    print("lossMax =", pyo.value(model.lossMax))
    print("vola2 sample =", {e: pyo.value(model.vola2[e]) for e in model.E})
    print("vols2 sample =", {e: pyo.value(model.vols2[e]) for e in model.E})
    print("nonzero dmd entries =", sum(1 for idx in model.dmd if pyo.value(model.dmd[idx]) != 0.0))
    print("nonzero dmd2 entries =", sum(1 for idx in model.dmd2 if pyo.value(model.dmd2[idx]) != 0.0))
    print("nonzero cap_p entries =", sum(1 for idx in model.cap_p if pyo.value(model.cap_p[idx]) != 0.0))
    print("nonzero ub_r entries =", sum(1 for idx in model.ub_r if pyo.value(model.ub_r[idx]) != 0.0))
    print("nonzero cap_we entries =", sum(1 for idx in model.cap_we if pyo.value(model.cap_we[idx]) != 0.0))
    print("nonzero cap_wi entries =", sum(1 for idx in model.cap_wi if pyo.value(model.cap_wi[idx]) != 0.0))
    print("nonzero cap_ww entries =", sum(1 for idx in model.cap_ww if pyo.value(model.cap_ww[idx]) != 0.0))
    print("objective expr built =", model.obj_total_cost is not None)
    if show_cz:
        print("c_z entries:")
        for z in model.Z:
            for e in model.E:
                print(f"  c_z[{z},{e}] = {pyo.value(model.c_z[z, e])}")

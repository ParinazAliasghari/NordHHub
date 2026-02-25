from __future__ import annotations

from typing import Dict, Tuple, Iterable, Optional
import pandas as pd

from .utils import _clean_str, _to_float


PenaltyKey = Tuple[str, str]
PenaltyLookup = Dict[PenaltyKey, float]


def norm(value) -> str:
    """Normalize text values and convert None/empty to ''."""
    return _clean_str(value) or ""


def _prepare_dat_o(dat_o: pd.DataFrame) -> pd.DataFrame:
    """
    Return a cleaned copy with normalized parameter/index columns and numeric value.
    Expected columns: param, indx1, indx2, value
    """
    df = dat_o.copy()
    df["param"] = df["param"].map(norm).str.lower()
    df["indx1"] = df["indx1"].map(norm)
    df["indx2"] = df["indx2"].map(norm)
    df["value"] = df["value"].map(_to_float)
    return df


def build_penalty_lookup(dat_o: pd.DataFrame) -> PenaltyLookup:
    """
    Build lookup for penalty rows:
      key   -> (z, e) == (indx1, indx2)
      value -> numeric penalty
    Accepts both 'penalty' and misspelled 'penality'.
    """
    df = _prepare_dat_o(dat_o)
    penalties = df[df["param"].isin(["penalty", "penality"])]

    lookup: PenaltyLookup = {}
    for z, e, value in penalties[["indx1", "indx2", "value"]].itertuples(index=False, name=None):
        lookup[(z, e)] = value
    return lookup


def penalty_value(lookup: PenaltyLookup, z: str, e: str) -> float:
    """
    GAMS-equivalent fallback chain for Penalty(z,e):
      1) val = Penalty(z,e)
      2) if val <= 0: val = Penalty(z,'')
      3) if val <= 0: val = Penalty('','')
      4) if still missing: 0.0
    """
    z = norm(z)
    e = norm(e)

    val = float(lookup.get((z, e), 0.0))
    if val <= 0:
        val = float(lookup.get((z, ""), 0.0))
    if val <= 0:
        val = float(lookup.get(("", ""), 0.0))
    return float(val)


def build_c_z(
    dat_o: pd.DataFrame,
    *,
    z_values: Optional[Iterable[str]] = None,
    e_values: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """
    Build c_z table with columns: z, e, c_z

    Domain behavior:
      - if z_values/e_values provided, use those (recommended for full GAMS parity)
      - otherwise infer from dat_o penalty rows (non-empty indices)
    """
    df = _prepare_dat_o(dat_o)
    penalty_rows = df[df["param"].isin(["penalty", "penality"])]

    if z_values is None:
        z_domain = sorted({z for z in penalty_rows["indx1"] if z != ""})
    else:
        z_domain = sorted({norm(z) for z in z_values if norm(z) != ""})

    if e_values is None:
        e_domain = sorted({e for e in penalty_rows["indx2"] if e != ""}) or [""]
    else:
        e_domain = sorted({norm(e) for e in e_values if norm(e) != ""}) or [""]

    lookup = build_penalty_lookup(df)

    rows = []
    for z in z_domain:
        for e in e_domain:
            rows.append({"z": z, "e": e, "c_z": penalty_value(lookup, z, e)})

    return pd.DataFrame(rows, columns=["z", "e", "c_z"])


def build_scalar_param(dat_o: pd.DataFrame, param_name: str) -> float:
    """
    Build scalar parameter from dat_o(param_name).

    Rules:
      - read rows where param == param_name
      - ignore indx1 / indx2
      - if multiple rows exist, use first strictly positive value
      - if missing or non-positive, return 0.0
    """
    df = _prepare_dat_o(dat_o)
    rows = df[df["param"] == norm(param_name).lower()]

    for value in rows["value"].tolist():
        v = float(value)
        if v > 0:
            return v

    return 0.0


def build_bigM(dat_o: pd.DataFrame) -> float:
    """
    Build scalar bigM from dat_o('bigM').

    Rules:
      - read rows where param == 'bigm'
      - ignore indx1 / indx2
      - if multiple rows exist, use first strictly positive value
      - if missing or non-positive, return 0.0
    """
    return build_scalar_param(dat_o, "bigm")


def build_yearstep(dat_o: pd.DataFrame) -> float:
    """
    Build scalar yearstep from dat_o('yearstep').

    Rules:
      - read rows where param == 'yearstep'
      - ignore indx1 / indx2
      - if multiple rows exist, use first strictly positive value
      - if missing or non-positive, return 0.0
    """
    return build_scalar_param(dat_o, "yearstep")


def build_disc_rate(dat_o: pd.DataFrame, default: float = 0.02) -> float:
    """
    Build scalar discount rate from dat_o('DiscRate').

    Rules:
      - read rows where param == 'discrate'
      - ignore indx1 / indx2
      - if multiple rows exist, use first strictly positive value
      - if missing or non-positive, return default (0.02)
    """
    value = build_scalar_param(dat_o, "discrate")
    if value > 0:
        return value
    return float(default)


def build_vola2(
    dat_o: pd.DataFrame,
    *,
    e_values: Optional[Iterable[str]] = None,
) -> Dict[str, float]:
    """
    Build vola2(e) map (energy-to-arc-volume conversion).

    GAMS parity:
      vola2(e)=1;
      vola2(e)$dat_o('vola2',e,'')=dat_o('vola2',e,'');
    """
    df = _prepare_dat_o(dat_o)
    rows = df[df["param"] == "vola2"]

    if e_values is None:
        e_domain = sorted({e for e in rows["indx1"] if e != ""})
    else:
        e_domain = sorted({norm(e) for e in e_values if norm(e) != ""})

    result: Dict[str, float] = {e: 1.0 for e in e_domain}

    for e, value in rows[["indx1", "value"]].itertuples(index=False, name=None):
        if e == "":
            continue
        v = float(value)
        if v != 0:
            result[e] = v

    return result


def build_vols2(
    dat_o: pd.DataFrame,
    *,
    e_values: Optional[Iterable[str]] = None,
) -> Dict[str, float]:
    """
    Build vols2(e) map (energy-to-storage-volume conversion).

    GAMS parity:
      vols2(e)=1;
      vols2(e)$dat_o('vols2',e,'')=dat_o('vols2',e,'');
    """
    df = _prepare_dat_o(dat_o)
    rows = df[df["param"] == "vols2"]

    if e_values is None:
        e_domain = sorted({e for e in rows["indx1"] if e != ""})
    else:
        e_domain = sorted({norm(e) for e in e_values if norm(e) != ""})

    result: Dict[str, float] = {e: 1.0 for e in e_domain}

    for e, value in rows[["indx1", "value"]].itertuples(index=False, name=None):
        if e == "":
            continue
        v = float(value)
        if v != 0:
            result[e] = v

    return result


def _build_pair_param_with_global_default(
    dat_o: pd.DataFrame,
    *,
    param_name: str,
    e_values: Optional[Iterable[str]] = None,
) -> Dict[Tuple[str, str], float]:
    """Build pair parameter p(e,f) with GAMS-style global default fallback."""
    df = _prepare_dat_o(dat_o)
    rows = df[df["param"] == norm(param_name).lower()]

    if e_values is None:
        e_domain = sorted({e for e in rows["indx1"] if e != ""} | {f for f in rows["indx2"] if f != ""})
    else:
        e_domain = sorted({norm(e) for e in e_values if norm(e) != ""})

    default_value = 0.0
    default_rows = rows[(rows["indx1"] == "") & (rows["indx2"] == "")]
    for value in default_rows["value"].tolist():
        default_value = float(value)
        break

    lookup: Dict[Tuple[str, str], float] = {}
    for e, f, value in rows[["indx1", "indx2", "value"]].itertuples(index=False, name=None):
        lookup[(e, f)] = float(value)

    result: Dict[Tuple[str, str], float] = {}
    for e in e_domain:
        for f in e_domain:
            val = float(lookup.get((e, f), 0.0))
            if val <= 0:
                val = float(default_value)
            result[(e, f)] = float(val)

    return result


def build_c_bl(
    dat_o: pd.DataFrame,
    *,
    e_values: Optional[Iterable[str]] = None,
) -> Dict[Tuple[str, str], float]:
    """
    Build c_bl(e,f) from dat_o('BlendCost',e,f).

    GAMS parity:
      dat_o('BlendCost',e,f)$(dat_o('BlendCost',e,f)<=0)=dat_o('BlendCost','','');
      c_bl(e,f)=dat_o('BlendCost',e,f);
    """
    return _build_pair_param_with_global_default(dat_o, param_name="blendcost", e_values=e_values)


def build_ub_bl(
    dat_o: pd.DataFrame,
    *,
    e_values: Optional[Iterable[str]] = None,
) -> Dict[Tuple[str, str], float]:
    """
    Build ub_bl(e,f) from dat_o('BlendLim',e,f).

    GAMS parity:
      dat_o('BlendLim',e,f)$(dat_o('BlendLim',e,f)<=0)=dat_o('BlendLim','','');
      ub_bl(e,f)=dat_o('BlendLim',e,f);
    """
    return _build_pair_param_with_global_default(dat_o, param_name="blendlim", e_values=e_values)


def build_loss_max(dat_o: pd.DataFrame, default: float = 0.0) -> float:
    """
    Build LossMax scalar from dat_o('LossMax','','').

    Used in GAMS efficiency expression, e.g. max(1-LossMax, ...).
    """
    value = build_scalar_param(dat_o, "lossmax")
    if value > 0:
        return value
    return float(default)
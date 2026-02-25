from __future__ import annotations

from pathlib import Path
from typing import Any
import warnings

import pandas as pd

from .param_table import (
    build_c_z,
    build_bigM,
    build_yearstep,
    build_disc_rate,
    build_vola2,
    build_vols2,
    build_c_bl,
    build_ub_bl,
    build_loss_max,
)


REQUIRED_O_COLUMNS = {"param", "indx1", "indx2", "value"}
DEFAULT_OTHER_CSV = Path(__file__).resolve().parents[2] / "data" / "scenario1" / "other.csv"
DEFAULT_TIMESERIES_CSV = Path(__file__).resolve().parents[2] / "data" / "scenario1" / "timeseries.csv"
DEFAULT_NODES_CSV = Path(__file__).resolve().parents[2] / "data" / "scenario1" / "nodes.csv"
DEFAULT_ARCS_CSV = Path(__file__).resolve().parents[2] / "data" / "scenario1" / "arcs.csv"
DEFAULT_REGAS_CSV = Path(__file__).resolve().parents[2] / "data" / "scenario1" / "regasification.csv"
DEFAULT_STORAGE_CSV = Path(__file__).resolve().parents[2] / "data" / "scenario1" / "storage.csv"
DEPRECATED_O_WARNING = "DEPRECATED: o.csv detected; please rename to other.csv"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(col).strip().lower() for col in out.columns]
    return out


def _resolve_other_csv_path(path: Path) -> Path:
    candidate = Path(path).resolve()

    if candidate.is_dir():
        other_candidate = candidate / "other.csv"
        legacy_candidate = candidate / "o.csv"
        if other_candidate.exists():
            return other_candidate
        if legacy_candidate.exists():
            warnings.warn(DEPRECATED_O_WARNING)
            return legacy_candidate
        return other_candidate

    if candidate.name.lower() == "other.csv":
        if candidate.exists():
            return candidate
        legacy_candidate = candidate.with_name("o.csv")
        if legacy_candidate.exists():
            warnings.warn(DEPRECATED_O_WARNING)
            return legacy_candidate
        return candidate

    if candidate.name.lower() == "o.csv":
        warnings.warn(DEPRECATED_O_WARNING)
        return candidate

    return candidate


def load_o_csv(path: Path) -> pd.DataFrame:
    """Load other.csv (with legacy o.csv fallback resolved upstream) and validate required columns."""
    df = _normalize_columns(pd.read_csv(path))

    missing = REQUIRED_O_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")

    return df


def load_timeseries_csv(path: Path) -> pd.DataFrame:
    """
    Load optional timeseries.csv.

    Expected columns (after normalization):
      - y (required)
      - h (required)
      - scaleup (optional)
    Accepts aliases: year->y, hour->h, scale_up->scaleup.
    """
    if not path.exists():
        return pd.DataFrame(columns=["y", "h", "scaleup"])

    df = _normalize_columns(pd.read_csv(path))
    rename_map = {"year": "y", "hour": "h", "scale_up": "scaleup"}
    df = df.rename(columns=rename_map)

    required = {"y", "h"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")

    if "scaleup" not in df.columns:
        df["scaleup"] = 1.0

    return df


def load_nodes_csv(path: Path) -> pd.DataFrame:
    """
    Load optional nodes.csv for node/country/NUTS2/region structures.

    Expected columns (after normalization):
      - n (required)
      - cn (required)
      - nuts2 (required)
      - rgn (optional; defaults to nuts2)
      - lat/lon (optional)
    """
    if not path.exists():
        return pd.DataFrame(columns=["n", "cn", "nuts2", "rgn", "lat", "lon"])

    df = _normalize_columns(pd.read_csv(path))
    required = {"n", "cn", "nuts2"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")

    if "rgn" not in df.columns:
        df["rgn"] = df["nuts2"]
    if "lat" not in df.columns:
        df["lat"] = pd.NA
    if "lon" not in df.columns:
        df["lon"] = pd.NA

    return df


def load_arcs_csv(path: Path) -> pd.DataFrame:
    """
    Load optional arcs.csv for arc transport definitions.

    Expected columns (after normalization):
      - a (required)
      - start (required)
      - end (required)
      - f or e (required; carrier)
      - cap, len, off, cal_c, cal_l (optional for flow-only subset)
    """
    if not path.exists():
        return pd.DataFrame(columns=["a", "start", "end", "f"])

    df = _normalize_columns(pd.read_csv(path))
    if "e" in df.columns and "f" not in df.columns:
        df = df.rename(columns={"e": "f"})

    required = {"a", "start", "end", "f"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")

    for col in ["cap", "len", "off", "cal_b", "cal_c", "cal_l", "cal_r", "cal_x", "bidir"]:
        if col not in df.columns:
            df[col] = 0.0

    return df


def _hour_columns(df: pd.DataFrame, fixed_cols: set[str]) -> list[str]:
    return sorted([c for c in df.columns if c not in fixed_cols and str(c).isdigit()], key=lambda x: int(x))


def _normalize_fuel_label(raw: object) -> str:
    s = str(raw).strip().upper()
    if s in {"GAS", "NATURAL_GAS", "NATURALGAS", "NG"}:
        return "G"
    if s in {"HYDROGEN", "H2"}:
        return "H"
    if s in {"COAL"}:
        return "C"
    return s


def load_consumption_csv(path: Path) -> pd.DataFrame:
    """
    Load optional consumption.csv (direct dmd input).

    Expected columns:
      - n, f, y
      - one or more hour columns named as integers (1,2,3,...)
    """
    if not path.exists():
        return pd.DataFrame(columns=["n", "f", "y"])

    df = _normalize_columns(pd.read_csv(path))
    required = {"n", "f", "y"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")

    h_cols = _hour_columns(df, required)
    if not h_cols:
        raise ValueError(f"No hour columns found in {path}. Expected columns like 1,2,3,...")

    return df


def load_production_csv(path: Path) -> pd.DataFrame:
    """
    Load optional production.csv (direct cap_p/c_p/lb_p input).

    Expected columns:
      - n, f, y
      - one or more hour columns named as integers (1,2,3,...)
      - optional: mc, lb
    """
    if not path.exists():
        return pd.DataFrame(columns=["n", "f", "y"])

    df = _normalize_columns(pd.read_csv(path))
    required = {"n", "f", "y"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")

    h_cols = _hour_columns(df, {"n", "f", "y", "mc", "lb"})
    if not h_cols:
        raise ValueError(f"No hour columns found in {path}. Expected columns like 1,2,3,...")

    return df


def load_regasification_csv(primary_path: Path, legacy_path: Path | None = None) -> tuple[pd.DataFrame, Path | None, list[str]]:
    """
    Load optional regasification file (ONLY regasification.csv is supported).

    Expected columns after normalization/aliasing:
      - n (or node_id)
      - f (or fuel)
      - y (or year) [optional, defaults to 2025]
      - cal_c (optional, defaults to 1)
      - ub (optional, defaults to 0)
    """
    warning_messages: list[str] = []

    if legacy_path is not None and legacy_path.exists():
        warning_messages.append(
            f"Legacy file '{legacy_path.name}' detected but ignored; use 'regasification.csv' only for Sheet-R inputs."
        )

    if not primary_path.exists():
        warning_messages.append(
            f"Regasification file not found: {primary_path}. Using defaults (c_lr gas=1/non-gas=9999, ub_r=0)."
        )
        return pd.DataFrame(columns=["n", "f", "y", "cal_c", "ub"]), None, warning_messages

    df = _normalize_columns(pd.read_csv(primary_path))
    df = df.rename(columns={"node_id": "n", "fuel": "f", "year": "y"})

    if not {"n", "f"}.issubset(df.columns):
        warning_messages.append(
            f"Invalid regasification.csv schema in {primary_path}: required columns include n/node_id and f/fuel. Using defaults."
        )
        return pd.DataFrame(columns=["n", "f", "y", "cal_c", "ub"]), primary_path, warning_messages

    if "y" not in df.columns:
        df["y"] = 2025
    if "cal_c" not in df.columns:
        df["cal_c"] = 1.0
    if "ub" not in df.columns:
        df["ub"] = 0.0

    return df, primary_path, warning_messages


def load_storage_csv(path: Path) -> tuple[pd.DataFrame, list[str]]:
    """
    Load optional storage.csv (Sheet-W representation).

    Expected columns (after normalization/aliasing):
      - n (or node_id)
      - f (or fuel)
      - y (or year) [optional]
      - w, x, i, cal_c, cal_l [optional -> default 0]
    """
    warning_messages: list[str] = []
    if not path.exists():
        warning_messages.append(f"Storage file not found: {path}. Using zero/default storage parameters.")
        return pd.DataFrame(columns=["n", "f", "y", "w", "x", "i", "cal_c", "cal_l"]), warning_messages

    df = _normalize_columns(pd.read_csv(path))
    df = df.rename(columns={"node_id": "n", "fuel": "f", "year": "y"})

    if not {"n", "f"}.issubset(df.columns):
        warning_messages.append(
            f"Invalid storage.csv schema in {path}: required columns include n/node_id and f/fuel. Using defaults."
        )
        return pd.DataFrame(columns=["n", "f", "y", "w", "x", "i", "cal_c", "cal_l"]), warning_messages

    if "y" not in df.columns:
        df["y"] = pd.NA
    for col in ["w", "x", "i", "cal_c", "cal_l"]:
        if col not in df.columns:
            df[col] = 0.0

    return df, warning_messages


def _extract_node_structures(
    df_n: pd.DataFrame,
) -> tuple[list[str], list[str], list[str], list[str], dict[tuple[str, str], int], dict[tuple[str, str], int], dict[tuple[str, str], int], dict[tuple[str, str, str, str, str], float]]:
    """Extract node set domains, mapping sets, and dat_n-compatible LAT/LON table."""
    if df_n.empty:
        return [], [], [], [], {}, {}, {}, {}

    clean = df_n.copy()
    for col in ["n", "cn", "nuts2", "rgn"]:
        clean[col] = clean[col].astype(str).str.strip()

    clean = clean[
        (clean["n"] != "")
        & (clean["cn"] != "")
        & (clean["nuts2"] != "")
        & (clean["rgn"] != "")
    ]

    n_values = sorted(set(clean["n"].tolist()))
    cn_values = sorted(set(clean["cn"].tolist()))
    nuts2_values = sorted(set(clean["nuts2"].tolist()))
    rgn_values = sorted(set(clean["rgn"].tolist()))

    n_in_c = {(r.n, r.cn): 1 for r in clean[["n", "cn"]].itertuples(index=False)}
    n_in_2 = {(r.n, r.nuts2): 1 for r in clean[["n", "nuts2"]].itertuples(index=False)}
    n_in_r = {(r.n, r.rgn): 1 for r in clean[["n", "rgn"]].itertuples(index=False)}

    dat_n: dict[tuple[str, str, str, str, str], float] = {}
    for r in clean[["n", "cn", "nuts2", "rgn", "lat", "lon"]].itertuples(index=False):
        lat = pd.to_numeric(pd.Series([r.lat]), errors="coerce").iloc[0]
        lon = pd.to_numeric(pd.Series([r.lon]), errors="coerce").iloc[0]
        if pd.notna(lat):
            dat_n[(r.n, r.cn, r.nuts2, r.rgn, "LAT")] = float(lat)
        if pd.notna(lon):
            dat_n[(r.n, r.cn, r.nuts2, r.rgn, "LON")] = float(lon)

    return n_values, cn_values, nuts2_values, rgn_values, n_in_c, n_in_2, n_in_r, dat_n


def _extract_time_domains(df_t: pd.DataFrame) -> tuple[list[int], list[int], dict[int, float]]:
    """Extract Y, H and scaleUp(h) from timeseries table."""
    if df_t.empty:
        return [], [], {}

    y_series = pd.to_numeric(df_t["y"], errors="coerce").dropna().astype(int)
    h_series = pd.to_numeric(df_t["h"], errors="coerce").dropna().astype(int)

    y_values = sorted(set(y_series.tolist()))
    h_values = sorted(set(h_series.tolist()))

    scale_map: dict[int, float] = {}
    for h in h_values:
        rows = df_t[pd.to_numeric(df_t["h"], errors="coerce") == h]
        vals = pd.to_numeric(rows["scaleup"], errors="coerce").dropna().tolist()
        chosen = 1.0
        for v in vals:
            fv = float(v)
            if fv > 0:
                chosen = fv
                break
        scale_map[int(h)] = float(chosen)

    return y_values, h_values, scale_map


def _extract_consumption_data(
    df_c: pd.DataFrame,
    n_in_2: dict[tuple[str, str], int],
) -> tuple[dict[tuple[str, str, int, int], float], dict[tuple[str, str, int, int], float], list[int], list[int], list[str]]:
    """Build dmd(n,e,y,h) and dmd2(nuts2,e,y,h) from consumption.csv."""
    if df_c.empty:
        return {}, {}, [], [], []

    hour_cols = _hour_columns(df_c, {"n", "f", "y"})
    work = df_c.copy()
    work["n"] = work["n"].astype(str).str.strip()
    work["f"] = work["f"].astype(str).str.strip()
    work["y"] = pd.to_numeric(work["y"], errors="coerce").astype("Int64")

    dmd: dict[tuple[str, str, int, int], float] = {}
    y_values: set[int] = set()
    h_values: set[int] = set()
    f_values: set[str] = set()

    for _, row in work.iterrows():
        n = str(row["n"]).strip()
        f = str(row["f"]).strip()
        y_raw = row["y"]
        if n == "" or f == "" or pd.isna(y_raw):
            continue
        y = int(y_raw)
        y_values.add(y)
        f_values.add(f)

        for h_col in hour_cols:
            h = int(h_col)
            val = pd.to_numeric(pd.Series([row[h_col]]), errors="coerce").iloc[0]
            v = 0.0 if pd.isna(val) else float(val)
            dmd[(n, f, y, h)] = v
            h_values.add(h)

    node_to_nuts2: dict[str, list[str]] = {}
    for (n, nuts2), flag in n_in_2.items():
        if int(flag) == 1:
            node_to_nuts2.setdefault(n, []).append(nuts2)

    dmd2: dict[tuple[str, str, int, int], float] = {}
    for (n, f, y, h), value in dmd.items():
        for nuts2 in node_to_nuts2.get(n, []):
            key = (nuts2, f, y, h)
            dmd2[key] = float(dmd2.get(key, 0.0) + value)

    return dmd, dmd2, sorted(y_values), sorted(h_values), sorted(f_values)


def _extract_arc_data(
    df_a: pd.DataFrame,
    dat_o: pd.DataFrame,
    y_values: list[int],
    e_values: list[str],
    vola2: dict[str, float],
    loss_max: float,
) -> tuple[
    list[str],
    dict[tuple[str, str], int],
    dict[tuple[str, str], int],
    dict[tuple[str, str], int],
    dict[str, int],
    dict[str, str],
    dict[tuple[str, str, int], float],
    dict[tuple[str, str, int], float],
    dict[tuple[str, str, int], float],
    dict[tuple[str, str, int], float],
    dict[tuple[str, str, str, int], float],
    dict[tuple[str, str, str, int], float],
    dict[tuple[str, int], float],
    dict[tuple[str, str], float],
    list[str],
    list[str],
]:
    """
    Build arc sets and flow-only parameters with GAMS parity formulas.

    Matches load_input_from_Excel.gms flow subset:
      a_s(a,n), a_e(a,n)
            opp(ai,ao), is_bid(a)
      cap_a(a,e,y)=dat_a(a,n,m,e,'cap')
      c_a(a,e,y)=BFPipe(e)*vola2(e)*(len+OffshMult*off)*cal_c/PipeLenStd
            c_ab(a,e,y)=BidirVar(e)*(len+off)*cal_b/PipeLenStd/YearStep
            f_ab(a,y)=BidirFix/YearStep
            c_ar(a,e,f,y)=RepurpArc(e,f)*(len+OffshMult*off)*cal_r/PipeLenStd/YearStep
            f_ar(a,e,f,y)=RepurpArc(Fix,f)*cal_r/YearStep
      e_a(a,e)=max(1-LossMax, 1-BLPipe(e)*len*cal_l/PipeLenStd)
    where OffshMult is transformed as: max(0, OffshMult-1)
    and cal_c/cal_l default to 1 when <=0.
    """
    if df_a.empty:
        return [], {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, [], []

    work = df_a.copy()
    work["a"] = work["a"].astype(str).str.strip()
    work["start"] = work["start"].astype(str).str.strip()
    work["end"] = work["end"].astype(str).str.strip()
    work["f"] = work["f"].map(_normalize_fuel_label)
    work = work[(work["a"] != "") & (work["start"] != "") & (work["end"] != "") & (work["f"] != "")]

    for col in ["cap", "len", "off", "cal_b", "cal_c", "cal_l", "cal_r", "cal_x", "bidir"]:
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)

    dat_o_norm = _normalize_columns(dat_o)
    dat_o_norm["param"] = dat_o_norm["param"].where(dat_o_norm["param"].notna(), "").astype(str).str.strip().str.lower()
    dat_o_norm["indx1"] = dat_o_norm["indx1"].where(dat_o_norm["indx1"].notna(), "").astype(str).str.strip().str.upper()
    dat_o_norm["indx2"] = dat_o_norm["indx2"].where(dat_o_norm["indx2"].notna(), "").astype(str).str.strip().str.upper()
    dat_o_norm["indx1"] = dat_o_norm["indx1"].replace({"NAN": "", "NONE": "", "NULL": ""})
    dat_o_norm["indx2"] = dat_o_norm["indx2"].replace({"NAN": "", "NONE": "", "NULL": ""})
    dat_o_norm["value"] = pd.to_numeric(dat_o_norm["value"], errors="coerce").fillna(0.0)

    def _o_value(param: str, indx1: str = "", indx2: str = "", default: float = 0.0) -> float:
        rows = dat_o_norm[
            (dat_o_norm["param"] == param.lower())
            & (dat_o_norm["indx1"] == str(indx1).strip().upper())
            & (dat_o_norm["indx2"] == str(indx2).strip().upper())
        ]
        if rows.empty:
            return float(default)
        return float(rows.iloc[0]["value"])

    offsh_mult = max(0.0, _o_value("offshmult", "", "", 0.0) - 1.0)
    pipe_len_std = _o_value("pipe", "LEN", "STD", 0.0)
    if pipe_len_std <= 0.0:
        raise ValueError("other.csv must define Pipe,Len,Std with a positive value for arc formulas.")
    year_step = _o_value("yearstep", "", "", 0.0)
    if year_step <= 0.0:
        raise ValueError("other.csv must define YearStep with a positive value for arc investment formulas.")

    bf_default = _o_value("bfpipe", "", "", 0.0)
    bl_default = _o_value("blpipe", "", "", 0.0)
    bi_default = _o_value("bipipe", "", "", 0.0)
    bidir_var_default = _o_value("bidir", "VAR", "", 0.0)
    bidir_fix = _o_value("bidir", "FIX", "", 0.0)
    repurp_var_default = _o_value("repurparc", "", "", 0.0)

    a_values = sorted(set(work["a"].tolist()))
    a_s: dict[tuple[str, str], int] = {}
    a_e: dict[tuple[str, str], int] = {}
    opp: dict[tuple[str, str], int] = {}
    is_bid: dict[str, int] = {}
    opp_map: dict[str, str] = {}
    cap_a: dict[tuple[str, str, int], float] = {}
    c_a: dict[tuple[str, str, int], float] = {}
    c_ax: dict[tuple[str, str, int], float] = {}
    c_ab: dict[tuple[str, str, int], float] = {}
    c_ar: dict[tuple[str, str, str, int], float] = {}
    f_ar: dict[tuple[str, str, str, int], float] = {}
    f_ab: dict[tuple[str, int], float] = {}
    e_a: dict[tuple[str, str], float] = {}

    arc_nodes = sorted(set(work["start"].tolist()) | set(work["end"].tolist()))
    arc_fuels = sorted(set(work["f"].tolist()))
    all_fuels = sorted(set(e_values) | set(arc_fuels))

    arc_endpoints: dict[str, tuple[str, str]] = {}
    for a in a_values:
        rows_a = work[work["a"] == a]
        if rows_a.empty:
            continue
        arc_endpoints[a] = (str(rows_a.iloc[0]["start"]).strip(), str(rows_a.iloc[0]["end"]).strip())

    for ai in a_values:
        if ai not in arc_endpoints:
            continue
        ni, mi = arc_endpoints[ai]
        for ao in a_values:
            if ao == ai or ao not in arc_endpoints:
                continue
            no, mo = arc_endpoints[ao]
            if ni == mo and mi == no:
                opp[(ai, ao)] = 1

    for a in a_values:
        opp_candidates = sorted([ao for (ai, ao), flag in opp.items() if ai == a and int(flag) == 1])
        opp_map[a] = opp_candidates[0] if len(opp_candidates) > 0 else ""

    for a in a_values:
        rows_a = work[work["a"] == a].copy()
        if rows_a.empty:
            continue

        n_start = str(rows_a.iloc[0]["start"]).strip()
        n_end = str(rows_a.iloc[0]["end"]).strip()
        a_s[(a, n_start)] = 1
        a_e[(a, n_end)] = 1

        len_agg = float(rows_a["len"].sum())
        off_agg_raw = float(rows_a["off"].sum())
        off_agg = min(len_agg, off_agg_raw)

        cal_x_by_f: dict[str, float] = {}
        cal_b_by_f: dict[str, float] = {}
        cal_r_by_f: dict[str, float] = {}

        for _, row in rows_a.iterrows():
            f = str(row["f"]).strip()
            cap_val = max(0.0, float(row["cap"]))

            cal_b_raw = float(row["cal_b"])
            cal_b = 1.0 if cal_b_raw <= 0.0 else cal_b_raw
            cal_b_by_f[f] = cal_b

            cal_c_raw = float(row["cal_c"])
            cal_c = 1.0 if cal_c_raw <= 0.0 else cal_c_raw

            cal_l_raw = float(row["cal_l"])
            cal_l = 1.0 if cal_l_raw <= 0.0 else cal_l_raw

            cal_x_raw = float(row["cal_x"])
            cal_x = 1.0 if cal_x_raw <= 0.0 else cal_x_raw
            cal_x_by_f[f] = cal_x

            cal_r_raw = float(row["cal_r"])
            cal_r = 1.0 if cal_r_raw <= 0.0 else cal_r_raw
            cal_r_by_f[f] = cal_r

            bf_pipe_e = _o_value("bfpipe", f, "", 0.0)
            if bf_pipe_e <= 0.0:
                bf_pipe_e = bf_default

            bl_pipe_e = _o_value("blpipe", f, "", 0.0)
            if bl_pipe_e <= 0.0:
                bl_pipe_e = bl_default

            vola2_e = float(vola2.get(f, 1.0))
            c_a_val = bf_pipe_e * vola2_e * (len_agg + offsh_mult * off_agg) * cal_c / pipe_len_std
            e_a_val = max(1.0 - float(loss_max), 1.0 - bl_pipe_e * len_agg * cal_l / pipe_len_std)

            e_a[(a, f)] = float(e_a_val)
            for y in y_values:
                cap_a[(a, f, int(y))] = float(cap_val)
                c_a[(a, f, int(y))] = float(c_a_val)

        is_bid[a] = 1 if float(rows_a["bidir"].sum()) > 0.0 else 0

        for f in all_fuels:
            bi_pipe_e = _o_value("bipipe", f, "", 0.0)
            if bi_pipe_e <= 0.0:
                bi_pipe_e = bi_default
            cal_x = float(cal_x_by_f.get(f, 1.0))
            c_ax_val = bi_pipe_e * (len_agg + offsh_mult * off_agg) * cal_x / pipe_len_std / year_step

            bidir_var_e = _o_value("bidir", "VAR", f, 0.0)
            if bidir_var_e <= 0.0:
                bidir_var_e = bidir_var_default
            cal_b = float(cal_b_by_f.get(f, 1.0))
            c_ab_val = bidir_var_e * (len_agg + off_agg) * cal_b / pipe_len_std / year_step

            for y in y_values:
                c_ax[(a, f, int(y))] = float(c_ax_val)
                c_ab[(a, f, int(y))] = float(c_ab_val)

        for e in all_fuels:
            cal_r = float(cal_r_by_f.get(e, 1.0))
            for f in all_fuels:
                repurp_var = _o_value("repurparc", e, f, 0.0)
                if repurp_var <= 0.0:
                    repurp_var = repurp_var_default
                if str(e).upper() == str(f).upper():
                    repurp_var = 0.0

                repurp_fix = _o_value("repurparc", "FIX", f, 0.0)
                repurp_fix_val = repurp_fix * cal_r / year_step
                repurp_var_val = repurp_var * (len_agg + offsh_mult * off_agg) * cal_r / pipe_len_std / year_step

                for y in y_values:
                    c_ar[(a, e, f, int(y))] = float(repurp_var_val)
                    f_ar[(a, e, f, int(y))] = float(repurp_fix_val)

        for y in y_values:
            f_ab[(a, int(y))] = float(bidir_fix / year_step)

    for ai in a_values:
        for ao in a_values:
            if int(opp.get((ai, ao), 0)) != 1:
                continue
            for f in all_fuels:
                for y in y_values:
                    if float(c_a.get((ai, f, int(y)), 0.0)) > 0.0 and float(c_a.get((ao, f, int(y)), 0.0)) <= 1e-5:
                        c_a[(ao, f, int(y))] = float(c_a[(ai, f, int(y))])
                        c_ax[(ao, f, int(y))] = float(c_ax.get((ai, f, int(y)), 0.0))
                        c_ab[(ao, f, int(y))] = float(c_ab.get((ai, f, int(y)), 0.0))
                        f_ab[(ao, int(y))] = float(f_ab.get((ai, int(y)), 0.0))
                        e_a[(ao, f)] = float(e_a.get((ai, f), e_a.get((ao, f), 1.0)))
                        is_bid[ao] = int(is_bid.get(ai, is_bid.get(ao, 0)))

    for ai in a_values:
        for ao in a_values:
            if int(opp.get((ai, ao), 0)) != 1:
                continue
            for e in all_fuels:
                for f in all_fuels:
                    for y in y_values:
                        src_car = float(c_ar.get((ai, e, f, int(y)), 0.0))
                        dst_car = float(c_ar.get((ao, e, f, int(y)), 0.0))
                        src_far = float(f_ar.get((ai, e, f, int(y)), 0.0))
                        dst_far = float(f_ar.get((ao, e, f, int(y)), 0.0))
                        if (src_car > 0.0 and dst_car <= 1e-5) or (src_far > 0.0 and dst_far <= 1e-5):
                            c_ar[(ao, e, f, int(y))] = src_car
                            f_ar[(ao, e, f, int(y))] = src_far

    # Ensure full model domain has defaults for all (a,e[,y]) combinations.
    for a in a_values:
        is_bid.setdefault(a, 0)
        for f in all_fuels:
            e_a.setdefault((a, f), 1.0)
            for y in y_values:
                cap_a.setdefault((a, f, int(y)), 0.0)
                c_a.setdefault((a, f, int(y)), 0.0)
                c_ax.setdefault((a, f, int(y)), 0.0)
                c_ab.setdefault((a, f, int(y)), 0.0)
                f_ab.setdefault((a, int(y)), 0.0)
        for e in all_fuels:
            for f in all_fuels:
                for y in y_values:
                    c_ar.setdefault((a, e, f, int(y)), 0.0)
                    f_ar.setdefault((a, e, f, int(y)), 0.0)

    for a in a_values:
        for e in all_fuels:
            for y in y_values:
                c_ar[(a, e, e, int(y))] = 0.0
                f_ar[(a, e, e, int(y))] = 0.0

    for ai in a_values:
        for ao in a_values:
            opp.setdefault((ai, ao), 0)
        opp_map.setdefault(ai, "")

    return a_values, a_s, a_e, opp, is_bid, opp_map, cap_a, c_a, c_ax, c_ab, c_ar, f_ar, f_ab, e_a, arc_nodes, arc_fuels


def _extract_production_data(
    df_p: pd.DataFrame,
) -> tuple[dict[tuple[str, str, int, int], float], dict[tuple[str, str, int], float], dict[tuple[str, str, int, int], float], list[int], list[int], list[str]]:
    """Build cap_p(n,e,y,h), c_p(n,e,y), lb_p(n,e,y,h) from production.csv."""
    if df_p.empty:
        return {}, {}, {}, [], [], []

    hour_cols = _hour_columns(df_p, {"n", "f", "y", "mc", "lb"})
    work = df_p.copy()
    work["n"] = work["n"].astype(str).str.strip()
    work["f"] = work["f"].astype(str).str.strip()
    work["y"] = pd.to_numeric(work["y"], errors="coerce").astype("Int64")
    if "mc" not in work.columns:
        work["mc"] = 0.0
    if "lb" not in work.columns:
        work["lb"] = 0.0

    cap_p: dict[tuple[str, str, int, int], float] = {}
    c_p: dict[tuple[str, str, int], float] = {}
    lb_p: dict[tuple[str, str, int, int], float] = {}
    y_values: set[int] = set()
    h_values: set[int] = set()
    f_values: set[str] = set()

    for _, row in work.iterrows():
        n = str(row["n"]).strip()
        f = str(row["f"]).strip()
        y_raw = row["y"]
        if n == "" or f == "" or pd.isna(y_raw):
            continue
        y = int(y_raw)
        f_values.add(f)

        mc_val = pd.to_numeric(pd.Series([row["mc"]]), errors="coerce").iloc[0]
        c_p[(n, f, y)] = 0.0 if pd.isna(mc_val) else float(mc_val)

        lb_val = pd.to_numeric(pd.Series([row["lb"]]), errors="coerce").iloc[0]
        lb_scalar = 0.0 if pd.isna(lb_val) else float(lb_val)

        for h_col in hour_cols:
            h = int(h_col)
            cap_val = pd.to_numeric(pd.Series([row[h_col]]), errors="coerce").iloc[0]
            cap_p[(n, f, y, h)] = 0.0 if pd.isna(cap_val) else float(cap_val)
            lb_p[(n, f, y, h)] = lb_scalar
            h_values.add(h)

    # GAMS parity (selected): c_p(n,e,y)$(ord(y)>2) = dat_p(n,e,'2030','MC')
    ordered_years = sorted(y_values)
    if len(ordered_years) >= 3 and 2030 in ordered_years:
        for n in sorted({key[0] for key in c_p.keys()}):
            for f in sorted({key[1] for key in c_p.keys() if key[0] == n}):
                ref_key = (n, f, 2030)
                if ref_key not in c_p:
                    continue
                ref_val = float(c_p[ref_key])
                for y in ordered_years[2:]:
                    c_p[(n, f, y)] = ref_val

    # GAMS parity (selected): lb_p(n,e,y,h) = min(lb_p(n,e,y,h), cap_p(n,e,y,h))
    for key, cap_val in cap_p.items():
        lb_p[key] = min(float(lb_p.get(key, 0.0)), float(cap_val))

    return cap_p, c_p, lb_p, sorted(y_values), sorted(h_values), sorted(f_values)


def _extract_regas_data(
    df_r: pd.DataFrame,
    n_values: list[str],
    e_values: list[str],
) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], float], list[str], list[str]]:
    """
    Build c_lr(n,e) and ub_r(n,e) from regasification inputs.

    GAMS parity subset:
      - dat_r(n,e,'2025','cal_c') <= 0 -> 1
      - c_lr(n,e) = dat_r(n,e,'2025','cal_c')
      - c_lr(n,e)$not_g(e) = 9999
      - Q_R.up(n,e,y,h) = dat_r(n,e,'2025','ub')
    """
    regas_nodes: list[str] = []
    regas_fuels: list[str] = []

    # Default c_lr parity: gas=1, non-gas=9999; ub_r default is 0
    c_lr: dict[tuple[str, str], float] = {}
    ub_r: dict[tuple[str, str], float] = {}
    for n in n_values:
        for e in e_values:
            e_norm = _normalize_fuel_label(e)
            c_lr[(str(n), str(e))] = 1.0 if e_norm == "G" else 9999.0
            ub_r[(str(n), str(e))] = 0.0

    if df_r.empty:
        return c_lr, ub_r, regas_nodes, regas_fuels

    work = df_r.copy()
    work["n"] = work["n"].astype(str).str.strip()
    work["f"] = work["f"].map(_normalize_fuel_label)
    work["y"] = pd.to_numeric(work["y"], errors="coerce").fillna(2025).astype(int)

    regas_nodes = sorted(set(work["n"][work["n"] != ""].tolist()))
    regas_fuels = sorted(set(work["f"][work["f"] != ""].tolist()))

    for _, row in work.iterrows():
        n = str(row["n"]).strip()
        f = str(row["f"]).strip()
        y = int(row["y"])
        if n == "" or f == "":
            continue
        if y != 2025:
            continue

        cal_c_raw = pd.to_numeric(pd.Series([row["cal_c"]]), errors="coerce").iloc[0]
        cal_c = 1.0 if pd.isna(cal_c_raw) or float(cal_c_raw) <= 0.0 else float(cal_c_raw)
        ub_raw = pd.to_numeric(pd.Series([row["ub"]]), errors="coerce").iloc[0]
        ub = 0.0 if pd.isna(ub_raw) else max(0.0, float(ub_raw))

        c_lr[(n, f)] = cal_c if _normalize_fuel_label(f) == "G" else 9999.0
        ub_r[(n, f)] = ub

    return c_lr, ub_r, regas_nodes, regas_fuels


def _extract_storage_data(
    df_s: pd.DataFrame,
    n_values: list[str],
    e_values: list[str],
    y_values: list[int],
    h_values: list[int],
    scaleup: dict[int, float],
    vols2: dict[str, float],
) -> tuple[
    dict[tuple[str, str, int], float],
    dict[tuple[str, str, int], float],
    dict[tuple[str, str, int], float],
    dict[tuple[str, str], float],
    dict[tuple[str, str], float],
    dict[tuple[str, str], float],
    list[str],
    list[str],
]:
    """
    Build storage parameters from Sheet-W representation.

    GAMS parity subset:
      cap_we(n,e,y)=dat_w(n,e,'X') with H/G cross-fuel fallback via vols2('H')
      cap_wi(n,e,y)=dat_w(n,e,'I') with H/G cross-fuel fallback via vols2('H')
      cap_ww(n,e,y)=dat_w(n,e,'W')*sum(h,scaleUp(h))/8760
      dat_w('cal_c')<=0 -> 1, dat_w('cal_l')<=0 -> 1
      c_we(n,e)=vols2(e)*dat_w(n,e,'cal_c')
      e_w(n,e)=1-0.01*dat_w(n,e,'cal_l')
    """
    cap_we: dict[tuple[str, str, int], float] = {}
    cap_wi: dict[tuple[str, str, int], float] = {}
    cap_ww: dict[tuple[str, str, int], float] = {}
    c_we: dict[tuple[str, str], float] = {}
    e_w: dict[tuple[str, str], float] = {}
    h2_ready: dict[tuple[str, str], float] = {}

    stor_nodes: list[str] = []
    stor_fuels: list[str] = []

    sum_scaleup = float(sum(float(scaleup.get(int(h), 1.0)) for h in h_values)) if len(h_values) > 0 else 0.0
    vols2_h = float(vols2.get("H", 1.0))

    dat_w_map: dict[tuple[str, str, str], float] = {}
    if not df_s.empty:
        work = df_s.copy()
        work["n"] = work["n"].where(work["n"].notna(), "").astype(str).str.strip()
        work["f"] = work["f"].where(work["f"].notna(), "").astype(str).str.strip()
        work = work[(work["n"] != "") & (work["f"] != "")]
        work["f"] = work["f"].map(_normalize_fuel_label)
        stor_nodes = sorted(set(work["n"].tolist()))
        stor_fuels = sorted(set(work["f"].tolist()))

        for _, row in work.iterrows():
            n = str(row["n"]).strip()
            f = str(row["f"]).strip()
            if n == "" or f == "":
                continue
            for key_col, key_name in [
                ("w", "W"),
                ("x", "X"),
                ("i", "I"),
                ("cal_c", "cal_c"),
                ("cal_l", "cal_l"),
                ("h2-ready", "H2-ready"),
            ]:
                if key_col not in row.index:
                    continue
                raw = pd.to_numeric(pd.Series([row[key_col]]), errors="coerce").iloc[0]
                val = 0.0 if pd.isna(raw) else float(raw)
                dat_w_map[(n, f, key_name)] = val

    all_nodes = sorted(set(n_values) | set(stor_nodes))
    for n in all_nodes:
        for e in e_values:
            e_norm = _normalize_fuel_label(e)
            x_raw = float(dat_w_map.get((n, e_norm, "X"), 0.0))
            i_raw = float(dat_w_map.get((n, e_norm, "I"), 0.0))
            w_raw = float(dat_w_map.get((n, e_norm, "W"), 0.0))

            if x_raw <= 0.0 and e_norm == "H":
                x_raw = float(dat_w_map.get((n, "G", "X"), 0.0)) / vols2_h if vols2_h != 0 else 0.0
            if x_raw <= 0.0 and e_norm == "G":
                x_raw = float(dat_w_map.get((n, "H", "X"), 0.0)) * vols2_h

            if i_raw <= 0.0 and e_norm == "H":
                i_raw = float(dat_w_map.get((n, "G", "I"), 0.0)) / vols2_h if vols2_h != 0 else 0.0
            if i_raw <= 0.0 and e_norm == "G":
                i_raw = float(dat_w_map.get((n, "H", "I"), 0.0)) * vols2_h

            cal_c_raw = float(dat_w_map.get((n, e_norm, "cal_c"), 0.0))
            cal_c = 1.0 if cal_c_raw <= 0.0 else cal_c_raw
            cal_l_raw = float(dat_w_map.get((n, e_norm, "cal_l"), 0.0))
            cal_l = 1.0 if cal_l_raw <= 0.0 else cal_l_raw

            c_we[(n, e_norm)] = float(vols2.get(e_norm, 1.0)) * cal_c
            e_w[(n, e_norm)] = 1.0 - 0.01 * cal_l
            h2_ready[(n, e_norm)] = float(dat_w_map.get((n, e_norm, "H2-ready"), 0.0))

            ww_scaled = w_raw * sum_scaleup / 8760.0 if sum_scaleup > 0 else 0.0
            for y in y_values:
                cap_we[(n, e_norm, int(y))] = max(0.0, x_raw)
                cap_wi[(n, e_norm, int(y))] = max(0.0, i_raw)
                cap_ww[(n, e_norm, int(y))] = max(0.0, ww_scaled)

    return cap_we, cap_wi, cap_ww, c_we, e_w, h2_ready, stor_nodes, stor_fuels


def load_inputs(
    *,
    other_path: Path | None = None,
    o_path: Path | None = None,
    timeseries_path: Path | None = None,
    nodes_path: Path | None = None,
    arcs_path: Path | None = None,
) -> dict[str, Any]:
    """
    Central data-loading entry point.

    Extend this function as new CSVs are added so model code stays clean.
    """
    if other_path is not None and o_path is not None:
        raise ValueError("Use only one of 'other_path' or legacy 'o_path'.")

    raw_other_path = Path(other_path).resolve() if other_path is not None else (
        Path(o_path).resolve() if o_path is not None else DEFAULT_OTHER_CSV
    )
    final_o_path = _resolve_other_csv_path(raw_other_path)
    if timeseries_path is not None:
        final_t_path = Path(timeseries_path).resolve()
    else:
        final_t_path = final_o_path.parent / "timeseries.csv"
    if nodes_path is not None:
        final_n_path = Path(nodes_path).resolve()
    else:
        final_n_path = final_o_path.parent / "nodes.csv"
    if arcs_path is not None:
        final_a_path = Path(arcs_path).resolve()
    else:
        final_a_path = final_o_path.parent / "arcs.csv"
    final_regas_path = final_o_path.parent / "regasification.csv"
    final_rega_legacy_path = final_o_path.parent / "rega.csv"
    final_storage_path = final_o_path.parent / "storage.csv"
    final_c_path = final_o_path.parent / "consumption.csv"
    final_p_path = final_o_path.parent / "production.csv"

    dat_o = load_o_csv(final_o_path)
    dat_t = load_timeseries_csv(final_t_path)
    dat_nodes = load_nodes_csv(final_n_path)
    dat_arcs = load_arcs_csv(final_a_path)
    dat_regas, loaded_regas_path, regas_warnings = load_regasification_csv(final_regas_path, final_rega_legacy_path)
    dat_storage, storage_warnings = load_storage_csv(final_storage_path)
    for msg in regas_warnings:
        warnings.warn(msg)
    for msg in storage_warnings:
        warnings.warn(msg)
    dat_consumption = load_consumption_csv(final_c_path)
    dat_production = load_production_csv(final_p_path)
    y_values, h_values, scaleup = _extract_time_domains(dat_t)
    n_values, cn_values, nuts2_values, rgn_values, n_in_c, n_in_2, n_in_r, dat_n = _extract_node_structures(dat_nodes)
    dmd, dmd2, y_dmd, h_dmd, f_dmd = _extract_consumption_data(dat_consumption, n_in_2)
    cap_p, c_p, lb_p, y_prod, h_prod, f_prod = _extract_production_data(dat_production)
    c_z = build_c_z(dat_o)
    regas_f_raw = [_normalize_fuel_label(v) for v in dat_regas.get("f", pd.Series([], dtype=str)).tolist()] if not dat_regas.empty else []
    storage_f_raw = [_normalize_fuel_label(v) for v in dat_storage.get("f", pd.Series([], dtype=str)).tolist()] if not dat_storage.empty else []
    e_values = sorted(set(c_z["e"].astype(str).tolist()) | set(f_dmd) | set(f_prod) | set(regas_f_raw) | set(storage_f_raw))
    c_lr, ub_r, regas_nodes, regas_fuels = _extract_regas_data(dat_regas, n_values=n_values, e_values=e_values)
    n_values = sorted(set(n_values) | set(regas_nodes))
    for n in n_values:
        for e in e_values:
            c_lr.setdefault((str(n), str(e)), 1.0 if _normalize_fuel_label(e) == "G" else 9999.0)
            ub_r.setdefault((str(n), str(e)), 0.0)
    final_y_values = sorted(set(y_values) | set(y_dmd) | set(y_prod))
    final_h_values = sorted(set(h_values) | set(h_dmd) | set(h_prod))

    vola2_map = build_vola2(dat_o, e_values=e_values)
    loss_max_value = build_loss_max(dat_o)
    a_values, a_s, a_e, opp, is_bid, opp_map, cap_a, c_a, c_ax, c_ab, c_ar, f_ar, f_ab, e_a, arc_nodes, arc_fuels = _extract_arc_data(
        dat_arcs,
        dat_o,
        y_values=final_y_values,
        e_values=e_values,
        vola2=vola2_map,
        loss_max=loss_max_value,
    )
    n_values = sorted(set(n_values) | set(arc_nodes))
    e_values = sorted(set(e_values) | set(arc_fuels))

    for h in final_h_values:
        if h not in scaleup:
            scaleup[h] = 1.0

    # GAMS parity (selected): c_p(n,e,y)$(ord(y)>2) = dat_p(n,e,'2030','MC')
    # Apply on full model-year domain (final_y_values), not only rows present in production.csv.
    if len(final_y_values) >= 3 and 2030 in final_y_values:
        cp_keys = list(c_p.keys())
        cp_nodes = sorted(set(k[0] for k in cp_keys))
        cp_fuels = sorted(set(k[1] for k in cp_keys))
        for n in cp_nodes:
            for f in cp_fuels:
                ref_key = (n, f, 2030)
                if ref_key not in c_p:
                    continue
                ref_val = float(c_p[ref_key])
                for y in final_y_values[2:]:
                    c_p[(n, f, int(y))] = ref_val

    vols2_map = build_vols2(dat_o, e_values=e_values)
    cap_we, cap_wi, cap_ww, c_we, e_w, h2_ready, stor_nodes, stor_fuels = _extract_storage_data(
        dat_storage,
        n_values=n_values,
        e_values=e_values,
        y_values=final_y_values,
        h_values=final_h_values,
        scaleup=scaleup,
        vols2=vols2_map,
    )
    n_values = sorted(set(n_values) | set(stor_nodes))

    return {
        "o_path": final_o_path,
        "other_path": final_o_path,
        "timeseries_path": final_t_path,
        "nodes_path": final_n_path,
        "arcs_path": final_a_path,
        "regas_path": loaded_regas_path if loaded_regas_path is not None else final_regas_path,
        "storage_path": final_storage_path,
        "regas_warnings": regas_warnings,
        "storage_warnings": storage_warnings,
        "dat_o": dat_o,
        "dat_t": dat_t,
        "dat_nodes": dat_nodes,
        "dat_arcs": dat_arcs,
        "dat_regas": dat_regas,
        "dat_storage": dat_storage,
        "consumption_path": final_c_path,
        "production_path": final_p_path,
        "dat_consumption": dat_consumption,
        "dat_production": dat_production,
        "dat_n": dat_n,
        "n_values": n_values,
        "cn_values": cn_values,
        "nuts2_values": nuts2_values,
        "rgn_values": rgn_values,
        "n_in_c": n_in_c,
        "n_in_2": n_in_2,
        "n_in_r": n_in_r,
        "a_values": a_values,
        "a_s": a_s,
        "a_e": a_e,
        "opp": opp,
        "opp_map": opp_map,
        "is_bid": is_bid,
        "y_values": final_y_values,
        "h_values": final_h_values,
        "e_values": e_values,
        "scaleUp": scaleup,
        "dmd": dmd,
        "dmd2": dmd2,
        "cap_p": cap_p,
        "c_p": c_p,
        "lb_p": lb_p,
        "c_lr": c_lr,
        "ub_r": ub_r,
        "cap_a": cap_a,
        "c_a": c_a,
        "c_ax": c_ax,
        "c_ab": c_ab,
        "c_ar": c_ar,
        "f_ar": f_ar,
        "f_ab": f_ab,
        "e_a": e_a,
        "regas_fuels": regas_fuels,
        "cap_we": cap_we,
        "cap_wi": cap_wi,
        "cap_ww": cap_ww,
        "c_we": c_we,
        "e_w": e_w,
        "h2_ready": h2_ready,
        "storage_fuels": stor_fuels,
        "c_z": c_z,
        "vola2": build_vola2(dat_o, e_values=e_values),
        "vols2": vols2_map,
        "c_bl": build_c_bl(dat_o, e_values=e_values),
        "ub_bl": build_ub_bl(dat_o, e_values=e_values),
        "bigM": build_bigM(dat_o),
        "yearstep": build_yearstep(dat_o),
        "discRate": build_disc_rate(dat_o),
        "lossMax": loss_max_value,
    }

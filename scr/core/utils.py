from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional
import math

import pandas as pd


def _read_csv_if_exists(data_dir: Path, filename: str) -> pd.DataFrame:
    """Read CSV file if it exists, return empty DataFrame otherwise."""
    path = data_dir / filename
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path, encoding="cp1252")

    df.columns = [
        str(c)
        .encode("utf-8", "ignore")
        .decode("utf-8")
        .replace("\ufeff", "")
        .replace("ï»¿", "")
        .strip()
        .lower()
        for c in df.columns
    ]
    return df


def _is_nan(x) -> bool:
    try:
        return x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x)
    except Exception:
        return False


def _clean_str(x) -> Optional[str]:
    if _is_nan(x):
        return None
    s = str(x).strip()
    return s if s else None


def _to_int(x, default: Optional[int] = 0) -> Optional[int]:
    if _is_nan(x):
        return default
    try:
        return int(float(x))
    except Exception:
        return default


def _to_float(x, default: float = 0.0):
    if _is_nan(x):
        return default
    try:
        return float(x)
    except Exception:
        return default


def _sorted_unique(it: Iterable) -> List:
    return sorted(set(it))


def _col(df: pd.DataFrame, name: str) -> Optional[str]:
    return name if (not df.empty and name in df.columns) else None

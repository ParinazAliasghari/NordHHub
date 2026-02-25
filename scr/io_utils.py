from __future__ import annotations

from scr.core.utils import _clean_str, _col, _is_nan, _read_csv_if_exists, _sorted_unique, _to_float, _to_int


_DEBUG_MODE = False


def set_debug_mode(enabled: bool) -> None:
    """Set global debug mode for helper logging."""
    global _DEBUG_MODE
    _DEBUG_MODE = enabled


def log(message: str, force: bool = False) -> None:
    """Print message only if debug mode is enabled or force=True."""
    if _DEBUG_MODE or force:
        print(message)

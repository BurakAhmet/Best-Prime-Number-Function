"""Stderr progress for long CLI proofs.

Quiet unless stderr is a TTY or ``BEST_PRIME_PROGRESS`` is set.
``BEST_PRIME_MAX_MS`` / ``set_deadline_ms`` is a wall-clock abort for
the search — a miss is unsettled, never a false composite.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional

_enabled: Optional[bool] = None
_t0: Optional[float] = None
_deadline: Optional[float] = None
_configured: bool = False


def is_configured() -> bool:
    return _configured


def configure(*, enabled: Optional[bool] = None) -> None:
    """Enable or disable progress lines. ``None`` = TTY / env auto."""
    global _enabled, _t0, _configured
    _configured = True
    if enabled is None:
        env = os.environ.get("BEST_PRIME_PROGRESS", "").strip().lower()
        if env in {"0", "false", "no", "off"}:
            enabled = False
        elif env in {"1", "true", "yes", "on"}:
            enabled = True
        else:
            enabled = sys.stderr.isatty()
    _enabled = bool(enabled)
    if _t0 is None:
        _t0 = time.perf_counter()


def set_deadline_ms(ms: Optional[int]) -> None:
    """Hard stop after ``ms`` milliseconds from now. ``None`` clears it."""
    global _deadline
    if ms is None:
        _deadline = None
        return
    _deadline = time.perf_counter() + max(0, int(ms)) / 1000.0


def deadline_ms_from_env() -> Optional[int]:
    raw = os.environ.get("BEST_PRIME_MAX_MS", "").strip()
    if not raw:
        return None
    try:
        val = int(raw)
    except ValueError:
        return None
    return val if val >= 0 else None


def deadline_hit() -> bool:
    return _deadline is not None and time.perf_counter() >= _deadline


def remaining_ms() -> Optional[int]:
    if _deadline is None:
        return None
    left = _deadline - time.perf_counter()
    return max(0, int(left * 1000.0))


def emit(stage: str, **fields: object) -> None:
    if _enabled is None:
        configure()
    if not _enabled:
        return
    extra = " ".join(f"{k}={v}" for k, v in fields.items() if v is not None)
    elapsed = time.perf_counter() - (_t0 if _t0 is not None else time.perf_counter())
    msg = f"[best-prime] {elapsed:7.2f}s  {stage}"
    if extra:
        msg += f"  {extra}"
    print(msg, file=sys.stderr, flush=True)

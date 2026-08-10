#!/usr/bin/env python3
"""Compatibility CLI and import path for ``best_prime.is_prime``.

Prefer ``from best_prime import is_prime``. This file keeps
``python is_prime.py`` and ``from is_prime import is_prime`` working
without loading ntheory / sieves into end-to-end CLI ``TIME``.
"""

from __future__ import annotations

from typing import Any

import best_prime.is_prime as _impl
from best_prime.is_prime import main


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return dir(_impl)


if __name__ == "__main__":
    raise SystemExit(main())

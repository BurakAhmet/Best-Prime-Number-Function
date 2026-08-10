#!/usr/bin/env python3
"""Compatibility CLI and import path for ``best_prime.next_prime``.

Prefer ``from best_prime import next_prime`` or the ``next-prime`` console
script. This file keeps ``python next_prime.py N`` working after the
library moved into the ``best_prime`` package.

    python3 next_prime.py 14
    python3 -m best_prime.next_prime 14
"""

from __future__ import annotations

from typing import Any

import best_prime.next_prime as _impl
from best_prime.next_prime import main


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return dir(_impl)


if __name__ == "__main__":
    raise SystemExit(main())

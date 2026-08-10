"""
best-prime-number-function — fully deterministic primality testing.

Canonical implementation lives in the ``is_prime`` module; this package is a
stable, library-friendly import path.

Example
-------
>>> from best_prime import is_prime, lab, next_prime
>>> is_prime(17)
True
>>> next_prime(14)
17
>>> lab(97)["path"]
'python_small'
"""

from __future__ import annotations

try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("best-prime-number-function")
    except PackageNotFoundError:  # pragma: no cover - editable / source tree
        __version__ = "1.6.0"
except ImportError:  # pragma: no cover
    __version__ = "1.6.0"

from is_prime import DEFAULT_N, is_prime, lab, main
from next_prime import next_prime

__all__ = ["DEFAULT_N", "is_prime", "lab", "main", "next_prime", "__version__"]

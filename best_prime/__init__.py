"""
best-prime-number-function — fully deterministic primality testing.

Canonical implementation lives in the ``is_prime`` module; this package is a
stable, library-friendly import path.

Example
-------
>>> from best_prime import is_prime, lab
>>> is_prime(17)
True
>>> lab(97)["path"]
'python_small'
"""

from __future__ import annotations

try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("best-prime-number-function")
    except PackageNotFoundError:  # pragma: no cover - editable / source tree
        __version__ = "1.4.1"
except ImportError:  # pragma: no cover
    __version__ = "1.4.1"

from is_prime import is_prime, lab, main

__all__ = ["is_prime", "lab", "main", "__version__"]

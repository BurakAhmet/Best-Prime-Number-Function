"""Last downrun witness, shared by BLS and ECPP.

Lives outside ``primality_ecpp`` so a boolean BLS proof does not import
curve arithmetic just to remember a cofactor certificate.
"""

from __future__ import annotations

_last_child: tuple[int, dict] | None = None


def _set_child_rec(q: int, rec: dict | None) -> None:
    global _last_child
    _last_child = None if rec is None else (int(q), rec)


def _take_child_rec(q: int) -> dict | None:
    global _last_child
    if _last_child is None or _last_child[0] != int(q):
        return None
    rec = _last_child[1]
    _last_child = None
    return rec

"""CM downrun of a successful ECPP / FastECPP proof.

Two primes of similar size can invert on wall-clock because of ``D``
and class number, not because the engine picked the wrong band. This
module records that tree so ``lab`` and the CLI can show it.
"""

from __future__ import annotations

from typing import Any

_last: list[dict[str, Any]] | None = None


def clear_cm_tree() -> None:
    global _last
    _last = None


def last_cm_tree() -> list[dict[str, Any]] | None:
    return None if _last is None else [dict(step) for step in _last]


def discriminant_class_number(D: int) -> int | None:
    from .primality_ecpp import CLASS_NUMBER_1_D

    if D in CLASS_NUMBER_1_D:
        return 1
    try:
        from ._fundamentals import FUNDAMENTAL_DH

        for d, h in FUNDAMENTAL_DH:
            if d == D:
                return int(h)
    except ImportError:
        pass
    try:
        from .classpoly import class_number

        return int(class_number(D))
    except (ValueError, ArithmeticError, TypeError):
        return None


def _step(n: int, rec: dict[str, Any]) -> dict[str, Any]:
    q = int(rec["q"]) if rec.get("q") is not None else 0
    D = int(rec["D"])
    h = rec.get("h")
    if h is None:
        h = discriminant_class_number(D)
    step: dict[str, Any] = {
        "n_digits": len(str(n)),
        "n_bits": n.bit_length(),
        "D": D,
        "h": int(h) if h is not None else None,
    }
    if q > 1:
        step["q_digits"] = len(str(q))
        step["q_bits"] = q.bit_length()
    return step


def tree_from_rec(n: int, rec: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Walk a FastECPP / ECPP search rec (nested ``q_rec``)."""
    out: list[dict[str, Any]] = []
    cur_n, cur = n, rec
    while isinstance(cur, dict) and "D" in cur and "q" in cur:
        out.append(_step(cur_n, cur))
        nxt = cur.get("q_rec")
        cur_n = int(cur["q"])
        cur = nxt if isinstance(nxt, dict) else None
    return out


def tree_from_cert(cert: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Walk an ``kind='ecpp'`` certificate (nested ``q_cert``)."""
    out: list[dict[str, Any]] = []
    cur = cert
    while isinstance(cur, dict) and cur.get("kind") == "ecpp" and "D" in cur:
        q_cert = cur.get("q_cert")
        q = int(q_cert["n"]) if isinstance(q_cert, dict) and "n" in q_cert else 0
        rec = {"D": cur["D"], "q": q, "h": cur.get("h")}
        out.append(_step(int(cur["n"]), rec))
        cur = q_cert if isinstance(q_cert, dict) else None
    return out


def record_from_rec(n: int, rec: dict[str, Any] | None) -> list[dict[str, Any]]:
    global _last
    tree = tree_from_rec(n, rec)
    _last = tree or None
    return tree


def record_from_cert(cert: dict[str, Any] | None) -> list[dict[str, Any]]:
    global _last
    tree = tree_from_cert(cert)
    _last = tree or None
    return tree


def format_tree(tree: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for step in tree:
        h = step.get("h")
        h_s = str(h) if h is not None else "?"
        parts.append(f"{step['n_digits']}d/D={step['D']}/h={h_s}")
    return " -> ".join(parts)


def emit_tree(tree: list[dict[str, Any]]) -> None:
    if not tree:
        return
    from .progress import emit

    emit("cm_tree", steps=len(tree), path=format_tree(tree))
    for i, step in enumerate(tree):
        emit(
            "cm",
            i=i,
            n_digits=step.get("n_digits"),
            n_bits=step.get("n_bits"),
            D=step.get("D"),
            h=step.get("h"),
            q_digits=step.get("q_digits"),
            q_bits=step.get("q_bits"),
        )

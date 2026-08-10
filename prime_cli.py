"""Console scripts for the public prime APIs.

Each command prints TEST / RESULT / TIME like ``is-prime`` / ``next-prime``.
"""

from __future__ import annotations

import sys
import time

t0 = time.perf_counter_ns()

from is_prime import _parse_n  # noqa: E402
from next_prime import _looks_like_int_token, _parse_k, next_prime  # noqa: E402
from prev_prime import prev_prime  # noqa: E402
from prime_factors import prime_factors  # noqa: E402
from prime_power import is_perfect_power, is_prime_power  # noqa: E402
from prime_sieve import nth_prime, prime_count, primerange, primes  # noqa: E402


def _print(test: str, result: object, **fields: object) -> None:
    print(f"TEST:    {test}")
    for key, val in fields.items():
        label = key.upper()
        print(f"{label + ':':<9}{val}")
    print(f"RESULT:  {result}")
    dt = time.perf_counter_ns() - t0
    print(f"TIME:    {dt} ns  ({dt / 1e6:.6f} ms)")


def _parse_k_token(raw: str) -> int:
    s = raw.strip()
    digits = s[1:] if s.startswith("+") else s
    if not digits.isdigit():
        raise ValueError(f"invalid k: {raw!r}")
    return _parse_k(int(digits))


def _scan(argv: list[str], usage: str, max_pos: int) -> tuple[list[str], bool]:
    serial = False
    positional: list[str] = []
    for a in argv:
        if a in {"-h", "--help"}:
            print(usage)
            raise SystemExit(0)
        if a == "--serial":
            serial = True
        elif a.startswith("-") and not _looks_like_int_token(a):
            print(f"unknown option: {a}", file=sys.stderr)
            raise SystemExit(2)
        else:
            positional.append(a)
    if not positional or len(positional) > max_pos:
        print(usage, file=sys.stderr)
        raise SystemExit(2)
    return positional, serial


def next_prime_main(argv: list[str] | None = None) -> None:
    usage = "usage: next-prime [--serial] n [k]"
    pos, serial = _scan(argv if argv is not None else sys.argv[1:], usage, 2)
    try:
        n = _parse_n(pos[0])
        k = _parse_k_token(pos[1]) if len(pos) > 1 else 1
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    _print(str(n), next_prime(n, k, parallel=not serial), k=k)


def prev_prime_main(argv: list[str] | None = None) -> None:
    usage = "usage: prev-prime [--serial] n [k]"
    pos, serial = _scan(argv if argv is not None else sys.argv[1:], usage, 2)
    try:
        n = _parse_n(pos[0])
        k = _parse_k_token(pos[1]) if len(pos) > 1 else 1
        value = prev_prime(n, k, parallel=not serial)
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    _print(str(n), value, k=k)


def nth_prime_main(argv: list[str] | None = None) -> None:
    usage = "usage: nth-prime k"
    pos, _ = _scan(argv if argv is not None else sys.argv[1:], usage, 1)
    try:
        k = _parse_k_token(pos[0])
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    _print(str(k), nth_prime(k))


def prime_count_main(argv: list[str] | None = None) -> None:
    usage = "usage: prime-count n"
    pos, _ = _scan(argv if argv is not None else sys.argv[1:], usage, 1)
    try:
        n = _parse_n(pos[0])
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    _print(str(n), prime_count(n))


def primes_main(argv: list[str] | None = None) -> None:
    usage = "usage: primes n"
    pos, _ = _scan(argv if argv is not None else sys.argv[1:], usage, 1)
    try:
        n = _parse_n(pos[0])
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    vals = primes(n)
    _print(str(n), " ".join(str(p) for p in vals), count=len(vals))


def primerange_main(argv: list[str] | None = None) -> None:
    usage = "usage: primerange low high"
    pos, _ = _scan(argv if argv is not None else sys.argv[1:], usage, 2)
    if len(pos) != 2:
        print(usage, file=sys.stderr)
        raise SystemExit(2)
    try:
        lo = _parse_n(pos[0])
        hi = _parse_n(pos[1])
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    vals = primerange(lo, hi)
    _print(f"{lo} {hi}", " ".join(str(p) for p in vals), count=len(vals))


def prime_factors_main(argv: list[str] | None = None) -> None:
    usage = "usage: prime-factors [--serial] n"
    pos, serial = _scan(argv if argv is not None else sys.argv[1:], usage, 1)
    try:
        n = _parse_n(pos[0])
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    facs = prime_factors(n, parallel=not serial)
    _print(str(n), " ".join(str(p) for p in facs), count=len(facs))


def is_prime_power_main(argv: list[str] | None = None) -> None:
    usage = "usage: is-prime-power [--serial] n"
    pos, serial = _scan(argv if argv is not None else sys.argv[1:], usage, 1)
    try:
        n = _parse_n(pos[0])
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    ok = is_prime_power(n, parallel=not serial)
    _print(str(n), "yes" if ok else "no")
    raise SystemExit(0 if ok else 1)


def is_perfect_power_main(argv: list[str] | None = None) -> None:
    usage = "usage: is-perfect-power n"
    pos, _ = _scan(argv if argv is not None else sys.argv[1:], usage, 1)
    try:
        n = _parse_n(pos[0])
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    ok = is_perfect_power(n)
    _print(str(n), "yes" if ok else "no")
    raise SystemExit(0 if ok else 1)

#!/usr/bin/env python3
"""Published is_prime timing table.

Measures wall-clock ``is_prime`` (and a cheap certificate check on the
PR band). Verdicts must be correct. Times are recorded, never gated —
a 200-digit proof is allowed to be slow; PR CI does not run it.

Bands:
  pr       P40, DEFAULT_N, C123 Fermat composite, P100
  main     pr + P150
  nightly  main + P200
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from tests.numbers import (
    DEFAULT_CLI_N,
    P40_H1_FRIENDLY,
    P100_DIGIT,
    P150_DIGIT,
    P200_DIGIT,
    USER_C123,
    USER_C123_FACTOR,
)

# (name, n, expected) — expected is True / False. Never a 10k-digit claim.
PR_ROWS: list[tuple[str, int, bool]] = [
    ("P40_H1", P40_H1_FRIENDLY, True),
    ("DEFAULT_N", DEFAULT_CLI_N, True),
    ("C123", USER_C123, False),
    ("P100", P100_DIGIT, True),
]
MAIN_EXTRA: list[tuple[str, int, bool]] = [
    ("P150", P150_DIGIT, True),
]
NIGHTLY_EXTRA: list[tuple[str, int, bool]] = [
    ("P200", P200_DIGIT, True),
]


def _rows(band: str) -> list[tuple[str, int, bool]]:
    if band == "pr":
        return list(PR_ROWS)
    if band == "main":
        return list(PR_ROWS) + list(MAIN_EXTRA)
    if band == "nightly":
        return list(PR_ROWS) + list(MAIN_EXTRA) + list(NIGHTLY_EXTRA)
    raise SystemExit(f"unknown band: {band}")


def _run_one(name: str, n: int, expect: bool) -> dict[str, Any]:
    from best_prime import is_prime, primality_certificate, verify_certificate

    t0 = time.perf_counter()
    got = is_prime(n)
    ms = (time.perf_counter() - t0) * 1000.0
    if got is not expect:
        raise SystemExit(
            f"{name}: is_prime returned {got!r}, expected {expect!r}"
        )
    row: dict[str, Any] = {
        "name": name,
        "digits": len(str(n)),
        "bits": n.bit_length(),
        "prime": bool(got),
        "is_prime_ms": round(ms, 3),
    }
    if name == "C123":
        assert n % USER_C123_FACTOR == 0
    # Independent arithmetic check — cheap on P40 / DEFAULT_N / C123.
    # P100+ certs are the same search as is_prime; skip on those rows so
    # the PR job is one proof, not two.
    if name in {"P40_H1", "DEFAULT_N", "C123"}:
        t1 = time.perf_counter()
        cert = primality_certificate(n)
        ok = verify_certificate(cert)
        row["cert_ms"] = round((time.perf_counter() - t1) * 1000.0, 3)
        row["cert_ok"] = bool(ok)
        row["cert_kind"] = cert.get("kind") or cert.get("reason")
        if not ok:
            raise SystemExit(f"{name}: certificate failed to verify")
        if expect and cert.get("prime") is not True:
            raise SystemExit(f"{name}: certificate is not a prime proof")
        if not expect and cert.get("prime") is not False:
            raise SystemExit(f"{name}: certificate is not a compositeness witness")
    return row


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--band", choices=("pr", "main", "nightly"), default="pr")
    p.add_argument("--json", default="")
    args = p.parse_args(argv)
    rows = [_run_one(name, n, exp) for name, n, exp in _rows(args.band)]
    print(f"# timing_table band={args.band}")
    print()
    print("| name | digits | bits | prime | is_prime_ms | cert |")
    print("|------|-------:|-----:|:-----:|------------:|------|")
    for r in rows:
        cert = r.get("cert_kind", "—")
        if "cert_ms" in r:
            cert = f"{cert} ({r['cert_ms']} ms)"
        print(
            f"| {r['name']} | {r['digits']} | {r['bits']} | "
            f"{'yes' if r['prime'] else 'no'} | {r['is_prime_ms']:.1f} | {cert} |"
        )
    print()
    print(
        "Times are this machine, this run. 10k-digit / 10 s is the "
        "north-star and is not claimed."
    )
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"band": args.band, "rows": rows}, fh, indent=2)
            fh.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

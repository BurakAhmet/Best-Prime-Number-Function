"""Public exceptions for the deterministic primality API."""

from __future__ import annotations


class UnsettledPrimalityError(Exception):
    """``n`` is too large for AKS and no complete engine settled it.

    ``is_prime`` must not return False for an unproved prime. Above
    ``AKS_SKIP_BITS`` a miss raises this instead of starting Kronecker AKS.
    """

    def __init__(self, n: int) -> None:
        self.n = int(n)
        super().__init__(
            f"primality of {self.n.bit_length()}-bit n is unsettled "
            f"(no ECPP / BLS decision; AKS skipped). FastECPP is the "
            f"planned engine for this size."
        )

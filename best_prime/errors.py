"""Public exceptions for the deterministic primality API."""

from __future__ import annotations


class UnsettledPrimalityError(Exception):
    """No complete engine proved ``n`` prime or composite.

    ``is_prime`` must not return False for an unproved prime. A miss
    raises this. Kronecker AKS is not in the library.
    """

    def __init__(self, n: int) -> None:
        self.n = int(n)
        super().__init__(
            f"primality of {self.n.bit_length()}-bit n is unsettled "
            f"(no BLS / FastECPP / cyclotomic decision)."
        )


class UnsettledFactorError(Exception):
    """``prime_factors`` stopped because ``max_ms`` expired.

    ``found`` is the prime factors already isolated; ``leftover`` is the
    still-composite remainder. The product of ``found`` and ``leftover``
    reconstructs the original ``n`` (up to units already stripped).
    """

    def __init__(self, n: int, *, leftover: int, found: list[int]) -> None:
        self.n = int(n)
        self.leftover = int(leftover)
        self.found = [int(p) for p in found]
        super().__init__(
            f"factorization of {self.n.bit_length()}-bit n unsettled "
            f"(leftover {self.leftover.bit_length()} bits; "
            f"{len(self.found)} prime factors isolated)"
        )

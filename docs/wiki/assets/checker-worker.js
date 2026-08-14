/* Deterministic primality lab worker (Pages).
 * Mirrors the library ladder in-browser:
 *   small precheck → (n ≥ 256 bits: class-number-1 ECPP first)
 *   → combined BLS (n−1 Pocklington / Lucas n+1 / Combined Theorem 1)
 *   → class-number-1 Atkin–Morain ECPP → 30-wheel trial when practical.
 *   Factoring: trial → Fermat → Brent → p−1 → Montgomery ECM (Suyama).
 *   Huge leftovers use a short ECM budget so 131-digit n cannot hang in BLS.
 *   ECPP point mul is Jacobian (one inversion); a wrong-order curve is the
 *   next (q,c) pair, not “point at infinity”. Peel of m is a cached stack.
 *   No hard digit / √n size ban: if proof is impractical, return path=inconclusive.
 * Not the OpenMP C core; no stochastic Miller–Rabin. No AKS in-tab.
 * Self-test: node docs/wiki/assets/checker-worker.js --self-test
 */
(function (g) {
  const STEPS = [4, 2, 4, 2, 4, 6, 2, 6];
  const STEPS_B = [4n, 2n, 4n, 2n, 4n, 6n, 2n, 6n];
  const SMALL = [3n, 5n, 7n, 11n, 13n, 17n, 19n, 23n, 29n, 31n, 37n, 41n, 43n, 47n, 53n];
  const SMALL_N = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53];
  const MAX_SAFE = BigInt(Number.MAX_SAFE_INTEGER);
  const TWO64 = 1n << 64n;
  const BASES = [2n, 3n, 5n, 7n, 11n, 13n, 17n, 19n, 23n, 29n, 31n, 37n];
  /** Confirm in the UI when pure trial would be long. */
  const WARN_ISQRT = 8_000_000n;
  /**
   * Soft budget for automatic pure 30-wheel trial (not a ban on n).
   * Above this √n, if n−1 is inconclusive we report inconclusive rather than spinning forever.
   * There is no digit-length hard limit.
   */
  const TRIAL_SOFT_ISQRT = 50_000_000_000n;
  /** Try n−1 once √n is past mid-size wheel comfort (or multi-limb). */
  const NM1_ISQRT = 10_000_000n;
  const TRIAL_BOUND_DEFAULT = 100_000;
  const TRIAL_BOUND_MID = 1_000_000;
  const TRIAL_BOUND_BIG = 5_000_000;
  const TRIAL_BOUND_HUGE = 50_000;
  /** Match Python _adaptive_trial_bound for 256–280-bit curve orders. */
  const TRIAL_BOUND_NEAR_HUGE = 200_000;
  /** Match Python: ECPP before a deep BLS peel. */
  const HUGE_BITS = 256;

  const P1_B1 = 250_000;
  /** Exact trial allowed when proving an n−1 cofactor (not the original n). */
  const COFACTOR_TRIAL_ISQRT = 150_000_000_000n;
  /** Brent cycle cap — match the Python library (1<<22), not a tiny browser cut. */
  const BRENT_MAX_R = 1n << 22n;

  let _primesCache = null;
  let _primesCacheLimit = 0;

  function isqrt(n) {
    if (n < 2n) return n;
    let x = n;
    let y = (x + 1n) >> 1n;
    while (y < x) {
      x = y;
      y = (x + n / x) >> 1n;
    }
    return x;
  }

  function icbrt(n) {
    if (n < 8n) return n < 1n ? 0n : 1n;
    let x = 1n << BigInt(Math.floor((bitLength(n) + 2) / 3));
    for (;;) {
      const y = (2n * x + n / (x * x)) / 3n;
      if (y >= x) return x;
      x = y;
    }
  }

  function isSquare(n) {
    if (n < 0n) return false;
    const s = isqrt(n);
    return s * s === n;
  }

  /**
   * BLS n^{1/3} extra (t5k / BLS75): n-1 = F R, n < 2 F^3,
   * R = r F + s with 0 < s < F, and (r odd or s²−4r not square).
   */
  function blsCubicOk(n, F) {
    if (F <= 1n || (n - 1n) % F !== 0n) return false;
    if (n >= 2n * F * F * F) return false;
    const R = (n - 1n) / F;
    if (R <= 0n || gcd(F, R) !== 1n) return false;
    const r = R / F;
    const s = R % F;
    if (s <= 0n || s >= F) return false;
    if ((r & 1n) === 1n) return true;
    return !isSquare(s * s - 4n * r);
  }

  /** Combined Theorem 1: n < max(F²G/2, FG²/2) and gcd(F,G)=2. Not FG > √n. */
  function combinedTheorem1Ok(n, F, G) {
    if (F <= 1n || G <= 1n) return false;
    if (gcd(F, G) !== 2n) return false;
    if ((n - 1n) % F !== 0n || (n + 1n) % G !== 0n) return false;
    const a = (F * F * G) / 2n;
    const b = (F * G * G) / 2n;
    return n < (a > b ? a : b);
  }

  function gkMinQ(n) {
    const r = isqrt(isqrt(n));
    return (r + 2n) * (r + 2n);
  }

  function jacobi(a, n) {
    if (n <= 0n || (n & 1n) === 0n) return 0;
    a %= n;
    if (a < 0n) a += n;
    let t = 1;
    while (a !== 0n) {
      while ((a & 1n) === 0n) {
        a >>= 1n;
        const r = n & 7n;
        if (r === 3n || r === 5n) t = -t;
      }
      const tmp = a;
      a = n;
      n = tmp;
      if ((a & 3n) === 3n && (n & 3n) === 3n) t = -t;
      a %= n;
    }
    return n === 1n ? t : 0;
  }

  /** Selfridge D: 5, −7, 9, −11, … used only to pick a Lucas witness. */
  function selfridgeParams(n) {
    let absD = 5n;
    let sign = 1n;
    for (let i = 0; i < 80; i++) {
      const D = sign * absD;
      const j = jacobi(D, n);
      if (j === 0) {
        const g = gcd(D < 0n ? -D : D, n);
        if (g > 1n && g < n) return { factor: g };
      } else if (j === -1) {
        return { D: D, P: 1n, Q: (1n - D) / 4n };
      }
      absD += 2n;
      sign = -sign;
    }
    return null;
  }

  /** Binary Lucas ladder. Returns {U,V,Qk} or {factor}. */
  function lucasUv(k, P, Q, n) {
    if ((n & 1n) === 0n) return null;
    const inv2 = modInv(2n, n);
    if (inv2 === null) {
      const g = gcd(2n, n);
      return g > 1n && g < n ? { factor: g } : null;
    }
    const D = P * P - 4n * Q;
    let U = 0n;
    let V = 2n;
    let Qk = 1n;
    if (k === 0n) return { U: U, V: V, Qk: Qk };
    const bits = bitLength(k);
    let seen = false;
    for (let i = bits - 1; i >= 0; i--) {
      if (seen) {
        U = (U * V) % n;
        V = (V * V - 2n * Qk) % n;
        if (V < 0n) V += n;
        Qk = (Qk * Qk) % n;
      }
      if ((k >> BigInt(i)) & 1n) {
        seen = true;
        const Up = ((P * U + V) * inv2) % n;
        const Vp = ((D * U + P * V) * inv2) % n;
        Qk = (Qk * Q) % n;
        U = Up < 0n ? Up + n : Up;
        V = Vp < 0n ? Vp + n : Vp;
      }
    }
    return { U: U, V: V, Qk: Qk };
  }

  function conditionII(n, primesOfG, onTick) {
    const pick = selfridgeParams(n);
    if (!pick) return { ok: null, factor: null };
    if (pick.factor) return { ok: false, factor: pick.factor };
    const full = lucasUv(n + 1n, pick.P, pick.Q, n);
    if (!full) return { ok: null, factor: null };
    if (full.factor) return { ok: false, factor: full.factor };
    if (full.U % n !== 0n) return { ok: null, factor: null };
    for (let i = 0; i < primesOfG.length; i++) {
      const q = primesOfG[i];
      emit(onTick, "lucas", BigInt(i + 1), BigInt(primesOfG.length), {
        q: String(q),
        D: String(pick.D),
      });
      const uq = lucasUv((n + 1n) / q, pick.P, pick.Q, n);
      if (!uq) return { ok: null, factor: null };
      if (uq.factor) return { ok: false, factor: uq.factor };
      const g = gcd(uq.U, n);
      if (g > 1n && g < n) return { ok: false, factor: g };
      if (g !== 1n) return { ok: null, factor: null };
    }
    return { ok: true, factor: null, lucas: pick };
  }

  function gcd(a, b) {
    a = a < 0n ? -a : a;
    b = b < 0n ? -b : b;
    while (b !== 0n) {
      const t = a % b;
      a = b;
      b = t;
    }
    return a;
  }

  /** Inverse of a mod m, or null if gcd(a, m) ≠ 1. */
  function modInv(a, m) {
    let t = 0n;
    let newt = 1n;
    let r = m;
    let newr = ((a % m) + m) % m;
    while (newr !== 0n) {
      const q = r / newr;
      const tmpT = newt;
      newt = t - q * newt;
      t = tmpT;
      const tmpR = newr;
      newr = r - q * newr;
      r = tmpR;
    }
    if (r > 1n) return null;
    if (t < 0n) t += m;
    return t;
  }

  function umod64(lo, hi, d) {
    let r = (hi >>> 16) % d;
    r = (r * 65536 + (hi & 0xffff)) % d;
    r = (r * 65536 + (lo >>> 16)) % d;
    r = (r * 65536 + (lo & 0xffff)) % d;
    return r;
  }

  function primesUpto(limit) {
    const need = Math.min(Math.max(2, limit | 0), TRIAL_BOUND_BIG);
    if (_primesCache && _primesCacheLimit >= need) {
      return _primesCache;
    }
    const n = need;
    const sieve = new Uint8Array(n + 1);
    sieve.fill(1);
    sieve[0] = 0;
    sieve[1] = 0;
    for (let i = 2; i * i <= n; i++) {
      if (!sieve[i]) continue;
      for (let j = i * i; j <= n; j += i) sieve[j] = 0;
    }
    const out = [];
    for (let i = 2; i <= n; i++) if (sieve[i]) out.push(i);
    _primesCache = out;
    _primesCacheLimit = n;
    return out;
  }

  function adaptiveTrialBound(m) {
    const bits = bitLength(m);
    if (bits <= 40) return TRIAL_BOUND_DEFAULT;
    if (bits <= 80) return TRIAL_BOUND_MID;
    if (bits >= 281) return TRIAL_BOUND_HUGE;
    if (bits >= HUGE_BITS) return TRIAL_BOUND_NEAR_HUGE;
    return TRIAL_BOUND_BIG;
  }

  function bitLength(n) {
    if (n <= 0n) return 0;
    let b = 0;
    let x = n;
    while (x > 0n) {
      x >>= 1n;
      b++;
    }
    return b;
  }

  function done(prime, path, factor, note, limit, t0) {
    return {
      prime: prime,
      path: path,
      factor: factor == null ? null : factor.toString(),
      isqrt: limit.toString(),
      ms: typeof performance !== "undefined" ? performance.now() - t0 : 0,
      note: note,
    };
  }

  /** Structured progress so the UI can mirror the live engine stage. */
  function emit(onTick, phase, i, limit, extra) {
    if (!onTick) return;
    const info = {
      phase: phase,
      i: i == null ? 0n : typeof i === "bigint" ? i : BigInt(i),
      limit: limit == null ? 1n : typeof limit === "bigint" ? limit : BigInt(limit),
      extra: extra || {},
    };
    try {
      onTick(info);
    } catch (_) {
      try {
        onTick(info.i, info.limit);
      } catch (__) {
        /* ignore */
      }
    }
  }

  function fermatSaysComposite(n) {
    if (n < 2n) return true;
    for (let i = 0; i < 6; i++) {
      const a = BASES[i];
      if (a % n === 0n) return n !== a;
      if (powBig(a, n - 1n, n) !== 1n) return true;
    }
    return false;
  }

  /** Proper factor of a known composite, or null. */
  function extractFactor(n, onTick, shouldStop) {
    if (n < 4n) return null;
    if ((n & 1n) === 0n) return 2n;
    for (let k = 0; k < SMALL.length; k++) {
      const p = SMALL[k];
      if (n % p === 0n) return n === p ? null : p;
    }
    for (let i = 0; i < BASES.length; i++) {
      const a = BASES[i];
      if (a % n === 0n) return a < n ? a : null;
      const ap = powBig(a, n - 1n, n);
      if (ap !== 1n) {
        let g = gcd(ap - 1n, n);
        if (g > 1n && g < n) return g;
        g = gcd(a - 1n, n);
        if (g > 1n && g < n) return g;
      }
    }
    emit(onTick, "split", 0n, 1n, { label: "searching for a factor of n" });
    return trySplitCofactor(n, onTick, shouldStop);
  }

  function trialSplit(m, bound) {
    const fac = new Map();
    if (m <= 1n) return { fac: fac, rem: m };
    let x = m;
    const primes = primesUpto(bound);
    for (let k = 0; k < primes.length; k++) {
      const p = BigInt(primes[k]);
      if (p > BigInt(bound) || p * p > x) break;
      if (x % p === 0n) {
        let e = 0;
        while (x % p === 0n) {
          x /= p;
          e++;
        }
        fac.set(p, (fac.get(p) || 0) + e);
        if (x === 1n) break;
      }
    }
    return { fac: fac, rem: x };
  }

  function FValue(fac) {
    let prod = 1n;
    for (const [q, e] of fac) {
      for (let i = 0; i < e; i++) prod *= q;
    }
    return prod;
  }

  function fermatSplit(n, rounds) {
    rounds = rounds || 65536;
    if (n < 4n || (n & 1n) === 0n) return null;
    let a = isqrt(n);
    if (a * a < n) a += 1n;
    for (let i = 0; i < rounds; i++) {
      const b2 = a * a - n;
      const b = isqrt(b2);
      if (b * b === b2 && b !== 0n) {
        const f = a - b;
        if (f > 1n && f < n) return f;
      }
      a += 1n;
    }
    return null;
  }

  function brent(n, c, x0, maxR) {
    if (x0 === undefined) x0 = 2n;
    if (maxR === undefined) maxR = BRENT_MAX_R;
    let y = x0 % n;
    let g = 1n;
    let q = 1n;
    let ys = y;
    let r = 1n;
    const m = 512n;
    let x = y;
    while (g === 1n && r <= maxR) {
      x = y;
      for (let i = 0n; i < r; i++) y = (y * y + c) % n;
      let k = 0n;
      while (k < r && g === 1n) {
        ys = y;
        let lim = r - k;
        if (lim > m) lim = m;
        for (let i = 0n; i < lim; i++) {
          y = (y * y + c) % n;
          let diff = x - y;
          if (diff < 0n) diff = -diff;
          q = (q * diff) % n;
        }
        g = gcd(q, n);
        k += m;
      }
      r <<= 1n;
    }
    if (g === 1n) return n;
    if (g === n) {
      for (;;) {
        ys = (ys * ys + c) % n;
        let diff = x - ys;
        if (diff < 0n) diff = -diff;
        g = gcd(diff, n);
        if (g > 1n) break;
      }
    }
    return g;
  }

  function pollardP1(n, B1) {
    B1 = B1 || P1_B1;
    if (n < 4n || (n & 1n) === 0n) return (n & 1n) === 0n && n > 2n ? 2n : null;
    let a = 2n;
    const primes = primesUpto(B1);
    for (let k = 0; k < primes.length; k++) {
      const p = primes[k];
      if (p > B1) break;
      let pe = p;
      while (pe <= Math.floor(B1 / p)) pe *= p;
      a = modPow(a, BigInt(pe), n);
      if (a === 0n) return null;
    }
    const g = gcd(a - 1n, n);
    if (g > 1n && g < n) return g;
    return null;
  }

  function modPow(base, exp, mod) {
    return powBig(base, exp, mod);
  }

  function powBig(base, exp, mod) {
    // BigInt ** works in modern engines; use binary for portability.
    let b = ((base % mod) + mod) % mod;
    let e = exp;
    let r = 1n;
    while (e > 0n) {
      if (e & 1n) r = (r * b) % mod;
      b = (b * b) % mod;
      e >>= 1n;
    }
    return r;
  }

  function trySplitCofactor(c, onTick, shouldStop) {
    const bound = adaptiveTrialBound(c);
    const ts = trialSplit(c, bound);
    if (ts.fac.size) {
      // return a proper factor
      let minP = null;
      for (const p of ts.fac.keys()) {
        if (minP === null || p < minP) minP = p;
      }
      if (minP !== null && minP < c) return minP;
    }
    if (ts.rem > 1n && ts.rem < c) return ts.rem;

    const bits = bitLength(c);
    // Mid-size hostile n−1 (hard55) still gets a deep peel.
    // ≥256-bit leftovers skip that: ECPP needs a cheap p8-class ECM, not minutes.
    const fermatRounds = bits >= HUGE_BITS ? 256 : bits > 140 ? 8192 : bits > 100 ? 4096 : 2048;
    const brentCurves = bits > 200 ? 0n : bits > 140 ? 16n : bits > 100 ? 32n : 64n;
    const brentMaxR = bits > 140 ? (1n << 18n) : bits > 100 ? (1n << 20n) : BRENT_MAX_R;
    const p1B1 = bits >= HUGE_BITS ? 0 : bits > 140 ? 1_000_000 : bits > 100 ? 500_000 : P1_B1;

    emit(onTick, "split", 0n, 4n, { label: "Fermat near-square probe" });
    let f = fermatSplit(c, fermatRounds);
    if (f && f > 1n && f < c) return f;

    for (let cv = 1n; cv <= brentCurves; cv++) {
      if (shouldStop && shouldStop()) return null;
      if ((cv & 7n) === 0n) {
        emit(onTick, "brent", cv, brentCurves, { curve: String(cv) });
      }
      const g = brent(c, cv, 2n, brentMaxR);
      if (g > 1n && g < c) return g;
    }

    if (p1B1 > 0) {
      emit(onTick, "p1", 1n, 1n, { B1: String(p1B1) });
      f = pollardP1(c, p1B1);
      if (f && f > 1n && f < c) return f;
    }

    f = ecmFactor(c, onTick, shouldStop, 6, ecmMaxMs(bits));
    if (f && f > 1n && f < c) return f;
    if (bits < HUGE_BITS) {
      f = ecmFactor(c, onTick, shouldStop, 806, ecmMaxMs(bits));
      if (f && f > 1n && f < c) return f;
    }
    return null;
  }

  function ecmMaxMs(bits) {
    if (bits <= 40) return 50;
    if (bits <= 64) return 200;
    if (bits <= 80) return 500;
    if (bits <= 100) return 2000;
    if (bits <= 160) return 8000;
    if (bits < HUGE_BITS) return 60000;
    return 2000;
  }

  function ecmPhases(bits) {
    // Montgomery ECM (Suyama). Phases: cheap B1 first, then deeper.
    if (bits <= 40) return [{ B1: 500, curves: 16 }];
    if (bits <= 64) return [{ B1: 2_000, curves: 40 }];
    if (bits <= 80) return [{ B1: 5_000, curves: 80 }];
    if (bits <= 100) return [{ B1: 11_000, curves: 120 }];
    if (bits <= 140) return [
      { B1: 11_000, curves: 100 },
      { B1: 25_000, curves: 140 },
    ];
    if (bits < HUGE_BITS) {
      // 22-digit factors of ~170-bit n−1 cofactors (hard55 exhibit).
      return [
        { B1: 2_000, curves: 40 },
        { B1: 11_000, curves: 160 },
        { B1: 25_000, curves: 220 },
        { B1: 50_000, curves: 280 },
      ];
    }
    // 131-digit yardstick: match Python p8-class Montgomery budget.
    return [{ B1: 6_000, curves: 6 }];
  }

  /** Python `_schedule` / `_ecm_max_ms` used when peeling ECPP curve orders. */
  function ecmPeelPhases(bits) {
    if (bits <= 40) return [{ B1: 200, curves: 8 }];
    if (bits <= 64) return [{ B1: 2_000, curves: 24 }];
    if (bits <= 80) return [{ B1: 5_000, curves: 40 }];
    if (bits <= 100) return [{ B1: 2_000, curves: 20 }];
    if (bits <= 160) return [{ B1: 5_000, curves: 24 }];
    if (bits <= 280) return [{ B1: 8_000, curves: 8 }];
    return [{ B1: 6_000, curves: 6 }];
  }

  function ecmPeelMaxMs(bits) {
    if (bits <= 40) return 50;
    if (bits <= 64) return 200;
    if (bits <= 80) return 500;
    if (bits <= 100) return 2000;
    if (bits <= 160) return 8000;
    if (bits <= 220) return 2000;
    return 2000;
  }

  function montDbl(x, z, A24, n) {
    const xpz = (x + z) % n;
    const xmz = (x - z + n) % n;
    const xpz2 = (xpz * xpz) % n;
    const xmz2 = (xmz * xmz) % n;
    const x2 = (xpz2 * xmz2) % n;
    const d = (xpz2 - xmz2 + n) % n;
    const z2 = (d * ((xmz2 + A24 * d) % n)) % n;
    return [x2, z2];
  }

  function montAdd(x1, z1, x2, z2, x0, z0, n) {
    const u = (((x2 - z2 + n) % n) * ((x1 + z1) % n)) % n;
    const v = (((x2 + z2) % n) * ((x1 - z1 + n) % n)) % n;
    const upv = (u + v) % n;
    const umv = (u - v + n) % n;
    const x3 = (((z0 * upv) % n) * upv) % n;
    const z3 = (((x0 * umv) % n) * umv) % n;
    return [x3, z3];
  }

  function montMul(k, x, z, A24, n) {
    if (k === 0n) return [0n, 0n];
    let R0x = x;
    let R0z = z;
    let dbl = montDbl(x, z, A24, n);
    let R1x = dbl[0];
    let R1z = dbl[1];
    let bits = bitLength(k) - 2;
    while (bits >= 0) {
      if ((k >> BigInt(bits)) & 1n) {
        const ad = montAdd(R0x, R0z, R1x, R1z, x, z, n);
        R0x = ad[0];
        R0z = ad[1];
        dbl = montDbl(R1x, R1z, A24, n);
        R1x = dbl[0];
        R1z = dbl[1];
      } else {
        const ad = montAdd(R1x, R1z, R0x, R0z, x, z, n);
        R1x = ad[0];
        R1z = ad[1];
        dbl = montDbl(R0x, R0z, A24, n);
        R0x = dbl[0];
        R0z = dbl[1];
      }
      bits--;
    }
    return [R0x, R0z];
  }

  /** Deterministic Montgomery ECM (Suyama σ = 6, 7, …). No RNG. */
  function ecmFactor(n, onTick, shouldStop, sigma0, maxMs, phasesOpt) {
    if (n < 4n || (n & 1n) === 0n) return n % 2n === 0n && n > 2n ? 2n : null;
    const bits = bitLength(n);
    const phases = phasesOpt || ecmPhases(bits);
    let sigmaBase = sigma0 == null ? 6 : sigma0;
    let doneCurves = 0;
    let totalCurves = 0;
    const tEcm =
      maxMs != null && typeof performance !== "undefined" ? performance.now() : null;
    for (let p = 0; p < phases.length; p++) totalCurves += phases[p].curves;
    for (let ph = 0; ph < phases.length; ph++) {
      const sch = phases[ph];
      const primes = primesUpto(sch.B1);
      const stage1 = [];
      for (let k = 0; k < primes.length; k++) {
        if (primes[k] <= sch.B1) stage1.push(primes[k]);
      }
      for (let i = 0; i < sch.curves; i++) {
        if (shouldStop && shouldStop()) return null;
        if (tEcm != null && performance.now() - tEcm >= maxMs) return null;
        doneCurves++;
        const sigma = BigInt(sigmaBase + i);
        emit(onTick, "ecm", BigInt(doneCurves), BigInt(totalCurves), {
          sigma: String(sigma),
          B1: String(sch.B1),
        });
        const u = (sigma * sigma - 5n) % n;
        const v = (4n * sigma) % n;
        const x = (((u * u) % n) * u) % n;
        const z = (((v * v) % n) * v) % n;
        const t = (v - u + n) % n;
        let num = (((t * t) % n) * t) % n;
        num = (num * ((3n * u + v) % n)) % n;
        const den = (16n * ((((u * u) % n) * u) % n) * v) % n;
        const g0 = gcd(den, n);
        if (g0 > 1n && g0 < n) return g0;
        if (g0 === n) continue;
        const inv = modInv(den, n);
        if (inv === null) continue;
        const A24 = (num * inv) % n;
        let Px = x;
        let Pz = z;
        for (let j = 0; j < stage1.length; j++) {
          let pe = stage1[j];
          while (pe <= Math.floor(sch.B1 / stage1[j])) pe *= stage1[j];
          const Q = montMul(BigInt(pe), Px, Pz, A24, n);
          Px = Q[0];
          Pz = Q[1];
          if (Pz === 0n) break;
        }
        const g = gcd(Pz, n);
        if (g > 1n && g < n) return g;
      }
      sigmaBase += sch.curves;
    }
    return null;
  }

  /** Exact trial for moderate n (√n as Number or BigInt). */
  function trialIsPrime(n, onTick, shouldStop) {
    if (n < 2n) return false;
    if (n < 4n) return true;
    if ((n & 1n) === 0n) return false;
    for (let k = 0; k < SMALL.length; k++) {
      const p = SMALL[k];
      if (n === p) return true;
      if (n % p === 0n) return false;
      if (p * p > n) return true;
    }
    const limit = isqrt(n);
    if (limit > TRIAL_SOFT_ISQRT) return null; // skip automatic pure trial of original n
    if (n <= MAX_SAFE) {
      const r = trialNumber(Number(n), Number(limit), 0, onTick, shouldStop);
      if (r.aborted) return null;
      return r.prime === true;
    }
    if (n < TWO64) {
      const r = trialU64(n, Number(limit), limit, 0, onTick, shouldStop);
      if (r.aborted) return null;
      return r.prime === true;
    }
    const r = trialBig(n, limit, 0, onTick, shouldStop);
    if (r.aborted) return null;
    return r.prime === true;
  }

  /** Exact wheel trial used only to prove n−1 cofactors (higher √n budget). */
  function trialIsPrimeCofactor(n, limit, onTick, shouldStop) {
    if (n < 2n) return false;
    if (n < 4n) return true;
    if ((n & 1n) === 0n) return false;
    for (let k = 0; k < SMALL.length; k++) {
      const p = SMALL[k];
      if (n === p) return true;
      if (n % p === 0n) return false;
      if (p * p > n) return true;
    }
    if (n <= MAX_SAFE) {
      const r = trialNumber(Number(n), Number(limit), 0, onTick, shouldStop);
      if (r.aborted) return null;
      return r.prime === true;
    }
    if (n < TWO64) {
      const r = trialU64(n, Number(limit), limit, 0, onTick, shouldStop);
      if (r.aborted) return null;
      return r.prime === true;
    }
    const r = trialBig(n, limit, 0, onTick, shouldStop);
    if (r.aborted) return null;
    return r.prime === true;
  }

  function cofactorIsPrime(c, depth, onTick, shouldStop) {
    if (c < 2n) return false;
    if (c < 4n) return true;
    if ((c & 1n) === 0n) return c === 2n;
    const lim = isqrt(c);
    // Cheap exact trial first.
    if (lim <= 2_000_000n) {
      const t = trialIsPrimeCofactor(c, lim, onTick, shouldStop);
      return t === true;
    }
    // Prefer n−1 (often cheaper than walking √c) before a long cofactor trial.
    if (depth < 6) {
      const r = nm1Primality(c, depth + 1, onTick, shouldStop);
      if (r.prime === true) return true;
      if (r.prime === false) return false;
    }
    if (lim <= COFACTOR_TRIAL_ISQRT) {
      const t = trialIsPrimeCofactor(c, lim, onTick, shouldStop);
      return t === true;
    }
    return false;
  }

  function factorEnough(n, depth, onTick, shouldStop) {
    const target = isqrt(n);
    let m = n - 1n;
    const fac = new Map();
    const bound = adaptiveTrialBound(m);
    const peeled = trialSplit(m, bound);
    for (const [p, e] of peeled.fac) fac.set(p, (fac.get(p) || 0) + e);
    const stack = [];
    if (peeled.rem > 1n) stack.push(peeled.rem);
    let splits = 0;
    const maxSplits = 48;

    function doneFac() {
      const F = FValue(fac);
      return F > target || n < 2n * F * F * F;
    }
    if (doneFac()) return fac;

    while (stack.length && !doneFac()) {
      if (shouldStop && shouldStop()) return null;
      let c = stack.pop();
      if (c <= 1n) continue;
      const sub = trialSplit(c, adaptiveTrialBound(c));
      for (const [p, e] of sub.fac) fac.set(p, (fac.get(p) || 0) + e);
      if (sub.rem === 1n) {
        if (doneFac()) return fac;
        continue;
      }
      c = sub.rem;
      // If Fermat fails, c is composite — split before a useless n−1 recurse.
      // If Fermat holds, c may be prime; do not ECM a probable prime first.
      if (
        splits < maxSplits &&
        isqrt(c) > COFACTOR_TRIAL_ISQRT &&
        fermatSaysComposite(c)
      ) {
        splits++;
        emit(onTick, "split", BigInt(splits), BigInt(maxSplits), {
          bits: String(bitLength(c)),
        });
        const f = trySplitCofactor(c, onTick, shouldStop);
        if (f && f > 1n && f < c) {
          const lo = f < c / f ? f : c / f;
          stack.push(c / lo);
          stack.push(lo);
          continue;
        }
      }
      if (cofactorIsPrime(c, depth, onTick, shouldStop)) {
        fac.set(c, (fac.get(c) || 0) + 1);
        if (doneFac()) return fac;
        continue;
      }
      if (splits >= maxSplits) return null;
      splits++;
      emit(onTick, "split", BigInt(splits), BigInt(maxSplits), {
        bits: String(bitLength(c)),
      });
      const f = trySplitCofactor(c, onTick, shouldStop);
      if (f === null || f <= 1n || f >= c) return null;
      const lo = f < c / f ? f : c / f;
      stack.push(c / lo);
      stack.push(lo);
    }
    return doneFac() ? fac : null;
  }

  /** Factor n+1 until G > √n or G = n+1. */
  function factorEnoughPlus(n, depth, onTick, shouldStop) {
    const target = isqrt(n);
    let m = n + 1n;
    const fac = new Map();
    const peeled = trialSplit(m, adaptiveTrialBound(m));
    for (const [p, e] of peeled.fac) fac.set(p, (fac.get(p) || 0) + e);
    const stack = [];
    if (peeled.rem > 1n) stack.push(peeled.rem);
    let splits = 0;
    const maxSplits = 48;

    function doneG() {
      const G = FValue(fac);
      return G > target || G === n + 1n;
    }
    if (doneG()) return fac;

    while (stack.length && !doneG()) {
      if (shouldStop && shouldStop()) return null;
      let c = stack.pop();
      if (c <= 1n) continue;
      const sub = trialSplit(c, adaptiveTrialBound(c));
      for (const [p, e] of sub.fac) fac.set(p, (fac.get(p) || 0) + e);
      if (sub.rem === 1n) {
        if (doneG()) return fac;
        continue;
      }
      c = sub.rem;
      if (cofactorIsPrime(c, depth, onTick, shouldStop)) {
        fac.set(c, (fac.get(c) || 0) + 1);
        if (doneG()) return fac;
        continue;
      }
      if (splits >= maxSplits) return null;
      splits++;
      emit(onTick, "split", BigInt(splits), BigInt(maxSplits), {
        bits: String(bitLength(c)),
        label: "factoring n+1",
      });
      const f = trySplitCofactor(c, onTick, shouldStop);
      if (f === null || f <= 1n || f >= c) return null;
      const lo = f < c / f ? f : c / f;
      stack.push(c / lo);
      stack.push(lo);
    }
    return doneG() ? fac : null;
  }

  function pocklington(n, primesOfF, onTick) {
    const fermatOk = new Map();
    for (let qi = 0; qi < primesOfF.length; qi++) {
      const q = primesOfF[qi];
      emit(onTick, "pocklington", BigInt(qi + 1), BigInt(primesOfF.length), {
        q: String(q),
      });
      let found = false;
      for (let ai = 0; ai < BASES.length; ai++) {
        const a = BASES[ai];
        if (a % n === 0n) {
          return { ok: n === a, factor: n === a ? null : a };
        }
        let ok = fermatOk.get(a);
        if (ok === undefined) {
          ok = powBig(a, n - 1n, n) === 1n;
          fermatOk.set(a, ok);
        }
        if (!ok) {
          let g = gcd(powBig(a, n - 1n, n) - 1n, n);
          if (!(g > 1n && g < n)) g = null;
          return { ok: false, factor: g };
        }
        const g = gcd(powBig(a, (n - 1n) / q, n) - 1n, n);
        if (g > 1n && g < n) return { ok: false, factor: g };
        if (g === 1n) {
          found = true;
          break;
        }
      }
      if (!found) return { ok: null, factor: null };
    }
    return { ok: true, factor: null };
  }

  /** {prime: true|false|null, factor}. */
  function nm1Primality(n, depth, onTick, shouldStop) {
    if (depth === undefined) depth = 0;
    if (n < 2n) return { prime: false, factor: null };
    if (n === 2n || n === 3n || n === 5n || n === 7n) {
      return { prime: true, factor: null };
    }
    if ((n & 1n) === 0n) return { prime: false, factor: 2n };
    if (n % 3n === 0n) return { prime: false, factor: 3n };
    if (n % 5n === 0n) return { prime: false, factor: 5n };

    for (let i = 0; i < 6; i++) {
      const a = BASES[i];
      emit(onTick, "fermat", BigInt(i + 1), 6n, { base: String(a) });
      if (a % n === 0n) return { prime: n === a, factor: n === a ? null : a };
      if (powBig(a, n - 1n, n) !== 1n) {
        let g = gcd(powBig(a, n - 1n, n) - 1n, n);
        if (!(g > 1n && g < n)) g = null;
        return { prime: false, factor: g };
      }
    }

    emit(onTick, "split", 0n, 1n, { label: "factoring n−1" });
    const fac = factorEnough(n, depth, onTick, shouldStop);
    if (!fac) return { prime: null, factor: null };

    const F = FValue(fac);
    if (F <= 1n || (n - 1n) % F !== 0n) return { prime: null, factor: null };
    const sqrtN = isqrt(n);
    const cubic = n < 2n * F * F * F;
    if (F <= sqrtN && !cubic) return { prime: null, factor: null };

    const primes = Array.from(fac.keys()).sort(function (a, b) {
      return a === b ? 0 : a > b ? -1 : 1;
    });
    const target = F > sqrtN ? sqrtN : icbrt(n);
    const used = [];
    let prod = 1n;
    for (let i = 0; i < primes.length; i++) {
      const q = primes[i];
      const e = fac.get(q);
      for (let j = 0; j < e; j++) {
        if (prod > target) break;
        prod *= q;
      }
      used.push(q);
      emit(onTick, "pocklington", prod, target, {
        F: String(prod),
        target: String(target),
        q: String(q),
      });
      if (prod > target) break;
    }
    const pk = pocklington(n, used, onTick);
    if (pk.ok === true && prod <= sqrtN) {
      if (!blsCubicOk(n, prod)) return { prime: null, factor: pk.factor || null };
    }
    return { prime: pk.ok, factor: pk.factor || null };
  }

  /** Combined BLS: n−1, then Lucas n+1, then Combined Theorem 1. */
  function blsPrimality(n, depth, onTick, shouldStop) {
    const nm1 = nm1Primality(n, depth, onTick, shouldStop);
    if (nm1.prime === true) return { prime: true, factor: null, side: "nm1" };
    if (nm1.prime === false) return { prime: false, factor: nm1.factor, side: "nm1" };

    emit(onTick, "split", 0n, 1n, { label: "factoring n+1" });
    const facG = factorEnoughPlus(n, depth, onTick, shouldStop);
    if (facG) {
      const G = FValue(facG);
      const primesG = Array.from(facG.keys()).sort(function (a, b) {
        return a === b ? 0 : a > b ? -1 : 1;
      });
      if (G > isqrt(n) || G === n + 1n) {
        const ii = conditionII(n, primesG, onTick);
        if (ii.ok === false) return { prime: false, factor: ii.factor, side: "np1" };
        if (ii.ok === true) return { prime: true, factor: null, side: "np1" };
      }

      emit(onTick, "split", 0n, 1n, { label: "factoring n−1 for Combined Theorem 1" });
      const facF = factorEnough(n, depth, onTick, shouldStop);
      if (facF) {
        const F = FValue(facF);
        emit(onTick, "combined", F, isqrt(n), {
          F: String(F),
          G: String(G),
        });
        if (combinedTheorem1Ok(n, F, G)) {
          const primesF = Array.from(facF.keys()).sort(function (a, b) {
            return a === b ? 0 : a > b ? -1 : 1;
          });
          const pk = pocklington(n, primesF, onTick);
          if (pk.ok === false) return { prime: false, factor: pk.factor, side: "combined" };
          const ii = conditionII(n, primesG, onTick);
          if (ii.ok === false) return { prime: false, factor: ii.factor, side: "combined" };
          if (pk.ok === true && ii.ok === true) {
            return { prime: true, factor: null, side: "combined" };
          }
        }
      }
    }
    return { prime: null, factor: null, side: null };
  }

  const CLASS_NUMBER_1_D = [-3n, -4n, -7n, -8n, -11n, -12n, -16n, -19n, -27n, -28n, -43n, -67n, -163n];
  const J_INVARIANT = {
    "-3": 0n,
    "-4": 1728n,
    "-7": -(15n ** 3n),
    "-8": 20n ** 3n,
    "-11": -(32n ** 3n),
    "-12": 2n * (30n ** 3n),
    "-16": 66n ** 3n,
    "-19": -(96n ** 3n),
    "-27": -3n * (160n ** 3n),
    "-28": 255n ** 3n,
    "-43": -(960n ** 3n),
    "-67": -(5280n ** 3n),
    "-163": -(640320n ** 3n),
  };
  const POINT_X_MAX = 4096;
  const TWIST_NONRESIDUE_MAX = 10000;
  const peelCache = new Map();
  const proving = new Set();

  function clearPeelCache() {
    peelCache.clear();
  }

  function maxSplitsFor(bits) {
    if (bits <= 160) return 48;
    if (bits <= 250) return 24;
    return 8;
  }

  function modN(x, n) {
    x %= n;
    return x < 0n ? x + n : x;
  }

  function tonelliModN(a, n) {
    a %= n;
    if (a < 0n) a += n;
    const g0 = gcd(a, n);
    if (g0 > 1n && g0 < n) return { factor: g0 };
    if (jacobi(a, n) !== 1) return null;
    let z = 2n;
    for (; z <= BigInt(TWIST_NONRESIDUE_MAX); z++) {
      const gz = gcd(z, n);
      if (gz > 1n && gz < n) return { factor: gz };
      if (jacobi(z, n) === -1) break;
    }
    if (z > BigInt(TWIST_NONRESIDUE_MAX)) return null;
    let q = n - 1n;
    let s = 0;
    while ((q & 1n) === 0n) {
      q >>= 1n;
      s++;
    }
    let m = s;
    let c = powBig(z, q, n);
    let r = powBig(a, (q + 1n) / 2n, n);
    let t = powBig(a, q, n);
    while (t !== 1n) {
      let i = 1;
      let tt = (t * t) % n;
      while (tt !== 1n) {
        tt = (tt * tt) % n;
        i++;
        if (i >= s) return null;
      }
      const b = powBig(c, 1n << BigInt(m - i - 1), n);
      r = (r * b) % n;
      c = (b * b) % n;
      t = (t * c) % n;
      m = i;
    }
    if ((r * r) % n !== a % n) return null;
    if (r > n - r) r = n - r;
    return r;
  }

  function cornacchia(D, n) {
    if (D >= 0n || n <= 2n || (n & 1n) === 0n) return { kind: "no" };
    const d = -D;
    const g = gcd(d, n);
    if (g > 1n && g < n) return { kind: "factor", g: g };
    if (g === n) return { kind: "no" };
    if (jacobi(D, n) !== 1) return { kind: "no" };
    const root = tonelliModN((-d) % n, n);
    if (root && root.factor) return { kind: "factor", g: root.factor };
    if (root == null || typeof root !== "bigint") return { kind: "no" };
    const fourN = 4n * n;
    const cands = [root, fourN - root, root + n, root + 2n * n, root + 3n * n];
    const R = [];
    const seen = new Set();
    for (let i = 0; i < cands.length; i++) {
      let r4 = cands[i] % fourN;
      if (r4 < 0n) r4 += fourN;
      if ((r4 * r4) % fourN !== ((-d) % fourN + fourN) % fourN) continue;
      const key = String(r4);
      if (seen.has(key)) continue;
      seen.add(key);
      R.push(r4);
    }
    R.sort(function (a, b) {
      return a === b ? 0 : a < b ? -1 : 1;
    });
    const hits = [];
    for (let i = 0; i < R.length; i++) {
      let aa = fourN;
      let b = R[i];
      if (b > 2n * n) b = fourN - b;
      let failed = false;
      while (b * b > fourN) {
        const nb = aa % b;
        aa = b;
        b = nb;
        if (b === 0n) {
          failed = true;
          break;
        }
      }
      if (failed) continue;
      const t = b < 0n ? -b : b;
      const rem = fourN - t * t;
      if (rem < 0n || rem % d !== 0n) continue;
      const vv = rem / d;
      const v = isqrt(vv);
      if (v * v !== vv || t === 0n) continue;
      hits.push([t, v]);
    }
    if (!hits.length) return { kind: "no" };
    hits.sort(function (x, y) {
      if (x[0] === y[0]) return x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0;
      return x[0] < y[0] ? -1 : 1;
    });
    return { kind: "ok", t: hits[0][0], v: hits[0][1] };
  }

  /** Jacobian doubling. Infinity is {inf:true}; a proper factor is {factor}. */
  function jacDbl(x, y, z, a, n) {
    if (y === 0n) return { inf: true };
    const y2 = (y * y) % n;
    const s = (4n * x * y2) % n;
    const z2 = (z * z) % n;
    const m = (3n * x * x + ((a * z2) % n) * z2) % n;
    const x3 = modN(m * m - 2n * s, n);
    const y3 = modN(m * (s - x3) - 8n * y2 * y2, n);
    const z3 = (2n * y * z) % n;
    const g = z3 === 0n ? 1n : gcd(z3, n);
    if (g > 1n && g < n) return { factor: g };
    return { x: x3, y: y3, z: z3 };
  }

  function jacAdd(x1, y1, z1, x2, y2, z2, n) {
    if (z1 === 0n) return { x: x2, y: y2, z: z2 };
    if (z2 === 0n) return { x: x1, y: y1, z: z1 };
    const z1z1 = (z1 * z1) % n;
    const z2z2 = (z2 * z2) % n;
    const u1 = (x1 * z2z2) % n;
    const u2 = (x2 * z1z1) % n;
    const s1 = (((y1 * z2) % n) * z2z2) % n;
    const s2 = (((y2 * z1) % n) * z1z1) % n;
    const h = modN(u2 - u1, n);
    const r = modN(s2 - s1, n);
    if (h === 0n) {
      if (r === 0n) return { dbl: true };
      return { inf: true };
    }
    const hh = (h * h) % n;
    const hhh = (h * hh) % n;
    const v = (u1 * hh) % n;
    const x3 = modN(r * r - hhh - 2n * v, n);
    const y3 = modN(r * (v - x3) - s1 * hhh, n);
    const z3 = (((z1 * z2) % n) * h) % n;
    const g = z3 === 0n ? 1n : gcd(z3, n);
    if (g > 1n && g < n) return { factor: g };
    return { x: x3, y: y3, z: z3 };
  }

  /** Scalar mul via Jacobian coordinates (one inversion at the end). */
  function ecMul(k, p, a, n) {
    if (p === null || k <= 0n) return { p: null, g: 1n };
    let jx = modN(p[0], n);
    let jy = modN(p[1], n);
    let jz = 1n;
    let rx = 0n;
    let ry = 0n;
    let rz = 0n;
    let kk = k;
    while (kk > 0n) {
      if (kk & 1n) {
        if (rz === 0n) {
          rx = jx;
          ry = jy;
          rz = jz;
        } else {
          let g = jacAdd(rx, ry, rz, jx, jy, jz, n);
          if (g.dbl) g = jacDbl(rx, ry, rz, a, n);
          if (g.factor) return { p: null, g: g.factor };
          if (g.inf) {
            rx = 0n;
            ry = 0n;
            rz = 0n;
          } else {
            rx = g.x;
            ry = g.y;
            rz = g.z;
          }
        }
      }
      kk >>= 1n;
      if (kk > 0n) {
        if (jz !== 0n) {
          const g = jacDbl(jx, jy, jz, a, n);
          if (g.factor) return { p: null, g: g.factor };
          if (g.inf) {
            jx = 0n;
            jy = 0n;
            jz = 0n;
          } else {
            jx = g.x;
            jy = g.y;
            jz = g.z;
          }
        }
      }
    }
    if (rz === 0n) return { p: null, g: 1n };
    const zinv = modInv(rz, n);
    if (zinv === null) {
      const g = gcd(rz, n);
      return { p: null, g: g > 1n && g < n ? g : 1n };
    }
    const z2 = (zinv * zinv) % n;
    return { p: [(rx * z2) % n, (((ry * z2) % n) * zinv) % n], g: 1n };
  }

  function twistGenNeg4(n) {
    for (let beta = 2n; beta <= BigInt(TWIST_NONRESIDUE_MAX); beta++) {
      const g = gcd(beta, n);
      if (g > 1n && g < n) return { factor: g };
      if (jacobi(beta, n) !== -1) continue;
      const set = new Set();
      for (let k = 0n; k < 4n; k++) set.add(String(powBig(beta, k, n)));
      if (set.size === 4) return beta;
    }
    return null;
  }

  function twistGenNeg3(n) {
    for (let alpha = 2n; alpha <= BigInt(TWIST_NONRESIDUE_MAX); alpha++) {
      const g = gcd(alpha, n);
      if (g > 1n && g < n) return { factor: g };
      if (jacobi(alpha, n) !== -1) continue;
      if ((n - 1n) % 3n === 0n && powBig(alpha, (n - 1n) / 3n, n) === 1n) continue;
      const set = new Set();
      for (let k = 0n; k < 6n; k++) set.add(String(powBig(alpha, k, n)));
      if (set.size === 6) return alpha;
    }
    return null;
  }

  function peelM(m, n, onTick, shouldStop) {
    const key = String(m) + ":" + String(n);
    const hit = peelCache.get(key);
    if (hit) {
      return {
        fac: new Map(hit.fac),
        rem: hit.rem,
        unproven: hit.unproven.slice(),
      };
    }
    const ts = trialSplit(m, adaptiveTrialBound(m));
    const fac = ts.fac;
    const unproven = [];
    if (ts.rem <= 1n) {
      const stored = { fac: Array.from(fac), rem: 1n, unproven: [] };
      peelCache.set(key, stored);
      return { fac: fac, rem: 1n, unproven: [] };
    }
    const stack = [ts.rem];
    let splits = 0;
    const cap = maxSplitsFor(bitLength(m));
    while (stack.length) {
      if (shouldStop && shouldStop()) break;
      let c = stack.pop();
      if (c <= 1n) continue;
      const sub = trialSplit(c, adaptiveTrialBound(c));
      for (const [p, e] of sub.fac) fac.set(p, (fac.get(p) || 0) + e);
      if (sub.rem <= 1n) continue;
      c = sub.rem;
      // Fermat-holding leftovers are q-candidates. Do not ECM a holding prime.
      if (c < n && !fermatSaysComposite(c)) {
        unproven.push(c);
        continue;
      }
      if (splits >= cap) {
        if (!fermatSaysComposite(c)) unproven.push(c);
        continue;
      }
      splits++;
      const cb = bitLength(c);
      const f = ecmFactor(
        c,
        onTick,
        shouldStop,
        6,
        ecmPeelMaxMs(cb),
        ecmPeelPhases(cb)
      );
      if (!f || f <= 1n || f >= c) {
        if (!fermatSaysComposite(c)) unproven.push(c);
        continue;
      }
      stack.push(f);
      stack.push(c / f);
    }
    let prod = 1n;
    for (const [p, e] of fac) {
      for (let i = 0; i < e; i++) prod *= p;
    }
    let leftover = prod === 0n ? m : m / prod;
    if (leftover <= 1n) leftover = 1n;
    if (!(shouldStop && shouldStop())) {
      peelCache.set(key, {
        fac: Array.from(fac),
        rem: leftover,
        unproven: unproven.slice(),
      });
    }
    return { fac: fac, rem: leftover, unproven: unproven };
  }

  function admissiblePairs(m, n, fac, leftover, unproven) {
    const minQ = gkMinQ(n);
    const pairs = [];
    const seen = new Set();
    for (const q of fac.keys()) {
      const k = String(q);
      if (seen.has(k) || q < minQ || m % q !== 0n) continue;
      const c = m / q;
      if (c >= 2n) {
        pairs.push({ q: q, c: c, proven: true });
        seen.add(k);
      }
    }
    const cands = unproven.slice();
    if (leftover > 1n && leftover < n && !fermatSaysComposite(leftover)) {
      cands.push(leftover);
    }
    for (let i = 0; i < cands.length; i++) {
      const q = cands[i];
      const k = String(q);
      if (seen.has(k) || q < minQ || q >= n || m % q !== 0n) continue;
      const c = m / q;
      if (c >= 2n) {
        pairs.push({ q: q, c: c, proven: false });
        seen.add(k);
      }
    }
    pairs.sort(function (a, b) {
      return a.q === b.q ? 0 : a.q < b.q ? -1 : 1;
    });
    return pairs;
  }

  /**
   * Goldwasser–Kilian point predicate.
   * g==n is “try next x”, not O. Wrong order aborts this (q,c) pair only.
   */
  function pointSearch(n, a, b, c, q) {
    for (let x = 1n; x <= BigInt(POINT_X_MAX); x++) {
      const rhs = (powBig(x, 3n, n) + a * x + b) % n;
      let j;
      try {
        j = jacobi(rhs, n);
      } catch (_) {
        return { prime: false };
      }
      if (j === 0) {
        const g = gcd(rhs, n);
        if (g > 1n && g < n) return { prime: false, factor: g };
        continue;
      }
      if (j === -1) continue;
      const y = tonelliModN(rhs, n);
      if (y && y.factor) return { prime: false, factor: y.factor };
      if (y == null || typeof y !== "bigint") continue;
      const Q = ecMul(c, [x, y], a, n);
      if (Q.g > 1n && Q.g < n) return { prime: false, factor: Q.g };
      if (Q.g > 1n || Q.p === null) continue;
      const R = ecMul(q, Q.p, a, n);
      if (R.g > 1n && R.g < n) return { prime: false, factor: R.g };
      if (R.g > 1n) continue;
      if (R.p === null) return { prime: true };
      return { prime: null };
    }
    return { prime: null };
  }

  /** Prove a strictly smaller Goldwasser–Kilian q. Recurse ECPP when BLS cannot. */
  function proveQ(q, depth, onTick, shouldStop, proven) {
    if (proven) return { prime: true };
    if (shouldStop && shouldStop()) return { aborted: true };
    if (q < 2n) return { prime: false };
    if (q === 2n || q === 3n) return { prime: true };
    if ((q & 1n) === 0n) return { prime: false };
    const lim = isqrt(q);
    if (lim <= 2_000_000n) {
      const t = trialIsPrimeCofactor(q, lim, onTick, shouldStop);
      if (t === true) return { prime: true };
      if (t === false) return { prime: false };
      return { prime: null };
    }
    // Downrun q: class-number-1 ECPP first. A mid-size BLS peel uses the
    // hard55 700-curve ECM and is what hung 10^130+1113 in the tab.
    if (depth < 10) {
      const e = ecppPrimality(q, depth + 1, onTick, shouldStop);
      if (e.aborted) return { aborted: true };
      if (e.prime === true) return { prime: true };
      if (e.prime === false) return { prime: false };
    }
    if (bitLength(q) < 200) {
      const b = blsPrimality(q, depth + 1, onTick, shouldStop);
      if (b.prime === true) return { prime: true };
      if (b.prime === false) return { prime: false };
    }
    return { prime: null };
  }

  function tryCurveOrders(n, a, b, orders, depth, onTick, shouldStop) {
    const disc = (4n * powBig(a, 3n, n) + 27n * ((b * b) % n)) % n;
    const gd = gcd(disc, n);
    if (gd > 1n && gd < n) return { prime: false, factor: gd };
    if (gd === n) return { prime: null };
    const cands = [];
    for (let i = 0; i < orders.length; i++) {
      const m = orders[i];
      if (m <= 2n) continue;
      const g0 = gcd(m, n);
      if (g0 > 1n && g0 < n) return { prime: false, factor: g0 };
      const peeled = peelM(m, n, onTick, shouldStop);
      if (shouldStop && shouldStop()) return { prime: null, aborted: true };
      const pairs = admissiblePairs(m, n, peeled.fac, peeled.rem, peeled.unproven);
      for (let j = 0; j < pairs.length; j++) {
        cands.push({
          q: pairs[j].q,
          c: pairs[j].c,
          proven: pairs[j].proven,
          m: m,
        });
      }
    }
    cands.sort(function (x, y) {
      return x.q === y.q ? 0 : x.q < y.q ? -1 : 1;
    });
    for (let i = 0; i < cands.length; i++) {
      if (shouldStop && shouldStop()) return { prime: null, aborted: true };
      const hit = pointSearch(n, a, b, cands[i].c, cands[i].q);
      if (hit.prime === false) return hit;
      if (hit.prime === true) {
        const pq = proveQ(cands[i].q, depth, onTick, shouldStop, cands[i].proven);
        if (pq.aborted) return { prime: null, aborted: true };
        if (pq.prime === true) return { prime: true };
        if (pq.prime === false) return { prime: false };
      }
    }
    return { prime: null };
  }

  function collectTwistPairs(n, t, coeff, isA, onTick, shouldStop) {
    const orders = [n + 1n - t, n + 1n + t];
    const cands = [];
    for (let i = 0; i < coeff.length; i++) {
      const tw = coeff[i];
      if (tw === 0n) continue;
      for (let j = 0; j < orders.length; j++) {
        const m = orders[j];
        if (m <= 2n) continue;
        const peeled = peelM(m, n, onTick, shouldStop);
        if (shouldStop && shouldStop()) return { aborted: true };
        const pairs = admissiblePairs(m, n, peeled.fac, peeled.rem, peeled.unproven);
        for (let k = 0; k < pairs.length; k++) {
          cands.push({
            q: pairs[k].q,
            c: pairs[k].c,
            proven: pairs[k].proven,
            m: m,
            a: isA ? tw : 0n,
            b: isA ? 0n : tw,
          });
        }
      }
    }
    cands.sort(function (x, y) {
      return x.q === y.q ? 0 : x.q < y.q ? -1 : 1;
    });
    return { cands: cands };
  }

  function tryDNeg4(n, t, depth, onTick, shouldStop) {
    const beta = twistGenNeg4(n);
    if (beta && beta.factor) return { prime: false, factor: beta.factor };
    if (beta == null || typeof beta !== "bigint") return { prime: null };
    const coeff = [];
    for (let k = 0n; k < 4n; k++) coeff.push(powBig(beta, k, n));
    const bag = collectTwistPairs(n, t, coeff, true, onTick, shouldStop);
    if (bag.aborted) return { prime: null, aborted: true };
    const cands = bag.cands;
    for (let i = 0; i < cands.length; i++) {
      if (shouldStop && shouldStop()) return { prime: null, aborted: true };
      const hit = pointSearch(n, cands[i].a, 0n, cands[i].c, cands[i].q);
      if (hit.prime === false) return hit;
      if (hit.prime === true) {
        const pq = proveQ(cands[i].q, depth, onTick, shouldStop, cands[i].proven);
        if (pq.aborted) return { prime: null, aborted: true };
        if (pq.prime === true) return { prime: true };
        if (pq.prime === false) return { prime: false };
      }
    }
    return { prime: null };
  }

  function tryDNeg3(n, t, depth, onTick, shouldStop) {
    const alpha = twistGenNeg3(n);
    if (alpha && alpha.factor) return { prime: false, factor: alpha.factor };
    if (alpha == null || typeof alpha !== "bigint") return { prime: null };
    const coeff = [];
    for (let k = 0n; k < 6n; k++) coeff.push(powBig(alpha, k, n));
    const bag = collectTwistPairs(n, t, coeff, false, onTick, shouldStop);
    if (bag.aborted) return { prime: null, aborted: true };
    const cands = bag.cands;
    for (let i = 0; i < cands.length; i++) {
      if (shouldStop && shouldStop()) return { prime: null, aborted: true };
      const hit = pointSearch(n, 0n, cands[i].b, cands[i].c, cands[i].q);
      if (hit.prime === false) return hit;
      if (hit.prime === true) {
        const pq = proveQ(cands[i].q, depth, onTick, shouldStop, cands[i].proven);
        if (pq.aborted) return { prime: null, aborted: true };
        if (pq.prime === true) return { prime: true };
        if (pq.prime === false) return { prime: false };
      }
    }
    return { prime: null };
  }

  function tryDFromJ(n, D, t, depth, onTick, shouldStop) {
    const j = ((J_INVARIANT[String(D)] % n) + n) % n;
    const g = gcd(j - 1728n, n);
    if (g > 1n && g < n) return { prime: false, factor: g };
    if (g === n) return { prime: null };
    const inv = modInv(j - 1728n, n);
    if (inv === null) {
      const g2 = gcd(j - 1728n, n);
      return g2 > 1n && g2 < n ? { prime: false, factor: g2 } : { prime: null };
    }
    const k = (j * inv) % n;
    let c = null;
    for (let x = 2n; x <= BigInt(TWIST_NONRESIDUE_MAX); x++) {
      const gx = gcd(x, n);
      if (gx > 1n && gx < n) return { prime: false, factor: gx };
      if (jacobi(x, n) === -1) {
        c = x;
        break;
      }
    }
    if (c === null) return { prime: null };
    for (let r = 0n; r < 2n; r++) {
      const cr2 = powBig(c, 2n * r, n);
      const cr3 = powBig(c, 3n * r, n);
      const a = modN(-3n * k * cr2, n);
      const b = modN(2n * k * cr3, n);
      const dec = tryCurveOrders(
        n,
        a,
        b,
        [n + 1n - t, n + 1n + t],
        depth,
        onTick,
        shouldStop
      );
      if (dec.aborted || dec.prime !== null) return dec;
    }
    return { prime: null };
  }

  function ecppPrimality(n, depth, onTick, shouldStop) {
    if (n < 2n) return { prime: false };
    if (n === 2n || n === 3n) return { prime: true };
    if ((n & 1n) === 0n) return { prime: false, factor: 2n };
    if (isSquare(n)) return { prime: false, factor: isqrt(n) };
    if (!depth) clearPeelCache();
    const key = String(n);
    if (proving.has(key)) return { prime: null };
    if (proving.size >= bitLength(n)) return { prime: null };
    proving.add(key);
    try {
      for (let i = 0; i < CLASS_NUMBER_1_D.length; i++) {
        const D = CLASS_NUMBER_1_D[i];
        emit(onTick, "ecpp", BigInt(i + 1), BigInt(CLASS_NUMBER_1_D.length), {
          D: String(D),
        });
        if (shouldStop && shouldStop()) return { prime: null, aborted: true };
        const cr = cornacchia(D, n);
        if (cr.kind === "factor") return { prime: false, factor: cr.g };
        if (cr.kind !== "ok") continue;
        let dec;
        if (D === -4n) dec = tryDNeg4(n, cr.t, depth, onTick, shouldStop);
        else if (D === -3n) dec = tryDNeg3(n, cr.t, depth, onTick, shouldStop);
        else dec = tryDFromJ(n, D, cr.t, depth, onTick, shouldStop);
        if (dec.aborted) return dec;
        if (dec.prime !== null) return dec;
      }
      return { prime: null };
    } finally {
      proving.delete(key);
    }
  }

  function checkPrime(n, onTick, shouldStop) {
    const t0 = typeof performance !== "undefined" ? performance.now() : 0;
    emit(onTick, "precheck", 0n, 1n, { label: "small-prime / parity filter" });
    if (n < 2n) return done(false, "tiny", null, "n < 2", isqrt(n), t0);
    if (n < 4n) return done(true, "tiny", null, "2 or 3", isqrt(n), t0);
    if ((n & 1n) === 0n) return done(false, "tiny", 2n, "even", isqrt(n), t0);

    for (let k = 0; k < SMALL.length; k++) {
      const p = SMALL[k];
      emit(onTick, "precheck", BigInt(k + 1), BigInt(SMALL.length), {
        p: String(p),
      });
      if (n === p) return done(true, "small-prime", null, "hits precheck table", isqrt(n), t0);
      if (n % p === 0n) return done(false, "small-prime", p, "divisible by small prime", isqrt(n), t0);
      if (p * p > n) return done(true, "small-prime", null, "√n inside precheck", isqrt(n), t0);
    }

    const limit = isqrt(n);
    const bits = bitLength(n);

    // Hard / multi-limb. ≥256-bit: Fermat composite reject, then ECPP first
    // (same as Python is_prime). No wall-clock budget — only user Stop.
    if (n >= TWO64 || limit >= NM1_ISQRT) {
      if (bits >= HUGE_BITS) {
        for (let i = 0; i < 6; i++) {
          const a = BASES[i];
          emit(onTick, "fermat", BigInt(i + 1), 6n, {
            base: String(a),
            label: "Fermat composite filter",
          });
          if (a % n === 0n) {
            return done(n === a, "fermat", n === a ? null : a, "divisible by Fermat base", limit, t0);
          }
          if (powBig(a, n - 1n, n) !== 1n) {
            let g = gcd(powBig(a, n - 1n, n) - 1n, n);
            if (!(g > 1n && g < n)) g = null;
            return done(
              false,
              "fermat",
              g,
              g ? "Fermat composite; factor " + g.toString() : "failed Fermat a^{n−1} ≡ 1 (composite)",
              limit,
              t0
            );
          }
        }
        emit(onTick, "ecpp", 0n, 13n, { label: "class-number-1 ECPP first" });
        const ecHuge = ecppPrimality(n, 0, onTick, shouldStop);
        if (shouldStop && shouldStop()) return { aborted: true };
        if (ecHuge.prime === true) {
          return done(
            true,
            "ecpp",
            null,
            "deterministic Atkin–Morain ECPP (class-number-1; browser)",
            limit,
            t0
          );
        }
        if (ecHuge.prime === false) {
          return done(
            false,
            "ecpp",
            ecHuge.factor,
            ecHuge.factor
              ? "ECPP extracted a factor " + ecHuge.factor.toString()
              : "ECPP proved composite",
            limit,
            t0
          );
        }
        // ECPP missed: fall through to combined BLS (no try/time cap).
      }
      emit(onTick, "fermat", 0n, 6n, { label: "combined BLS n±1" });
      const decided = blsPrimality(n, 0, onTick, shouldStop);
      if (shouldStop && shouldStop()) return { aborted: true };
      if (decided.prime === true) {
        const path =
          decided.side === "np1"
            ? "n+1-lucas"
            : decided.side === "combined"
              ? "bls-combined"
              : "n-1-pocklington";
        const note =
          path === "n+1-lucas"
            ? "BLS n+1 Lucas proof (browser; no RNG)"
            : path === "bls-combined"
              ? "Combined Theorem 1 (n < max(F²G/2, FG²/2); not FG>√n)"
              : "n−1 Pocklington proof (browser; no RNG)";
        return done(true, path, null, note, limit, t0);
      }
      if (decided.prime === false) {
        let fac = decided.factor;
        if (fac == null) fac = extractFactor(n, onTick, shouldStop);
        return done(
          false,
          decided.side === "np1" ? "n+1-lucas" : "n-1-pocklington",
          fac,
          fac
            ? "composite; factor " + fac.toString()
            : "failed Fermat / Lucas / Pocklington filter (composite)",
          limit,
          t0
        );
      }
      emit(onTick, "ecpp", 0n, 13n, { label: "class-number-1 ECPP" });
      const ec = ecppPrimality(n, 0, onTick, shouldStop);
      if (shouldStop && shouldStop()) return { aborted: true };
      if (ec.prime === true) {
        return done(
          true,
          "ecpp",
          null,
          "deterministic Atkin–Morain ECPP (class-number-1; browser)",
          limit,
          t0
        );
      }
      if (ec.prime === false) {
        return done(
          false,
          "ecpp",
          ec.factor,
          ec.factor
            ? "ECPP extracted a factor " + ec.factor.toString()
            : "ECPP proved composite",
          limit,
          t0
        );
      }
    }

    if (limit > TRIAL_SOFT_ISQRT) {
      return {
        prime: null,
        path: "inconclusive",
        factor: null,
        isqrt: limit.toString(),
        ms: typeof performance !== "undefined" ? performance.now() - t0 : 0,
        note:
          "No size ban: combined BLS and class-number-1 ECPP did not settle, and automatic pure trial would need ~⌊√n⌋ modular divisions (impractical in a tab). The Python library continues with small-h ECPP / SIQS / AKS.",
      };
    }

    if (n <= MAX_SAFE) {
      return trialNumber(Number(n), Number(limit), t0, onTick, shouldStop);
    }
    if (n < TWO64) {
      return trialU64(n, Number(limit), limit, t0, onTick, shouldStop);
    }
    return trialBig(n, limit, t0, onTick, shouldStop);
  }

  const NEIGHBOR_MAX_K = 64;

  function parseK(raw) {
    const k = Number(raw);
    if (!Number.isInteger(k) || k < 1 || k > NEIGHBOR_MAX_K) return null;
    return k;
  }

  function smallComposite(n) {
    if (n < 2n) return true;
    if (n === 2n || n === 3n) return false;
    if ((n & 1n) === 0n) return true;
    for (let i = 0; i < SMALL.length; i++) {
      const p = SMALL[i];
      if (n === p) return false;
      if (n % p === 0n) return true;
      if (p * p > n) return false;
    }
    return false;
  }

  function nextPrime(n, k, onTick, shouldStop) {
    const kk = parseK(k == null ? 1 : k);
    if (kk == null) {
      return { ok: false, error: "k must be an integer from 1 to " + NEIGHBOR_MAX_K };
    }
    const t0 = typeof performance !== "undefined" ? performance.now() : 0;
    const found = [];
    let cand = n < 2n ? 2n : n + 1n;
    let tried = 0;
    while (found.length < kk) {
      if (shouldStop && shouldStop()) return { aborted: true };
      if (cand > 3n && (cand & 1n) === 0n) cand += 1n;
      tried++;
      emit(onTick, "neighbor", BigInt(found.length + 1), BigInt(kk), {
        label: "next prime · candidate " + cand.toString(),
        candidate: cand.toString(),
        found: String(found.length),
      });
      if (!smallComposite(cand)) {
        const r = checkPrime(cand, onTick, shouldStop);
        if (r && r.aborted) return { aborted: true };
        if (r && r.prime === true) {
          found.push({ p: cand, path: r.path, ms: r.ms });
        } else if (r && r.prime == null) {
          return {
            ok: false,
            inconclusive: true,
            n: n.toString(),
            k: kk,
            direction: "next",
            tried: tried,
            last: cand.toString(),
            ms: typeof performance !== "undefined" ? performance.now() - t0 : 0,
            note:
              "Candidate " +
              cand.toString() +
              " held Fermat but class-number-1 ECPP / BLS did not settle. The walk cannot skip it (it may be prime). Stop and try Python next_prime, or Check that candidate.",
          };
        }
      }
      if (cand === 2n) cand = 3n;
      else cand += 2n;
    }
    const last = found[found.length - 1];
    return {
      ok: true,
      n: n.toString(),
      k: kk,
      direction: "next",
      value: last.p.toString(),
      path: last.path,
      tried: tried,
      ms: typeof performance !== "undefined" ? performance.now() - t0 : 0,
      note:
        kk === 1
          ? "least prime strictly greater than n (same engines as Check)"
          : kk + "-th prime strictly greater than n",
    };
  }

  function prevPrime(n, k, onTick, shouldStop) {
    const kk = parseK(k == null ? 1 : k);
    if (kk == null) {
      return { ok: false, error: "k must be an integer from 1 to " + NEIGHBOR_MAX_K };
    }
    const t0 = typeof performance !== "undefined" ? performance.now() : 0;
    if (n <= 2n) {
      return {
        ok: false,
        error: "there is no prime strictly less than " + n.toString(),
      };
    }
    const found = [];
    let cand = n - 1n;
    let tried = 0;
    while (found.length < kk) {
      if (shouldStop && shouldStop()) return { aborted: true };
      if (cand < 2n) {
        return {
          ok: false,
          error:
            "only " +
            found.length +
            " prime(s) strictly less than n; cannot take the " +
            kk +
            "-th previous",
        };
      }
      if (cand > 3n && (cand & 1n) === 0n) cand -= 1n;
      tried++;
      emit(onTick, "neighbor", BigInt(found.length + 1), BigInt(kk), {
        label: "previous prime · candidate " + cand.toString(),
        candidate: cand.toString(),
        found: String(found.length),
      });
      if (!smallComposite(cand)) {
        const r = checkPrime(cand, onTick, shouldStop);
        if (r && r.aborted) return { aborted: true };
        if (r && r.prime === true) {
          found.push({ p: cand, path: r.path, ms: r.ms });
        } else if (r && r.prime == null) {
          return {
            ok: false,
            inconclusive: true,
            n: n.toString(),
            k: kk,
            direction: "prev",
            tried: tried,
            last: cand.toString(),
            ms: typeof performance !== "undefined" ? performance.now() - t0 : 0,
            note:
              "Candidate " +
              cand.toString() +
              " held Fermat but class-number-1 ECPP / BLS did not settle. The walk cannot skip it (it may be prime). Stop and try Python prev_prime, or Check that candidate.",
          };
        }
      }
      if (cand === 3n) cand = 2n;
      else if (cand === 2n) cand = 1n;
      else cand -= 2n;
    }
    const last = found[found.length - 1];
    return {
      ok: true,
      n: n.toString(),
      k: kk,
      direction: "prev",
      value: last.p.toString(),
      path: last.path,
      tried: tried,
      ms: typeof performance !== "undefined" ? performance.now() - t0 : 0,
      note:
        kk === 1
          ? "greatest prime strictly less than n (same engines as Check)"
          : kk + "-th prime strictly less than n",
    };
  }

  function trialNumber(n, limit, t0, onTick, shouldStop) {
    let i = 59;
    let si = 6;
    let steps = 0;
    while (i <= limit) {
      if (n % i === 0) return done(false, "wheel-30", i, "30-wheel trial division", BigInt(limit), t0);
      i += STEPS[si];
      si = (si + 1) & 7;
      steps++;
      if ((steps & 0xfffff) === 0) {
        if (shouldStop && shouldStop()) return { aborted: true };
        emit(onTick, "wheel", BigInt(i), BigInt(limit), { residue: i % 30 });
      }
    }
    return done(true, "wheel-30", null, "no factor ≤ √n (exact trial)", BigInt(limit), t0);
  }

  function trialU64(n, limitNum, limitB, t0, onTick, shouldStop) {
    const lo = Number(n & 0xffffffffn);
    const hi = Number(n >> 32n);
    let i = 59;
    let steps = 0;
    while (i + 24 <= limitNum) {
      if (umod64(lo, hi, i) === 0) return done(false, "wheel-30", i, "30-wheel trial division", limitB, t0);
      if (umod64(lo, hi, i + 2) === 0) return done(false, "wheel-30", i + 2, "30-wheel trial division", limitB, t0);
      if (umod64(lo, hi, i + 8) === 0) return done(false, "wheel-30", i + 8, "30-wheel trial division", limitB, t0);
      if (umod64(lo, hi, i + 12) === 0) return done(false, "wheel-30", i + 12, "30-wheel trial division", limitB, t0);
      if (umod64(lo, hi, i + 14) === 0) return done(false, "wheel-30", i + 14, "30-wheel trial division", limitB, t0);
      if (umod64(lo, hi, i + 18) === 0) return done(false, "wheel-30", i + 18, "30-wheel trial division", limitB, t0);
      if (umod64(lo, hi, i + 20) === 0) return done(false, "wheel-30", i + 20, "30-wheel trial division", limitB, t0);
      if (umod64(lo, hi, i + 24) === 0) return done(false, "wheel-30", i + 24, "30-wheel trial division", limitB, t0);
      i += 30;
      steps += 8;
      if ((steps & 0xfffff) === 0) {
        if (shouldStop && shouldStop()) return { aborted: true };
        emit(onTick, "wheel", BigInt(i), BigInt(limitNum), { residue: i % 30 });
      }
    }
    let si = 6;
    while (i <= limitNum) {
      if (umod64(lo, hi, i) === 0) return done(false, "wheel-30", i, "30-wheel trial division", limitB, t0);
      i += STEPS[si];
      si = (si + 1) & 7;
    }
    return done(true, "wheel-30", null, "no factor ≤ √n (exact trial)", limitB, t0);
  }

  function trialBig(n, limit, t0, onTick, shouldStop) {
    let i = 59n;
    let si = 6;
    let steps = 0;
    while (i <= limit) {
      if (n % i === 0n) return done(false, "wheel-30", i, "30-wheel trial division", limit, t0);
      i += STEPS_B[si];
      si = (si + 1) & 7;
      steps++;
      if ((steps & 0xfffff) === 0) {
        if (shouldStop && shouldStop()) return { aborted: true };
        emit(onTick, "wheel", i, limit, { residue: Number(i % 30n) });
      }
    }
    return done(true, "wheel-30", null, "no factor ≤ √n (exact trial)", limit, t0);
  }

  const api = {
    isqrt: isqrt,
    icbrt: icbrt,
    blsCubicOk: blsCubicOk,
    combinedTheorem1Ok: combinedTheorem1Ok,
    gkMinQ: gkMinQ,
    lucasUv: lucasUv,
    cornacchia: cornacchia,
    checkPrime: checkPrime,
    nextPrime: nextPrime,
    prevPrime: prevPrime,
    ecmFactor: ecmFactor,
    umod64: umod64,
    nm1Primality: nm1Primality,
    blsPrimality: blsPrimality,
    ecppPrimality: ecppPrimality,
    WARN_ISQRT: WARN_ISQRT,
    TRIAL_SOFT_ISQRT: TRIAL_SOFT_ISQRT,
    COFACTOR_TRIAL_ISQRT: COFACTOR_TRIAL_ISQRT,
    NM1_ISQRT: NM1_ISQRT,
    HUGE_BITS: HUGE_BITS,
    POINT_X_MAX: POINT_X_MAX,
    adaptiveTrialBound: adaptiveTrialBound,
    ecmPhases: ecmPhases,
    SMALL_N: SMALL_N,
  };

  const inWorker =
    typeof WorkerGlobalScope !== "undefined" &&
    typeof g === "object" &&
    g instanceof WorkerGlobalScope;

  if (inWorker) {
    let stop = false;
    g.onmessage = function (ev) {
      const msg = ev.data || {};
      if (msg.cmd === "stop") {
        stop = true;
        return;
      }
      if (msg.cmd !== "check" && msg.cmd !== "nextPrime" && msg.cmd !== "prevPrime") {
        return;
      }
      stop = false;
      try {
        const n = BigInt(String(msg.n));
        const onTick = function (info, lim) {
          if (info && typeof info === "object") {
            g.postMessage({
              type: "progress",
              phase: info.phase || "wheel",
              i: String(info.i),
              limit: String(info.limit),
              extra: info.extra || {},
            });
          } else {
            g.postMessage({
              type: "progress",
              phase: "wheel",
              i: String(info),
              limit: String(lim),
              extra: {},
            });
          }
        };
        const shouldStop = function () {
          return stop;
        };
        let res;
        if (msg.cmd === "nextPrime") res = nextPrime(n, msg.k, onTick, shouldStop);
        else if (msg.cmd === "prevPrime") res = prevPrime(n, msg.k, onTick, shouldStop);
        else res = checkPrime(n, onTick, shouldStop);
        if (res && res.aborted) {
          g.postMessage({ type: "aborted" });
          return;
        }
        g.postMessage({ type: "done", result: res, kind: msg.cmd });
      } catch (err) {
        g.postMessage({ type: "error", message: String(err && err.message ? err.message : err) });
      }
    };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  g.PrimeLabTrial = api;

  function assert(cond, msg) {
    if (!cond) throw new Error(msg);
  }

  function selfTest() {
    const knownPrime = [
      2n, 3n, 5n, 17n, 53n, 59n, 97n, 1000000007n, 1000000009n, 2147483647n,
      600000000000000000001n, // smooth n−1 specimen
      100000000000000000000000000000000000000000031n, // CLI DEFAULT_N 147-bit
    ];
    const knownComp = [
      [4n, 2n],
      [9n, 3n],
      [91n, 7n],
      [121n, 11n],
      [143n, 11n],
      [1048583n * 1048601n, 1048583n],
    ];
    for (const p of knownPrime) {
      const r = checkPrime(p);
      assert(r.prime === true, "expected prime " + p + " got " + JSON.stringify(r));
    }
    for (const [c, f] of knownComp) {
      const r = checkPrime(c);
      assert(r.prime === false, "expected composite " + c);
      assert(r.factor != null, "composite must print a factor: " + c);
      assert(BigInt(r.factor) === f || c % BigInt(r.factor) === 0n, "bad factor for " + c);
    }
    assert(checkPrime(0n).prime === false, "0");
    assert(checkPrime(1n).prime === false, "1");

    const def = 100000000000000000000000000000000000000000031n;
    const rd = checkPrime(def);
    assert(rd.prime === true, "DEFAULT_N prime");
    assert(rd.path === "n-1-pocklington", "DEFAULT_N path " + rd.path);

    const hard = 9223372036854775783n;
    const lim = isqrt(hard);
    assert(lim === 3037000499n, "isqrt(near-2^63) = " + lim);
    assert(lim <= TRIAL_SOFT_ISQRT, "TRIAL_SOFT_ISQRT still allows near-2^63 trial");
    assert(lim > WARN_ISQRT, "WARN_ISQRT should flag near-2^63 as slow");

    // Hostile 55-digit n is not run here (ECM can take minutes).
    // docs/wiki/assets/checker-worker.js must not hard-ban by digit length.
    assert(typeof TRIAL_SOFT_ISQRT === "bigint", "soft trial budget");
    assert(typeof COFACTOR_TRIAL_ISQRT === "bigint", "cofactor trial budget");
    const p131 = 10n ** 130n + 1113n;
    assert(bitLength(p131) >= HUGE_BITS, "P131 is the ≥256-bit ECPP-first yardstick");
    assert(adaptiveTrialBound(p131) === TRIAL_BOUND_HUGE, "huge n trial bound");
    assert(POINT_X_MAX === 4096, "POINT_X_MAX matches the Python library");
    const cHuge = 10n ** 130n + 1117n;
    const rh = checkPrime(cHuge);
    assert(rh.prime === false, "131-digit Fermat composite must not be inconclusive: " + JSON.stringify(rh));
    let hugeCurves = 0;
    const hugePh = ecmPhases(bitLength(p131));
    for (let i = 0; i < hugePh.length; i++) hugeCurves += hugePh[i].curves;
    assert(hugeCurves >= 6 && hugeCurves <= 16, "huge ECM must match Python p8 budget, got " + hugeCurves);
    const huge = 10n ** 96n + 127n;
    const Fbls =
      2n * 55667n * 195376548589n * 323382331513450093n;
    assert(blsCubicOk(huge, Fbls), "BLS cubic extra must settle 10^96+127");
    assert(!blsCubicOk(huge, 2n * 55667n), "too-small F must fail BLS");

    // Combined Theorem 1 is cubic in F,G — not FG > √n.
    const nComb = 10007n;
    const Ffake = 32n;
    const Gfake = 32n;
    assert(Ffake * Gfake > isqrt(nComb), "fixture FG > √n");
    assert(!combinedTheorem1Ok(nComb, Ffake, Gfake), "FG>√n must not prove prime");

    const r = isqrt(isqrt(nComb));
    const weak = (r + 1n) * (r + 1n);
    assert(gkMinQ(nComb) === (r + 2n) * (r + 2n), "gkMinQ");
    assert(weak < gkMinQ(nComb), "weak (r+1)² is below gkMinQ");

    const np1 = 47265372806959999999n;
    const rnp = checkPrime(np1);
    assert(rnp.prime === true, "n+1-smooth specimen prime");
    assert(rnp.path === "n+1-lucas" || rnp.path === "n-1-pocklington", "n+1 specimen path " + rnp.path);

    const p40 = 100000000000000001000000000000000003029n;
    const cr40 = cornacchia(-4n, p40);
    assert(cr40.kind === "ok", "P40 Cornacchia");
    assert(cr40.t === 20000000000000000100n, "P40 t");
    assert(cr40.v === 23n, "P40 v");
    assert(4n * p40 === cr40.t * cr40.t + 4n * cr40.v * cr40.v, "P40 4n = t²+4v²");

    const overSafe = 59n * (MAX_SAFE / 59n + 11n);
    assert(overSafe > MAX_SAFE && overSafe < TWO64, "u64 fixture range");
    assert(nextPrime(0n, 1).value === "2", "next(0)=2");
    assert(nextPrime(1n, 1).value === "2", "next(1)=2");
    assert(nextPrime(2n, 1).value === "3", "next(2)=3");
    assert(nextPrime(14n, 1).value === "17", "next(14)=17");
    assert(nextPrime(14n, 3).value === "23", "next(14,3)=23");
    assert(nextPrime(100n, 1).value === "101", "next(100)=101");
    assert(prevPrime(14n, 1).value === "13", "prev(14)=13");
    assert(prevPrime(14n, 2).value === "11", "prev(14,2)=11");
    assert(prevPrime(3n, 1).value === "2", "prev(3)=2");
    assert(prevPrime(2n, 1).ok === false, "no prime < 2");

    const over = checkPrime(overSafe);
    assert(over.prime === false, "u64 composite should be composite");
    assert(overSafe % BigInt(over.factor) === 0n, "u64 factor must divide n");

    const samples = [
      100n,
      4294967296n,
      9223372036854775783n,
      (1n << 64n) - 1n,
      18446744073709551557n,
    ];
    for (const n of samples) {
      if (n >= TWO64) continue;
      const lo = Number(n & 0xffffffffn);
      const hi = Number(n >> 32n);
      for (const d of [3, 5, 7, 11, 59, 97, 10007, 1048583, 3037000499]) {
        if (d === 0) continue;
        const got = umod64(lo, hi, d);
        const exp = Number(n % BigInt(d));
        assert(got === exp, "umod64(" + n + "," + d + ")=" + got + " exp " + exp);
      }
    }
    console.log("checker-worker self-test OK");
  }

  if (typeof process !== "undefined" && process.argv && process.argv.includes("--self-test")) {
    selfTest();
  }
})(typeof self !== "undefined" ? self : globalThis);

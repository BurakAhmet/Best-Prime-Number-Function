/* Deterministic primality lab worker (Pages).
 * Mirrors the library ladder in-browser:
 *   small precheck → n−1 Pocklington (when n−1 factors) → 30-wheel trial when practical.
 *   n−1 factoring: trial → Fermat → Brent → p−1 → Montgomery ECM (Suyama).
 *   No hard digit / √n size ban: if proof is impractical, return path=inconclusive.
 * Not the OpenMP C core; no stochastic Miller–Rabin.
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
    // Scale *up* with size: hostile n−1 needs more work, not less.
    // Stop button still aborts via shouldStop in the caller.
    const fermatRounds = bits > 140 ? 8192 : bits > 100 ? 4096 : 2048;
    // Brent finds small/medium factors; huge cofactors go to ECM quickly.
    const brentCurves = bits > 140 ? 16n : bits > 100 ? 32n : 64n;
    const brentMaxR = bits > 140 ? (1n << 18n) : bits > 100 ? (1n << 20n) : BRENT_MAX_R;
    const p1B1 = bits > 140 ? 1_000_000 : bits > 100 ? 500_000 : P1_B1;

    let f = fermatSplit(c, fermatRounds);
    if (f && f > 1n && f < c) return f;

    for (let cv = 1n; cv <= brentCurves; cv++) {
      if (shouldStop && shouldStop()) return null;
      if (onTick && (cv & 7n) === 0n) onTick(cv, brentCurves);
      const g = brent(c, cv, 2n, brentMaxR);
      if (g > 1n && g < c) return g;
    }

    f = pollardP1(c, p1B1);
    if (f && f > 1n && f < c) return f;

    f = ecmFactor(c, onTick, shouldStop);
    if (f && f > 1n && f < c) return f;
    return null;
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
    // 22-digit factors of ~170-bit n−1 cofactors (hard55 exhibit).
    return [
      { B1: 11_000, curves: 200 },
      { B1: 25_000, curves: 200 },
      { B1: 50_000, curves: 300 },
    ];
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
  function ecmFactor(n, onTick, shouldStop) {
    if (n < 4n || (n & 1n) === 0n) return n % 2n === 0n && n > 2n ? 2n : null;
    const bits = bitLength(n);
    const phases = ecmPhases(bits);
    let sigmaBase = 6;
    let doneCurves = 0;
    let totalCurves = 0;
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
        doneCurves++;
        if (onTick) onTick(BigInt(doneCurves), BigInt(totalCurves));
        const sigma = BigInt(sigmaBase + i);
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
      if (r === true) return true;
      if (r === false) return false;
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
      return FValue(fac) > target;
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
      if (cofactorIsPrime(c, depth, onTick, shouldStop)) {
        fac.set(c, (fac.get(c) || 0) + 1);
        if (doneFac()) return fac;
        continue;
      }
      if (splits >= maxSplits) return null;
      splits++;
      if (onTick) onTick(0n, target);
      const f = trySplitCofactor(c, onTick, shouldStop);
      if (f === null || f <= 1n || f >= c) return null;
      stack.push(f);
      stack.push(c / f);
    }
    return doneFac() ? fac : null;
  }

  function pocklington(n, primesOfF) {
    const fermatOk = new Map();
    for (let qi = 0; qi < primesOfF.length; qi++) {
      const q = primesOfF[qi];
      let found = false;
      for (let ai = 0; ai < BASES.length; ai++) {
        const a = BASES[ai];
        if (a % n === 0n) return n === a ? true : false;
        let ok = fermatOk.get(a);
        if (ok === undefined) {
          ok = powBig(a, n - 1n, n) === 1n;
          fermatOk.set(a, ok);
        }
        if (!ok) return false;
        if (gcd(powBig(a, (n - 1n) / q, n) - 1n, n) === 1n) {
          found = true;
          break;
        }
      }
      if (!found) return null;
    }
    return true;
  }

  /** True / False / null (inconclusive). */
  function nm1Primality(n, depth, onTick, shouldStop) {
    if (depth === undefined) depth = 0;
    if (n < 2n) return false;
    if (n === 2n || n === 3n || n === 5n || n === 7n) return true;
    if ((n & 1n) === 0n || n % 3n === 0n || n % 5n === 0n) return false;

    for (let i = 0; i < 6; i++) {
      const a = BASES[i];
      if (a % n === 0n) return n === a;
      if (powBig(a, n - 1n, n) !== 1n) return false;
    }

    const fac = factorEnough(n, depth, onTick, shouldStop);
    if (!fac) return null;

    const F = FValue(fac);
    if (F <= 1n || (n - 1n) % F !== 0n) return null;
    if (F * F <= n) return null;

    const primes = Array.from(fac.keys()).sort(function (a, b) {
      return a === b ? 0 : a > b ? -1 : 1;
    });
    const target = isqrt(n);
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
      if (prod > target) break;
    }
    return pocklington(n, used);
  }

  function checkPrime(n, onTick, shouldStop) {
    const t0 = typeof performance !== "undefined" ? performance.now() : 0;
    if (n < 2n) return done(false, "tiny", null, "n < 2", isqrt(n), t0);
    if (n < 4n) return done(true, "tiny", null, "2 or 3", isqrt(n), t0);
    if ((n & 1n) === 0n) return done(false, "tiny", 2n, "even", isqrt(n), t0);

    for (let k = 0; k < SMALL.length; k++) {
      const p = SMALL[k];
      if (n === p) return done(true, "small-prime", null, "hits precheck table", isqrt(n), t0);
      if (n % p === 0n) return done(false, "small-prime", p, "divisible by small prime", isqrt(n), t0);
      if (p * p > n) return done(true, "small-prime", null, "√n inside precheck", isqrt(n), t0);
    }

    const limit = isqrt(n);

    // Hard / multi-limb: n−1 Pocklington first (same idea as the Python library).
    if (n >= TWO64 || limit >= NM1_ISQRT) {
      if (onTick) onTick(0n, limit);
      const decided = nm1Primality(n, 0, onTick, shouldStop);
      if (shouldStop && shouldStop()) return { aborted: true };
      if (decided === true) {
        return done(
          true,
          "n-1-pocklington",
          null,
          "n−1 Pocklington proof (browser; no RNG)",
          limit,
          t0
        );
      }
      if (decided === false) {
        return done(
          false,
          "n-1-pocklington",
          null,
          "failed fixed-base Fermat / Pocklington filter (composite)",
          limit,
          t0
        );
      }
      // inconclusive → trial if budget allows
    }

    if (limit > TRIAL_SOFT_ISQRT) {
      return {
        prime: null,
        path: "inconclusive",
        factor: null,
        isqrt: limit.toString(),
        ms: typeof performance !== "undefined" ? performance.now() - t0 : 0,
        note:
          "No size ban: n−1 could not be factored enough for a Pocklington proof, and automatic pure trial would need ~⌊√n⌋ modular divisions (impractical in a tab). Use the Python / OpenMP library for longer ECM/SIQS factoring, or try a smaller n / a prime with smoother n−1.",
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
        if (onTick) onTick(i, limit);
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
        if (onTick) onTick(i, limitNum);
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
        if (onTick) onTick(i, limit);
      }
    }
    return done(true, "wheel-30", null, "no factor ≤ √n (exact trial)", limit, t0);
  }

  const api = {
    isqrt: isqrt,
    checkPrime: checkPrime,
    ecmFactor: ecmFactor,
    umod64: umod64,
    nm1Primality: nm1Primality,
    WARN_ISQRT: WARN_ISQRT,
    TRIAL_SOFT_ISQRT: TRIAL_SOFT_ISQRT,
    COFACTOR_TRIAL_ISQRT: COFACTOR_TRIAL_ISQRT,
    NM1_ISQRT: NM1_ISQRT,
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
      if (msg.cmd !== "check") return;
      stop = false;
      try {
        const n = BigInt(String(msg.n));
        const res = checkPrime(
          n,
          function (i, lim) {
            g.postMessage({
              type: "progress",
              i: String(i),
              limit: String(lim),
            });
          },
          function () {
            return stop;
          }
        );
        if (res && res.aborted) {
          g.postMessage({ type: "aborted" });
          return;
        }
        g.postMessage({ type: "done", result: res });
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

    const overSafe = 59n * (MAX_SAFE / 59n + 11n);
    assert(overSafe > MAX_SAFE && overSafe < TWO64, "u64 fixture range");
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

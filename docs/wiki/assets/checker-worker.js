/* Deterministic 30-wheel trial for the Pages lab (not the OpenMP C core).
 * Loaded as a Web Worker from checker.js; also runnable via
 *   node docs/wiki/assets/checker-worker.js --self-test
 */
(function (g) {
  const STEPS = [4, 2, 4, 2, 4, 6, 2, 6];
  const STEPS_B = [4n, 2n, 4n, 2n, 4n, 6n, 2n, 6n];
  const SMALL = [3n, 5n, 7n, 11n, 13n, 17n, 19n, 23n, 29n, 31n, 37n, 41n, 43n, 47n, 53n];
  const SMALL_N = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53];
  const MAX_SAFE = BigInt(Number.MAX_SAFE_INTEGER);
  const TWO64 = 1n << 64n;
  /** Confirm in the UI above this √n (still exact; just slow). */
  const WARN_ISQRT = 8_000_000n;
  /** Browser demo hard stop — far above any 64-bit n (√(2^64-1) ≈ 2^32). */
  const REFUSE_ISQRT = 20_000_000_000n;

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

  /** (hi<<32 | lo) % d for uint32 hi/lo and Number d in [1, 2^53). */
  function umod64(lo, hi, d) {
    let r = (hi >>> 16) % d;
    r = (r * 65536 + (hi & 0xffff)) % d;
    r = (r * 65536 + (lo >>> 16)) % d;
    r = (r * 65536 + (lo & 0xffff)) % d;
    return r;
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
    if (limit > REFUSE_ISQRT) {
      return {
        prime: null,
        path: "too-large-for-browser",
        factor: null,
        isqrt: limit.toString(),
        ms: typeof performance !== "undefined" ? performance.now() - t0 : 0,
        note: "√n is too large for a tab. Use the Python / OpenMP library.",
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
    let si = 0;
    // i ≡ 59 ≡ 29 (mod 30); STEPS[6] starts the 59→61 step. After full +30 cycles, si stays 6.
    si = 6;
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
    umod64: umod64,
    WARN_ISQRT: WARN_ISQRT,
    REFUSE_ISQRT: REFUSE_ISQRT,
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

    const hard = 9223372036854775783n;
    const lim = isqrt(hard);
    assert(lim === 3037000499n, "isqrt(near-2^63) = " + lim);
    assert(lim <= REFUSE_ISQRT, "REFUSE_ISQRT still blocks near-2^63");
    assert(lim > WARN_ISQRT, "WARN_ISQRT should flag near-2^63 as slow");

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

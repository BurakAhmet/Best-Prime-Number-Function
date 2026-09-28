/* Deterministic cyclotomic proof for the in-browser lab.
 * Same Jacobi-sum test as best_prime/primality_aprcl.py (Schoof §3,
 * Cohen–Lenstra one-exponentiation form). No randomness.
 */
(function (g) {
  // Same ladder as best_prime/primality_aprcl.py. The last entry clears
  // sqrt(n) for every 5000-digit integer. Primes above Q_CAP are omitted.
  const R_LADDER = [720720, 12252240, 73513440, 367567200, 1396755360, 4655851200];
  const R_SMALL = R_LADDER[0];
  const R_LARGE = R_LADDER[R_LADDER.length - 1];
  const Q_CAP = 250000000;

  function factor(n) {
    const fac = [];
    n = Math.trunc(n);
    let d = 2;
    while (d * d <= n) {
      if (n % d === 0) {
        let c = 0;
        while (n % d === 0) {
          n = Math.trunc(n / d);
          c++;
        }
        fac.push([d, c]);
      }
      d += d === 2 ? 1 : 2;
    }
    if (n > 1) fac.push([n, 1]);
    return fac;
  }

  function divisors(n) {
    let ds = [1];
    for (const [p, e] of factor(n)) {
      let pe = 1;
      const nd = [];
      for (let i = 0; i <= e; i++) {
        for (const d of ds) nd.push(d * pe);
        pe *= p;
      }
      ds = nd;
    }
    return ds;
  }

  function isPrimeSmall(q) {
    if (q < 2) return false;
    if (q % 2 === 0) return q === 2;
    for (let d = 3; d * d <= q; d += 2) if (q % d === 0) return false;
    return true;
  }

  function phi(n) {
    let v = n;
    for (const [p] of factor(n)) v = (v / p) * (p - 1);
    return v;
  }

  function primRoot(q) {
    const n = q - 1;
    const fac = [];
    let x = n;
    for (let d = 2; d * d <= x; d += d === 2 ? 1 : 2) {
      if (x % d === 0) {
        fac.push(d);
        while (x % d === 0) x = (x / d) | 0;
      }
    }
    if (x > 1) fac.push(x);
    for (let g0 = 2; ; g0++) {
      let ok = true;
      for (const f of fac) {
        let e = (n / f) | 0;
        let p = 1;
        let b = g0 % q;
        while (e) {
          if (e & 1) p = (p * b) % q;
          b = (b * b) % q;
          e >>= 1;
        }
        if (p === 1) {
          ok = false;
          break;
        }
      }
      if (ok) return g0;
    }
  }

  function jacobi(q, r, twice) {
    const g0 = primRoot(q);
    const ind = new Uint8Array(q);
    let x = 1;
    const step = ((q - 1) / r) | 0;
    for (let i = 0; i < q - 1; i++) {
      ind[x] = (i * step) % r;
      x = (x * g0) % q;
    }
    const acc = new Array(r).fill(0);
    const mult = twice ? 2 : 1;
    for (let t = 1; t < q; t++) {
      const u = (q + 1 - t) % q;
      if (u === 0) continue;
      acc[(ind[t] + ((mult * ind[u]) % r)) % r]--;
    }
    return acc;
  }

  const tables = new Map();
  const moduli = new Map();

  function modulus(R) {
    const hit = moduli.get(R);
    if (hit) return hit;
    const qs = divisors(R)
      .map((d) => d + 1)
      .filter((q) => q <= Q_CAP && isPrimeSmall(q))
      .sort((a, b) => a - b);
    let s = 1n;
    for (const q of qs) s *= BigInt(q);
    const built = { s, qs };
    moduli.set(R, built);
    return built;
  }

  function table(R) {
    const hit = tables.get(R);
    if (hit) return hit;
    const mod = modulus(R);
    const tests = [];
    for (const q of mod.qs) {
      for (const [p, e] of factor(q - 1)) {
        const r = p ** e;
        tests.push({ q, r, prime: p, j: jacobi(q, r, false), j2: null });
      }
    }
    const built = { s: mod.s, tests };
    tables.set(R, built);
    return built;
  }

  function phiPoly(r) {
    const [p, e] = factor(r)[0];
    const pk = p ** (e - 1);
    const deg = pk * (p - 1);
    const phi = new Array(deg + 1).fill(0n);
    for (let i = 0; i < p; i++) phi[i * pk] = 1n;
    return phi;
  }

  function modn(c, n) {
    const r = c % n;
    return r < 0n ? r + n : r;
  }

  function modPhi(raw, phi, n) {
    const deg = phi.length - 1;
    const r = raw.slice();
    while (r.length > deg) {
      let lead = r[r.length - 1];
      const shift = r.length - 1 - deg;
      r.pop();
      if (lead === 0n) continue;
      // Phi coefficients are 0 or 1. Reduce the lead once, then subtract.
      lead = modn(lead, n);
      if (lead === 0n) continue;
      for (let i = 0; i < deg; i++) {
        if (phi[i] !== 0n) r[shift + i] -= lead;
      }
    }
    while (r.length < deg) r.push(0n);
    for (let i = 0; i < deg; i++) r[i] = modn(r[i], n);
    return r;
  }

  function ringMul(a, b, phi, n) {
    const deg = a.length;
    if (deg >= 6) return kroneckerMul(a, b, phi, n);
    const raw = new Array(deg * 2 - 1).fill(0n);
    for (let i = 0; i < deg; i++) {
      const ai = a[i];
      if (ai === 0n) continue;
      for (let j = 0; j < deg; j++) {
        const bj = b[j];
        if (bj !== 0n) raw[i + j] += ai * bj;
      }
    }
    for (let i = 0; i < raw.length; i++) if (raw[i] !== 0n) raw[i] = modn(raw[i], n);
    return modPhi(raw, phi, n);
  }

  const gapCache = new Map();

  function kroneckerMul(a, b, phi, n) {
    const deg = a.length;
    let gap = gapCache.get(n);
    if (gap === undefined) {
      gap = BigInt(n.toString(2).length * 2 + 16);
      gapCache.set(n, gap);
    }
    const mask = (1n << gap) - 1n;
    let A = 0n;
    let B = 0n;
    let sh = 0n;
    for (let i = 0; i < deg; i++) {
      A += a[i] << sh;
      B += b[i] << sh;
      sh += gap;
    }
    let P = A * B;
    const raw = new Array(deg * 2 - 1);
    for (let i = 0; i < raw.length; i++) {
      raw[i] = P & mask;
      P >>= gap;
    }
    return modPhi(raw, phi, n);
  }

  function ringPow(base, exp, phi, n) {
    const deg = base.length;
    const one = new Array(deg).fill(0n);
    one[0] = 1n;
    if (exp === 0n) return one;
    const table = [one, base.slice()];
    for (let t = 2; t < 16; t++) table.push(ringMul(table[t - 1], base, phi, n));
    let bits = 0;
    let e = exp;
    while (e > 0n) {
      e >>= 1n;
      bits++;
    }
    let acc = null;
    for (let bit = bits - 1; bit >= 0; ) {
      let nb = 4;
      if (bit + 1 < nb) nb = bit + 1;
      let w = 0;
      for (let s = 0; s < nb; s++) {
        w = (w << 1) | Number((exp >> BigInt(bit - s)) & 1n);
      }
      if (acc === null) {
        if (w !== 0) acc = table[w].slice();
        bit -= nb;
        continue;
      }
      for (let s = 0; s < nb; s++) acc = ringMul(acc, acc, phi, n);
      if (w) acc = ringMul(acc, table[w], phi, n);
      bit -= nb;
    }
    return acc || one;
  }

  function galois(a, m, phi, n) {
    const raw = new Array((a.length - 1) * m + 1).fill(0n);
    for (let i = 0; i < a.length; i++) if (a[i] !== 0n) raw[i * m] = a[i];
    return modPhi(raw, phi, n);
  }

  function rootIndex(elem, r, phi, n) {
    const deg = phi.length - 1;
    for (let m = 0; m < r; m++) {
      const raw = new Array(Math.max(m + 1, deg)).fill(0n);
      raw[m] = 1n;
      const z = modPhi(raw, phi, n);
      let same = true;
      for (let i = 0; i < deg; i++) {
        if (z[i] !== elem[i]) {
          same = false;
          break;
        }
      }
      if (same) return m;
    }
    return -1;
  }

  function coprimeIdxs(r) {
    const out = [];
    for (let i = 1; i < r; i++) {
      let a = i;
      let b = r;
      while (b) {
        const t = a % b;
        a = b;
        b = t;
      }
      if (a === 1) out.push(i);
    }
    return out;
  }

  function modInverse(i, r) {
    let a = i;
    let b = r;
    let x = 1;
    let y = 0;
    while (b) {
      const q = (a / b) | 0;
      const t = a - q * b;
      a = b;
      b = t;
      const tx = x - q * y;
      x = y;
      y = tx;
    }
    return ((x % r) + r) % r;
  }

  function productH(n, r, baseCoeffs, idxs) {
    const phi = phiPoly(r);
    let base = modPhi(baseCoeffs.map((c) => BigInt(c)), phi, n);
    const deg = base.length;
    const one = new Array(deg).fill(0n);
    one[0] = 1n;
    const cache = new Map();
    function image(i) {
      const inv = modInverse(i, r);
      let hit = cache.get(inv);
      if (!hit) {
        hit = galois(base, inv, phi, n);
        cache.set(inv, hit);
      }
      return hit;
    }
    const rN = BigInt(r);
    const q = n / rN;
    const tmod = Number(n % rN);
    let s1 = one;
    let alpha = one.slice();
    for (const i of idxs) {
      const img = image(i);
      s1 = ringMul(s1, ringPow(img, BigInt(i), phi, n), phi, n);
      const e = ((tmod * i) / r) | 0;
      if (e) alpha = ringMul(alpha, ringPow(img, BigInt(e), phi, n), phi, n);
    }
    const acc = ringMul(ringPow(s1, q, phi, n), alpha, phi, n);
    return rootIndex(acc, r, phi, n);
  }

  function oneTest(n, test) {
    const r = test.r;
    const prime = test.prime;
    let base;
    let idxs;
    if (r >= 8 && prime === 2 && (n % 8n === 1n || n % 8n === 3n)) {
      if (!test.j2) test.j2 = jacobi(test.q, r, true);
      const both = new Array(2 * r).fill(0);
      for (let i = 0; i < test.j.length; i++) {
        const ca = test.j[i];
        if (!ca) continue;
        for (let k = 0; k < test.j2.length; k++) {
          const cb = test.j2[k];
          if (cb) both[i + k] += ca * cb;
        }
      }
      base = both;
      idxs = [];
      for (let i = 1; i < r; i++) if (i % 8 === 1 || i % 8 === 3) idxs.push(i);
    } else {
      base = test.j;
      idxs = coprimeIdxs(r);
    }
    const h = productH(n, r, base, idxs);
    return { ok: h >= 0, prime, h };
  }

  function lpHit(n, q, prime, h) {
    if (h < 0 || h % prime !== 0) return false;
    if (h % prime === 0) return false;
    return true;
  }

  function witness(n, q, prime, h) {
    if (h < 0 || h % prime === 0) return false;
    if (prime === 2) return modPow(BigInt(q), (n - 1n) / 2n, n) === n - 1n;
    return true;
  }

  function modPow(base, exp, mod) {
    let result = 1n;
    let b = base % mod;
    let e = exp;
    while (e > 0n) {
      if (e & 1n) result = (result * b) % mod;
      e >>= 1n;
      if (e) b = (b * b) % mod;
    }
    return result;
  }

  function chooseR(n) {
    const root = isqrt(n);
    for (let i = 0; i < R_LADDER.length; i++) {
      if (modulus(R_LADDER[i]).s > root) return R_LADDER[i];
    }
    return null;
  }

  function isqrt(n) {
    if (n < 2n) return n;
    let x = 1n << BigInt((bitlen(n) + 1) >> 1);
    for (;;) {
      const y = (x + n / x) >> 1n;
      if (y >= x) return x;
      x = y;
    }
  }

  function bitlen(n) {
    let b = 0;
    let x = n;
    while (x > 0n) {
      x >>= 1n;
      b++;
    }
    return b;
  }

  function proveSerial(n, onTick, shouldStop) {
    if (n < 2n) return { prime: false };
    if ((n & 1n) === 0n) return { prime: false, factor: 2n };
    const root = isqrt(n);
    if (root * root === n) return { prime: false, factor: root };
    const R = chooseR(n);
    if (R == null) return { prime: null, note: "cyclotomic modulus does not cover n" };
    if (onTick) onTick({ phase: "cyclotomic", i: 0n, limit: 1n, extra: { label: "Jacobi sums" } });
    const tab = table(R);
    if (tab.s <= root) return { prime: null, note: "cyclotomic modulus does not cover n" };
    const g = gcd(n, tab.s);
    if (g > 1n) return { prime: false, factor: g };
    const satisfied = new Set();
    const tests = tab.tests;
    for (let i = 0; i < tests.length; i++) {
      if (shouldStop && shouldStop()) return { aborted: true };
      if (onTick && (i & 7) === 0) {
        onTick({
          phase: "cyclotomic",
          i: BigInt(i),
          limit: BigInt(tests.length),
          extra: { label: "cyclotomic test " + (i + 1) + "/" + tests.length },
        });
      }
      const row = oneTest(n, tests[i]);
      if (!row.ok) return { prime: false };
      if (witnessOk(n, tests[i].q, row.prime, row.h)) satisfied.add(row.prime);
    }
    for (const [prime] of factor(R)) {
      if (prime >= 3 && modPow(n, BigInt(prime - 1), BigInt(prime * prime)) !== 1n) {
        satisfied.add(prime);
      } else if (!satisfied.has(prime)) {
        const w = witnessPrime(n, prime, shouldStop);
        if (w === "abort") return { aborted: true };
        if (w === false) return { prime: false };
        if (w == null) return { prime: null, note: "missing l-adic witness" };
      }
    }
    if (onTick) onTick({ phase: "cyclotomic", i: 0n, limit: 1n, extra: { label: "residue scan" } });
    const scan = scanResidues(n, tab.s, root, R - 1, shouldStop);
    if (scan.aborted) return { aborted: true };
    if (scan.hit) return { prime: false, factor: scan.factor };
    return { prime: true, path: "aprcl" };
  }

  function gcd(a, b) {
    while (b) {
      const t = a % b;
      a = b;
      b = t;
    }
    return a;
  }

  function witnessPrime(n, prime, shouldStop) {
    let tried = 0;
    let i = 1;
    while (tried < 48 && i < 2000000) {
      if (shouldStop && shouldStop()) return "abort";
      const q = prime * i + 1;
      i++;
      if (!isPrimeSmall(q) || n % BigInt(q) === 0n) {
        if (q > 1 && n % BigInt(q) === 0n) return false;
        continue;
      }
      let qq = q - 1;
      let k = 0;
      while (qq % prime === 0) {
        qq = (qq / prime) | 0;
        k++;
      }
      const r = prime ** k;
      if (r >= 40) continue;
      tried++;
      const test = { q, r, prime, j: jacobi(q, r, false), j2: null };
      const row = oneTest(n, test);
      if (!row.ok) return false;
      if (witnessOk(n, q, prime, row.h)) return true;
    }
    return null;
  }

  function scanResidues(n, s, root, span, shouldStop) {
    const base = n % s;
    let acc = 1n;
    for (let k = 0; k < span; k++) {
      if ((k & 262143) === 0 && shouldStop && shouldStop()) return { aborted: true };
      acc = (acc * base) % s;
      if (acc > 1n && acc <= root && n % acc === 0n) return { hit: true, factor: acc };
    }
    return { hit: false };
  }

  function witnessOk(n, q, prime, h) {
    if (h < 0 || h % prime === 0) return false;
    if (prime === 2) return modPow(BigInt(q), (n - 1n) / 2n, n) === n - 1n;
    return true;
  }

  function runTestIndexes(n, R, indexes, progress) {
    const tab = table(R);
    const satisfied = [];
    for (let k = 0; k < indexes.length; k++) {
      const row = oneTest(n, tab.tests[indexes[k]]);
      if (progress && (k & 3) === 0) progress(k, indexes.length);
      if (!row.ok) return { ok: false };
      if (witnessOk(n, tab.tests[indexes[k]].q, row.prime, row.h)) satisfied.push(row.prime);
    }
    return { ok: true, satisfied };
  }

  function runScan(n, s, root, start, count, progress) {
    const base = n % s;
    let acc = modPow(base, BigInt(start), s);
    const step = 65536;
    for (let k = 0; k < count; k++) {
      acc = (acc * base) % s;
      if (progress && k % step === 0) progress(k, count);
      if (acc > 1n && acc <= root && n % acc === 0n) return { hit: true, factor: acc.toString() };
    }
    return { hit: false };
  }

  function handleJob(msg, progress) {
    const n = BigInt(msg.n);
    let out;
    if (msg.cmd === "tests") out = runTestIndexes(n, msg.R, msg.indexes, progress);
    else if (msg.cmd === "scan") {
      out = runScan(n, BigInt(msg.s), BigInt(msg.root), msg.start, msg.count, progress);
    } else out = { ok: false };
    if (msg._id != null) out._id = msg._id;
    return out;
  }

  function proveParallel(n, onTick, shouldStop, spawn) {
    if (n < 2n) return Promise.resolve({ prime: false });
    const root = isqrt(n);
    if (root * root === n) return Promise.resolve({ prime: false, factor: root });
    const R = chooseR(n);
    if (R == null) {
      return Promise.resolve({ prime: null, note: "cyclotomic modulus does not cover n" });
    }
    if (onTick) onTick({ phase: "cyclotomic", i: 0n, limit: 1n, extra: { label: "Jacobi sums" } });
    const tab = table(R);
    if (tab.s <= root) return Promise.resolve({ prime: null, note: "cyclotomic modulus does not cover n" });
    const g0 = gcd(n, tab.s);
    if (g0 > 1n && g0 < n) return Promise.resolve({ prime: false, factor: g0 });
    const cores = spawn.cores;
    const indexes = tab.tests.map((_, i) => i);
    // Heavier prime powers first so the chunks stay even.
    indexes.sort((a, b) => tab.tests[b].r - tab.tests[a].r);
    const chunks = Array.from({ length: cores }, () => []);
    indexes.forEach((ix, i) => chunks[i % cores].push(ix));
    return spawn
      .run(chunks.map((indexes) => ({ cmd: "tests", n: n.toString(), R, indexes })))
      .then((parts) => {
        if (shouldStop && shouldStop()) return { aborted: true };
        const satisfied = new Set();
        for (const part of parts) {
          if (!part.ok) return { prime: false };
          for (const p of part.satisfied) satisfied.add(p);
        }
        for (const [prime] of factor(R)) {
          if (prime >= 3 && modPow(n, BigInt(prime - 1), BigInt(prime * prime)) !== 1n) {
            satisfied.add(prime);
          } else if (!satisfied.has(prime)) {
            const w = witnessPrime(n, prime, shouldStop);
            if (w === "abort") return { aborted: true };
            if (w === false) return { prime: false };
            if (w == null) return { prime: null, note: "missing l-adic witness" };
          }
        }
        if (onTick) onTick({ phase: "cyclotomic", i: 0n, limit: 1n, extra: { label: "residue scan" } });
        const span = R - 1;
        const jobs = [];
        const chunk = Math.ceil(span / cores);
        for (let i = 0; i < cores; i++) {
          const start = i * chunk;
          if (start >= span) break;
          jobs.push({
            cmd: "scan",
            n: n.toString(),
            s: tab.s.toString(),
            root: root.toString(),
            start,
            count: Math.min(chunk, span - start),
          });
        }
        return spawn.run(jobs).then((scans) => {
          for (const sc of scans) {
            if (sc.hit) return { prime: false, factor: BigInt(sc.factor) };
          }
          return { prime: true, path: "aprcl" };
        });
      });
  }

  const api = {
    R_SMALL,
    R_LARGE,
    R_LADDER,
    Q_CAP,
    modulus,
    chooseR,
    table,
    proveSerial,
    proveParallel,
    handleJob,
    oneTest,
    witnessOk,
    isqrt,
    factor,
    modPow,
    scanResidues,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  g.Aprcl = api;

  if (typeof WorkerGlobalScope !== "undefined" && g instanceof WorkerGlobalScope) {
    const path = String(g.location && g.location.pathname ? g.location.pathname : "");
    if (path.endsWith("aprcl.js")) {
      g.onmessage = function (ev) {
        const msg = ev.data || {};
        try {
          g.postMessage(
            handleJob(msg, function (k, total) {
              g.postMessage({
                progress: true,
                k: k,
                total: total,
                stage: msg.cmd === "scan" ? "scan" : "tests",
                _id: msg._id,
              });
            })
          );
        } catch (err) {
          g.postMessage({ ok: false, error: String(err && err.stack ? err.stack : err), _id: msg._id });
        }
      };
    }
  }

  try {
    const wt = require("worker_threads");
    if (wt.parentPort && wt.workerData && wt.workerData.aprcl) {
      wt.parentPort.on("message", (msg) => {
        try {
          wt.parentPort.postMessage(
            handleJob(msg, function (k, total) {
              wt.parentPort.postMessage({
                progress: true,
                k: k,
                total: total,
                stage: msg.cmd === "scan" ? "scan" : "tests",
                _id: msg._id,
              });
            })
          );
        } catch (err) {
          wt.parentPort.postMessage({
            ok: false,
            error: String(err && err.stack ? err.stack : err),
            _id: msg._id,
          });
        }
      });
    }
  } catch (err) {
    /* browser */
  }
})(typeof globalThis !== "undefined" ? globalThis : this);

/* Deterministic 30-wheel trial in the browser (demo; not the OpenMP C core). */
(function () {
  const STEPS = [4n, 2n, 4n, 2n, 4n, 6n, 2n, 6n];
  const SMALL = [3n, 5n, 7n, 11n, 13n, 17n, 19n, 23n, 29n, 31n, 37n, 41n, 43n, 47n, 53n];
  const HARD_ISQRT = 2_000_000n;
  const REFUSE_ISQRT = 8_000_000n;

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

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

  function parseN(raw) {
    const s = String(raw).trim().replace(/[_\s]/g, "");
    if (!s || !/^\d+$/.test(s)) return null;
    return BigInt(s);
  }

  function fmt(n) {
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  async function checkPrime(n, onTick, signal) {
    const t0 = performance.now();
    if (n < 2n) return done(false, "tiny", null, "n < 2");
    if (n < 4n) return done(true, "tiny", null, "2 or 3");
    if ((n & 1n) === 0n) return done(false, "tiny", 2n, "even");
    for (const p of SMALL) {
      if (n === p) return done(true, "small-prime", null, "hits precheck table");
      if (n % p === 0n) return done(false, "small-prime", p, "divisible by small prime");
      if (p * p > n) return done(true, "small-prime", null, "√n inside precheck");
    }
    const limit = isqrt(n);
    if (limit > REFUSE_ISQRT) {
      return {
        prime: null,
        path: "too-large-for-browser",
        isqrt: limit,
        ms: performance.now() - t0,
        note: "√n is too large for a tab. Use the Python / OpenMP library.",
      };
    }
    let i = 59n;
    let si = 6;
    let steps = 0;
    while (i <= limit) {
      if (signal.aborted) throw new DOMException("aborted", "AbortError");
      if (n % i === 0n) return done(false, "wheel-30", i, "30-wheel trial division");
      i += STEPS[si];
      si = (si + 1) & 7;
      steps++;
      if ((steps & 16383) === 0) {
        onTick(i, limit);
        await new Promise((r) => setTimeout(r, 0));
      }
    }
    return done(true, "wheel-30", null, "no factor ≤ √n (exact trial)");

    function done(prime, path, factor, note) {
      return { prime, path, factor, isqrt: isqrt(n), ms: performance.now() - t0, note };
    }
  }

  function mount(root) {
    root.innerHTML = `
      <section class="prime-lab" aria-label="Interactive primality lab">
        <label class="lab-label" for="lab-n">n</label>
        <div class="row">
          <input id="lab-n" type="text" inputmode="numeric" autocomplete="off"
            placeholder="Enter a natural number" aria-label="n"/>
          <button type="button" class="primary" id="lab-go">Check</button>
          <button type="button" id="lab-stop" disabled>Stop</button>
        </div>
        <div class="lab-progress" id="lab-bar"><i></i></div>
        <div class="lab-out" id="lab-out" aria-live="polite"></div>
      </section>`;

    const input = $("#lab-n", root);
    const go = $("#lab-go", root);
    const stop = $("#lab-stop", root);
    const out = $("#lab-out", root);
    const bar = $("#lab-bar", root);
    const barFill = $("i", bar);

    let ac = null;

    function render(state) {
      out.classList.add("show");
      out.className = "lab-out show " + (state.busy ? "busy" : state.prime ? "yes" : "no");
      if (state.busy) {
        out.innerHTML = `<p class="verdict">Checking…</p>
          <dl><dt>n</dt><dd>${escapeHtml(state.n)}</dd>
          <dt>⌊√n⌋</dt><dd>${state.isqrt}</dd>
          <dt>candidate</dt><dd>${state.i || "—"}</dd></dl>`;
        return;
      }
      if (state.prime === null) {
        out.innerHTML = `<p class="verdict">Too large here</p>
          <dl><dt>n</dt><dd>${escapeHtml(state.n)}</dd>
          <dt>⌊√n⌋</dt><dd>${fmt(state.isqrt)}</dd>
          <dt>note</dt><dd>${escapeHtml(state.note || "")}</dd></dl>`;
        return;
      }
      const verdict = state.prime ? "Prime" : "Composite";
      out.innerHTML = `<p class="verdict">${verdict}</p>
        <dl>
          <dt>n</dt><dd>${escapeHtml(state.n)}</dd>
          <dt>path</dt><dd>${escapeHtml(state.path)}</dd>
          <dt>⌊√n⌋</dt><dd>${fmt(state.isqrt)}</dd>
          ${state.factor != null ? `<dt>factor</dt><dd>${fmt(state.factor)}</dd>` : ""}
          <dt>time</dt><dd>${state.ms.toFixed(2)} ms</dd>
          <dt>note</dt><dd>${escapeHtml(state.note || "")}</dd>
        </dl>`;
    }

    async function run() {
      const n = parseN(input.value);
      if (n === null) {
        out.className = "lab-out show no";
        out.innerHTML = `<p class="verdict">Invalid n</p><p>Enter a non-negative decimal integer.</p>`;
        out.classList.add("show");
        return;
      }
      if (ac) ac.abort();
      ac = new AbortController();
      go.disabled = true;
      stop.disabled = false;
      bar.classList.add("show");
      barFill.style.width = "0%";
      const limit = isqrt(n);
      if (limit > HARD_ISQRT) {
        const ok = window.confirm(
          `⌊√n⌋ ≈ ${fmt(limit)}. This exact trial may take a long time in the browser. Continue?`
        );
        if (!ok) {
          go.disabled = false;
          stop.disabled = true;
          bar.classList.remove("show");
          return;
        }
      }
      render({ busy: true, n: n.toString(), isqrt: fmt(limit), i: "starting" });
      try {
        const res = await checkPrime(
          n,
          (i, lim) => {
            const pct = lim === 0n ? 100 : Number((i * 1000n) / lim) / 10;
            barFill.style.width = Math.min(100, pct) + "%";
            render({ busy: true, n: n.toString(), isqrt: fmt(lim), i: fmt(i) });
          },
          ac.signal
        );
        barFill.style.width = "100%";
        render({
          busy: false,
          prime: res.prime,
          n: n.toString(),
          path: res.path,
          isqrt: res.isqrt,
          factor: res.factor,
          ms: res.ms,
          note: res.note,
        });
      } catch (err) {
        if (err && err.name === "AbortError") {
          out.className = "lab-out show busy";
          out.innerHTML = `<p class="verdict">Stopped</p><p>Trial cancelled.</p>`;
        } else {
          out.className = "lab-out show no";
          out.innerHTML = `<p class="verdict">Error</p><p>${escapeHtml(String(err))}</p>`;
        }
      } finally {
        go.disabled = false;
        stop.disabled = true;
        bar.classList.remove("show");
        ac = null;
      }
    }

    go.addEventListener("click", run);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") run();
    });
    stop.addEventListener("click", () => ac && ac.abort());
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("prime-lab-root");
    if (root) mount(root);
  });
})();

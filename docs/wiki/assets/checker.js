/* Deterministic 30-wheel lab UI. Long trials run in checker-worker.js. */
(function () {
  const WARN_ISQRT = 8_000_000n;
  const REFUSE_ISQRT = 20_000_000_000n;

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

  function workerUrl() {
    const el = document.querySelector("script[src*='checker.js']");
    if (el && el.src) {
      return el.src.replace(/checker\.js(\?[^/?#]*)?/, "checker-worker.js$1");
    }
    return "assets/checker-worker.js";
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
        <p class="lab-hint">Exact 30-wheel trial in this tab (not the OpenMP C core).
          64-bit <em>n</em> is allowed — hard primes can take minutes. Stop anytime.</p>
        <div class="lab-progress" id="lab-bar"><i></i></div>
        <div class="lab-out" id="lab-out" aria-live="polite"></div>
      </section>`;

    const input = $("#lab-n", root);
    const go = $("#lab-go", root);
    const stop = $("#lab-stop", root);
    const out = $("#lab-out", root);
    const bar = $("#lab-bar", root);
    const barFill = $("i", bar);

    let worker = null;

    function killWorker() {
      if (worker) {
        try {
          worker.terminate();
        } catch (_) {
          /* ignore */
        }
        worker = null;
      }
    }

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
          <dt>time</dt><dd>${Number(state.ms).toFixed(2)} ms</dd>
          <dt>note</dt><dd>${escapeHtml(state.note || "")}</dd>
        </dl>`;
    }

    function finishIdle() {
      go.disabled = false;
      stop.disabled = true;
      bar.classList.remove("show");
      killWorker();
    }

    function run() {
      const n = parseN(input.value);
      if (n === null) {
        out.className = "lab-out show no";
        out.innerHTML = `<p class="verdict">Invalid n</p><p>Enter a non-negative decimal integer.</p>`;
        out.classList.add("show");
        return;
      }
      if (typeof Worker === "undefined") {
        out.className = "lab-out show no";
        out.innerHTML = `<p class="verdict">No Web Worker</p>
          <p>This browser cannot run the background trial. Use the Python / OpenMP library.</p>`;
        return;
      }

      const limit = isqrt(n);
      if (limit > REFUSE_ISQRT) {
        render({
          busy: false,
          prime: null,
          n: n.toString(),
          isqrt: limit,
          note: "√n is too large for a tab. Use the Python / OpenMP library.",
        });
        return;
      }
      if (limit > WARN_ISQRT) {
        const ok = window.confirm(
          "⌊√n⌋ ≈ " +
            fmt(limit) +
            ". Exact 30-wheel trial may take minutes in the browser " +
            "(background worker; Stop is available). Continue?"
        );
        if (!ok) return;
      }

      killWorker();
      go.disabled = true;
      stop.disabled = false;
      bar.classList.add("show");
      barFill.style.width = "0%";
      render({ busy: true, n: n.toString(), isqrt: fmt(limit), i: "starting" });

      try {
        worker = new Worker(workerUrl());
      } catch (err) {
        finishIdle();
        out.className = "lab-out show no";
        out.innerHTML = `<p class="verdict">Worker failed</p><p>${escapeHtml(String(err))}</p>`;
        return;
      }

      worker.onmessage = function (ev) {
        const msg = ev.data || {};
        if (msg.type === "progress") {
          try {
            const i = BigInt(msg.i);
            const lim = BigInt(msg.limit);
            const pct = lim === 0n ? 100 : Number((i * 1000n) / lim) / 10;
            barFill.style.width = Math.min(100, pct) + "%";
            render({ busy: true, n: n.toString(), isqrt: fmt(lim), i: fmt(i) });
          } catch (_) {
            /* ignore malformed progress */
          }
          return;
        }
        if (msg.type === "aborted") {
          out.className = "lab-out show busy";
          out.innerHTML = `<p class="verdict">Stopped</p><p>Trial cancelled.</p>`;
          finishIdle();
          return;
        }
        if (msg.type === "error") {
          out.className = "lab-out show no";
          out.innerHTML = `<p class="verdict">Error</p><p>${escapeHtml(msg.message || "unknown")}</p>`;
          finishIdle();
          return;
        }
        if (msg.type === "done" && msg.result) {
          const res = msg.result;
          barFill.style.width = "100%";
          render({
            busy: false,
            prime: res.prime,
            n: n.toString(),
            path: res.path,
            isqrt: BigInt(res.isqrt),
            factor: res.factor == null ? null : BigInt(res.factor),
            ms: res.ms,
            note: res.note,
          });
          finishIdle();
        }
      };

      worker.onerror = function (err) {
        out.className = "lab-out show no";
        out.innerHTML = `<p class="verdict">Error</p><p>${escapeHtml(err && err.message ? err.message : String(err))}</p>`;
        finishIdle();
      };

      worker.postMessage({ cmd: "check", n: n.toString() });
    }

    go.addEventListener("click", run);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") run();
    });
    stop.addEventListener("click", function () {
      if (worker) {
        try {
          worker.postMessage({ cmd: "stop" });
        } catch (_) {
          /* ignore */
        }
        killWorker();
        out.className = "lab-out show busy";
        out.innerHTML = `<p class="verdict">Stopped</p><p>Trial cancelled.</p>`;
        go.disabled = false;
        stop.disabled = true;
        bar.classList.remove("show");
      }
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  document.addEventListener("DOMContentLoaded", function () {
    const root = document.getElementById("prime-lab-root");
    if (root) mount(root);
  });
})();

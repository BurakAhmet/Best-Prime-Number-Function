/* Deterministic lab UI. Heavy work runs in checker-worker.js
 * (n−1 Pocklington when n−1 factors, else 30-wheel trial). */
(function () {
  const WARN_ISQRT = 8_000_000n;
  const TWO64 = 1n << 64n;
  const ORRERY_ISQRT = 100_000n;
  const WHEEL30 = [1, 7, 11, 13, 17, 19, 23, 29];
  const DOCTRINE = "deterministic · n−1 Pocklington / trial · no stochastic Miller–Rabin";

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

  function xmlEscape(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function certificateText(state) {
    const lines = [
      "DETERMINISTIC PRIMORUM RECORD",
      "Best-Prime-Number-Function",
      "",
      "n = " + state.n,
      "floor(sqrt(n)) = " + state.isqrt.toString(),
      "verdict = " + (state.prime ? "prime" : "composite"),
      "path = " + state.path,
    ];
    if (state.factor != null) lines.push("factor = " + state.factor.toString());
    else if (state.prime) lines.push("factor = none (proof path: " + state.path + ")");
    lines.push("time_ms = " + Number(state.ms).toFixed(2));
    if (state.note) lines.push("note = " + state.note);
    lines.push("");
    lines.push(DOCTRINE);
    return lines.join("\n");
  }

  function certificateSvg(state) {
    const verdict = state.prime ? "Prime" : "Composite";
    const ink = state.prime ? "#245c3d" : "#c45c2c";
    const rows = [
      ["n", state.n],
      ["⌊√n⌋", fmt(state.isqrt)],
      ["path", state.path],
    ];
    if (state.factor != null) rows.push(["factor", fmt(state.factor)]);
    rows.push(["time", Number(state.ms).toFixed(2) + " ms"]);
    if (state.note) rows.push(["note", state.note]);
    const rowH = 28;
    const blockH = rows.length * rowH;
    const h = 220 + blockH;
    let y = 168;
    const dl = rows
      .map(function (pair) {
        const line =
          '<text x="56" y="' +
          y +
          '" font-size="13" fill="#5c6778" font-family="ui-monospace, monospace">' +
          xmlEscape(pair[0].toUpperCase()) +
          '</text>' +
          '<text x="150" y="' +
          y +
          '" font-size="15" fill="#1b2437" font-family="ui-monospace, monospace">' +
          xmlEscape(pair[1]) +
          "</text>";
        y += rowH;
        return line;
      })
      .join("\n");
    return (
      '<?xml version="1.0" encoding="UTF-8"?>\n' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="' +
      h +
      '" viewBox="0 0 800 ' +
      h +
      '">\n' +
      '<rect width="800" height="' +
      h +
      '" fill="#fbf6ea"/>\n' +
      '<rect x="18" y="18" width="764" height="' +
      (h - 36) +
      '" fill="none" stroke="#e4d9c4" stroke-width="1"/>\n' +
      '<text x="56" y="58" font-size="13" letter-spacing="0.18em" fill="#c45c2c" ' +
      'font-family="Times New Roman, STIX Two Text, serif">ACTA PRIMORUM</text>\n' +
      '<text x="744" y="58" text-anchor="end" font-size="13" fill="#245c3d" ' +
      'font-family="Times New Roman, STIX Two Text, serif">DETERMINISTIC</text>\n' +
      '<text x="56" y="108" font-size="36" fill="' +
      ink +
      '" font-family="Times New Roman, STIX Two Text, serif" font-style="italic">' +
      xmlEscape(verdict) +
      "</text>\n" +
      '<text x="56" y="136" font-size="14" fill="#5c6778" ' +
      'font-family="Times New Roman, STIX Two Text, serif">Deterministic primality record</text>\n' +
      dl +
      "\n" +
      '<line x1="56" y1="' +
      (y + 4) +
      '" x2="744" y2="' +
      (y + 4) +
      '" stroke="#e4d9c4"/>\n' +
      '<text x="56" y="' +
      (y + 32) +
      '" font-size="14" fill="#245c3d" font-family="Times New Roman, STIX Two Text, serif">' +
      xmlEscape(DOCTRINE) +
      "</text>\n" +
      "</svg>\n"
    );
  }

  function downloadText(filename, text, mime) {
    const blob = new Blob([text], { type: mime });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () {
      URL.revokeObjectURL(a.href);
    }, 1000);
  }

  function orrerySvg() {
    const cx = 60;
    const cy = 60;
    const r = 40;
    const spokes = WHEEL30.map(function (res) {
      const ang = (res / 30) * Math.PI * 2 - Math.PI / 2;
      const x = cx + r * Math.cos(ang);
      const y = cy + r * Math.sin(ang);
      const lx = cx + (r + 14) * Math.cos(ang);
      const ly = cy + (r + 14) * Math.sin(ang);
      return (
        '<g class="spoke" data-res="' +
        res +
        '">' +
        '<line class="spoke-arm" x1="' +
        cx +
        '" y1="' +
        cy +
        '" x2="' +
        x +
        '" y2="' +
        y +
        '"/>' +
        '<circle class="spoke-dot" cx="' +
        x +
        '" cy="' +
        y +
        '" r="3.4"/>' +
        '<text x="' +
        lx +
        '" y="' +
        (ly + 3) +
        '">' +
        res +
        "</text></g>"
      );
    }).join("");
    return (
      '<svg viewBox="0 0 120 120" aria-hidden="true">' +
      '<circle class="orrery-ring" cx="60" cy="60" r="40"/>' +
      spokes +
      '<text class="orrery-hub" x="60" y="64">30</text></svg>'
    );
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
        <p class="lab-hint">Deterministic lab in this tab (not the OpenMP C core):
          <strong>n−1 Pocklington</strong> when <em>n</em>−1 factors, else exact 30-wheel trial.
          <strong>No digit-length limit.</strong> Smooth <em>n</em>−1 multi-limb primes (e.g. CLI default) finish fast;
          hostile <em>n</em>−1 may be inconclusive here without spinning forever. Stop anytime.</p>
        <figure class="lab-orrery" id="lab-orrery" hidden>
          ${orrerySvg()}
          <figcaption>residue <span id="orrery-res">—</span> (mod 30)</figcaption>
        </figure>
        <div class="lab-progress" id="lab-bar"><i></i></div>
        <div class="lab-out" id="lab-out" aria-live="polite"></div>
      </section>`;

    const input = $("#lab-n", root);
    const go = $("#lab-go", root);
    const stop = $("#lab-stop", root);
    const out = $("#lab-out", root);
    const bar = $("#lab-bar", root);
    const barFill = $("i", bar);
    const orrery = $("#lab-orrery", root);
    const orreryRes = $("#orrery-res", root);

    let worker = null;
    let lastCert = null;

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

    function setOrrery(res, on) {
      if (on) orrery.removeAttribute("hidden");
      else orrery.setAttribute("hidden", "");
      orrery.classList.toggle("show", !!on);
      const spokes = orrery.querySelectorAll(".spoke");
      spokes.forEach(function (el) {
        const r = Number(el.getAttribute("data-res"));
        el.classList.toggle("active", on && res != null && r === res);
      });
      orreryRes.textContent = on && res != null ? String(res) : "—";
    }

    function hideOrrery() {
      setOrrery(null, false);
    }

    function renderBusy(state) {
      out.className = "lab-out show busy";
      out.innerHTML = `<p class="verdict">Checking…</p>
        <dl><dt>n</dt><dd>${escapeHtml(state.n)}</dd>
        <dt>⌊√n⌋</dt><dd>${state.isqrt}</dd>
        <dt>candidate</dt><dd>${state.i || "—"}</dd></dl>`;
    }

    function renderCert(state) {
      lastCert = state;
      const verdict = state.prime ? "Prime" : "Composite";
      out.className = "lab-out show cert " + (state.prime ? "yes" : "no");
      out.innerHTML = `<article class="cert-card">
        <p class="cert-kicker">Deterministic primality record</p>
        <p class="verdict">${verdict}</p>
        <dl>
          <dt>n</dt><dd>${escapeHtml(state.n)}</dd>
          <dt>path</dt><dd>${escapeHtml(state.path)}</dd>
          <dt>⌊√n⌋</dt><dd>${fmt(state.isqrt)}</dd>
          ${state.factor != null ? `<dt>factor</dt><dd>${fmt(state.factor)}</dd>` : ""}
          <dt>time</dt><dd>${Number(state.ms).toFixed(2)} ms</dd>
          <dt>note</dt><dd>${escapeHtml(state.note || "")}</dd>
        </dl>
        <p class="cert-doctrine">${escapeHtml(DOCTRINE)}</p>
        <div class="cert-actions">
          <button type="button" id="lab-copy">Copy</button>
          <button type="button" id="lab-svg">Download SVG</button>
        </div>
      </article>`;
      const copyBtn = $("#lab-copy", out);
      const svgBtn = $("#lab-svg", out);
      copyBtn.addEventListener("click", function () {
        const text = certificateText(state);
        const done = function () {
          copyBtn.textContent = "Copied";
          setTimeout(function () {
            copyBtn.textContent = "Copy";
          }, 1400);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done).catch(function () {
            window.prompt("Copy trial record", text);
          });
        } else {
          window.prompt("Copy trial record", text);
        }
      });
      svgBtn.addEventListener("click", function () {
        const name =
          "trial-" +
          state.n.slice(0, 24) +
          "-" +
          (state.prime ? "prime" : "composite") +
          ".svg";
        downloadText(name, certificateSvg(state), "image/svg+xml");
      });
    }

    function renderSimple(cls, title, body) {
      lastCert = null;
      out.className = "lab-out show " + cls;
      out.innerHTML = `<p class="verdict">${title}</p>${body}`;
    }

    function finishIdle() {
      go.disabled = false;
      stop.disabled = true;
      bar.classList.remove("show");
      hideOrrery();
      killWorker();
    }

    function run() {
      const n = parseN(input.value);
      if (n === null) {
        hideOrrery();
        renderSimple("no", "Invalid n", "<p>Enter a non-negative decimal integer.</p>");
        return;
      }
      if (typeof Worker === "undefined") {
        hideOrrery();
        renderSimple(
          "no",
          "No Web Worker",
          "<p>This browser cannot run the background trial. Use the Python / OpenMP library.</p>"
        );
        return;
      }

      const limit = isqrt(n);
      const multiLimb = n >= TWO64;
      // No digit / √n hard ban. Optional confirm only for long pure-trial class (64-bit hard).
      if (!multiLimb && limit > WARN_ISQRT) {
        const ok = window.confirm(
          "⌊√n⌋ ≈ " +
            fmt(limit) +
            ". If n−1 is hostile, exact 30-wheel trial may take minutes in the browser " +
            "(background worker; Stop is available). Multi-limb n tries n−1 first with no size ban. Continue?"
        );
        if (!ok) return;
      }

      killWorker();
      go.disabled = true;
      stop.disabled = false;
      bar.classList.add("show");
      barFill.style.width = "0%";
      if (limit >= ORRERY_ISQRT) setOrrery(null, true);
      else hideOrrery();
      renderBusy({ n: n.toString(), isqrt: fmt(limit), i: "starting" });

      try {
        worker = new Worker(workerUrl());
      } catch (err) {
        finishIdle();
        renderSimple("no", "Worker failed", `<p>${escapeHtml(String(err))}</p>`);
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
            const res = Number(i % 30n);
            setOrrery(res, true);
            renderBusy({ n: n.toString(), isqrt: fmt(lim), i: fmt(i) });
          } catch (_) {
            /* ignore malformed progress */
          }
          return;
        }
        if (msg.type === "aborted") {
          finishIdle();
          renderSimple("busy", "Stopped", "<p>Trial cancelled.</p>");
          return;
        }
        if (msg.type === "error") {
          finishIdle();
          renderSimple("no", "Error", `<p>${escapeHtml(msg.message || "unknown")}</p>`);
          return;
        }
        if (msg.type === "done" && msg.result) {
          const res = msg.result;
          barFill.style.width = "100%";
          hideOrrery();
          if (res.prime === null) {
            const title =
              res.path === "inconclusive" ? "Inconclusive here" : "No decision";
            renderSimple(
              "busy",
              title,
              `<dl><dt>n</dt><dd>${escapeHtml(n.toString())}</dd>
              <dt>path</dt><dd>${escapeHtml(res.path || "")}</dd>
              <dt>⌊√n⌋</dt><dd>${fmt(res.isqrt)}</dd>
              <dt>time</dt><dd>${Number(res.ms).toFixed(2)} ms</dd>
              <dt>note</dt><dd>${escapeHtml(res.note || "")}</dd></dl>
              <p class="lab-hint">There is no maximum digit length. When n−1 cannot be factored enough for a Pocklington proof and pure trial is impractical (~⌊√n⌋ steps), the lab stops rather than spinning forever. The Python library can run longer factoring (ECM/SIQS).</p>`
            );
          } else {
            renderCert({
              prime: res.prime,
              n: n.toString(),
              path: res.path,
              isqrt: BigInt(res.isqrt),
              factor: res.factor == null ? null : BigInt(res.factor),
              ms: res.ms,
              note: res.note,
            });
          }
          go.disabled = false;
          stop.disabled = true;
          bar.classList.remove("show");
          killWorker();
        }
      };

      worker.onerror = function (err) {
        finishIdle();
        renderSimple(
          "no",
          "Error",
          `<p>${escapeHtml(err && err.message ? err.message : String(err))}</p>`
        );
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
        hideOrrery();
        renderSimple("busy", "Stopped", "<p>Trial cancelled.</p>");
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
    document.addEventListener("click", function (e) {
      const btn = e.target && e.target.closest && e.target.closest(".acta-use");
      if (!btn) return;
      const input = document.getElementById("lab-n");
      if (!input) return;
      input.value = btn.getAttribute("data-n") || "";
      input.focus();
      input.select();
    });
  });
})();

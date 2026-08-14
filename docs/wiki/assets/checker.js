/* Deterministic lab UI. Heavy work runs in checker-worker.js
 * (≥256-bit: class-number-1 ECPP first; else combined BLS then ECPP; then trial). */
(function () {
  const WARN_ISQRT = 8_000_000n;
  const TWO64 = 1n << 64n;
  const WHEEL30 = [1, 7, 11, 13, 17, 19, 23, 29];
  const DOCTRINE = "deterministic · combined BLS / ECPP / trial · no stochastic Miller–Rabin";

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
    if (state.factor != null) {
      lines.push("factor = " + state.factor.toString());
      try {
        const nn = BigInt(state.n);
        const ff = BigInt(state.factor);
        if (ff > 0n && nn % ff === 0n) {
          lines.push("cofactor = " + (nn / ff).toString());
        }
      } catch (_) {
        /* ignore */
      }
    } else if (state.prime) {
      lines.push("factor = none (proof path: " + state.path + ")");
    } else if (state.prime === false) {
      lines.push("factor = (not isolated)");
    }
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
    if (state.factor != null) {
      rows.push(["factor", fmt(state.factor)]);
      try {
        const nn = BigInt(state.n);
        const ff = BigInt(state.factor);
        if (ff > 0n && nn % ff === 0n) rows.push(["n/factor", fmt(nn / ff)]);
      } catch (_) {
        /* ignore */
      }
    }
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

  function factorRows(state) {
    if (state.prime) return "";
    if (state.factor == null) {
      return `<dt>factor</dt><dd class="factor-missing">not isolated</dd>`;
    }
    let cof = "";
    try {
      const nn = BigInt(state.n);
      const ff = BigInt(state.factor);
      if (ff > 0n && nn % ff === 0n) {
        cof = `<dt>n / f</dt><dd>${fmt(nn / ff)}</dd>`;
      }
    } catch (_) {
      /* ignore */
    }
    return (
      `<dt>factor</dt><dd class="factor-hit">${fmt(state.factor)}</dd>` + cof
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

  function stageMarkup() {
    return `
      <div class="lab-stage" id="lab-stage" hidden>
        <figure class="lab-viz" data-phase="precheck" hidden>
          <svg viewBox="0 0 200 72" aria-hidden="true">
            <text class="viz-title" x="4" y="14">small-prime filter</text>
            <g id="viz-precheck-dots"></g>
          </svg>
          <figcaption>trying p | n for the precheck table</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="fermat" hidden>
          <svg viewBox="0 0 200 72" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Fermat filter  a<sup>n−1</sup> ≡ 1 (mod n)</text>
            <rect class="viz-track" x="8" y="32" width="184" height="10" rx="2"/>
            <rect class="viz-fill" id="viz-fermat-fill" x="8" y="32" width="0" height="10" rx="2"/>
            <text class="viz-mono" id="viz-fermat-a" x="8" y="60">a = —</text>
          </svg>
          <figcaption>fixed bases only — not Miller–Rabin</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="split" hidden>
          <svg viewBox="0 0 200 72" aria-hidden="true">
            <text class="viz-title" x="4" y="14">splitting an n−1 cofactor</text>
            <rect class="viz-box" x="20" y="28" width="160" height="28" rx="2"/>
            <line class="viz-cut" id="viz-split-cut" x1="100" y1="26" x2="100" y2="58"/>
            <text class="viz-mono" id="viz-split-bits" x="100" y="46" text-anchor="middle">cofactor</text>
          </svg>
          <figcaption>trial / Fermat / then harder splits</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="brent" hidden>
          <svg viewBox="0 0 200 72" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Brent–Pollard cycle</text>
            <ellipse class="viz-orbit" cx="100" cy="44" rx="70" ry="18"/>
            <circle class="viz-hare" id="viz-brent-hare" cx="170" cy="44" r="4"/>
            <circle class="viz-tort" id="viz-brent-tort" cx="30" cy="44" r="4"/>
          </svg>
          <figcaption>two walkers on x ↦ x² + c (mod n)</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="p1" hidden>
          <svg viewBox="0 0 200 72" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Pollard p−1  (smooth B1)</text>
            <rect class="viz-track" x="8" y="34" width="184" height="10" rx="2"/>
            <rect class="viz-fill" id="viz-p1-fill" x="8" y="34" width="184" height="10" rx="2"/>
            <text class="viz-mono" id="viz-p1-b1" x="8" y="60">B1 = —</text>
          </svg>
          <figcaption>a ← a^{p^k} mod n for p^k ≤ B1</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="ecm" hidden>
          <svg viewBox="0 0 200 88" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Montgomery ECM  (Suyama σ)</text>
            <path id="viz-ecm-path" class="viz-curve" d="M12 70 C 50 10, 90 10, 100 40 S 150 78, 188 28"/>
            <circle class="viz-point" id="viz-ecm-pt" cx="12" cy="70" r="4.5"/>
            <text class="viz-mono" id="viz-ecm-sigma" x="8" y="84">σ = —</text>
          </svg>
          <figcaption>point [lcm(1..B1)]P on curve σ — gcd(Z, n) may split</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="pocklington" hidden>
          <svg viewBox="0 0 200 80" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Pocklington  F &gt; √n</text>
            <text class="viz-mono" x="8" y="32">F</text>
            <rect class="viz-track" x="28" y="24" width="164" height="8" rx="2"/>
            <rect class="viz-fill" id="viz-pock-f" x="28" y="24" width="0" height="8" rx="2"/>
            <text class="viz-mono" x="8" y="52">√n</text>
            <rect class="viz-track" x="28" y="44" width="164" height="8" rx="2"/>
            <rect class="viz-fill viz-fill-alt" x="28" y="44" width="164" height="8" rx="2"/>
            <text class="viz-mono" id="viz-pock-q" x="8" y="72">q | F</text>
          </svg>
          <figcaption>need a fully-factored F with F² &gt; n</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="lucas" hidden>
          <svg viewBox="0 0 200 72" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Lucas n+1  U<sub>n+1</sub> ≡ 0</text>
            <rect class="viz-track" x="8" y="32" width="184" height="10" rx="2"/>
            <rect class="viz-fill viz-fill-alt" id="viz-lucas-fill" x="8" y="32" width="0" height="10" rx="2"/>
            <text class="viz-mono" id="viz-lucas-q" x="8" y="60">q | G</text>
          </svg>
          <figcaption>Selfridge discriminant · Condition (II) on primes of G</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="combined" hidden>
          <svg viewBox="0 0 200 80" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Combined Theorem 1</text>
            <text class="viz-mono" x="8" y="32">F</text>
            <rect class="viz-track" x="28" y="24" width="164" height="8" rx="2"/>
            <rect class="viz-fill" id="viz-comb-f" x="28" y="24" width="0" height="8" rx="2"/>
            <text class="viz-mono" x="8" y="52">G</text>
            <rect class="viz-track" x="28" y="44" width="164" height="8" rx="2"/>
            <rect class="viz-fill viz-fill-alt" id="viz-comb-g" x="28" y="44" width="0" height="8" rx="2"/>
            <text class="viz-mono" id="viz-comb-note" x="8" y="72">n &lt; max(F²G/2, FG²/2)</text>
          </svg>
          <figcaption>gcd(F,G)=2 · not FG &gt; √n</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="ecpp" hidden>
          <svg viewBox="0 0 200 80" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Atkin–Morain ECPP</text>
            <ellipse class="viz-orbit" cx="100" cy="48" rx="72" ry="20"/>
            <circle class="viz-point" id="viz-ecpp-pt" cx="28" cy="48" r="4.5"/>
            <text class="viz-mono" id="viz-ecpp-d" x="8" y="76">D = —</text>
          </svg>
          <figcaption>class-number-1 discriminants in fixed order (no RNG)</figcaption>
        </figure>
        <figure class="lab-viz lab-orrery" data-phase="wheel" hidden>
          ${orrerySvg()}
          <figcaption>30-wheel trial · residue <span id="orrery-res">—</span> (mod 30)</figcaption>
        </figure>
        <p class="lab-stage-label" id="lab-stage-label"></p>
      </div>`;
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
          <strong>ECPP first</strong> when <em>n</em> has 256 or more bits
          (class-number-1; Montgomery ECM), else <strong>combined BLS</strong>
          (n−1 Pocklington, Lucas n+1, Combined Theorem 1), then ECPP, then exact 30-wheel trial.
          Factoring uses trial / Brent / p−1 / <strong>ECM</strong>.
          <strong>No digit-length limit.</strong> Smooth <em>n</em>±1 is typically sub-second;
          the 131-digit CM-friendly prime 10^130+1113 proves in this tab via class-number-1
          ECPP (often tens of seconds). Hostile mid-size
          <em>n</em>−1 can take a minute or two of ECM. Stop anytime.
          Composites print a factor when one is found.</p>
        ${stageMarkup()}
        <div class="lab-progress" id="lab-bar"><i></i></div>
        <div class="lab-out" id="lab-out" aria-live="polite"></div>
      </section>`;

    const input = $("#lab-n", root);
    const go = $("#lab-go", root);
    const stop = $("#lab-stop", root);
    const out = $("#lab-out", root);
    const bar = $("#lab-bar", root);
    const barFill = $("i", bar);
    const stage = $("#lab-stage", root);
    const stageLabel = $("#lab-stage-label", root);
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

    function hideStage() {
      if (!stage) return;
      stage.setAttribute("hidden", "");
      stage.querySelectorAll(".lab-viz").forEach(function (el) {
        el.setAttribute("hidden", "");
      });
    }

    function showPhase(phase) {
      if (!stage) return;
      stage.removeAttribute("hidden");
      stage.querySelectorAll(".lab-viz").forEach(function (el) {
        const on = el.getAttribute("data-phase") === phase;
        if (on) el.removeAttribute("hidden");
        else el.setAttribute("hidden", "");
      });
    }

    function setOrrery(res) {
      if (!orreryRes) return;
      const spokes = stage ? stage.querySelectorAll(".spoke") : [];
      spokes.forEach(function (el) {
        const r = Number(el.getAttribute("data-res"));
        el.classList.toggle("active", res != null && r === res);
      });
      orreryRes.textContent = res != null ? String(res) : "—";
    }

    function applyPhase(msg) {
      const phase = msg.phase || "wheel";
      const extra = msg.extra || {};
      showPhase(phase);
      if (stageLabel) {
        stageLabel.textContent = extra.label || phaseLabel(phase, extra);
      }
      if (phase === "wheel") {
        const res =
          extra.residue != null
            ? Number(extra.residue)
            : Number(BigInt(msg.i || "0") % 30n);
        setOrrery(res);
      } else if (phase === "ecm") {
        const tot = Number(msg.limit) || 1;
        const i = Number(msg.i) || 0;
        const t = Math.min(1, Math.max(0, i / tot));
        const pt = $("#viz-ecm-pt", root);
        const curve = $("#viz-ecm-path", root);
        if (pt && curve && typeof curve.getTotalLength === "function") {
          const len = curve.getTotalLength();
          const p = curve.getPointAtLength(t * len);
          pt.setAttribute("cx", String(p.x));
          pt.setAttribute("cy", String(p.y));
        } else if (pt) {
          // jsdom / no SVG geometry: stay on the start point
          pt.setAttribute("cx", "12");
          pt.setAttribute("cy", "70");
        }
        const sg = $("#viz-ecm-sigma", root);
        if (sg) {
          sg.textContent =
            "σ = " + (extra.sigma || "—") + (extra.B1 ? "   B1 = " + extra.B1 : "");
        }
      } else if (phase === "brent") {
        const tot = Number(msg.limit) || 1;
        const i = Number(msg.i) || 0;
        const th = (i / Math.max(1, tot)) * Math.PI * 4;
        const hare = $("#viz-brent-hare", root);
        const tort = $("#viz-brent-tort", root);
        if (hare) {
          hare.setAttribute("cx", String(100 + 70 * Math.cos(th)));
          hare.setAttribute("cy", String(44 + 18 * Math.sin(th)));
        }
        if (tort) {
          tort.setAttribute("cx", String(100 + 70 * Math.cos(th * 0.5)));
          tort.setAttribute("cy", String(44 + 18 * Math.sin(th * 0.5)));
        }
      } else if (phase === "fermat") {
        const tot = Number(msg.limit) || 6;
        const i = Number(msg.i) || 0;
        const fill = $("#viz-fermat-fill", root);
        if (fill) fill.setAttribute("width", String((184 * i) / tot));
        const a = $("#viz-fermat-a", root);
        if (a) a.textContent = "a = " + (extra.base || "—");
      } else if (phase === "p1") {
        const b1 = $("#viz-p1-b1", root);
        if (b1) b1.textContent = "B1 = " + (extra.B1 || "—");
      } else if (phase === "pocklington") {
        let frac = 0;
        try {
          const F = extra.F ? BigInt(extra.F) : BigInt(msg.i || "0");
          const T = extra.target ? BigInt(extra.target) : BigInt(msg.limit || "1");
          if (T > 0n) frac = Number((F * 164n) / T);
        } catch (_) {
          frac = 0;
        }
        const fbar = $("#viz-pock-f", root);
        if (fbar) fbar.setAttribute("width", String(Math.min(164, Math.max(2, frac))));
        const qel = $("#viz-pock-q", root);
        if (qel) qel.textContent = extra.q ? "q | F = " + extra.q : "building F";
      } else if (phase === "lucas") {
        const tot = Number(msg.limit) || 1;
        const i = Number(msg.i) || 0;
        const fill = $("#viz-lucas-fill", root);
        if (fill) fill.setAttribute("width", String((184 * i) / tot));
        const qel = $("#viz-lucas-q", root);
        if (qel) {
          qel.textContent =
            (extra.q ? "q | G = " + extra.q : "U_{n+1}") +
            (extra.D ? "   D = " + extra.D : "");
        }
      } else if (phase === "combined") {
        const fbar = $("#viz-comb-f", root);
        const gbar = $("#viz-comb-g", root);
        try {
          const F = extra.F ? BigInt(extra.F) : 0n;
          const G = extra.G ? BigInt(extra.G) : 0n;
          const T = extra.target ? BigInt(extra.target) : BigInt(msg.limit || "1");
          if (fbar && T > 0n) fbar.setAttribute("width", String(Math.min(164, Number((F * 164n) / (T + 1n)))));
          if (gbar && T > 0n) gbar.setAttribute("width", String(Math.min(164, Number((G * 164n) / (T + 1n)))));
        } catch (_) {
          /* ignore */
        }
      } else if (phase === "ecpp") {
        const tot = Number(msg.limit) || 13;
        const i = Number(msg.i) || 0;
        const th = (i / Math.max(1, tot)) * Math.PI * 2;
        const pt = $("#viz-ecpp-pt", root);
        if (pt) {
          pt.setAttribute("cx", String(100 + 72 * Math.cos(th)));
          pt.setAttribute("cy", String(48 + 20 * Math.sin(th)));
        }
        const dEl = $("#viz-ecpp-d", root);
        if (dEl) dEl.textContent = extra.D ? "D = " + extra.D : "searching discriminants";
      } else if (phase === "split") {
        const bits = $("#viz-split-bits", root);
        if (bits) bits.textContent = extra.bits ? extra.bits + "-bit cofactor" : extra.label || "cofactor";
        const cut = $("#viz-split-cut", root);
        if (cut) {
          const tot = Number(msg.limit) || 1;
          const i = Number(msg.i) || 0;
          const x = 40 + ((i * 120) / Math.max(1, tot)) % 120;
          cut.setAttribute("x1", String(x));
          cut.setAttribute("x2", String(x));
        }
      } else if (phase === "precheck") {
        const host = $("#viz-precheck-dots", root);
        if (host && !host.childElementCount) {
          const primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53];
          host.innerHTML = primes
            .map(function (p, idx) {
              const x = 10 + idx * 12;
              return (
                '<circle class="viz-pd" data-p="' +
                p +
                '" cx="' +
                x +
                '" cy="40" r="4"/>'
              );
            })
            .join("");
        }
        if (host) {
          const cur = extra.p ? Number(extra.p) : 0;
          host.querySelectorAll(".viz-pd").forEach(function (el) {
            el.classList.toggle("active", Number(el.getAttribute("data-p")) === cur);
          });
        }
      }
    }

    function phaseLabel(phase, extra) {
      if (phase === "ecm") return "ECM curve " + (extra.sigma ? "σ=" + extra.sigma : "");
      if (phase === "brent") return "Brent–Pollard on a cofactor";
      if (phase === "fermat") return "Fermat a^{n−1} mod n";
      if (phase === "p1") return "Pollard p−1 stage 1";
      if (phase === "pocklington") return "Pocklington check on primes of F";
      if (phase === "lucas") return "Lucas n+1 on primes of G";
      if (phase === "combined") return "Combined Theorem 1 (not FG>√n)";
      if (phase === "ecpp") return extra.D ? "ECPP discriminant D=" + extra.D : "class-number-1 ECPP";
      if (phase === "split") return extra.label || "factoring a cofactor of n±1";
      if (phase === "precheck") return "small-prime / parity filter";
      if (phase === "wheel") return "30-wheel trial division";
      return phase;
    }

    function renderBusy(state) {
      out.className = "lab-out show busy";
      out.innerHTML = `<p class="verdict">Checking…</p>
        <dl><dt>n</dt><dd>${escapeHtml(state.n)}</dd>
        <dt>⌊√n⌋</dt><dd>${state.isqrt}</dd>
        <dt>stage</dt><dd>${escapeHtml(state.stage || "—")}</dd>
        <dt>step</dt><dd>${escapeHtml(state.i || "—")}</dd></dl>`;
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
          ${factorRows(state)}
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
      hideStage();
      killWorker();
    }

    function run() {
      const n = parseN(input.value);
      if (n === null) {
        hideStage();
        renderSimple("no", "Invalid n", "<p>Enter a non-negative decimal integer.</p>");
        return;
      }
      if (typeof Worker === "undefined") {
        hideStage();
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
      showPhase("precheck");
      renderBusy({ n: n.toString(), isqrt: fmt(limit), i: "starting", stage: "precheck" });

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
            const i = BigInt(msg.i || "0");
            const lim = BigInt(msg.limit || "1");
            const pct = lim === 0n ? 100 : Number((i * 1000n) / lim) / 10;
            barFill.style.width = Math.min(100, Math.max(0, pct)) + "%";
            applyPhase(msg);
            renderBusy({
              n: n.toString(),
              isqrt: fmt(isqrt(n)),
              stage: phaseLabel(msg.phase || "wheel", msg.extra || {}),
              i: fmt(i) + " / " + fmt(lim),
            });
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
          hideStage();
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
              <p class="lab-hint">There is no maximum digit length. The tab runs ECPP first on ≥256-bit <em>n</em> (Jacobian point mul, stacked Montgomery ECM peel; no multi-minute BLS peel), else combined BLS then class-number-1 ECPP, plus trial / Brent / p−1 / Montgomery ECM. CM-friendly huge primes such as 10^130+1113 are in scope. If that still cannot settle <em>n</em> and pure trial is impractical (~⌊√n⌋ steps), the lab stops rather than spinning forever. The Python library continues with small-h ECPP, SIQS, and AKS.</p>`
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
        hideStage();
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

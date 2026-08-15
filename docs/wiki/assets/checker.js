/* Deterministic lab UI. Heavy work runs in checker-worker.js
 * (≥256-bit: class-number-1 then in-tab FastECPP H_D; else combined BLS; then trial). */
(function () {
  const WARN_ISQRT = 8_000_000n;
  const TWO64 = 1n << 64n;
  const WHEEL30 = [1, 7, 11, 13, 17, 19, 23, 29];
  const DOCTRINE = "deterministic · BLS (<256 bits) / class-number-1 then FastECPP H_D (256+) · no stochastic Miller–Rabin";

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
      "digits = " + String(state.n).length,
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
      ["digits", String(state.n).length],
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
      const lx = cx + (r + 16) * Math.cos(ang);
      const ly = cy + (r + 16) * Math.sin(ang);
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
        '" r="3.6"/>' +
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
      '<circle class="orrery-ring orrery-ring-outer" cx="60" cy="60" r="52"/>' +
      '<circle class="orrery-ring" cx="60" cy="60" r="40"/>' +
      '<circle class="orrery-ring orrery-ring-inner" cx="60" cy="60" r="18"/>' +
      spokes +
      '<g id="viz-wheel-needle" class="orrery-needle" transform="rotate(-90 60 60)">' +
      '<line x1="60" y1="60" x2="60" y2="22"/>' +
      '<circle cx="60" cy="22" r="2.6"/>' +
      "</g>" +
      '<circle class="orrery-hub-seal" cx="60" cy="60" r="11"/>' +
      '<text class="orrery-hub" x="60" y="64">30</text></svg>'
    );
  }

  function ecppConstellation() {
    const ds = [-3, -4, -7, -8, -11, -12, -16, -19, -27, -28, -43, -67, -163];
    return ds
      .map(function (d, i) {
        const th = (i / ds.length) * Math.PI * 2 - Math.PI / 2;
        const x = (100 + 74 * Math.cos(th)).toFixed(1);
        const y = (50 + 22 * Math.sin(th)).toFixed(1);
        return (
          '<g class="viz-star" data-d="' +
          d +
          '"><circle cx="' +
          x +
          '" cy="' +
          y +
          '" r="2.3"/><text x="' +
          x +
          '" y="' +
          (Number(y) - 6).toFixed(1) +
          '">' +
          d +
          "</text></g>"
        );
      })
      .join("");
  }

  function fermatLanterns() {
    const bases = [2, 3, 5, 7, 11, 13];
    return bases
      .map(function (a, i) {
        const x = 18 + i * 30;
        return (
          '<g class="viz-lantern" data-a="' +
          a +
          '" transform="translate(' +
          x +
          ',36)">' +
          '<rect class="viz-lantern-post" x="-1" y="8" width="2" height="10"/>' +
          '<path class="viz-lantern-glass" d="M-6 8 L-6 0 Q-6 -8 0 -8 Q6 -8 6 0 L6 8 Z"/>' +
          '<circle class="viz-lantern-glow" cx="0" cy="0" r="5"/>' +
          '<text x="0" y="24">' +
          a +
          "</text></g>"
        );
      })
      .join("");
  }

  function stageMarkup() {
    return `
      <div class="lab-stage" id="lab-stage" hidden>
        <p class="lab-theatre-kicker">engine theatre · deterministic cast · no understudies named Miller or Rabin</p>
        <p class="lab-theatre-act" id="lab-theatre-act"></p>
        <figure class="lab-viz" data-phase="precheck" hidden>
          <svg viewBox="0 0 200 88" aria-hidden="true">
            <text class="viz-title" x="4" y="14">the doormen</text>
            <line class="viz-floor" x1="8" y1="62" x2="192" y2="62"/>
            <g id="viz-precheck-dots"></g>
            <g id="viz-precheck-glass" class="viz-glass">
              <circle cx="0" cy="0" r="7"/>
              <line x1="5" y1="5" x2="10" y2="11"/>
            </g>
          </svg>
          <figcaption>small primes knock first · p | n?</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="fermat" hidden>
          <svg viewBox="0 0 200 92" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Fermat lanterns  a<sup>n−1</sup> ≡ 1</text>
            ${fermatLanterns()}
            <rect class="viz-track" x="8" y="72" width="184" height="6" rx="2"/>
            <rect class="viz-fill" id="viz-fermat-fill" x="8" y="72" width="0" height="6" rx="2"/>
            <text class="viz-mono" id="viz-fermat-a" x="8" y="88">a = —</text>
          </svg>
          <figcaption>six fixed witnesses. no dice. not Miller–Rabin.</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="split" hidden>
          <svg viewBox="0 0 200 88" aria-hidden="true">
            <text class="viz-title" x="4" y="14">sawing a leftover</text>
            <rect class="viz-log" x="24" y="36" width="152" height="22" rx="6"/>
            <text class="viz-mono" id="viz-split-bits" x="100" y="51" text-anchor="middle">cofactor</text>
            <g id="viz-split-saw" class="viz-saw">
              <polygon points="0,28 8,40 0,52 -8,40"/>
              <line class="viz-cut" id="viz-split-cut" x1="0" y1="30" x2="0" y2="64"/>
            </g>
          </svg>
          <figcaption>trial / Fermat / then the heavier tools</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="brent" hidden>
          <svg viewBox="0 0 200 92" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Brent–Pollard racetrack</text>
            <ellipse class="viz-orbit viz-orbit-dash" cx="100" cy="52" rx="72" ry="20"/>
            <g id="viz-brent-hare" class="viz-hare" transform="translate(172,52)">
              <ellipse cx="0" cy="2" rx="6" ry="3.4"/>
              <ellipse class="viz-ear" cx="-3" cy="-5" rx="1.4" ry="4"/>
              <ellipse class="viz-ear" cx="1" cy="-5" rx="1.4" ry="4"/>
              <circle cx="4" cy="1" r="1.1"/>
            </g>
            <g id="viz-brent-tort" class="viz-tort" transform="translate(28,52)">
              <ellipse cx="0" cy="2" rx="6.5" ry="3.6"/>
              <path class="viz-shell" d="M-4 1 Q0 -6 4 1 Z"/>
              <circle cx="5" cy="2" r="1.1"/>
            </g>
          </svg>
          <figcaption>hare laps tortoise on x ↦ x²+c · meeting ⇒ gcd</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="p1" hidden>
          <svg viewBox="0 0 200 88" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Pollard p−1  thermometer</text>
            <rect class="viz-thermo-body" x="88" y="20" width="18" height="50" rx="9"/>
            <circle class="viz-thermo-bulb" cx="97" cy="72" r="12"/>
            <rect class="viz-fill" id="viz-p1-fill" x="92" y="24" width="10" height="48" rx="5"/>
            <text class="viz-mono" id="viz-p1-b1" x="8" y="84">B1 = —</text>
          </svg>
          <figcaption>if p−1 is B1-smooth, n confesses a factor</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="ecm" hidden>
          <svg viewBox="0 0 200 96" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Montgomery ECM  (Suyama σ)</text>
            <path id="viz-ecm-path" class="viz-curve viz-curve-trail" d="M12 70 C 50 10, 90 10, 100 40 S 150 78, 188 28"/>
            <g id="viz-ecm-scout">
              <circle class="viz-point" id="viz-ecm-pt" cx="12" cy="70" r="4.5"/>
              <text class="viz-pennant" id="viz-ecm-flag" x="18" y="66">σ</text>
            </g>
            <text class="viz-mono" id="viz-ecm-sigma" x="8" y="90">σ = —</text>
          </svg>
          <figcaption>a scout on E(σ). gcd(Z, n) may split the integer.</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="pocklington" hidden>
          <svg viewBox="0 0 200 92" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Pocklington  ivy over the √n fence</text>
            <line class="viz-fence" x1="28" y1="58" x2="192" y2="58"/>
            <text class="viz-mono" x="8" y="36">F</text>
            <rect class="viz-track" x="28" y="28" width="164" height="8" rx="2"/>
            <rect class="viz-fill" id="viz-pock-f" x="28" y="28" width="0" height="8" rx="2"/>
            <text class="viz-mono" x="8" y="56">√n</text>
            <rect class="viz-track" x="28" y="48" width="164" height="8" rx="2"/>
            <rect class="viz-fill viz-fill-alt" x="28" y="48" width="164" height="8" rx="2"/>
            <text class="viz-mono" id="viz-pock-q" x="8" y="80">q | F</text>
          </svg>
          <figcaption>grow a fully-factored F until F² &gt; n</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="lucas" hidden>
          <svg viewBox="0 0 200 88" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Lucas n+1  the bouncing U</text>
            <path class="viz-wave" d="M8 50 Q 32 22 56 50 T 104 50 T 152 50 T 192 50"/>
            <circle class="viz-point viz-bob" id="viz-lucas-bob" cx="8" cy="50" r="4"/>
            <rect class="viz-track" x="8" y="68" width="184" height="6" rx="2"/>
            <rect class="viz-fill viz-fill-alt" id="viz-lucas-fill" x="8" y="68" width="0" height="6" rx="2"/>
            <text class="viz-mono" id="viz-lucas-q" x="8" y="84">q | G</text>
          </svg>
          <figcaption>Selfridge D · U<sub>n+1</sub> must vanish · Condition (II)</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="combined" hidden>
          <svg viewBox="0 0 200 96" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Combined Theorem 1</text>
            <g id="viz-comb-beam" class="viz-beam">
              <line x1="40" y1="40" x2="160" y2="40"/>
              <rect class="viz-pan" x="28" y="40" width="28" height="14" rx="2"/>
              <rect class="viz-pan viz-pan-g" x="144" y="40" width="28" height="14" rx="2"/>
              <text class="viz-mono" x="42" y="51">F</text>
              <text class="viz-mono" x="154" y="51">G</text>
            </g>
            <polygon class="viz-fulcrum" points="100,40 92,62 108,62"/>
            <rect class="viz-track" x="28" y="70" width="70" height="6" rx="2"/>
            <rect class="viz-fill" id="viz-comb-f" x="28" y="70" width="0" height="6" rx="2"/>
            <rect class="viz-track" x="102" y="70" width="70" height="6" rx="2"/>
            <rect class="viz-fill viz-fill-alt" id="viz-comb-g" x="102" y="70" width="0" height="6" rx="2"/>
            <text class="viz-mono" id="viz-comb-note" x="8" y="90">n &lt; max(F²G/2, FG²/2)</text>
          </svg>
          <figcaption>gcd(F,G)=2 · the cubic roof, not FG &gt; √n</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="ecpp" hidden>
          <svg viewBox="0 0 200 110" aria-hidden="true">
            <text class="viz-title" x="4" y="14">Atkin–Morain sky</text>
            <ellipse class="viz-orbit viz-orbit-dash" cx="100" cy="50" rx="74" ry="22"/>
            ${ecppConstellation()}
            <g id="viz-ecpp-comet">
              <circle class="viz-point" id="viz-ecpp-pt" cx="26" cy="50" r="4.5"/>
              <path class="viz-tail" d="M26 50 l-10 3"/>
            </g>
            <text class="viz-mono" id="viz-ecpp-d" x="8" y="102">D = —</text>
          </svg>
          <figcaption>shopping for a CM curve · class-number-1, then H_D · no RNG</figcaption>
        </figure>
        <figure class="lab-viz" data-phase="neighbor" hidden>
          <svg viewBox="0 0 200 88" aria-hidden="true">
            <text class="viz-title" x="4" y="14">hopping candidates</text>
            <line class="viz-floor" x1="10" y1="52" x2="190" y2="52"/>
            <g id="viz-neighbor-ticks"></g>
            <g id="viz-neighbor-hopper" class="viz-hopper" transform="translate(20,52)">
              <circle cx="0" cy="-8" r="5"/>
              <line x1="0" y1="-3" x2="-4" y2="6"/>
              <line x1="0" y1="-3" x2="4" y2="6"/>
            </g>
            <text class="viz-mono" id="viz-neighbor-n" x="8" y="80">candidate —</text>
          </svg>
          <figcaption>odd leftovers only · then the same engines as Check</figcaption>
        </figure>
        <figure class="lab-viz lab-orrery" data-phase="wheel" hidden>
          ${orrerySvg()}
          <figcaption>30-wheel orrery · residue <span id="orrery-res">—</span> (mod 30) gets the trial</figcaption>
        </figure>
        <p class="lab-stage-label" id="lab-stage-label"></p>
      </div>`;
  }

  function digitCountOf(raw) {
    const n = parseN(raw);
    if (n === null) return null;
    return n.toString().length;
  }

  function formatDigitCount(raw) {
    const s = String(raw == null ? "" : raw).trim();
    if (!s) return "—";
    const d = digitCountOf(s);
    if (d == null) return "not a natural number";
    return d === 1 ? "1 digit" : d + " digits";
  }

  function mount(root) {
    root.innerHTML = `
      <section class="prime-lab" aria-label="Interactive primality lab">
        <div class="lab-nhead">
          <label class="lab-label" for="lab-n">n</label>
          <p class="lab-digits" id="lab-digits" aria-live="polite">—</p>
        </div>
        <div class="row">
          <input id="lab-n" type="text" inputmode="numeric" autocomplete="off"
            placeholder="Enter a natural number" aria-label="n"/>
          <button type="button" class="primary" id="lab-go">Check</button>
          <button type="button" id="lab-stop" disabled>Stop</button>
        </div>
        <p class="lab-hint">Deterministic lab in this tab (not the OpenMP C core).
          One engine per band, matching the Python library:
          <strong>class-number-1 ECPP, then in-tab FastECPP H_D</strong> when <em>n</em> has 256 or more bits
          (Montgomery ECM; no BLS fallback), else <strong>combined BLS only</strong>
          (n−1 Pocklington, Lucas n+1, Combined Theorem 1). Then exact 30-wheel trial if practical.
          Factoring uses trial / Brent / p−1 / <strong>ECM</strong>.
          <strong>No digit-length limit.</strong> Smooth <em>n</em>±1 is typically sub-second;
          the 131-digit CM-friendly prime 10^130+1113 proves in this tab via class-number-1
          ECPP. General 132–150 digit primes use in-tab computed H_D FastECPP (tens of seconds).
          Stop anytime. Composites print a factor when one is found.
          Wider misses are <strong>inconclusive</strong> here (Python may still prove them).</p>
        ${stageMarkup()}
        <div class="lab-progress" id="lab-bar"><i></i></div>
        <div class="lab-out" id="lab-out" aria-live="polite"></div>
      </section>
      <section class="prime-lab lab-neighbors" aria-label="Next and previous prime">
        <h3 class="lab-subhead">Next / previous prime</h3>
        <p class="lab-hint">Uses the same <em>n</em> above. Finds the
          <em>k</em>-th prime strictly greater or strictly less than <em>n</em>
          (default <em>k</em> = 1), with the same deterministic engines. Composites
          are skipped by a small-prime filter, then Check. No candidate-count
          or time cap — Stop whenever you want.</p>
        <div class="row">
          <label class="lab-kwrap" for="lab-k">k
            <input id="lab-k" type="text" inputmode="numeric" value="1"
              aria-label="k-th neighbor"/>
          </label>
          <button type="button" id="lab-prev">Previous prime</button>
          <button type="button" id="lab-next">Next prime</button>
        </div>
        <div class="lab-out" id="lab-nb-out" aria-live="polite"></div>
      </section>`;

    const input = $("#lab-n", root);
    const digits = $("#lab-digits", root);
    const go = $("#lab-go", root);
    const stop = $("#lab-stop", root);
    const nextBtn = $("#lab-next", root);
    const prevBtn = $("#lab-prev", root);
    const kInput = $("#lab-k", root);
    const out = $("#lab-out", root);
    const nbOut = $("#lab-nb-out", root);
    const bar = $("#lab-bar", root);
    const barFill = $("i", bar);
    const stage = $("#lab-stage", root);
    const stageLabel = $("#lab-stage-label", root);
    const theatreAct = $("#lab-theatre-act", root);
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
      const needle = $("#viz-wheel-needle", root);
      if (needle && res != null) {
        const ang = (res / 30) * 360 - 90;
        needle.setAttribute("transform", "rotate(" + ang + " 60 60)");
      }
    }

    function setTheatreAct(phase, extra) {
      if (!theatreAct) return;
      const lines = {
        precheck: "Act I · The doormen ask for ID.",
        fermat: "Act II · Six lanterns. No dice.",
        split: "An interlude with a saw.",
        brent: "The hare is twice as fast. When they meet, gcd.",
        p1: "A smoothness thermometer. If p−1 is tame, n cracks.",
        ecm: "Suyama sends a scout. The curve may confess.",
        pocklington: "Ivy over the √n fence: grow F until F² > n.",
        lucas: "The bouncing U must land on zero at n+1.",
        combined: "A balance, not FG > √n. The cubic roof decides.",
        ecpp: "Shopping the CM sky. No RNG in the catalogue.",
        wheel: "Only residues coprime to 30 may approach the hub.",
        neighbor: "Hopping odd stones across the number line.",
      };
      theatreAct.textContent = extra.act || lines[phase] || phaseLabel(phase, extra);
    }

    function applyPhase(msg) {
      const phase = msg.phase || "wheel";
      const extra = msg.extra || {};
      showPhase(phase);
      setTheatreAct(phase, extra);
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
        const flag = $("#viz-ecm-flag", root);
        if (pt && curve && typeof curve.getTotalLength === "function") {
          const len = curve.getTotalLength();
          const p = curve.getPointAtLength(t * len);
          pt.setAttribute("cx", String(p.x));
          pt.setAttribute("cy", String(p.y));
          if (flag) {
            flag.setAttribute("x", String(p.x + 6));
            flag.setAttribute("y", String(p.y - 6));
          }
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
          hare.setAttribute(
            "transform",
            "translate(" + (100 + 72 * Math.cos(th)) + "," + (52 + 20 * Math.sin(th)) + ")"
          );
        }
        if (tort) {
          tort.setAttribute(
            "transform",
            "translate(" +
              (100 + 72 * Math.cos(th * 0.5)) +
              "," +
              (52 + 20 * Math.sin(th * 0.5)) +
              ")"
          );
        }
      } else if (phase === "fermat") {
        const tot = Number(msg.limit) || 6;
        const i = Number(msg.i) || 0;
        const fill = $("#viz-fermat-fill", root);
        if (fill) fill.setAttribute("width", String((184 * i) / tot));
        const a = $("#viz-fermat-a", root);
        if (a) a.textContent = "a = " + (extra.base || "—");
        const cur = extra.base != null ? String(extra.base) : "";
        root.querySelectorAll(".viz-lantern").forEach(function (el) {
          const on = el.getAttribute("data-a") === cur;
          const lit = Number(el.getAttribute("data-a")) <= Number(cur || 0);
          el.classList.toggle("on", on);
          el.classList.toggle("lit", lit);
        });
      } else if (phase === "p1") {
        const b1 = $("#viz-p1-b1", root);
        if (b1) b1.textContent = "B1 = " + (extra.B1 || "—");
        const fill = $("#viz-p1-fill", root);
        if (fill) {
          const tot = Number(msg.limit) || 1;
          const i = Number(msg.i) || 0;
          const h = 8 + (40 * i) / Math.max(1, tot);
          fill.setAttribute("y", String(72 - h));
          fill.setAttribute("height", String(h));
        }
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
        const bob = $("#viz-lucas-bob", root);
        if (bob) {
          const x = 8 + (184 * i) / Math.max(1, tot);
          const y = 50 + 16 * Math.sin((i / Math.max(1, tot)) * 6);
          bob.setAttribute("cx", String(x));
          bob.setAttribute("cy", String(y));
        }
        const qel = $("#viz-lucas-q", root);
        if (qel) {
          qel.textContent =
            (extra.q ? "q | G = " + extra.q : "U_{n+1}") +
            (extra.D ? "   D = " + extra.D : "");
        }
      } else if (phase === "combined") {
        const fbar = $("#viz-comb-f", root);
        const gbar = $("#viz-comb-g", root);
        let tilt = 0;
        try {
          const F = extra.F ? BigInt(extra.F) : 0n;
          const G = extra.G ? BigInt(extra.G) : 0n;
          const T = extra.target ? BigInt(extra.target) : BigInt(msg.limit || "1");
          if (fbar && T > 0n) fbar.setAttribute("width", String(Math.min(70, Number((F * 70n) / (T + 1n)))));
          if (gbar && T > 0n) gbar.setAttribute("width", String(Math.min(70, Number((G * 70n) / (T + 1n)))));
          if (F + G > 0n) {
            const left = Number((F * 100n) / (F + G));
            tilt = ((left - 50) / 50) * 8;
          }
        } catch (_) {
          /* ignore */
        }
        const beam = $("#viz-comb-beam", root);
        if (beam) beam.setAttribute("transform", "rotate(" + tilt + " 100 40)");
      } else if (phase === "ecpp") {
        const tot = Number(msg.limit) || 13;
        const i = Number(msg.i) || 0;
        const th = (i / Math.max(1, tot)) * Math.PI * 2 - Math.PI / 2;
        const px = 100 + 74 * Math.cos(th);
        const py = 50 + 22 * Math.sin(th);
        const pt = $("#viz-ecpp-pt", root);
        if (pt) {
          pt.setAttribute("cx", String(px));
          pt.setAttribute("cy", String(py));
        }
        const tail = root.querySelector("#viz-ecpp-comet .viz-tail");
        if (tail) {
          tail.setAttribute(
            "d",
            "M" + px + " " + py + " l" + (-10 * Math.cos(th)) + " " + (-6 * Math.sin(th))
          );
        }
        const dEl = $("#viz-ecpp-d", root);
        if (dEl) dEl.textContent = extra.D ? "D = " + extra.D : "searching discriminants";
        const want = extra.D ? String(extra.D).replace("−", "-") : "";
        root.querySelectorAll(".viz-star").forEach(function (el) {
          el.classList.toggle("on", el.getAttribute("data-d") === want);
        });
      } else if (phase === "split") {
        const bits = $("#viz-split-bits", root);
        if (bits) bits.textContent = extra.bits ? extra.bits + "-bit leftover" : extra.label || "cofactor";
        const tot = Number(msg.limit) || 1;
        const i = Number(msg.i) || 0;
        const x = 40 + ((i * 120) / Math.max(1, tot)) % 120;
        const saw = $("#viz-split-saw", root);
        if (saw) saw.setAttribute("transform", "translate(" + x + ",0)");
        const cut = $("#viz-split-cut", root);
        if (cut) {
          cut.setAttribute("x1", "0");
          cut.setAttribute("x2", "0");
        }
      } else if (phase === "precheck") {
        const host = $("#viz-precheck-dots", root);
        if (host && !host.childElementCount) {
          const primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53];
          host.innerHTML = primes
            .map(function (p, idx) {
              const x = 14 + idx * 11.5;
              return (
                '<g class="viz-doorman" data-p="' +
                p +
                '"><circle class="viz-pd" data-p="' +
                p +
                '" cx="' +
                x +
                '" cy="52" r="5"/><text x="' +
                x +
                '" y="76">' +
                p +
                "</text></g>"
              );
            })
            .join("");
        }
        if (host) {
          const cur = extra.p ? Number(extra.p) : 0;
          let glassX = 14;
          host.querySelectorAll(".viz-doorman").forEach(function (el) {
            const on = Number(el.getAttribute("data-p")) === cur;
            el.classList.toggle("active", on);
            const dot = el.querySelector(".viz-pd");
            if (dot) dot.classList.toggle("active", on);
            if (on) glassX = Number(el.querySelector("circle").getAttribute("cx"));
          });
          const glass = $("#viz-precheck-glass", root);
          if (glass) glass.setAttribute("transform", "translate(" + glassX + ",40)");
        }
      } else if (phase === "neighbor") {
        const ticks = $("#viz-neighbor-ticks", root);
        if (ticks && !ticks.childElementCount) {
          let marks = "";
          for (let k = 0; k < 9; k++) {
            const x = 16 + k * 21;
            marks += '<line class="viz-tick" x1="' + x + '" y1="48" x2="' + x + '" y2="56"/>';
          }
          ticks.innerHTML = marks;
        }
        const tot = Number(msg.limit) || 1;
        const i = Number(msg.i) || 0;
        const x = 16 + ((i * 21) % 168);
        const hop = $("#viz-neighbor-hopper", root);
        if (hop) hop.setAttribute("transform", "translate(" + x + ",52)");
        const lab = $("#viz-neighbor-n", root);
        if (lab) {
          lab.textContent = extra.candidate
            ? "candidate " + extra.candidate
            : extra.label || "hopping…";
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
      if (phase === "ecpp") return extra.D ? "ECPP discriminant D=" + extra.D : "class-number-1 / FastECPP";
      if (phase === "split") return extra.label || "factoring a cofactor of n±1";
      if (phase === "precheck") return "small-prime / parity filter";
      if (phase === "wheel") return "30-wheel trial division";
      if (phase === "neighbor") {
        return extra.label || "searching neighboring primes";
      }
      return phase;
    }

    function renderBusy(state) {
      out.className = "lab-out show busy";
      out.innerHTML = `<p class="verdict">Checking…</p>
        <dl><dt>n</dt><dd>${escapeHtml(state.n)}</dd>
        <dt>digits</dt><dd>${String(state.n).length}</dd>
        <dt>⌊√n⌋</dt><dd>${state.isqrt}</dd>
        <dt>stage</dt><dd>${escapeHtml(state.stage || "—")}</dd>
        <dt>step</dt><dd>${escapeHtml(state.i || "—")}</dd></dl>`;
    }

    function renderCert(state) {
      lastCert = state;
      const verdict = state.prime ? "Prime" : "Composite";
      out.className = "lab-out show cert " + (state.prime ? "yes" : "no");
      out.innerHTML = `<article class="cert-card">
        <p class="cert-kicker">${state.prime ? "the curtain falls · a proof" : "the curtain falls · a factor"}</p>
        <p class="verdict">${verdict}</p>
        <dl>
          <dt>n</dt><dd>${escapeHtml(state.n)}</dd>
          <dt>digits</dt><dd>${state.n.length}</dd>
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
      if (nextBtn) nextBtn.disabled = false;
      if (prevBtn) prevBtn.disabled = false;
      stop.disabled = true;
      bar.classList.remove("show");
      hideStage();
      killWorker();
    }

    function updateDigits() {
      if (digits) digits.textContent = formatDigitCount(input.value);
    }

    function parseK() {
      const s = String(kInput ? kInput.value : "1").trim() || "1";
      if (!/^\d+$/.test(s)) return null;
      const k = Number(s);
      if (!Number.isInteger(k) || k < 1 || k > 64) return null;
      return k;
    }

    function renderNeighbor(res) {
      if (!nbOut) return;
      if (res.ok) {
        nbOut.className = "lab-out show yes";
        nbOut.innerHTML =
          '<p class="verdict">' +
          (res.direction === "prev" ? "Previous prime" : "Next prime") +
          "</p><dl>" +
          "<dt>n</dt><dd>" +
          escapeHtml(res.n) +
          "</dd>" +
          "<dt>digits</dt><dd>" +
          escapeHtml(String(res.n.length)) +
          "</dd>" +
          "<dt>k</dt><dd>" +
          escapeHtml(String(res.k)) +
          "</dd>" +
          "<dt>result</dt><dd>" +
          escapeHtml(res.value) +
          "</dd>" +
          "<dt>result digits</dt><dd>" +
          escapeHtml(String(res.value.length)) +
          "</dd>" +
          "<dt>path</dt><dd>" +
          escapeHtml(res.path || "") +
          "</dd>" +
          "<dt>tried</dt><dd>" +
          escapeHtml(String(res.tried)) +
          " candidates</dd>" +
          "<dt>time</dt><dd>" +
          Number(res.ms).toFixed(2) +
          " ms</dd>" +
          "<dt>note</dt><dd>" +
          escapeHtml(res.note || "") +
          "</dd></dl>";
        return;
      }
      nbOut.className = "lab-out show " + (res.inconclusive ? "busy" : "no");
      nbOut.innerHTML =
        '<p class="verdict">' +
        (res.inconclusive ? "Inconclusive here" : "No neighbor") +
        "</p><dl>" +
        (res.last
          ? "<dt>candidate</dt><dd>" + escapeHtml(res.last) + "</dd>"
          : "") +
        (res.tried != null
          ? "<dt>tried</dt><dd>" + escapeHtml(String(res.tried)) + " candidates</dd>"
          : "") +
        "<dt>note</dt><dd>" +
        escapeHtml(res.error || res.note || "Could not find that prime in-tab.") +
        "</dd></dl>";
    }

    function run(kind) {
      kind = kind || "check";
      const n = parseN(input.value);
      if (n === null) {
        hideStage();
        if (kind === "check") {
          renderSimple("no", "Invalid n", "<p>Enter a non-negative decimal integer.</p>");
        } else if (nbOut) {
          nbOut.className = "lab-out show no";
          nbOut.innerHTML = '<p class="verdict">Invalid n</p><p>Enter a non-negative decimal integer above.</p>';
        }
        return;
      }
      let k = 1;
      if (kind !== "check") {
        k = parseK();
        if (k == null) {
          if (nbOut) {
            nbOut.className = "lab-out show no";
            nbOut.innerHTML =
              '<p class="verdict">Invalid k</p><p>k must be an integer from 1 to 64.</p>';
          }
          return;
        }
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
      if (kind === "check" && !multiLimb && limit > WARN_ISQRT) {
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
      if (nextBtn) nextBtn.disabled = true;
      if (prevBtn) prevBtn.disabled = true;
      stop.disabled = false;
      bar.classList.add("show");
      barFill.style.width = "0%";
      showPhase(kind === "check" ? "precheck" : "precheck");
      const busyState = {
        n: n.toString(),
        isqrt: fmt(limit),
        i: "starting",
        stage: kind === "check" ? "precheck" : kind === "nextPrime" ? "next prime" : "previous prime",
      };
      if (kind === "check") renderBusy(busyState);
      else if (nbOut) {
        nbOut.className = "lab-out show busy";
        nbOut.innerHTML =
          '<p class="verdict">' +
          (kind === "nextPrime" ? "Searching next…" : "Searching previous…") +
          "</p><dl><dt>n</dt><dd>" +
          escapeHtml(n.toString()) +
          "</dd><dt>digits</dt><dd>" +
          n.toString().length +
          "</dd><dt>k</dt><dd>" +
          k +
          "</dd></dl>";
      }

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
            const stageTxt = phaseLabel(msg.phase || "wheel", msg.extra || {});
            if (kind === "check") {
              renderBusy({
                n: n.toString(),
                isqrt: fmt(isqrt(n)),
                stage: stageTxt,
                i: fmt(i) + " / " + fmt(lim),
              });
            } else if (nbOut) {
              nbOut.className = "lab-out show busy";
              nbOut.innerHTML =
                '<p class="verdict">Searching…</p><dl><dt>n</dt><dd>' +
                escapeHtml(n.toString()) +
                "</dd><dt>stage</dt><dd>" +
                escapeHtml(stageTxt) +
                "</dd><dt>step</dt><dd>" +
                fmt(i) +
                " / " +
                fmt(lim) +
                "</dd></dl>";
            }
          } catch (_) {
            /* ignore malformed progress */
          }
          return;
        }
        if (msg.type === "aborted") {
          finishIdle();
          if (kind === "check") {
            renderSimple("busy", "Stopped", "<p>Trial cancelled.</p>");
          } else if (nbOut) {
            nbOut.className = "lab-out show busy";
            nbOut.innerHTML = '<p class="verdict">Stopped</p><p>Search cancelled.</p>';
          }
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
          if (kind !== "check") {
            renderNeighbor(res);
          } else if (res.prime === null) {
            const title =
              res.path === "inconclusive" ? "Inconclusive here" : "No decision";
            renderSimple(
              "busy",
              title,
              `<dl><dt>n</dt><dd>${escapeHtml(n.toString())}</dd>
              <dt>digits</dt><dd>${n.toString().length}</dd>
              <dt>path</dt><dd>${escapeHtml(res.path || "")}</dd>
              <dt>⌊√n⌋</dt><dd>${fmt(res.isqrt)}</dd>
              <dt>time</dt><dd>${Number(res.ms).toFixed(2)} ms</dd>
              <dt>note</dt><dd>${escapeHtml(res.note || "")}</dd></dl>
              <p class="lab-hint">There is no maximum digit length. The tab uses one engine per band: class-number-1 then computed-H_D FastECPP on ≥256-bit <em>n</em> (Jacobian mul, stacked Montgomery ECM), combined BLS only below that. No BLS after an ECPP miss. 132–150 digit general primes such as 10^131+63 and 10^149+183 are in scope. A miss is inconclusive here; Python may still prove it, else UnsettledPrimalityError (AKS is not a product-path fallback).</p>`
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
          finishIdle();
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

      worker.postMessage({ cmd: kind, n: n.toString(), k: k });
    }

    function updateDigitsAndMaybeRun(e) {
      updateDigits();
    }

    go.addEventListener("click", function () {
      run("check");
    });
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        run("nextPrime");
      });
    }
    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        run("prevPrime");
      });
    }
    input.addEventListener("input", updateDigitsAndMaybeRun);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") run("check");
    });
    updateDigits();
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
        if (nbOut && nbOut.classList.contains("show")) {
          nbOut.className = "lab-out show busy";
          nbOut.innerHTML = '<p class="verdict">Stopped</p><p>Search cancelled.</p>';
        }
        finishIdle();
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
      input.dispatchEvent(new Event("input"));
      input.focus();
      input.select();
    });
  });
})();

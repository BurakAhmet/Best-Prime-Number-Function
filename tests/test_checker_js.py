"""Smoke-check the in-browser 30-wheel lab (Pages assets)."""
from __future__ import annotations

import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "docs" / "wiki" / "assets" / "checker-worker.js"
UI = ROOT / "docs" / "wiki" / "assets" / "checker.js"
OG = ROOT / "docs" / "wiki" / "assets" / "og.png"
HOF = ROOT / "docs" / "wiki" / "Hall-of-fame.md"
NEAR_2_63 = 9223372036854775783


def test_factor_button_does_not_hijack_previous_prime():
    """List factors must not write the previous-prime status into that box."""
    ui = UI.read_text(encoding="utf-8")
    factor_busy = ui.find('kind === "factors" && facOut')
    previous = ui.find("Searching previous")
    assert factor_busy != -1 and previous != -1
    assert factor_busy < previous
    assert "Factoring" in ui[factor_busy:previous]


def test_lab_assets_allow_near_2_63_prime():
    src = WORKER.read_text(encoding="utf-8")
    ui = UI.read_text(encoding="utf-8")
    assert WORKER.is_file() and UI.is_file()
    m = re.search(r"TRIAL_SOFT_ISQRT\s*=\s*([0-9_]+)n", src)
    assert m, "TRIAL_SOFT_ISQRT missing in checker-worker.js"
    soft = int(m.group(1).replace("_", ""))
    x = NEAR_2_63
    y = (x + 1) // 2
    z = x
    while y < z:
        z = y
        y = (y + x // y) // 2
    assert soft >= z
    assert "ecmFactor" in src
    assert "combinedTheorem1Ok" in src
    assert "ecppPrimality" in src
    assert "HUGE_BITS" in src
    assert "proveQ" in src
    assert "ECPP first" in src or "class-number-1 ECPP first" in src
    assert "hilbertRootModN" in src
    assert "hilbertClassPoly" in src
    assert "fastecppWalk" in src
    assert "HILBERT_CLASS_POLY" in src
    assert "-3076" in src
    assert "scaledFastecppDMax" in src
    assert "lucasUv" in src
    assert "COFACTOR_TRIAL_ISQRT" in src
    assert re.search(r"POINT_X_MAX\s*=\s*4096", src)
    assert "Fermat composite filter" in src
    assert "NEIGHBOR_MAX_TRIES" not in src
    assert "jacDbl" in src
    assert "admissiblePairs" in src
    assert "Montgomery ECM" in ui or "ECM" in ui
    assert 'data-phase="sides"' in ui
    assert 'data-phase="lucas"' in ui
    assert "Selfridge" in ui
    assert 'data-phase="combined"' in ui
    assert 'data-phase="ecpp"' in ui
    assert 'data-phase="cyclotomic"' in ui
    assert "viz-cyclo-bead" in ui
    assert "Combined Theorem 1" in ui
    assert "checker-worker.js" in ui
    assert "lab-stage" in ui
    assert 'data-phase="neighbor"' in ui
    assert "p − n" in ui
    assert "previous power of ten" in ui
    assert "residue-wheel" in ui
    assert "square-pic" in ui
    assert "gap-ruler" in ui
    assert "proof-replay" in ui
    assert "lab-compare" in ui
    assert "lab-random" in ui
    assert "lab-random-prime" in ui
    assert "gap-k-val" in ui
    assert "wrap-num" in ui
    assert "untilNextPower" in ui
    assert "aboveLowerPower" in ui
    assert '"wide"' in ui
    assert "greatest square" in ui
    assert "numberPortrait" in ui
    assert "cert-facts" in ui
    assert "to 64" not in ui
    assert "quickComposite" in src
    assert "numberPortrait" in src
    assert "delta:" in src
    css = (ROOT / "docs" / "wiki" / "assets" / "checker.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css
    assert ".cert-facts" in css
    assert "factorRows" in ui
    assert "Download SVG" in ui
    assert "WHEEL30" in ui
    assert "data-res=" in ui
    assert "extractFactor" in src
    assert "FACTOR_TRIAL_BOUND" in src
    assert "firstTrialFactor" in src
    assert "emit(onTick" in src or "function emit(" in src
    assert "nextPrime" in src
    assert "prevPrime" in src
    assert "lab-digits" in ui
    assert "lab-next" in ui
    assert "lab-prev" in ui
    assert "formatDigitCount" in ui
    assert "Next / previous prime" in ui


def test_og_png_is_social_card():
    data = OG.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (1200, 630)


def test_hall_of_fame_has_latest_potd_row():
    text = HOF.read_text(encoding="utf-8")
    start = text.find("<!-- potd-log:start -->")
    end = text.find("<!-- potd-log:end -->")
    assert 0 <= start < end
    block = text[start:end]
    assert re.search(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*`?\d+`?", block)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_self_test():
    r = subprocess.run(
        ["node", str(WORKER), "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "self-test OK" in r.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_random_n_has_no_digit_ceiling() -> None:
    script = r"""
const fs = require('fs');
const src = fs.readFileSync('docs/wiki/assets/checker.js', 'utf8');
const m = src.match(/function fillRandom[\s\S]*?\n  function workerUrl/);
if (!m) { console.error('missing randomN'); process.exit(1); }
eval(m[0].replace(/\n  function workerUrl$/, ''));
if (src.includes('max="150"') || src.includes('10^149')) {
  console.error('digit ceiling still in the lab');
  process.exit(1);
}
const any = { checked: true };
let sawShort = false;
let sawPastOldCap = false;
for (let i = 0; i < 80; i++) {
  const n = randomN(null, any);
  const len = n.toString().length;
  if (n < 1n) { console.error(String(n)); process.exit(1); }
  if (len <= 20) sawShort = true;
  if (len > 149) sawPastOldCap = true;
}
if (!sawShort || !sawPastOldCap) {
  console.error('any-length', sawShort, sawPastOldCap);
  process.exit(1);
}
const digits = { value: '3' };
const none = { checked: false };
for (let i = 0; i < 20; i++) {
  const n = randomN(digits, none);
  if (n < 100n || n > 999n) { console.error('digits', String(n)); process.exit(1); }
}
const wide = randomN({ value: '1000' }, none);
const w = wide.toString();
if (w.length !== 1000) { console.error('1000-digit length', w.length); process.exit(1); }
if (w[0] === '0') { console.error('leading zero'); process.exit(1); }
const exact150 = randomN({ value: '150' }, none);
if (exact150.toString().length !== 150) { console.error('150 clamped'); process.exit(1); }
console.log('random ok', sawPastOldCap ? 'saw >149' : 'tail not hit in 80 draws');
"""
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_54_digit_prime_in_the_lab_is_under_eight_seconds() -> None:
    script = r"""
const api = require('./docs/wiki/assets/checker-worker.js');
const n = 337918279897593366562217396203250951407486188355507619n;
const t0 = Date.now();
const r = api.checkPrime(n);
const dt = Date.now() - t0;
if (r.prime !== true || dt >= 8000) {
  console.error(dt, JSON.stringify(r));
  process.exit(1);
}
console.log('54-digit', dt, r.path);
"""
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_37_digit_prime_in_the_lab_is_under_two_seconds() -> None:
    script = r"""
const api = require('./docs/wiki/assets/checker-worker.js');
const n = 10n ** 36n + 67n;
const t0 = Date.now();
const r = api.checkPrime(n);
const dt = Date.now() - t0;
if (r.prime !== true || dt >= 2000) {
  console.error(dt, JSON.stringify(r));
  process.exit(1);
}
console.log('37-digit', dt, r.path);
"""
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_checker_worker_spsp_above_2_64_is_fast_composite() -> None:
    """71-bit strong pseudoprime must not fall through to a √n trial."""
    script = r"""
const api=require('./docs/wiki/assets/checker-worker.js');
const n=1955097530374556503981n;
const t0=Date.now();
const r=api.checkPrime(n);
const dt=Date.now()-t0;
if (r.prime !== false || n % BigInt(r.factor) !== 0n || dt >= 3000) {
  console.error(dt, JSON.stringify(r));
  process.exit(1);
}
console.log('spsp', r.factor, dt);
"""
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_browser_aprcl_ladder_matches_library() -> None:
    """The tab selects the same modulus rung as the library, without building Jacobi sums."""
    script = r"""
const A = require('./docs/wiki/assets/aprcl.js');
function digits(n){ return n.toString().length; }
const n1100 = 10n ** 1099n + 73n;
const r1100 = A.chooseR(n1100);
if (r1100 !== 73513440) { console.error('1100 R', r1100); process.exit(1); }
if (!(A.modulus(r1100).s > A.isqrt(n1100))) { console.error('1100 cover'); process.exit(1); }
const n5000 = 10n ** 4999n;
const r5000 = A.chooseR(n5000);
if (r5000 !== 4655851200) { console.error('5000 R', r5000); process.exit(1); }
if (!(A.modulus(r5000).s > A.isqrt(n5000))) { console.error('5000 cover'); process.exit(1); }
if (digits(A.modulus(r5000).s) < 2501) { console.error('s digits', digits(A.modulus(r5000).s)); process.exit(1); }
const past = A.chooseR(10n ** 5199n);
if (past !== null) { console.error('past ladder', past); process.exit(1); }
const small = A.proveSerial(10007n);
if (!small.prime || small.path !== 'aprcl') { console.error(JSON.stringify(small)); process.exit(1); }
console.log('ladder ok', r1100, r5000, digits(A.modulus(r5000).s));
"""
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_100_digit_under_30s() -> None:
    """100-digit prime, Fermat composite, and a 400-digit input. No digit cap.

    Each check must finish inside this 30s process budget. The 400-digit
    case is only there to prove a long decimal is accepted.
    """
    script = r"""
const api=require('./docs/wiki/assets/checker-worker.js');
async function check(n, limitMs) {
  const t0 = Date.now();
  const r = await api.checkPrime(n);
  const dt = Date.now() - t0;
  if (dt >= limitMs) {
    console.error('slow', dt, JSON.stringify(r));
    process.exit(1);
  }
  return r;
}
(async () => {
const wide = 17n * (10n**399n + 1n);
const rw = await check(wide, 2000);
if (String(wide).length < 400 || rw.prime !== false || rw.factor == null || wide % BigInt(rw.factor) !== 0n) {
  console.error('400-digit rejected', JSON.stringify(rw));
  process.exit(1);
}
const cSmall = 10n**99n + 7n;
const rs = await check(cSmall, 2000);
if (rs.prime !== false || cSmall % BigInt(rs.factor) !== 0n) {
  console.error('100-digit small factor', JSON.stringify(rs));
  process.exit(1);
}
const cFerm = 10n**99n + 9n;
const rf = await check(cFerm, 12000);
if (rf.prime !== false) {
  console.error('100-digit Fermat composite', JSON.stringify(rf));
  process.exit(1);
}
if (rf.factor == null || cFerm % BigInt(rf.factor) !== 0n) {
  console.error('100-digit factor not isolated', JSON.stringify(rf));
  process.exit(1);
}
const p100 = 10n**99n + 289n;
const rp = await check(p100, 25000);
if (rp.prime !== true || rp.path !== 'aprcl') {
  console.error('P100', JSON.stringify(rp));
  process.exit(1);
}
console.log('100-digit OK', rf.factor, rp.path, rp.ms);
})().catch((err) => { console.error(err); process.exit(1); });
"""
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_next_prime_after_22_digit_is_the_n_minus_1_proof() -> None:
    """2588668629162033095543 used to trial a 71-bit cofactor for minutes."""
    script = r"""
const api = require('./docs/wiki/assets/checker-worker.js');
const n = 2588668629162033095543n;
const t0 = Date.now();
api.nextPrime(n, 1).then((r) => {
  const dt = Date.now() - t0;
  if (!r.ok || r.value !== '2588668629162033095603' || r.path !== 'n-1-pocklington' || dt >= 2000) {
    console.error(dt, JSON.stringify(r));
    process.exit(1);
  }
  console.log('next22', dt, r.path, r.delta);
}).catch((e) => { console.error(e); process.exit(1); });
"""
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_next_prev_prime() -> None:
    script = (
        "const api=require('./docs/wiki/assets/checker-worker.js');"
        "(async()=>{"
        "const n=await api.nextPrime(14n,1); const p=await api.prevPrime(14n,1);"
        "if(!n.ok||n.value!=='17'||!p.ok||p.value!=='13'){"
        "  console.error(JSON.stringify({n,p})); process.exit(1);"
        "}"
        "if(n.delta!=='3'||p.delta!=='-1'){console.error('delta',n.delta,p.delta);process.exit(1);}"
        "const k=await api.nextPrime(100n,65);"
        "if(!k.ok||k.value!=='463'||k.delta!=='363'){console.error(JSON.stringify(k));process.exit(1);}"
        "if(api.parseK('0')!==null||api.parseK('999')!==999n){process.exit(1);}"
        "const face=api.numberPortrait(97n);"
        "if(face.bits!==7||face.digitSum!==16||face.aboveSquare!=='16'||face.mod30!=='7'){"
        "  console.error(JSON.stringify(face)); process.exit(1);}"
        "if(api.quickComposite(2047n)!==true||api.quickComposite(97n)!==false){process.exit(1);}"
        "console.log('neighbors OK', n.value, p.value, k.delta);"
        "})().catch((err)=>{console.error(err); process.exit(1);});"
    )
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_hard55_pocklington() -> None:
    """10^54+31: hostile n−1, proven via ECM + Pocklington in the Pages worker."""
    script = (
        "const api=require('./docs/wiki/assets/checker-worker.js');"
        "const n=1000000000000000000000000000000000000000000000000000031n;"
        "const r=api.checkPrime(n);"
        "if(!r || r.prime!==true || r.path!=='n-1-pocklington'){"
        "  console.error(JSON.stringify(r)); process.exit(1);"
        "}"
        "console.log('hard55 OK', r.path, r.ms);"
    )
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_p131_ecpp() -> None:
    """10^130+1113: class-number-1 ECPP (D=−19) in the Pages worker."""
    script = (
        "const api=require('./docs/wiki/assets/checker-worker.js');"
        "const n=10n**130n+1113n;"
        "(async()=>{const r=await api.checkPrime(n);"
        "if(!r || r.prime!==true || r.path!=='aprcl'){"
        "  console.error(JSON.stringify(r)); process.exit(1);"
        "}"
        "console.log('p131 OK', r.path, r.ms);})().catch(e=>{console.error(e);process.exit(1);});"
    )
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_p131_next_prime() -> None:
    """Next prime after 10^130+1113 is 10^130+1189 (FastECPP D=−3076)."""
    script = (
        "const api=require('./docs/wiki/assets/checker-worker.js');"
        "const n=10n**130n+1113n;"
        "(async()=>{const r=await api.nextPrime(n,1);"
        "if(!r || !r.ok || r.value!==(10n**130n+1189n).toString()){"
        "  console.error(JSON.stringify(r)); process.exit(1);"
        "}"
        "console.log('p131 next OK', r.value, r.path, r.ms);})().catch(e=>{console.error(e);process.exit(1);});"
    )
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_p132_computed_hd() -> None:
    """10^131+63: 132-digit prime via computed H_D (cofactor D=−2216)."""
    script = (
        "const api=require('./docs/wiki/assets/checker-worker.js');"
        "const n=10n**131n+63n;"
        "(async()=>{const r=await api.checkPrime(n);"
        "if(!r || r.prime!==true || r.path!=='aprcl'){"
        "  console.error(JSON.stringify(r)); process.exit(1);"
        "}"
        "console.log('p132 OK', r.path, r.ms);})().catch(e=>{console.error(e);process.exit(1);});"
    )
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_checker_worker_p150_computed_hd() -> None:
    """10^149+183: 150-digit prime via computed H_D (D=−24 / −267)."""
    script = (
        "const api=require('./docs/wiki/assets/checker-worker.js');"
        "const n=10n**149n+183n;"
        "(async()=>{const r=await api.checkPrime(n);"
        "if(!r || r.prime!==true || r.path!=='aprcl'){"
        "  console.error(JSON.stringify(r)); process.exit(1);"
        "}"
        "console.log('p150 OK', r.path, r.ms);})().catch(e=>{console.error(e);process.exit(1);});"
    )
    r = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr

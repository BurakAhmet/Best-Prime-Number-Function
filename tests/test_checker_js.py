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
    assert "Combined Theorem 1" in ui
    assert "checker-worker.js" in ui
    assert "lab-stage" in ui
    assert 'data-phase="neighbor"' in ui
    assert "p − n" in ui
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
def test_checker_worker_100_digit_under_30s() -> None:
    """100-digit prime, Fermat composite, and a 400-digit input. No digit cap.

    Each check must finish inside this 30s process budget. The 400-digit
    case is only there to prove a long decimal is accepted.
    """
    script = r"""
const api=require('./docs/wiki/assets/checker-worker.js');
function check(n, limitMs) {
  const t0 = Date.now();
  const r = api.checkPrime(n);
  const dt = Date.now() - t0;
  if (dt >= limitMs) {
    console.error('slow', dt, JSON.stringify(r));
    process.exit(1);
  }
  return r;
}
const wide = 17n * (10n**399n + 1n);
const rw = check(wide, 2000);
if (String(wide).length < 400 || rw.prime !== false || rw.factor == null || wide % BigInt(rw.factor) !== 0n) {
  console.error('400-digit rejected', JSON.stringify(rw));
  process.exit(1);
}
const cSmall = 10n**99n + 7n;
const rs = check(cSmall, 2000);
if (rs.prime !== false || cSmall % BigInt(rs.factor) !== 0n) {
  console.error('100-digit small factor', JSON.stringify(rs));
  process.exit(1);
}
const cFerm = 10n**99n + 9n;
const rf = check(cFerm, 12000);
if (rf.prime !== false) {
  console.error('100-digit Fermat composite', JSON.stringify(rf));
  process.exit(1);
}
if (rf.factor == null || cFerm % BigInt(rf.factor) !== 0n) {
  console.error('100-digit factor not isolated', JSON.stringify(rf));
  process.exit(1);
}
const p100 = 10n**99n + 289n;
const rp = check(p100, 25000);
if (rp.prime !== true || rp.path !== 'ecpp') {
  console.error('P100', JSON.stringify(rp));
  process.exit(1);
}
console.log('100-digit OK', rf.factor, rp.path, rp.ms);
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
def test_checker_worker_next_prev_prime() -> None:
    script = (
        "const api=require('./docs/wiki/assets/checker-worker.js');"
        "const n=api.nextPrime(14n,1); const p=api.prevPrime(14n,1);"
        "if(!n.ok||n.value!=='17'||!p.ok||p.value!=='13'){"
        "  console.error(JSON.stringify({n,p})); process.exit(1);"
        "}"
        "if(n.delta!=='3'||p.delta!=='-1'){console.error('delta',n.delta,p.delta);process.exit(1);}"
        "const k=api.nextPrime(100n,65);"
        "if(!k.ok||k.value!=='463'||k.delta!=='363'){console.error(JSON.stringify(k));process.exit(1);}"
        "if(api.parseK('0')!==null||api.parseK('999')!==999n){process.exit(1);}"
        "const face=api.numberPortrait(97n);"
        "if(face.bits!==7||face.digitSum!==16||face.aboveSquare!=='16'||face.mod30!=='7'){"
        "  console.error(JSON.stringify(face)); process.exit(1);}"
        "if(api.quickComposite(2047n)!==true||api.quickComposite(97n)!==false){process.exit(1);}"
        "console.log('neighbors OK', n.value, p.value, k.delta);"
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
        "const r=api.checkPrime(n);"
        "if(!r || r.prime!==true || r.path!=='ecpp'){"
        "  console.error(JSON.stringify(r)); process.exit(1);"
        "}"
        "console.log('p131 OK', r.path, r.ms);"
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
        "const r=api.nextPrime(n,1);"
        "if(!r || !r.ok || r.value!==(10n**130n+1189n).toString()){"
        "  console.error(JSON.stringify(r)); process.exit(1);"
        "}"
        "console.log('p131 next OK', r.value, r.path, r.ms);"
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
        "const r=api.checkPrime(n);"
        "if(!r || r.prime!==true || r.path!=='ecpp'){"
        "  console.error(JSON.stringify(r)); process.exit(1);"
        "}"
        "console.log('p132 OK', r.path, r.ms);"
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
        "const r=api.checkPrime(n);"
        "if(!r || r.prime!==true || r.path!=='ecpp'){"
        "  console.error(JSON.stringify(r)); process.exit(1);"
        "}"
        "console.log('p150 OK', r.path, r.ms);"
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

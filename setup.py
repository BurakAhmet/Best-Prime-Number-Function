"""Optional native OpenMP build for is_prime_data/wheel_core.so during packaging."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.develop import develop as _develop

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "is_prime_data"
SRC_C = DATA / "wheel_core.c"


def _ensure_c_source() -> bool:
    """Generate wheel_core.c when missing (scripts/generate_wheel_core_c.py)."""
    if SRC_C.is_file():
        return True
    gen = ROOT / "scripts" / "generate_wheel_core_c.py"
    if not gen.is_file():
        return False
    try:
        subprocess.run([sys.executable, str(gen)], check=True, cwd=ROOT)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"is_prime: could not generate wheel_core.c ({exc})", file=sys.stderr)
        return False
    return SRC_C.is_file()


def _compile_wheel_core(target_dir: Path) -> bool:
    """Compile wheel_core.so/.dylib into target_dir. Returns True on success."""
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    if not _ensure_c_source():
        print("is_prime: wheel_core.c not found; skipping native build", file=sys.stderr)
        return False
    src = SRC_C if SRC_C.is_file() else target_dir / "wheel_core.c"
    if not src.is_file():
        print("is_prime: wheel_core.c not found; skipping native build", file=sys.stderr)
        return False

    if sys.platform == "darwin":
        ext = "dylib"
        cc = os.environ.get("CC", "clang")
    elif sys.platform == "win32":
        ext = "dll"
        cc = os.environ.get("CC", "gcc")
    else:
        ext = "so"
        cc = os.environ.get("CC", "gcc")
    out = target_dir / f"wheel_core.{ext}"
    omp: list[str] = ["-fopenmp"]
    if sys.platform == "darwin":
        for prefix in ("/opt/homebrew/opt/libomp", "/usr/local/opt/libomp"):
            if Path(prefix).is_dir():
                omp = [
                    "-Xpreprocessor",
                    "-fopenmp",
                    f"-I{prefix}/include",
                    f"-L{prefix}/lib",
                    "-lomp",
                ]
                break
    flag_sets = (
        ["-march=native", "-mtune=native"],
        ["-march=x86-64-v2"],
        [],
    )
    last_err: object = "unknown"
    for arch in flag_sets:
        cmd = [
            cc,
            "-O3",
            "-fPIC",
            "-shared",
            *omp,
            *arch,
            "-funroll-loops",
            "-fomit-frame-pointer",
            "-o",
            str(out),
            str(src),
            "-lm",
            *omp,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"is_prime: built native core -> {out}")
            # ctypes loader also looks for wheel_core.so
            so = target_dir / "wheel_core.so"
            if out != so:
                try:
                    shutil.copy2(out, so)
                except OSError:
                    pass
            return True
        except FileNotFoundError as exc:
            last_err = exc
            break
        except subprocess.CalledProcessError as exc:
            last_err = (exc.stderr or exc.stdout or str(exc)).strip()
            continue
    print(
        "is_prime: optional OpenMP core not built "
        f"({last_err}). Stdlib/Numba paths still work; "
        "run scripts/compile_wheel_core.sh later.",
        file=sys.stderr,
    )
    return False


class build_py(_build_py):
    def run(self) -> None:
        super().run()
        lib = Path(self.build_lib) / "is_prime_data"
        if SRC_C.is_file():
            lib.mkdir(parents=True, exist_ok=True)
            if not (lib / "wheel_core.c").is_file():
                shutil.copy2(SRC_C, lib / "wheel_core.c")
        _compile_wheel_core(lib)


class develop(_develop):
    def run(self) -> None:
        super().run()
        _compile_wheel_core(DATA)


_cmdclass = {"build_py": build_py, "develop": develop}

try:
    from setuptools.command.editable_wheel import editable_wheel as _editable_wheel

    class editable_wheel(_editable_wheel):
        def run(self) -> None:
            super().run()
            _compile_wheel_core(DATA)

    _cmdclass["editable_wheel"] = editable_wheel
except Exception:
    pass


setup(cmdclass=_cmdclass)

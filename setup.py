"""Optional native OpenMP build for is_prime_data/wheel_core.so during packaging.

The C core is a ctypes shared library (no PyInit_*). Local installs still
skip it when no compiler is present. Published wheels set
``BEST_PRIME_REQUIRE_NATIVE=1`` so a missing ``.so`` is a hard error, and
``BEST_PRIME_PORTABLE=1`` so we never bake ``-march=native`` into artifacts.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.develop import develop as _develop
from setuptools.dist import Distribution

try:
    from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:  # pragma: no cover - older setuptools
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel  # type: ignore

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "is_prime_data"
SRC_C = DATA / "wheel_core.c"

_TRUE = {"1", "true", "yes", "on"}
REQUIRE_NATIVE = os.environ.get("BEST_PRIME_REQUIRE_NATIVE", "").strip().lower() in _TRUE
PORTABLE = os.environ.get("BEST_PRIME_PORTABLE", "").strip().lower() in _TRUE
_NATIVE_BUILT = False


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
    if PORTABLE:
        # Published wheels must run on machines other than the builder.
        flag_sets = (["-march=x86-64-v2"], []) if sys.platform != "darwin" else ([],)
    else:
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
        ]
        lehman_c = DATA / "lehman_core.c"
        if lehman_c.is_file():
            cmd.append(str(lehman_c))
        cmd.extend(["-lm", *omp])
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
            global _NATIVE_BUILT
            _NATIVE_BUILT = True
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
        ok = _compile_wheel_core(lib)
        if REQUIRE_NATIVE and not ok:
            raise SystemExit(
                "BEST_PRIME_REQUIRE_NATIVE=1 but wheel_core failed to compile"
            )


class develop(_develop):
    def run(self) -> None:
        super().run()
        ok = _compile_wheel_core(DATA)
        if REQUIRE_NATIVE and not ok:
            raise SystemExit(
                "BEST_PRIME_REQUIRE_NATIVE=1 but wheel_core failed to compile"
            )


class bdist_wheel(_bdist_wheel):
    """ctypes ``.so`` is Python-version independent: tag ``py3-none-<plat>``.

    ``finalize_options`` runs *before* ``build_py``, so we compile (or honour
    ``BEST_PRIME_REQUIRE_NATIVE``) in ``run`` before the tag is written.
    No compiler and no REQUIRE_NATIVE → keep a pure wheel.
    """

    def finalize_options(self) -> None:
        super().finalize_options()
        if REQUIRE_NATIVE:
            self.root_is_pure = False

    def run(self) -> None:
        ok = _NATIVE_BUILT or _compile_wheel_core(DATA)
        if REQUIRE_NATIVE and not ok:
            raise SystemExit(
                "BEST_PRIME_REQUIRE_NATIVE=1 but wheel_core failed to compile"
            )
        if ok:
            self.root_is_pure = False
        super().run()

    def get_tag(self):
        python, abi, plat = super().get_tag()
        if REQUIRE_NATIVE or _NATIVE_BUILT or not getattr(self, "root_is_pure", True):
            return "py3", "none", plat
        return python, abi, plat


_cmdclass = {"build_py": build_py, "develop": develop, "bdist_wheel": bdist_wheel}

try:
    from setuptools.command.editable_wheel import editable_wheel as _editable_wheel

    class editable_wheel(_editable_wheel):
        def run(self) -> None:
            super().run()
            ok = _compile_wheel_core(DATA)
            if REQUIRE_NATIVE and not ok:
                raise SystemExit(
                    "BEST_PRIME_REQUIRE_NATIVE=1 but wheel_core failed to compile"
                )

    _cmdclass["editable_wheel"] = editable_wheel
except Exception:
    pass


class BinaryDistribution(Distribution):
    """ctypes core is not an Extension, but published wheels are platform-specific."""

    def has_ext_modules(self) -> bool:
        if REQUIRE_NATIVE or _NATIVE_BUILT:
            return True
        return super().has_ext_modules()


setup(cmdclass=_cmdclass, distclass=BinaryDistribution)

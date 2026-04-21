from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from distutils.errors import DistutilsSetupError
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


ROOT = Path(__file__).resolve().parent
UPSTREAM_ROOT = Path("vendor") / "axidev-io"
PKG_CONFIG_PACKAGES = ["libinput", "libudev", "xkbcommon"]

COMMON_SOURCES = [
    UPSTREAM_ROOT / "src" / "c_api.c",
    UPSTREAM_ROOT / "src" / "core" / "context.c",
    UPSTREAM_ROOT / "src" / "core" / "log.c",
    UPSTREAM_ROOT / "src" / "internal" / "utf.c",
    UPSTREAM_ROOT / "src" / "vendor" / "stb_ds_impl.c",
    UPSTREAM_ROOT / "src" / "keyboard" / "common" / "key_utils.c",
    UPSTREAM_ROOT / "src" / "keyboard" / "common" / "keymap.c",
]

WINDOWS_SOURCES = [
    UPSTREAM_ROOT / "src" / "internal" / "thread_win32.c",
    UPSTREAM_ROOT / "src" / "keyboard" / "common" / "windows_keymap.c",
    UPSTREAM_ROOT / "src" / "keyboard" / "sender" / "sender_windows.c",
    UPSTREAM_ROOT / "src" / "keyboard" / "listener" / "listener_windows.c",
]

LINUX_SOURCES = [
    UPSTREAM_ROOT / "src" / "internal" / "thread_pthread.c",
    UPSTREAM_ROOT / "src" / "keyboard" / "common" / "linux_layout.c",
    UPSTREAM_ROOT / "src" / "keyboard" / "common" / "linux_keysym.c",
    UPSTREAM_ROOT / "src" / "keyboard" / "sender" / "sender_uinput.c",
    UPSTREAM_ROOT / "src" / "keyboard" / "listener" / "listener_linux.c",
]


def split_flags(value: str | None) -> list[str]:
    if not value:
        return []
    return shlex.split(value, posix=(os.name != "nt"))


def ensure_linux_dynamic_link_flags(flags: list[str], source: str) -> None:
    forbidden_prefixes = ("-Wl,-Bstatic", "-Wl,--whole-archive")
    forbidden_exact = {"-static", "--static"}

    for flag in flags:
        if flag in forbidden_exact:
            raise DistutilsSetupError(
                f"{source} requested static linkage on Linux via {flag}. "
                "Linux dependencies must stay dynamically linked for legal/compliance reasons."
            )
        if flag.startswith(forbidden_prefixes):
            raise DistutilsSetupError(
                f"{source} requested static linkage on Linux via {flag}. "
                "Linux dependencies must stay dynamically linked for legal/compliance reasons."
            )
        if flag.endswith(".a") or ".a." in flag or flag.endswith(".a)"):
            raise DistutilsSetupError(
                f"{source} referenced a static archive on Linux via {flag}. "
                "Linux dependencies must stay dynamically linked for legal/compliance reasons."
            )
        if flag.startswith("-l:") and flag.endswith(".a"):
            raise DistutilsSetupError(
                f"{source} requested a static archive on Linux via {flag}. "
                "Linux dependencies must stay dynamically linked for legal/compliance reasons."
            )


def pkg_config_flags(flag: str) -> list[str]:
    pkg_config = os.environ.get("PKG_CONFIG", "pkg-config")

    try:
        output = subprocess.check_output(
            [pkg_config, flag, *PKG_CONFIG_PACKAGES],
            cwd=ROOT,
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
    except FileNotFoundError as exc:
        raise DistutilsSetupError(
            "pkg-config is required to build axidev-io on Linux."
        ) from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or str(exc)
        raise DistutilsSetupError(
            f"pkg-config failed for {' '.join(PKG_CONFIG_PACKAGES)}: {message}"
        ) from exc

    return split_flags(output)


class AxidevIoBuildExt(build_ext):
    def build_extensions(self) -> None:
        if os.name == "nt":
            self._configure_windows()
        else:
            self._configure_linux()

        super().build_extensions()

    def _configure_windows(self) -> None:
        if self.compiler.compiler_type == "msvc":
            for executable_name in ("compiler", "compiler_so", "compiler_cxx", "cc"):
                try:
                    self.compiler.set_executable(executable_name, "clang-cl")
                except (AttributeError, ValueError):
                    pass

        for extension in self.extensions:
            extension.define_macros.extend(
                [
                    ("AXIDEV_IO_STATIC", "1"),
                    ("_CRT_SECURE_NO_WARNINGS", "1"),
                    ("max_align_t", "double"),
                ]
            )
            extension.libraries.extend(["user32", "kernel32"])
            extension.extra_compile_args.extend(["/std:c11", "/experimental:c11atomics"])

    def _configure_linux(self) -> None:
        env_ldflags = split_flags(os.environ.get("LDFLAGS"))
        env_ldlibs = split_flags(os.environ.get("LDLIBS"))
        pkg_cflags = pkg_config_flags("--cflags")
        pkg_libs = pkg_config_flags("--libs")

        ensure_linux_dynamic_link_flags(env_ldflags, "LDFLAGS")
        ensure_linux_dynamic_link_flags(env_ldlibs, "LDLIBS")
        ensure_linux_dynamic_link_flags(pkg_libs, "pkg-config --libs")

        for extension in self.extensions:
            extension.define_macros.append(("AXIDEV_IO_STATIC", "1"))
            extension.extra_compile_args.extend(
                ["-std=c11", "-Wall", "-Wextra", "-Wno-unused-parameter", *pkg_cflags]
            )
            extension.extra_link_args.extend([*pkg_libs, "-pthread"])


def make_extension() -> Extension:
    sources = [Path("csrc") / "axidev_io_module.c", *COMMON_SOURCES]

    if os.name == "nt":
        sources.extend(WINDOWS_SOURCES)
    else:
        sources.extend(LINUX_SOURCES)

    return Extension(
        name="axidev_io._native",
        sources=[path.as_posix() for path in sources],
        include_dirs=[
            (UPSTREAM_ROOT / "include").as_posix(),
            (UPSTREAM_ROOT / "src").as_posix(),
            (UPSTREAM_ROOT / "vendor").as_posix(),
        ],
        define_macros=[],
        extra_compile_args=[],
        extra_link_args=[],
        libraries=[],
        language="c",
    )


setup(
    ext_modules=[make_extension()],
    cmdclass={"build_ext": AxidevIoBuildExt},
)

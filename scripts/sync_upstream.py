from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UPSTREAM = ROOT / "vendor" / "axidev-io"
RUNTIME_VENDOR_DIR = ROOT / "src" / "axidev_io" / "vendor" / "axidev-io"


def reset_directory(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def format_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def validate_upstream_root(upstream_root: Path) -> None:
    required_paths = [
        upstream_root / "include",
        upstream_root / "src",
        upstream_root / "docs" / "consumers" / "README.md",
        upstream_root / "scripts" / "setup_uinput_permissions.sh",
        upstream_root / "vendor" / "licenses" / "stb.txt",
        upstream_root / "LICENSE",
        upstream_root / "README.md",
    ]
    missing_paths = [path for path in required_paths if not path.exists()]

    if missing_paths:
        missing_text = ", ".join(format_path(path) for path in missing_paths)
        raise SystemExit(
            "Upstream checkout is incomplete: "
            f"{missing_text}. If you are using the git submodule, run "
            "'git submodule update --init --remote vendor/axidev-io' first."
        )


def sync_upstream(upstream_root: Path) -> None:
    reset_directory(RUNTIME_VENDOR_DIR)

    for file_name in ("LICENSE", "README.md"):
        copy_file(upstream_root / file_name, RUNTIME_VENDOR_DIR / file_name)

    copy_file(
        upstream_root / "docs" / "consumers" / "README.md",
        RUNTIME_VENDOR_DIR / "docs" / "consumers" / "README.md",
    )
    copy_file(
        upstream_root / "scripts" / "setup_uinput_permissions.sh",
        RUNTIME_VENDOR_DIR / "scripts" / "setup_uinput_permissions.sh",
    )
    copy_file(
        upstream_root / "vendor" / "licenses" / "stb.txt",
        RUNTIME_VENDOR_DIR / "vendor" / "licenses" / "stb.txt",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--upstream",
        type=Path,
        default=DEFAULT_UPSTREAM,
        help="Path to the axidev-io checkout or initialized git submodule",
    )
    args = parser.parse_args()

    upstream_root = args.upstream.resolve()
    if not upstream_root.is_dir():
        raise SystemExit(f"Upstream path does not exist: {upstream_root}")

    validate_upstream_root(upstream_root)
    sync_upstream(upstream_root)
    print(f"Synced runtime vendor assets from {upstream_root}")


if __name__ == "__main__":
    main()

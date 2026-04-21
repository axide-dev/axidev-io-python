from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UPSTREAM = ROOT.parent / "axidev-io"
UPSTREAM_VENDOR_DIR = ROOT / "vendor" / "axidev-io"
RUNTIME_VENDOR_DIR = ROOT / "src" / "axidev_io" / "vendor" / "axidev-io"


def reset_directory(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, dirs_exist_ok=True)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def sync_upstream(upstream_root: Path) -> None:
    reset_directory(UPSTREAM_VENDOR_DIR)
    reset_directory(RUNTIME_VENDOR_DIR)

    for directory_name in ("include", "src", "vendor", "docs", "scripts"):
        copy_tree(upstream_root / directory_name, UPSTREAM_VENDOR_DIR / directory_name)

    for file_name in ("LICENSE", "README.md"):
        copy_file(upstream_root / file_name, UPSTREAM_VENDOR_DIR / file_name)
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
        help="Path to the local axidev-io checkout",
    )
    args = parser.parse_args()

    upstream_root = args.upstream.resolve()
    if not upstream_root.is_dir():
        raise SystemExit(f"Upstream path does not exist: {upstream_root}")

    sync_upstream(upstream_root)
    print(f"Synced upstream from {upstream_root}")


if __name__ == "__main__":
    main()

"""Create Windows and macOS icon files from the canonical application PNG."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPOSITORY_ROOT / "src" / "atomic_structure_explorer" / "assets" / "app-icon.png"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "build" / "icons"
WINDOWS_SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with Image.open(args.source) as source:
        image = source.convert("RGBA")
    if image.width != image.height:
        raise ValueError(f"Application icon must be square, got {image.size}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    windows_icon = args.output_dir / "app-icon.ico"
    macos_icon = args.output_dir / "app-icon.icns"

    image.resize((256, 256), Image.Resampling.LANCZOS).save(
        windows_icon,
        format="ICO",
        sizes=[(size, size) for size in WINDOWS_SIZES],
    )
    image.resize((1024, 1024), Image.Resampling.LANCZOS).save(macos_icon, format="ICNS")

    print(windows_icon)
    print(macos_icon)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

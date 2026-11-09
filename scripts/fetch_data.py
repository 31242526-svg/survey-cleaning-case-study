"""Download the published dataset and verify it against the archive's MD5.

The raw files are committed, so this is only needed to rebuild `data/raw/` from
scratch or to prove that the committed files are the published ones.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

RECORD = "4408243"
BASE = f"https://zenodo.org/api/records/{RECORD}/files"
FILES = {
    "Wong_Carr_Wildfire_Dataset.csv": "32e450c6c021d023b0d5c9bbc0cea94b",
    "Wong_Carr_Wildfire_Survey.pdf": "f159beba4883c87957c9977fdba35307",
}


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(name: str, destination: Path) -> None:
    url = f"{BASE}/{name}/content"
    print(f"downloading {url}")
    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
        while chunk := response.read(1024 * 1024):
            handle.write(chunk)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path("data/raw"))
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    args = parser.parse_args(argv)

    args.dest.mkdir(parents=True, exist_ok=True)
    for name, expected in FILES.items():
        destination = args.dest / name
        if destination.exists() and not args.force:
            print(f"exists   {destination} (use --force to replace)")
        else:
            download(name, destination)
        actual = md5(destination)
        if actual != expected:
            print(f"CHECKSUM MISMATCH {destination}: {actual} != {expected}")
            return 1
        print(f"verified {destination}")

    print("raw files match the published archive")
    return 0


if __name__ == "__main__":
    sys.exit(main())

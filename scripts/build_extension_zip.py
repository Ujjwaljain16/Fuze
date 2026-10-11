"""Build frontend/public/extension/fuze-web-clipper.zip from the pinned BookmarkExtension commit.

The zip is reproducible: files are read from the submodule's committed tree (not the working
copy, so local edits and CRLF checkouts never leak in), entries are sorted, timestamps are fixed
and nothing is compressed. CI runs `--check` to fail when the committed zip and the pinned
commit disagree.

    python scripts/build_extension_zip.py           # rewrite the zip
    python scripts/build_extension_zip.py --check   # exit 1 if it is out of date
"""

import argparse
import io
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTENSION = ROOT / "BookmarkExtension"
OUTPUT = ROOT / "frontend" / "public" / "extension" / "fuze-web-clipper.zip"

# What Chrome loads. Tests, docs and package.json stay out of the download.
INCLUDE_FILES = {"manifest.json", "background.js"}
INCLUDE_DIRS = ("content/", "lib/", "options/", "popup/", "icons/")
EXCLUDE_SUFFIXES = (".md",)
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def _git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(EXTENSION), *args], check=True, capture_output=True).stdout


def packaged_paths(commit: str) -> list:
    names = _git("ls-tree", "-r", "--name-only", commit).decode().splitlines()
    keep = [n for n in names
            if (n in INCLUDE_FILES or n.startswith(INCLUDE_DIRS)) and not n.endswith(EXCLUDE_SUFFIXES)]
    if "manifest.json" not in keep:
        sys.exit(f"manifest.json is missing from BookmarkExtension at {commit}")
    return sorted(keep)


def build(commit: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for path in packaged_paths(commit):
            info = zipfile.ZipInfo(path, date_time=FIXED_TIME)
            info.external_attr = 0o644 << 16
            info.create_system = 3  # Unix, so the attributes mean the same everywhere
            zf.writestr(info, _git("cat-file", "blob", f"{commit}:{path}"))
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if the committed zip is out of date")
    args = parser.parse_args()

    if not (EXTENSION / ".git").exists():
        sys.exit("BookmarkExtension is not checked out: run `git submodule update --init`")
    commit = _git("rev-parse", "HEAD").decode().strip()
    data = build(commit)

    if args.check:
        current = OUTPUT.read_bytes() if OUTPUT.exists() else b""
        if current != data:
            print(f"{OUTPUT.relative_to(ROOT)} does not match BookmarkExtension {commit[:7]}. "
                  "Run: python scripts/build_extension_zip.py", file=sys.stderr)
            return 1
        print(f"Extension zip matches BookmarkExtension {commit[:7]}")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(data)
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(data) // 1024} KB) from BookmarkExtension {commit[:7]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

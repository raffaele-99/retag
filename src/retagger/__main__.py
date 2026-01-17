#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from retagger import core


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convert Artist 'Main/Feat' -> Artist=Main, Title+='(ft. Feat...)', excluding remixers in title"
    )
    ap.add_argument("root", type=Path, help="Folder to scan (recursive)")
    ap.add_argument("--delimiter", default="/", help="Artist delimiter (default: /)")
    ap.add_argument(
        "--write", action="store_true", help="Actually write changes (otherwise dry-run)"
    )
    ap.add_argument(
        "--set-albumartist",
        action="store_true",
        help="Set albumartist to main artist",
    )
    args = ap.parse_args()

    root: Path = args.root
    if not root.exists():
        print(f"Path not found: {root}")
        return 1

    mp3s = core.get_mp3_files(root)
    if not mp3s:
        print("No mp3 files found.")
        return 0

    config = core.RetagConfig(
        delimiter=args.delimiter,
        write=args.write,
        set_albumartist=args.set_albumartist,
    )

    changed_count = 0

    for p in mp3s:
        result = core.process_file(p, config)

        if result:
            if result.error:
                print(f"[skip] {result.path} (couldn't read tags: {result.error})")
                continue

            if result.changed:
                print(f"\n{result.path}")
                print(f"  Artist: {result.old_artist}  ->  {result.new_artist}")
                print(f"  Title : {result.old_title}  ->  {result.new_title}")
                changed_count += 1

    print(
        f"\nDone. Files matched/changed: {changed_count} (write={'yes' if args.write else 'no'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

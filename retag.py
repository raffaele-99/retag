#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError


FEAT_IN_TITLE_RE = re.compile(r"\((?:ft\.|feat\.|featuring)\s+.+?\)", re.IGNORECASE)


def ensure_id3_header(mp3_path: Path) -> None:
    try:
        ID3(mp3_path)
    except ID3NoHeaderError:
        tags = ID3()
        tags.save(mp3_path)


def norm(s: str) -> str:
    # Lowercase, remove accents, collapse punctuation to spaces, collapse whitespace.
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.casefold()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def has_feat_in_title(title: str) -> bool:
    return bool(FEAT_IN_TITLE_RE.search(title))


def looks_like_remixer_in_title(title: str, artist_name: str) -> bool:
    """
    True if the artist name appears in the title *as a remixer*, i.e.
    '... <artist> ... remix' (case/diacritic-insensitive).
    Examples caught:
      - "(Zedd Remix)"
      - "Tiesto's Club Life Remix"
      - "(Skrillex & Zedd Remix)"
    """
    t = norm(title)
    a = norm(artist_name)
    if not a:
        return False

    # Find "remix" and see if artist name occurs shortly before it (within ~6 words).
    words = t.split()
    try:
        remix_i = words.index("remix")
    except ValueError:
        return False

    window = " ".join(words[max(0, remix_i - 6):remix_i])  # up to 6 words before "remix"
    return a in window


def pick_main_artist(tags: EasyID3, artists: list[str]) -> str:
    # Prefer albumartist/band when present (common for albums where Artist includes remixers, etc.)
    for key in ("albumartist", "band"):
        v = (tags.get(key, [""])[0] or "").strip()
        if v:
            return v
    return artists[0] if artists else ""


def unique_keep_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for x in items:
        k = norm(x)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convert Artist 'Main/Feat' -> Artist=Main, Title+='(ft. Feat...)', excluding remixers in title"
    )
    ap.add_argument("root", type=Path, help="Folder to scan (recursive)")
    ap.add_argument("--delimiter", default="/", help="Artist delimiter (default: /)")
    ap.add_argument("--write", action="store_true", help="Actually write changes (otherwise dry-run)")
    ap.add_argument("--set-albumartist", action="store_true", help="Set albumartist to main artist")
    args = ap.parse_args()

    root: Path = args.root
    if not root.exists():
        raise SystemExit(f"Path not found: {root}")

    mp3s = sorted(root.rglob("*.mp3"))
    if not mp3s:
        print("No mp3 files found.")
        return 0

    changed = 0

    for p in mp3s:
        try:
            ensure_id3_header(p)
            tags = EasyID3(p)
        except Exception as e:
            print(f"[skip] {p} (couldn't read tags: {e})")
            continue

        artist_raw = (tags.get("artist", [""])[0] or "").strip()
        if not artist_raw or args.delimiter not in artist_raw:
            continue

        artists = [s.strip() for s in artist_raw.split(args.delimiter) if s.strip()]
        if len(artists) < 2:
            continue

        title = (tags.get("title", [p.stem])[0] or p.stem).strip()

        main_artist = pick_main_artist(tags, artists).strip()
        if not main_artist:
            continue

        # Featured = everyone except main
        featured = [a for a in artists if norm(a) != norm(main_artist)]
        featured = unique_keep_order(featured)

        # Drop featured artists who are credited as remixers in the title
        featured = [a for a in featured if not looks_like_remixer_in_title(title, a)]

        new_artist = main_artist
        new_title = title

        if featured and not has_feat_in_title(title):
            new_title = f"{title} (ft. {', '.join(featured)})"

        # If no featured left after filtering, still normalize Artist to main.
        would_change = (new_artist != artist_raw) or (new_title != title)
        if not would_change:
            continue

        print(f"\n{p}")
        print(f"  Artist: {artist_raw}  ->  {new_artist}")
        print(f"  Title : {title}  ->  {new_title}")

        if args.write:
            tags["artist"] = [new_artist]
            tags["title"] = [new_title]
            if args.set_albumartist:
                tags["albumartist"] = [new_artist]
            tags.save(p, v2_version=3)

        changed += 1

    print(f"\nDone. Files matched/changed: {changed} (write={'yes' if args.write else 'no'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


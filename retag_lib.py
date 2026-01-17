from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError

FEAT_IN_TITLE_RE = re.compile(r"\((?:ft\.|feat\.|featuring)\s+.+?\)", re.IGNORECASE)


@dataclass
class RetagConfig:
    delimiter: str = "/"
    write: bool = False
    set_albumartist: bool = False


@dataclass
class ChangeResult:
    path: Path
    old_artist: str
    new_artist: str
    old_title: str
    new_title: str
    changed: bool
    error: Optional[str] = None


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

    window = " ".join(words[max(0, remix_i - 6) : remix_i])  # up to 6 words before "remix"
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


def get_mp3_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("*.mp3"))


def process_file(path: Path, config: RetagConfig) -> Optional[ChangeResult]:
    try:
        ensure_id3_header(path)
        tags = EasyID3(path)
    except Exception as e:
        return ChangeResult(
            path=path,
            old_artist="",
            new_artist="",
            old_title="",
            new_title="",
            changed=False,
            error=str(e),
        )

    artist_raw = (tags.get("artist", [""])[0] or "").strip()
    if not artist_raw or config.delimiter not in artist_raw:
        return None

    artists = [s.strip() for s in artist_raw.split(config.delimiter) if s.strip()]
    if len(artists) < 2:
        return None

    title = (tags.get("title", [path.stem])[0] or path.stem).strip()

    main_artist = pick_main_artist(tags, artists).strip()
    if not main_artist:
        return None

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
        return None

    if config.write:
        tags["artist"] = [new_artist]
        tags["title"] = [new_title]
        if config.set_albumartist:
            tags["albumartist"] = [new_artist]
        tags.save(path, v2_version=3)

    return ChangeResult(
        path=path,
        old_artist=artist_raw,
        new_artist=new_artist,
        old_title=title,
        new_title=new_title,
        changed=True,
    )

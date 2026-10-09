"""Slide splitting and strict picture/diagram detection (theme-agnostic).

Logic ported verbatim from the legacy md2pdf. Detection is deliberately STRICT:
a slide qualifies as a picture or diagram slide only when it contains exactly
one ``# Title`` plus exactly one image / diagram fence and nothing else.
"""
from __future__ import annotations

import re

# One Markdown image token: ![alt](path "optional title"). The path captures a
# run of non-space chars (optionally quoted title is dropped). Relative and
# absolute paths are both captured verbatim.
_IMAGE_RE = re.compile(r'^!\[(?P<alt>.*?)\]\((?P<path>\S+?)(?:\s+"[^"]*")?\)$')
_H1_RE = re.compile(r'^#\s+(?P<title>.+?)\s*$')
_SLIDE_BREAK_RE = re.compile(r'^-{3,}\s*$')

_FENCE_RE = re.compile(r'^(?P<fence>`{3,}|~{3,})(?P<info>.*)$')
_DIAGRAM_LANGS = ("mermaid", "d2")


def split_slides(body: str) -> list[str]:
    """Split a (front-matter-stripped) Markdown body into slide chunks.

    Slides are separated by a line containing only ``---`` (three or more
    dashes). Returned chunks retain their inner line breaks but not the
    separators. Leading/trailing all-blank chunks are preserved as-is so the
    caller can re-join faithfully.
    """
    chunks: list[str] = []
    current: list[str] = []
    for line in body.splitlines():
        if _SLIDE_BREAK_RE.match(line):
            chunks.append("\n".join(current))
            current = []
        else:
            current.append(line)
    chunks.append("\n".join(current))
    return chunks


def match_picture_slide(chunk: str) -> dict | None:
    """Return ``{title, alt, path}`` iff ``chunk`` is a strict title+picture slide.

    Strict rule: exactly one ``# Heading`` line and exactly one Markdown image,
    with no other non-blank content (no bullets, prose, tables, or a second
    image). Otherwise return ``None``.
    """
    title: str | None = None
    alt: str | None = None
    path: str | None = None
    for raw in chunk.splitlines():
        line = raw.strip()
        if not line:
            continue
        hm = _H1_RE.match(line)
        if hm:
            if title is not None:
                return None  # second heading -> not a simple picture slide
            title = hm.group("title").strip()
            continue
        im = _IMAGE_RE.match(line)
        if im:
            if path is not None:
                return None  # second image -> disqualify
            alt = im.group("alt").strip()
            path = im.group("path").strip()
            continue
        # Any other non-blank content disqualifies the slide.
        return None
    if title is None or path is None:
        return None
    return {"title": title, "alt": alt or "", "path": path}


def match_diagram_slide(chunk: str) -> dict | None:
    """Return ``{title, lang, source}`` iff ``chunk`` is a strict title+diagram slide.

    Strict rule: exactly one ``# Heading`` line and exactly one fenced code
    block whose info string is the lone token ``mermaid`` or ``d2``, with no
    other non-blank content (no prose, bullets, tables, a second fence, or a
    non-diagram fence). The fenced block body is captured verbatim (indentation
    and inner newlines preserved). Otherwise return ``None``.

    Fence info-string rules: trailing whitespace on the info string is
    stripped; only an exact lone language token is accepted; info strings
    carrying extra parameters (e.g. ``d2 layout=elk``) are rejected.
    """
    title: str | None = None
    lang: str | None = None
    source: str | None = None

    lines = chunk.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue
        # Heading?
        hm = _H1_RE.match(stripped)
        if hm:
            if title is not None:
                return None  # second heading -> disqualify
            title = hm.group("title").strip()
            i += 1
            continue
        # Fence open? (fence markers are matched on the raw, left-trimmed line)
        fm = _FENCE_RE.match(raw.lstrip())
        if fm:
            if source is not None:
                return None  # second fence -> disqualify
            info = fm.group("info").strip()
            if info not in _DIAGRAM_LANGS:
                return None  # non-diagram fence or extra info params
            fence = fm.group("fence")
            lang = info
            # Collect verbatim body until the matching closing fence.
            body_lines: list[str] = []
            i += 1
            closed = False
            while i < n:
                line = lines[i]
                close = line.lstrip()
                if close.startswith(fence) and close[len(fence):].strip() == "":
                    closed = True
                    i += 1
                    break
                body_lines.append(line)
                i += 1
            if not closed:
                return None  # unterminated fence -> not a strict diagram slide
            source = "\n".join(body_lines)
            continue
        # Any other non-blank content disqualifies the slide.
        return None

    if title is None or lang is None or source is None:
        return None
    return {"title": title, "lang": lang, "source": source}


def _chunk_has_diagram_fence(chunk: str) -> bool:
    """True if ``chunk`` opens a ``mermaid`` or ``d2`` fence anywhere."""
    for raw in chunk.splitlines():
        fm = _FENCE_RE.match(raw.lstrip())
        if fm:
            # Warning-detection uses the FIRST whitespace-delimited token so a
            # near-miss fence like ```d2 layout=elk (which match_diagram_slide
            # rejects) still trips the disqualified-slide warning. This does not
            # affect strict matching, which still requires a lone token.
            tokens = fm.group("info").strip().split()
            if tokens and tokens[0] in _DIAGRAM_LANGS:
                return True
    return False

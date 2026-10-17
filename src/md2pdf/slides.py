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

# A two-column region delimiter: a line that is only three-or-more colons,
# tolerating up to three leading spaces (CommonMark fence-indent tolerance;
# critique E8). Matched only OUTSIDE inner code fences (see _scan_code_fences).
_COLON_FENCE_RE = re.compile(r'^\s{0,3}:{3,}\s*$')


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



# --- Two-column (picture + text) slides ------------------------------------
#
# A two-column slide is `# Title` followed by a body that OPENS (first non-blank
# line after the title) with a `:::` delimiter. The body carries exactly three
# `:::` delimiter lines (open / separator / close) framing two regions. The
# feature is strictly opt-in: a slide that does not open with `:::` is returned
# as `None` and handled by the ordinary/picture/diagram paths — so an ordinary
# slide carrying a Pandoc fenced div (e.g. `::: notes`) whose closing bare `:::`
# matches `_COLON_FENCE_RE` is never hijacked (critique task-level P1 / R6).


def _two_column_error(title: str | None, snippet: str, message: str) -> SystemExit:
    """Build a loud, slide-identifying ``SystemExit`` for a bad two-column slide."""
    ident = f"slide '{title}'" if title else f"slide near '{snippet.strip()[:40]}'"
    return SystemExit(f"ERROR: {ident}: {message}")


def _diagram_fence_only(region_lines: list[str]) -> tuple[str, str] | None:
    """Return ``(lang, source)`` iff ``region_lines`` is one lone diagram fence.

    The region must contain exactly one fenced block whose info string is the
    lone token ``mermaid`` or ``d2`` and no other non-blank content. Mirrors
    ``match_diagram_slide``'s single-fence rule, scoped to a column region.
    """
    lang: str | None = None
    source: str | None = None
    i = 0
    n = len(region_lines)
    while i < n:
        raw = region_lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue
        fm = _FENCE_RE.match(raw.lstrip())
        if fm and source is None:
            info = fm.group("info").strip()
            if info not in _DIAGRAM_LANGS:
                return None
            fence = fm.group("fence")
            lang = info
            body_lines: list[str] = []
            i += 1
            closed = False
            while i < n:
                line = region_lines[i]
                close = line.lstrip()
                if close.startswith(fence) and close[len(fence):].strip() == "":
                    closed = True
                    i += 1
                    break
                body_lines.append(line)
                i += 1
            if not closed:
                return None
            source = "\n".join(body_lines)
            continue
        # Any non-blank content that is not the single diagram fence.
        return None
    if lang is None or source is None:
        return None
    return lang, source


def classify_region(region: str) -> tuple:
    """Classify a column region's render mode.

    Returns one of:

    * ``("image", alt, path)`` — the region's sole non-blank content is one
      Markdown image.
    * ``("diagram", lang, source)`` — the region's sole non-blank content is one
      lone ``mermaid``/``d2`` fence.
    * ``("markdown", region)`` — anything else (bullets, prose, tables, mixed,
      or an image/diagram accompanied by other content); rendered by pandoc.
    """
    lines = region.splitlines()
    non_blank = [ln for ln in lines if ln.strip()]
    # Lone image?
    if len(non_blank) == 1:
        im = _IMAGE_RE.match(non_blank[0].strip())
        if im:
            return ("image", im.group("alt").strip(), im.group("path").strip())
    # Lone diagram fence?
    diag = _diagram_fence_only(lines)
    if diag is not None:
        return ("diagram", diag[0], diag[1])
    return ("markdown", region)


def match_two_column_slide(chunk: str) -> dict | None:
    """Return ``{title, left, right}`` iff ``chunk`` is a valid two-column slide.

    Tri-state contract:

    * returns a dict when ``chunk`` is a well-formed two-column slide;
    * returns ``None`` when ``chunk`` is *not* a two-column slide (its body does
      not open, after the ``# Title``, with a ``:::`` delimiter) — the caller
      handles it via the ordinary/picture/diagram paths (R6);
    * raises ``SystemExit`` (fail-loud, R5) when the slide opted in but violates
      the grammar.
    """
    lines = chunk.splitlines()

    # Parse the first heading up front for identification. The `# Title` MUST be
    # the strict first non-blank line of the chunk (as in match_picture_slide /
    # match_diagram_slide). If any non-blank content precedes it, this is not a
    # two-column slide — return None so the slide is handled untouched and its
    # pre-heading content is never silently dropped (code-review HIGH, R1/R6).
    title: str | None = None
    first_non_blank = ""
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        first_non_blank = s
        hm = _H1_RE.match(s)
        if hm:
            title = hm.group("title").strip()
        break  # only inspect the first non-blank line here
    if title is None:
        return None

    # Scan the body (after the first heading line) fence-aware, recording the
    # first non-blank post-title line and every top-level `:::` delimiter.
    in_fence = False
    fence_marker = ""
    fence_open_info = ""
    seen_title = False
    first_body_non_blank_is_delim: bool | None = None
    delim_indices: list[int] = []
    headings = 0

    for idx, raw in enumerate(lines):
        stripped = raw.strip()
        if in_fence:
            close = raw.lstrip()
            if close.startswith(fence_marker) and close[len(fence_marker):].strip() == "":
                in_fence = False
            continue
        if not stripped:
            continue
        hm = _H1_RE.match(stripped)
        if hm:
            headings += 1
            seen_title = True
            continue
        # Opening a code fence?
        fm = _FENCE_RE.match(raw.lstrip())
        if fm:
            in_fence = True
            fence_marker = fm.group("fence")
            fence_open_info = fm.group("info").strip()
            if first_body_non_blank_is_delim is None and seen_title:
                first_body_non_blank_is_delim = False
            continue
        is_delim = bool(_COLON_FENCE_RE.match(raw))
        if first_body_non_blank_is_delim is None and seen_title:
            first_body_non_blank_is_delim = is_delim
        if is_delim:
            delim_indices.append(idx)

    # Opt-in trigger: the slide is two-column IFF the first non-blank line after
    # the title is a `:::` delimiter. Otherwise it is not a two-column slide.
    if not seen_title or not first_body_non_blank_is_delim:
        return None

    snippet = first_non_blank

    # Fail-loud ordering: an unterminated inner code fence is diagnosed BEFORE
    # the delimiter-count check so the message is not a misleading
    # "expected 3 delimiters" (critique task-level E2).
    if in_fence:
        lang = fence_open_info or "code"
        raise _two_column_error(
            title, snippet,
            f"unterminated inner code fence ('{lang}') inside the two-column body",
        )

    if headings > 1:
        raise _two_column_error(
            title, snippet, "a two-column slide must have exactly one '# Title'"
        )

    if len(delim_indices) != 3:
        raise _two_column_error(
            title, snippet,
            f"a two-column body needs exactly three ':::' delimiter lines "
            f"(open / separator / close), found {len(delim_indices)}",
        )

    open_i, sep_i, close_i = delim_indices
    left_lines = lines[open_i + 1:sep_i]
    right_lines = lines[sep_i + 1:close_i]
    trailing = lines[close_i + 1:]

    if any(ln.strip() for ln in trailing):
        raise _two_column_error(
            title, snippet,
            "non-blank content after the closing ':::' delimiter is not allowed",
        )
    if not any(ln.strip() for ln in left_lines):
        raise _two_column_error(title, snippet, "the left column region is empty")
    if not any(ln.strip() for ln in right_lines):
        raise _two_column_error(title, snippet, "the right column region is empty")

    return {
        "title": title or "",
        "left": "\n".join(left_lines).strip("\n"),
        "right": "\n".join(right_lines).strip("\n"),
    }

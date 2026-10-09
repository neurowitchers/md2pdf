"""Front-matter parsing (theme-agnostic).

Ported from the legacy md2pdf with two spec-mandated additions:

* All scalar values are coerced to ``str`` before escaping/templating so that
  unquoted YAML scalars (e.g. ``wp: 2``, ``date: 2026-10-09``) do not surface
  as ``int``/``date`` and break downstream LaTeX escaping (critique E8).
* An optional ``theme`` key is recognised and parsed like any other field; the
  engine consumes it for theme resolution (critique P2). No special handling is
  required here beyond parsing it into the returned mapping.
"""
from __future__ import annotations

import re

# A front-matter key: value line. Keys are ``[A-Za-z0-9_-]+``; this already
# admits the optional ``theme`` key (critique P2).
_FM_LINE_RE = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$")


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Return ``(fields, body_without_front_matter)``.

    Minimal, line-based ``key: value`` parsing (matching the legacy tool).
    Every parsed value is coerced to ``str`` (critique E8). An optional
    ``theme`` key is parsed like any other field (critique P2).
    """
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not m:
        return {}, text
    fm_block, body = m.group(1), text[m.end():]
    fields: dict[str, str] = {}
    for line in fm_block.splitlines():
        line = line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = _FM_LINE_RE.match(line)
        if km:
            key = km.group(1).strip()
            val = km.group(2).strip().strip('"').strip("'")
            # Coerce to str defensively (critique E8). The minimal parser
            # already yields str, but this makes the contract explicit and
            # robust against future changes.
            fields[key] = str(val)
    return fields, body

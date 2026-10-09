"""LaTeX helpers (theme-agnostic). Ported verbatim from the legacy md2pdf."""
from __future__ import annotations

from pathlib import Path


def latex_path(p: Path) -> str:
    """Normalise a path to forward slashes for LaTeX/graphicx."""
    return str(p).replace("\\", "/")


def latex_escape(s: str) -> str:
    """Escape LaTeX specials in a plain field value."""
    s = str(s)
    repl = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(c, c) for c in s)

"""Diagram rendering (theme-agnostic).

Ported from the legacy md2pdf. ``render_diagram`` renders a mermaid/d2 source
to an image (content-addressed cache, white background, loud failures,
partial-file cleanup, zero-byte re-render). ``_resolve_diagram_binary`` locates
the renderer executable cross-platform (critique E6): it probes the plain name
and a platform-appropriate suffix (``.exe`` on Windows, extensionless on POSIX)
on PATH and in the known fallback locations (``~/go/bin``, ``~/.cargo/bin``).
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

# Per-language renderer metadata: PATH binary base name, the fallback install
# directory, and an actionable install hint.
_RENDERERS = {
    "d2": {
        "name": "d2",
        "fallback_dir": Path.home() / "go" / "bin",
        "hint": "go install oss.terrastruct.com/d2@latest",
    },
    "mermaid": {
        "name": "mmdr",
        "fallback_dir": Path.home() / ".cargo" / "bin",
        "hint": "cargo install mmdr",
    },
}


def _candidate_names(base: str) -> list[str]:
    """Return platform-appropriate executable names to probe for ``base``.

    On Windows, probe both the plain name and ``<base>.exe``. On POSIX, probe
    the extensionless plain name. The plain name is listed first so a
    PATH-resolved match is preferred (critique E6).
    """
    if os.name == "nt":
        return [base, f"{base}.exe"]
    return [base]


def _resolve_diagram_binary(lang: str) -> str:
    """Resolve the renderer executable for ``lang``, or fail loudly.

    Probes each candidate name (plain + platform suffix) on PATH via
    ``shutil.which``; then checks the known fallback directory for each
    candidate. Raises ``SystemExit`` with an actionable install hint if the CLI
    cannot be found (critique E6).
    """
    meta = _RENDERERS.get(lang)
    if meta is None:  # pragma: no cover - guarded by caller
        raise SystemExit(f"ERROR: unknown diagram language '{lang}'")

    base = meta["name"]
    fallback_dir: Path = meta["fallback_dir"]
    hint = meta["hint"]
    candidates = _candidate_names(base)

    # 1) PATH lookup for each candidate name.
    for cand in candidates:
        found = shutil.which(cand)
        if found:
            return found

    # 2) Known fallback directory, each candidate name.
    probed: list[Path] = []
    for cand in candidates:
        fb = fallback_dir / cand
        probed.append(fb)
        if fb.exists():
            return str(fb)

    locations = ", ".join(str(p) for p in probed)
    raise SystemExit(
        f"ERROR: diagram CLI '{base}' not found for a {lang} slide.\n"
        f"Install it with: {hint}\n"
        f"(looked on PATH and at {locations})"
    )


def render_diagram(lang: str, source: str, out_dir: Path, slide_title: str) -> Path:
    """Render ``source`` (mermaid/d2) to an image in ``out_dir``; return its path.

    Filename is content-addressed and language-namespaced:
    ``diagram_{lang}_{sha256(source)[:16]}.{ext}`` (``.pdf`` for d2, ``.png``
    for mermaid). An existing non-empty output is returned immediately
    (idempotent); a zero-byte/partial cache file is re-rendered.

    Fails loudly (``SystemExit``) naming the tool and the offending slide on a
    missing CLI, a non-zero exit (decoded stderr), or a render timeout.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = "pdf" if lang == "d2" else "png"
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    out_file = out_dir / f"diagram_{lang}_{digest}.{ext}"
    # Only trust the cache if the file is non-empty; a zero-byte/partial file
    # from a prior aborted run must be re-rendered, not returned as-is.
    if out_file.exists() and out_file.stat().st_size > 0:
        return out_file

    binary = _resolve_diagram_binary(lang)
    src_ext = "d2" if lang == "d2" else "mmd"
    src_file = out_dir / f"diagram_{lang}_{digest}.{src_ext}"
    src_file.write_text(source, encoding="utf-8")

    if lang == "d2":
        cmd = [binary, "--theme", "0", "--browser", "0",
               str(src_file), str(out_file)]
    else:  # mermaid via mmdr
        # mmdr 0.3.1 has no background flag; it already rasterises PNGs on an
        # OPAQUE WHITE background by default, satisfying the white-background
        # requirement without a flag the installed binary rejects. -w 2400
        # gives high resolution without -H (preserves intrinsic aspect ratio).
        cmd = [binary, "-i", str(src_file), "-o", str(out_file),
               "-e", "png", "-w", "2400", "-t", "default"]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=30, stdin=subprocess.DEVNULL
        )
    except subprocess.TimeoutExpired:
        out_file.unlink(missing_ok=True)
        raise SystemExit(
            f"ERROR: {lang} rendering timed out (>30s) for slide "
            f"'{slide_title}'. The diagram source may be too large or the "
            f"renderer may be hung."
        )
    if proc.returncode != 0:
        out_file.unlink(missing_ok=True)
        diagnostic = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        tool = "d2" if lang == "d2" else "mmdr"
        raise SystemExit(
            f"ERROR: {tool} failed to render {lang} slide '{slide_title}' "
            f"(exit {proc.returncode}):\n{diagnostic}"
        )
    return out_file

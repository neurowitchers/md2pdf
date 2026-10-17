"""Engine: assemble the pandoc/xelatex build pipeline against a loaded Theme.

The engine is theme-agnostic: theme-specific presentation
(``THEME``/``ASSETS``/``REQUIRED_FIELDS``/``FONT_SCALES``/``title_frame_tex``/
``thankyou_frame_tex``) is supplied by a :class:`md2pdf.theme.Theme`.

Preserved theme-agnostic behaviour:

* Strict picture/diagram slide rewriting to fit-to-frame raw LaTeX.
* Diagram-dir lifecycle: a build-scoped temp dir, or a persistent
  ``<stem>_diagrams`` directory beside the output under ``--keep-tex``.
* pandoc ``--resource-path`` for the input dir AND the diagram dir, plus a
  brace-protected, forward-slash-normalised ``\\graphicspath`` carrying the
  diagram dir and the theme assets dir (critique E9).
* ``aspectratio=169`` / ``classoption=t``.
* ``--keep-tex`` writes the intermediate ``.tex``.

New (critique E4): on a pandoc/xelatex failure, the intermediate artifacts
(``body.md``, ``preamble.tex``, ``theme.tex``, ``before.tex``, ``after.tex``)
are copied to a persistent diagnostic directory and their paths printed to
stderr before raising, so XeLaTeX line numbers are inspectable without a rerun.

The caption colour for picture/diagram captions is theme-agnostic: every theme
preamble defines a ``captioncolor`` colour (``\\colorlet{captioncolor}{...}``),
so the engine emits ``\\color{captioncolor}`` without knowing the theme palette.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from .diagrams import render_diagram
from .latex import latex_escape, latex_path
from .slides import (
    _chunk_has_diagram_fence,
    classify_region,
    match_diagram_slide,
    match_picture_slide,
    match_two_column_slide,
    split_slides,
)
from .theme import Theme, load_theme


def _fit_image_tex(
    width_expr: str,
    height_expr: str,
    alt: str,
    path: str,
    *,
    vcenter: bool,
) -> str:
    r"""Raw-LaTeX fit-to-box image block, shared by whole-slide and column fits.

    ``vcenter=True`` wraps the image in ``\vfill … \vfill`` and a ``center``
    environment to centre it vertically in the available space (whole-slide
    picture/diagram frames). ``vcenter=False`` emits a *top-aligned* block using
    the ``\centering`` **declaration** (not the ``center`` environment, whose
    ``trivlist`` ``\topsep`` padding would push a column image below its
    companion text — critique task-level E1); it carries no ``\vfill``.

    If ``alt`` is non-empty it renders as a small centred caption beneath the
    image, in the theme-defined ``captioncolor``.
    """
    img = latex_path(Path(path)) if path else path
    caption = ""
    if alt.strip():
        caption = (
            r"\vskip0.4em{\small\color{captioncolor}" + latex_escape(alt) + r"\par}"
            + "\n"
        )
    graphic = (
        r"\includegraphics[width=" + width_expr + r",height=" + height_expr
        + r",keepaspectratio]{" + img + r"}\par" + "\n"
    )
    if vcenter:
        return (
            r"\vfill" + "\n"
            r"\begin{center}" + "\n"
            + graphic
            + caption
            + r"\end{center}" + "\n"
            r"\vfill" + "\n"
        )
    # Top-aligned column variant: \centering declaration, no \vfill, no center env.
    return (
        r"{\centering" + "\n"
        + graphic
        + caption
        + r"}" + "\n"
    )


def picture_body_tex(alt: str, path: str) -> str:
    """Raw-LaTeX *frame body* for a strict title+picture / diagram slide.

    Emits only the content that sits inside the frame pandoc opens for the
    ``# Title`` heading (so the branded title band is preserved). The image is
    scaled to fit the area below the title (width/height bounded, aspect ratio
    preserved) and centred both horizontally and vertically. If ``alt`` is
    non-empty it renders as a small centred caption beneath the image, in the
    theme-defined ``captioncolor``.

    Relative paths stay relative so xelatex resolves them against the pandoc
    run directory (the input ``.md`` folder) or the diagram dir on
    ``--resource-path``/``\\graphicspath``; absolute paths pass through.
    """
    return _fit_image_tex(
        r"\textwidth", r"0.78\textheight", alt, path, vcenter=True
    )


def column_body_tex(alt: str, path: str) -> str:
    r"""Raw-LaTeX fit-to-column image block for a two-column slide region.

    Scoped to ``\columnwidth`` with a slightly reduced height bound
    (``0.72\textheight``) so a multi-line caption cannot overflow a 16:9 frame
    (critique E6). Top-aligned (no ``\vfill``) so the image lines up with the
    companion column's text (critique P2 / task-level E1).
    """
    return _fit_image_tex(
        r"\columnwidth", r"0.72\textheight", alt, path, vcenter=False
    )


def _column_region_tex(
    region: str, diagram_dir: Path | None, title: str
) -> str:
    r"""Lower one two-column region to the markup placed inside its ``.column``.

    A region whose sole non-blank content is one image or one lone
    ``mermaid``/``d2`` fence is rewritten to a ``\columnwidth``-fit raw-LaTeX
    block (``column_body_tex``); a diagram region is first rendered via
    ``render_diagram`` and emitted by relative filename. Any other region is
    returned verbatim so pandoc renders its Markdown inside the column.
    """
    kind, *rest = classify_region(region)
    if kind == "image":
        alt, path = rest
        return "```{=latex}\n" + column_body_tex(alt, path) + "```"
    if kind == "diagram":
        lang, source = rest
        if diagram_dir is None:
            raise SystemExit(
                "ERROR: diagram region encountered but no diagram output "
                "directory was provided (internal error)."
            )
        img_path = render_diagram(lang, source, diagram_dir, title)
        return "```{=latex}\n" + column_body_tex("", img_path.name) + "```"
    # markdown: pandoc renders it inside the column.
    return region


def preprocess_body(body: str, diagram_dir: Path | None = None) -> str:
    """Rewrite strict title+picture and title+diagram slides for fit-to-frame.

    Theme-agnostic; identical in behaviour to the legacy implementation. For a
    strict picture slide the ``# Title`` heading is kept as Markdown (pandoc
    opens the normal branded frame with its title band) and the image is
    replaced by a pandoc raw-LaTeX block that centres the image to fit the
    frame. For a strict diagram slide the fenced source is rendered to an image
    under ``diagram_dir`` and emitted the same way using a RELATIVE filename.

    A chunk that carries a ``mermaid``/``d2`` fence but is not a strict diagram
    slide triggers a non-fatal stderr warning. All other chunks are untouched.
    Chunks are re-joined with ``---`` slide breaks so pandoc's splitting is
    unchanged.
    """
    out_parts: list[str] = []
    for chunk in split_slides(body):
        two_col = match_two_column_slide(chunk)
        if two_col is not None:
            left_block = _column_region_tex(
                two_col["left"], diagram_dir, two_col["title"]
            )
            right_block = _column_region_tex(
                two_col["right"], diagram_dir, two_col["title"]
            )
            out_parts.append(
                "# " + two_col["title"] + "\n\n"
                ":::::: {.columns .onlytextwidth align=top}\n"
                ':::: {.column width="50%"}\n'
                + left_block + "\n"
                "::::\n"
                ':::: {.column width="50%"}\n'
                + right_block + "\n"
                "::::\n"
                "::::::"
            )
            continue
        pic = match_picture_slide(chunk)
        if pic is not None:
            body_tex = picture_body_tex(pic["alt"], pic["path"])
            out_parts.append(
                "# " + pic["title"] + "\n\n```{=latex}\n" + body_tex + "```"
            )
            continue
        diag = match_diagram_slide(chunk)
        if diag is not None:
            if diagram_dir is None:
                raise SystemExit(
                    "ERROR: diagram slide encountered but no diagram output "
                    "directory was provided (internal error)."
                )
            img_path = render_diagram(
                diag["lang"], diag["source"], diagram_dir, diag["title"]
            )
            # Emit a RELATIVE filename; diagram_dir is on pandoc's
            # --resource-path and the LaTeX \graphicspath, so paths with spaces
            # resolve safely (critique E9).
            body_tex = picture_body_tex("", img_path.name)
            out_parts.append(
                "# " + diag["title"] + "\n\n```{=latex}\n" + body_tex + "```"
            )
            continue
        # Not a strict diagram slide: warn if it nonetheless carries a
        # mermaid/d2 fence, so authors are not left guessing.
        if _chunk_has_diagram_fence(chunk):
            sys.stderr.write(
                "WARNING: a slide contains a ```mermaid or ```d2 fence but is "
                "not a strict diagram slide (needs exactly one '# Title' plus "
                "exactly one diagram fence and nothing else). It will render "
                "as a verbatim code block, not an auto-rendered diagram.\n"
            )
        out_parts.append(chunk)
    joined = "\n\n---\n\n".join(part.strip("\n") for part in out_parts)
    return joined + "\n"


def _graphicspath(dirs: list[Path]) -> str:
    r"""Return a brace-protected, forward-slash-normalised ``\graphicspath``.

    Each directory is wrapped in its own ``{...}`` group with a trailing slash
    so paths containing spaces resolve under XeLaTeX (critique E9/E17). Empty
    or non-existent dirs are skipped.
    """
    groups = []
    for d in dirs:
        if d is None:
            continue
        g = latex_path(d)
        if not g.endswith("/"):
            g += "/"
        groups.append("{" + g + "}")
    return r"\graphicspath{" + "".join(groups) + "}" + "\n"


def _preserve_diagnostics(artifacts: dict[str, Path], output: Path) -> Path:
    """Copy intermediate build artifacts to a persistent diagnostic dir (E4).

    Returns the diagnostic directory path. Robust to missing artifacts.
    """
    import shutil

    diag_dir = output.parent / f"{output.stem}_build_diagnostics"
    diag_dir.mkdir(parents=True, exist_ok=True)
    for name, src in artifacts.items():
        try:
            if src is not None and Path(src).is_file():
                shutil.copy2(src, diag_dir / name)
        except OSError:  # pragma: no cover - best-effort diagnostics
            pass
    return diag_dir


def build(
    md_path: Path,
    output: Path,
    *,
    theme: Theme | None = None,
    theme_name: str | None = None,
    theme_dir: Path | str | None = None,
    keep_tex: bool = False,
) -> Path:
    """Build ``md_path`` into a branded PDF ``output`` using ``theme``.

    A ready :class:`Theme` may be passed directly as ``theme``; otherwise it is
    loaded from ``theme_name``/``theme_dir`` (bundled by name or external
    directory). When neither is supplied the bundled ``default`` theme is used.
    Front-matter ``theme:`` resolution is performed by the CLI, which passes the
    resolved selector here.

    Fails loudly (``SystemExit``) on missing required front-matter fields, an
    unknown fontsize, or a non-zero pandoc/xelatex exit (artifacts preserved).
    """
    md_path = Path(md_path).resolve()
    output = Path(output).resolve()
    if not md_path.exists():
        raise FileNotFoundError(f"input not found: {md_path}")

    if theme is None:
        theme = load_theme(name=theme_name, theme_dir=theme_dir)

    text = md_path.read_text(encoding="utf-8")
    from .frontmatter import parse_front_matter

    fields, body = parse_front_matter(text)
    theme.validate_fields(fields)          # fails loudly if a required field missing

    # Rendered theme fragments (preamble body + custom title/thank-you frames).
    theme_preamble = theme.render_preamble(fields)
    title_tex = theme.render_title(fields)
    thankyou_tex = theme.render_thankyou(fields)

    short_title = latex_escape(
        str(fields.get("short_title") or fields.get("title", "")).strip()
    )
    body_fontsize = theme.resolve_font_scale(fields)

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)

        # Diagram asset lifecycle: a persistent `<stem>_diagrams` dir beside the
        # output when keeping the .tex (so the kept .tex references stay valid),
        # otherwise a build-scoped dir inside the TemporaryDirectory.
        if keep_tex:
            diagram_dir = output.parent / f"{output.stem}_diagrams"
        else:
            diagram_dir = tdp / "diagrams"
        diagram_dir.mkdir(parents=True, exist_ok=True)

        # Engine-owned preamble prologue: graphicx, the fontsize package, the
        # footer short-title (set WITHOUT -V title so pandoc does not emit its
        # own \titlepage), and a brace-protected \graphicspath carrying BOTH the
        # diagram dir and the theme assets dir (critique E9) so relative image
        # filenames resolve under xelatex even when paths contain spaces.
        prologue = (
            r"\usepackage{graphicx}" + "\n"
            r"\usepackage[fontsize=" + body_fontsize + r"]{fontsize}" + "\n"
            r"\title[" + short_title + r"]{" + short_title + r"}" + "\n"
        )
        prologue += _graphicspath([diagram_dir, theme.assets_dir])

        # The engine prologue precedes the theme preamble so the theme can
        # override anything (fonts, colours), and so `captioncolor` defined in
        # the theme preamble is available to the picture/diagram frame bodies.
        preamble_full = prologue + theme_preamble

        # Body written without front-matter so pandoc doesn't auto-title.
        body_file = tdp / "body.md"
        body_file.write_text(
            preprocess_body(body, diagram_dir), encoding="utf-8"
        )

        pre_file = tdp / "preamble.tex"
        pre_file.write_text(preamble_full, encoding="utf-8")
        before_file = tdp / "before.tex"
        before_file.write_text(title_tex, encoding="utf-8")
        after_file = tdp / "after.tex"
        after_file.write_text(thankyou_tex, encoding="utf-8")

        output.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "pandoc",
            str(body_file),
            "-t", "beamer",
            "--pdf-engine=xelatex",
            "--slide-level=1",
            "--resource-path", str(md_path.parent),
            # Diagram images are emitted as relative filenames; add their dir
            # to the resource path so pandoc resolves them even when the path
            # contains spaces (critique E9).
            "--resource-path", str(diagram_dir),
            "-V", "aspectratio=169",
            "-V", "classoption=t",
            "--include-in-header", str(pre_file),
            "--include-before-body", str(before_file),
            "--include-after-body", str(after_file),
            "-o", str(output),
        ]

        if keep_tex:
            tex_out = output.with_suffix(".tex")
            tex_cmd = cmd[: cmd.index("-o")] + ["-o", str(tex_out)]
            proc = subprocess.run(
                tex_cmd, cwd=str(md_path.parent), capture_output=True
            )
            if proc.returncode != 0:
                out = (proc.stdout or b"").decode("utf-8", "replace")
                err = (proc.stderr or b"").decode("utf-8", "replace")
                sys.stderr.write(out + "\n" + err + "\n")
                diag = _preserve_diagnostics(
                    {
                        "body.md": body_file,
                        "preamble.tex": pre_file,
                        "before.tex": before_file,
                        "after.tex": after_file,
                    },
                    output,
                )
                sys.stderr.write(
                    f"ERROR: build artifacts preserved for inspection in: {diag}\n"
                )
                raise SystemExit(
                    f"pandoc/xelatex failed (exit {proc.returncode}) while "
                    f"generating the intermediate .tex"
                )
            print(f"kept intermediate TeX: {tex_out}")

        proc = subprocess.run(cmd, cwd=str(md_path.parent), capture_output=True)
        if proc.returncode != 0:
            out = (proc.stdout or b"").decode("utf-8", "replace")
            err = (proc.stderr or b"").decode("utf-8", "replace")
            sys.stderr.write(out + "\n" + err + "\n")
            # Preserve intermediate artifacts for inspection (critique E4).
            diag = _preserve_diagnostics(
                {
                    "body.md": body_file,
                    "preamble.tex": pre_file,
                    "before.tex": before_file,
                    "after.tex": after_file,
                },
                output,
            )
            sys.stderr.write(
                f"ERROR: build artifacts preserved for inspection in: {diag}\n"
            )
            raise SystemExit(f"pandoc/xelatex failed (exit {proc.returncode})")

    return output

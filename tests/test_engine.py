"""Tests for the engine wiring + CLI (Task 6).

The full toolchain (pandoc/xelatex/d2/mmdr) is present on some dev boxes and
absent on CI; end-to-end tests are therefore ``skipif``-guarded. A pandoc-only
TeX-generation test exercises the rendered ``.tex`` structure without xelatex
(critique E7). Unit-level theme-precedence and diagnostic-dir tests run
unconditionally.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from md2pdf import cli, engine


# --- availability guards ---------------------------------------------------
def _pandoc() -> bool:
    return bool(shutil.which("pandoc"))


def _toolchain() -> bool:
    return _pandoc() and bool(shutil.which("xelatex"))


DEFAULT_FM = "---\ntitle: Engine Test Deck\nauthor: Tester\ndate: 2026-10-09\n---\n\n"


# --- preprocess_body / picture_body_tex (theme-agnostic, no toolchain) -----
def test_picture_body_tex_fit_layout_and_caption_color():
    tex = engine.picture_body_tex("A caption", "images/x.png")
    assert (
        r"\includegraphics[width=\textwidth,height=0.78\textheight,"
        r"keepaspectratio]{images/x.png}" in tex
    )
    assert r"\begin{center}" in tex and r"\end{center}" in tex
    # Theme-agnostic caption colour hook.
    assert r"\color{captioncolor}" in tex
    assert "A caption" in tex


def test_picture_body_tex_no_caption_when_alt_empty():
    tex = engine.picture_body_tex("", "x.png")
    assert "captioncolor" not in tex
    assert r"\includegraphics" in tex


def test_preprocess_body_rewrites_only_picture_slides():
    body = (
        "# Regular\n\n- a\n- b\n\n"
        "---\n\n"
        "# Picture\n\n![cap](p.png)\n"
    )
    out = engine.preprocess_body(body)
    assert "```{=latex}" in out
    assert r"\includegraphics" in out
    assert "- a" in out  # regular slide untouched
    assert "# Regular" in out


# --- pandoc-only TeX generation (no xelatex) — critique E7 -----------------
@pytest.mark.skipif(not _pandoc(), reason="pandoc not available")
def test_pandoc_tex_generation_default_theme(tmp_path):
    """Generate the beamer .tex via pandoc only (no PDF engine) and assert
    the default theme preamble + picture fit-frame structure are present."""
    md = tmp_path / "deck.md"
    md.write_text(
        DEFAULT_FM
        + "# Regular\n\n- point one\n\n"
        + "---\n\n"
        + "# Picture\n\n![A demo caption](img.png)\n",
        encoding="utf-8",
    )
    # Replicate the engine's pandoc invocation but target .tex (no xelatex).
    theme = engine.load_theme(name="default")
    from md2pdf.frontmatter import parse_front_matter

    fields, body = parse_front_matter(md.read_text(encoding="utf-8"))
    pre = theme.render_preamble(fields)
    before = theme.render_title(fields)
    after = theme.render_thankyou(fields)
    body_md = engine.preprocess_body(body, tmp_path / "diagrams")

    pre_f = tmp_path / "preamble.tex"; pre_f.write_text(pre, encoding="utf-8")
    bef_f = tmp_path / "before.tex"; bef_f.write_text(before, encoding="utf-8")
    aft_f = tmp_path / "after.tex"; aft_f.write_text(after, encoding="utf-8")
    body_f = tmp_path / "body.md"; body_f.write_text(body_md, encoding="utf-8")
    tex_out = tmp_path / "deck.tex"

    proc = subprocess.run(
        [
            "pandoc", str(body_f), "-t", "beamer", "--slide-level=1",
            "-V", "aspectratio=169", "-V", "classoption=t",
            "--include-in-header", str(pre_f),
            "--include-before-body", str(bef_f),
            "--include-after-body", str(aft_f),
            "-o", str(tex_out),
        ],
        cwd=str(tmp_path), capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    tex = tex_out.read_text(encoding="utf-8")
    # Default-theme preamble markers.
    assert r"\definecolor{themeprimary}" in tex
    assert r"\colorlet{captioncolor}{themegrey}" in tex
    # Fit-to-frame picture body + caption.
    assert (
        r"\includegraphics[width=\textwidth,height=0.78\textheight,"
        r"keepaspectratio]" in tex
    )
    assert "A demo caption" in tex
    assert "point one" in tex
    # No brand-specific colour defs leaked into the neutral default.
    assert "SESAR" not in tex and "wp2-image" not in tex


# --- end-to-end PDF (skipif xelatex absent) --------------------------------
@pytest.mark.skipif(not _toolchain(), reason="pandoc/xelatex not available")
def test_build_end_to_end_default_theme(tmp_path):
    md = tmp_path / "deck.md"
    md.write_text(DEFAULT_FM + "# Only Slide\n\n- a\n- b\n", encoding="utf-8")
    out_pdf = tmp_path / "deck.pdf"
    result = engine.build(md, out_pdf, theme_name="default")
    assert result.exists() and out_pdf.stat().st_size > 0


@pytest.mark.skipif(not _toolchain(), reason="pandoc/xelatex not available")
def test_build_keep_tex_emits_picture_fit_frame(tmp_path):
    # Use the shipped neutral placeholder (a valid PNG) rather than an inline
    # byte-blob, so xelatex has real image data to embed.
    img_src = Path(__file__).resolve().parents[1] / "examples" / "assets" / "placeholder.png"
    img = tmp_path / "img.png"
    img.write_bytes(img_src.read_bytes())
    md = tmp_path / "deck.md"
    md.write_text(
        DEFAULT_FM
        + "# Regular\n\n- point one\n\n---\n\n"
        + f"# Picture\n\n![A demo caption]({img.as_posix()})\n",
        encoding="utf-8",
    )
    out_pdf = tmp_path / "deck.pdf"
    engine.build(md, out_pdf, theme_name="default", keep_tex=True)
    tex = (tmp_path / "deck.tex").read_text(encoding="utf-8")
    assert (
        r"\includegraphics[width=\textwidth,height=0.78\textheight,"
        r"keepaspectratio]" in tex
    )
    assert "A demo caption" in tex
    assert "point one" in tex


# --- theme resolution precedence (critique P2) -----------------------------
def test_front_matter_theme_selected_when_no_cli_flag(tmp_path, monkeypatch):
    """With no --theme/--theme-dir, the deck's front-matter `theme:` wins."""
    captured = {}

    def fake_build(inp, out, *, theme_name, theme_dir, keep_tex):
        captured["theme_name"] = theme_name
        captured["theme_dir"] = theme_dir
        return Path(out)

    monkeypatch.setattr(cli, "build", fake_build, raising=False)
    # Patch the symbol the CLI imports lazily inside main().
    import md2pdf.engine as eng
    monkeypatch.setattr(eng, "build", fake_build)

    md = tmp_path / "deck.md"
    md.write_text("---\ntheme: custom\ntitle: X\n---\n\n# S\n", encoding="utf-8")
    rc = cli.main([str(md), "--output", str(tmp_path / "o.pdf")])
    assert rc == 0
    assert captured["theme_name"] == "custom"
    assert captured["theme_dir"] is None


def test_cli_theme_overrides_front_matter(tmp_path, monkeypatch):
    captured = {}

    def fake_build(inp, out, *, theme_name, theme_dir, keep_tex):
        captured["theme_name"] = theme_name
        return Path(out)

    import md2pdf.engine as eng
    monkeypatch.setattr(eng, "build", fake_build)

    md = tmp_path / "deck.md"
    md.write_text("---\ntheme: custom\ntitle: X\n---\n\n# S\n", encoding="utf-8")
    rc = cli.main(
        [str(md), "--output", str(tmp_path / "o.pdf"), "--theme", "default"]
    )
    assert rc == 0
    # CLI --theme beats the front-matter theme.
    assert captured["theme_name"] == "default"


# --- default --output derivation -------------------------------------------
def test_output_defaults_to_input_with_pdf_suffix(tmp_path, monkeypatch):
    """With --output omitted, the PDF path is the input path with .pdf."""
    captured = {}

    def fake_build(inp, out, *, theme_name, theme_dir, keep_tex):
        captured["out"] = Path(out)
        return Path(out)

    import md2pdf.engine as eng
    monkeypatch.setattr(eng, "build", fake_build)

    md = tmp_path / "my deck.md"
    md.write_text("---\ntitle: X\n---\n\n# S\n", encoding="utf-8")
    rc = cli.main([str(md)])
    assert rc == 0
    assert captured["out"] == md.with_suffix(".pdf")
    assert captured["out"] == tmp_path / "my deck.pdf"


def test_explicit_output_overrides_default(tmp_path, monkeypatch):
    captured = {}

    def fake_build(inp, out, *, theme_name, theme_dir, keep_tex):
        captured["out"] = Path(out)
        return Path(out)

    import md2pdf.engine as eng
    monkeypatch.setattr(eng, "build", fake_build)

    md = tmp_path / "deck.md"
    md.write_text("---\ntitle: X\n---\n\n# S\n", encoding="utf-8")
    explicit = tmp_path / "custom-name.pdf"
    rc = cli.main([str(md), "--output", str(explicit)])
    assert rc == 0
    assert captured["out"] == explicit


def test_unknown_bundled_theme_fails_loudly(tmp_path):
    md = tmp_path / "deck.md"
    md.write_text("---\ntitle: X\n---\n\n# S\n", encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        cli.main(
            [str(md), "--output", str(tmp_path / "o.pdf"), "--theme", "nope"]
        )
    assert "nope" in str(ei.value)


# --- forced failure leaves a diagnostic directory (critique E4) ------------
@pytest.mark.skipif(not _toolchain(), reason="pandoc/xelatex not available")
def test_forced_failure_preserves_diagnostics(tmp_path, capsys):
    """A deck whose title frame injects invalid raw TeX forces an xelatex
    failure; the engine must preserve body.md/preamble.tex/before.tex/after.tex
    in a diagnostic directory and print its path to stderr."""
    md = tmp_path / "deck.md"
    # raw_fields are injected unescaped by the template; a stray \undefinedcmd
    # here would be escaped by the default title template, so instead inject
    # broken LaTeX via a raw-latex body block that xelatex rejects.
    md.write_text(
        DEFAULT_FM
        + "# Boom\n\n```{=latex}\n\\thiscommanddoesnotexist\n```\n",
        encoding="utf-8",
    )
    out_pdf = tmp_path / "deck.pdf"
    with pytest.raises(SystemExit):
        engine.build(md, out_pdf, theme_name="default")
    err = capsys.readouterr().err
    diag_dir = tmp_path / "deck_build_diagnostics"
    assert diag_dir.is_dir()
    for name in ("body.md", "preamble.tex", "before.tex", "after.tex"):
        assert (diag_dir / name).is_file()
    assert str(diag_dir) in err



# --- column_body_tex / two-column lowering (theme-agnostic, no toolchain) ---
def test_column_body_tex_top_aligned_no_vfill():
    tex = engine.column_body_tex("", "x.png")
    assert (
        r"\includegraphics[width=\columnwidth,height=0.72\textheight,"
        r"keepaspectratio]{x.png}" in tex
    )
    # Top-aligned: \centering declaration, no \vfill, no center environment
    # (critique P2 / task-level E1).
    assert r"{\centering" in tex
    assert r"\vfill" not in tex
    assert r"\begin{center}" not in tex


def test_column_body_tex_caption_when_alt():
    tex = engine.column_body_tex("Fig 1", "x.png")
    assert r"\color{captioncolor}" in tex and "Fig 1" in tex


def test_picture_body_tex_regression_unchanged():
    # The refactor into _fit_image_tex must not change whole-slide output.
    tex = engine.picture_body_tex("cap", "a.png")
    assert tex == (
        "\\vfill\n"
        "\\begin{center}\n"
        "\\includegraphics[width=\\textwidth,height=0.78\\textheight,"
        "keepaspectratio]{a.png}\\par\n"
        "\\vskip0.4em{\\small\\color{captioncolor}cap\\par}\n"
        "\\end{center}\n"
        "\\vfill\n"
    )


def test_preprocess_body_two_column_structure():
    out = engine.preprocess_body(
        "# T\n\n:::\n![alt](p.png)\n:::\n- one\n- two\n:::\n"
    )
    assert "{.columns .onlytextwidth align=top}" in out
    assert out.count('{.column width="50%"}') == 2
    assert (
        r"\includegraphics[width=\columnwidth,height=0.72\textheight,"
        r"keepaspectratio]{p.png}" in out
    )
    # right (markdown) region flows verbatim
    assert "- one\n- two" in out
    # no whole-slide vertical centring leaked into the column lowering
    assert r"\vfill" not in out


def test_preprocess_body_two_column_diagram_region(monkeypatch, tmp_path):
    # Diagram-in-column lowering without requiring d2/mmdr (task-level E5):
    # monkeypatch render_diagram to a fake rendered file.
    fake = tmp_path / "diagram_d2_abc.pdf"
    fake.write_bytes(b"%PDF-1.4\n")

    def _fake_render(lang, source, out_dir, title):
        return fake

    monkeypatch.setattr(engine, "render_diagram", _fake_render)
    out = engine.preprocess_body(
        "# T\n\n:::\n```d2\na -> b\n```\n:::\n- note\n:::\n",
        diagram_dir=tmp_path,
    )
    assert "{.columns .onlytextwidth align=top}" in out
    # the diagram region was rewritten to a columnwidth-fit includegraphics by
    # relative filename
    assert r"\includegraphics[width=\columnwidth" in out
    assert "diagram_d2_abc.pdf" in out
    assert "- note" in out


def test_preprocess_body_ordinary_slide_untouched():
    ordinary = "# Topic\n\n- bullet one\n- bullet two"
    out = engine.preprocess_body(ordinary)
    assert ".columns" not in out
    assert "- bullet one" in out


def test_preprocess_body_pandoc_div_slide_untouched():
    # An ordinary slide with a Pandoc fenced div must not be lowered (R6).
    deck = "# T\n\nprose\n\n::: notes\nnote\n:::"
    out = engine.preprocess_body(deck)
    assert ".columns .onlytextwidth" not in out
    assert "::: notes" in out

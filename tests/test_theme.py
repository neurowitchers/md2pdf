"""Tests for the theme loader + Jinja2 rendering layer (Task 4)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment
from jinja2.sandbox import SandboxedEnvironment

from md2pdf.theme import Theme, load_theme, validate_theme

FIXTURES = Path(__file__).parent / "fixtures" / "themes"
MINI = FIXTURES / "mini"


# --- loading & parsing -----------------------------------------------------
def test_load_external_theme_parses_palette_and_fields():
    theme = load_theme(theme_dir=MINI)
    assert isinstance(theme, Theme)
    assert theme.name == "mini"
    assert theme.palette["primary"] == "112233"
    assert theme.palette["accent"] == "AABBCC"
    assert theme.required_fields == ["title"]
    assert "author" in theme.optional_fields
    assert theme.font_scales["normal"] == "11pt"
    assert theme.default_font_scale == "normal"
    assert len(theme.logos) == 2


def test_theme_has_no_headline_field():
    # Critique E2: the Theme dataclass must NOT carry a headline field.
    theme = load_theme(theme_dir=MINI)
    assert not hasattr(theme, "headline")


# --- required-field validation --------------------------------------------
def test_missing_required_field_fails_loudly():
    theme = load_theme(theme_dir=MINI)
    with pytest.raises(SystemExit) as exc:
        theme.validate_fields({})  # no title
    msg = str(exc.value)
    assert "title" in msg
    assert "required" in msg.lower()


def test_required_field_present_passes():
    theme = load_theme(theme_dir=MINI)
    theme.validate_fields({"title": "Hello"})  # no raise


# --- auto-escape WITHOUT a filter + raw_fields -----------------------------
def test_fields_autoescaped_without_filter():
    theme = load_theme(theme_dir=MINI)
    out = theme.render_title({"title": "A & B_100%"})
    # Escaped output appears on the HEADLINE line (template has no filter).
    assert r"\&" in out
    assert r"\_" in out
    assert r"\%" in out
    # And the raw, unescaped value is available via raw_fields.
    assert "RAW: A & B_100%" in out


def test_raw_fields_available_unescaped():
    theme = load_theme(theme_dir=MINI)
    ctx = theme._context({"title": "x&y"})
    assert ctx["raw_fields"]["title"] == "x&y"
    assert ctx["title"] == r"x\&y"  # escaped at top level


# --- validate_theme actionable errors -------------------------------------
def test_validate_theme_missing_preamble(tmp_path):
    # Build a theme dir missing preamble.tex.j2.
    (tmp_path / "theme.yaml").write_text("name: broken\n", encoding="utf-8")
    (tmp_path / "title.tex.j2").write_text("x", encoding="utf-8")
    (tmp_path / "thankyou.tex.j2").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        validate_theme(tmp_path)
    msg = str(exc.value)
    assert "preamble.tex.j2" in msg
    assert "missing" in msg.lower()


def test_validate_theme_bad_yaml(tmp_path):
    (tmp_path / "theme.yaml").write_text(": : bad\n  - x\n", encoding="utf-8")
    for f in ("preamble.tex.j2", "title.tex.j2", "thankyou.tex.j2"):
        (tmp_path / f).write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        validate_theme(tmp_path)
    assert "YAML" in str(exc.value) or "yaml" in str(exc.value)


def test_validate_theme_template_syntax_error(tmp_path):
    (tmp_path / "theme.yaml").write_text("name: t\n", encoding="utf-8")
    (tmp_path / "preamble.tex.j2").write_text("ok", encoding="utf-8")
    (tmp_path / "title.tex.j2").write_text("<% if %>", encoding="utf-8")
    (tmp_path / "thankyou.tex.j2").write_text("ok", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        validate_theme(tmp_path)
    msg = str(exc.value)
    assert "title.tex.j2" in msg
    assert "compile" in msg.lower() or "line" in msg.lower()


# --- sandbox for external themes -------------------------------------------
def test_external_theme_uses_sandboxed_environment():
    theme = load_theme(theme_dir=MINI)
    assert isinstance(theme._env, SandboxedEnvironment)


def test_bundled_theme_uses_standard_environment():
    theme = load_theme(name="default")
    # Standard Environment, and NOT the sandboxed subclass.
    assert isinstance(theme._env, Environment)
    assert not isinstance(theme._env, SandboxedEnvironment)


# --- logos loop renders N includegraphics ----------------------------------
def test_logos_loop_renders_n_includegraphics():
    theme = load_theme(theme_dir=MINI)
    out = theme.render_title({"title": "T"})
    includes = re.findall(r"\\includegraphics", out)
    assert len(includes) == len(theme.logos) == 2
    assert "one.png" in out
    assert "two.png" in out


# --- font scale resolution -------------------------------------------------
def test_resolve_font_scale_default_and_named():
    theme = load_theme(theme_dir=MINI)
    assert theme.resolve_font_scale({}) == "11pt"           # default normal
    assert theme.resolve_font_scale({"fontsize": "large"}) == "12pt"


def test_resolve_font_scale_unknown_fails_loudly():
    theme = load_theme(theme_dir=MINI)
    with pytest.raises(SystemExit) as exc:
        theme.resolve_font_scale({"fontsize": "gigantic"})
    assert "gigantic" in str(exc.value)


# --- bad --theme-dir -------------------------------------------------------
def test_missing_theme_dir_fails_loudly(tmp_path):
    with pytest.raises(SystemExit):
        load_theme(theme_dir=tmp_path / "does-not-exist")


def test_unknown_bundled_theme_fails_loudly():
    with pytest.raises(SystemExit) as exc:
        load_theme(name="no-such-theme")
    assert "no-such-theme" in str(exc.value)


# --- LaTeX `{%` collision is handled (delimiter choice) --------------------
def test_latex_percent_brace_is_literal_not_jinja_block():
    # The default preamble uses `\setbeamertemplate{frametitle}{%` — a literal
    # LaTeX `{%` that must survive rendering untouched (it is NOT a Jinja block
    # opener, because statements use `<% %>`).
    theme = load_theme(name="default")
    out = theme.render_preamble({"title": "T"})
    assert r"\setbeamertemplate{frametitle}{%" in out
    assert "<%" not in out  # all statement tags consumed


def test_default_preamble_defines_palette_colors():
    theme = load_theme(name="default")
    out = theme.render_preamble({"title": "T"})
    # The palette loop emitted one \definecolor per palette entry.
    for key in theme.palette:
        assert f"\\definecolor{{theme{key}}}" in out

"""Tests for the neutral `default` theme (Task 5)."""
from __future__ import annotations

import pytest

from md2pdf.theme import load_theme

# Sentinels that must never appear in the neutral default theme — these guard
# against brand-specific colour names, logo filenames, or wordmarks bleeding in.
BRAND_MARKERS = ("SESAR", "Co-funded", "wp2-image", "eu-cofunded")


def _load():
    return load_theme(name="default")


def test_default_theme_loads_and_requires_only_title():
    theme = _load()
    assert theme.name == "default"
    assert theme.required_fields == ["title"]
    for opt in ("author", "date", "subtitle", "fontsize", "short_title"):
        assert opt in theme.optional_fields


def test_default_renders_all_three_with_only_title():
    theme = _load()
    fields = {"title": "A Neutral Deck"}
    pre = theme.render_preamble(fields)
    title = theme.render_title(fields)
    thanks = theme.render_thankyou(fields)
    assert pre.strip()
    assert "A Neutral Deck" in title
    assert "Thank you!" in thanks


def test_default_renders_with_optional_fields():
    theme = _load()
    fields = {
        "title": "Deck",
        "subtitle": "A subtitle",
        "author": "Jane Doe",
        "date": "2026-10-09",
    }
    title = theme.render_title(fields)
    assert "A subtitle" in title
    assert "Jane Doe" in title
    assert "2026-10-09" in title


def test_default_author_and_date_optional():
    theme = _load()
    # Only title — must validate and render without author/date.
    theme.validate_fields({"title": "Just a title"})
    title = theme.render_title({"title": "Just a title"})
    assert "Just a title" in title


def test_default_required_validation_rejects_missing_title():
    theme = _load()
    with pytest.raises(SystemExit):
        theme.validate_fields({"author": "nobody"})


def test_default_theme_has_no_brand_strings():
    theme = _load()
    rendered = (
        theme.render_preamble({"title": "T"})
        + theme.render_title({"title": "T"})
        + theme.render_thankyou({"title": "T"})
    )
    for marker in BRAND_MARKERS:
        assert marker not in rendered, f"brand marker leaked: {marker!r}"


def test_default_theme_yaml_source_has_no_brand_strings():
    theme = _load()
    for f in ("theme.yaml", "preamble.tex.j2", "title.tex.j2", "thankyou.tex.j2"):
        text = (theme.dir / f).read_text(encoding="utf-8")
        for marker in ("SESAR", "wp2-image", "eu-cofunded"):
            assert marker not in text, f"{marker!r} present in {f}"


def test_default_font_scales_carried_over():
    theme = _load()
    assert theme.font_scales == {
        "xsmall": "8pt",
        "small": "10pt",
        "normal": "11pt",
        "large": "12pt",
        "xlarge": "14pt",
    }
    assert theme.default_font_scale == "normal"


def test_default_theme_has_no_logos():
    theme = _load()
    assert theme.logos == []

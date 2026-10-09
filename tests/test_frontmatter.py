"""Tests for md2pdf front-matter parsing.

Covers the legacy minimal-YAML behaviour plus the spec additions: str-coercion
of scalar values (critique E8) and recognition of an optional ``theme`` key
(critique P2).
"""
from __future__ import annotations

from md2pdf import latex
from md2pdf.frontmatter import parse_front_matter


def test_no_front_matter_returns_empty_and_body():
    text = "# Just a slide\n\nbody\n"
    fields, body = parse_front_matter(text)
    assert fields == {}
    assert body == text


def test_basic_front_matter_parse():
    text = (
        "---\n"
        "title: Fleet Operational Concept\n"
        "author: Acme Consortium\n"
        "---\n\n"
        "# Slide\n"
    )
    fields, body = parse_front_matter(text)
    assert fields["title"] == "Fleet Operational Concept"
    assert fields["author"] == "Acme Consortium"
    assert body.startswith("\n# Slide") or body.lstrip().startswith("# Slide")


def test_front_matter_strips_quotes():
    text = '---\ntitle: "Quoted Title"\nother: \'single\'\n---\n\nbody\n'
    fields, _ = parse_front_matter(text)
    assert fields["title"] == "Quoted Title"
    assert fields["other"] == "single"


def test_front_matter_ignores_comments_and_blank_lines():
    text = "---\n# a comment\n\ntitle: X\n---\n\nbody\n"
    fields, _ = parse_front_matter(text)
    assert fields == {"title": "X"}


def test_malformed_front_matter_returns_whole_text():
    # Starts with --- but no closing fence.
    text = "---\ntitle: X\nno closing fence\n"
    fields, body = parse_front_matter(text)
    assert fields == {}
    assert body == text


# --- str-coercion (critique E8) --------------------------------------------

def test_numeric_scalar_coerced_to_str():
    text = "---\ntitle: Demo\nwp: 2\n---\n\nbody\n"
    fields, _ = parse_front_matter(text)
    assert fields["wp"] == "2"
    assert isinstance(fields["wp"], str)


def test_date_scalar_coerced_to_str():
    text = "---\ntitle: Demo\ndate: 2026-10-09\n---\n\nbody\n"
    fields, _ = parse_front_matter(text)
    assert fields["date"] == "2026-10-09"
    assert isinstance(fields["date"], str)


def test_all_values_are_str_and_latex_escapable():
    # A coerced str must flow through latex_escape without type errors.
    text = "---\ntitle: Demo\nwp: 2\ntask: 2.1\n---\n\nbody\n"
    fields, _ = parse_front_matter(text)
    for value in fields.values():
        assert isinstance(value, str)
        # Should not raise.
        latex.latex_escape(value)


# --- optional theme key ----------------------------------------------------

def test_theme_key_is_parsed():
    text = "---\ntitle: Demo\ntheme: custom\n---\n\nbody\n"
    fields, _ = parse_front_matter(text)
    assert fields["theme"] == "custom"


def test_theme_key_absent_is_fine():
    text = "---\ntitle: Demo\n---\n\nbody\n"
    fields, _ = parse_front_matter(text)
    assert "theme" not in fields

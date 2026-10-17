"""Build the shipped example decks (Task 7), skipif the toolchain is absent.

The example decks live in ``examples/`` and use the neutral ``default`` theme
(``default-demo.md``, ``picture-demo.md``, ``diagram-demo.md``). Picture/diagram
demos reference a neutral placeholder image under ``examples/assets/`` — no
proprietary assets are involved. The diagram demo additionally needs ``d2``/``mmdr``.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from md2pdf import engine

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _pandoc_xelatex() -> bool:
    return bool(shutil.which("pandoc")) and bool(shutil.which("xelatex"))


def _diagram_toolchain() -> bool:
    return (
        _pandoc_xelatex()
        and bool(shutil.which("d2"))
        and bool(shutil.which("mmdr"))
    )


def test_example_assets_placeholder_exists():
    """The neutral placeholder image ships with the examples (no proprietary asset)."""
    img = EXAMPLES / "assets" / "placeholder.png"
    assert img.is_file() and img.stat().st_size > 0


@pytest.mark.skipif(not _pandoc_xelatex(), reason="pandoc/xelatex not available")
@pytest.mark.parametrize("deck", ["default-demo.md", "picture-demo.md"])
def test_build_example_deck_produces_pdf(deck, tmp_path):
    src = EXAMPLES / deck
    assert src.is_file(), f"missing example deck: {src}"
    out_pdf = tmp_path / (Path(deck).stem + ".pdf")
    result = engine.build(src, out_pdf, theme_name="default")
    assert result.exists()
    assert out_pdf.stat().st_size > 0


@pytest.mark.skipif(not _diagram_toolchain(), reason="pandoc/xelatex/d2/mmdr not all available")
def test_build_diagram_example_deck_produces_pdf(tmp_path):
    src = EXAMPLES / "diagram-demo.md"
    out_pdf = tmp_path / "diagram-demo.pdf"
    result = engine.build(src, out_pdf, theme_name="default")
    assert result.exists()
    assert out_pdf.stat().st_size > 0



@pytest.mark.skipif(
    not _diagram_toolchain(),
    reason="pandoc/xelatex/d2/mmdr not all available",
)
def test_build_two_column_example_deck_produces_pdf(tmp_path):
    # The two-column demo exercises a picture column and a d2-diagram column.
    src = EXAMPLES / "two-column-demo.md"
    assert src.is_file(), f"missing example deck: {src}"
    out_pdf = tmp_path / "two-column-demo.pdf"
    result = engine.build(src, out_pdf, theme_name="default")
    assert result.exists()
    assert out_pdf.stat().st_size > 0

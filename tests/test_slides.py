"""Tests for md2pdf slide splitting and strict picture/diagram detection.

Migrated from the legacy tools/md2pdf/test_md2pdf.py (theme-agnostic subset).
"""
from __future__ import annotations

from md2pdf import slides


MERMAID_SRC = "flowchart LR\n    A --> B --> C"
D2_SRC = "x -> y: edge\ny -> z: edge"


# --- split_slides ----------------------------------------------------------

def test_split_slides_basic():
    body = "# A\n\ntext\n\n---\n\n# B\n\nmore\n"
    chunks = slides.split_slides(body)
    assert len(chunks) == 2
    assert "# A" in chunks[0]
    assert "# B" in chunks[1]


def test_split_slides_no_break():
    assert len(slides.split_slides("# Only\n\nbody\n")) == 1


# --- match_picture_slide ---------------------------------------------------

def test_match_picture_slide_with_alt():
    chunk = "# Architecture\n\n![System overview](images/arch.png)\n"
    got = slides.match_picture_slide(chunk)
    assert got == {
        "title": "Architecture",
        "alt": "System overview",
        "path": "images/arch.png",
    }


def test_match_picture_slide_without_alt():
    got = slides.match_picture_slide("# Pic\n\n![](diagram.png)\n")
    assert got == {"title": "Pic", "alt": "", "path": "diagram.png"}


def test_match_picture_slide_absolute_windows_path():
    chunk = r"# Pic" + "\n\n" + r"![x](C:/data/plot.png)" + "\n"
    got = slides.match_picture_slide(chunk)
    assert got is not None and got["path"] == "C:/data/plot.png"


def test_match_picture_slide_strips_quoted_title():
    got = slides.match_picture_slide('# T\n\n![a](p.png "a title")\n')
    assert got is not None and got["path"] == "p.png" and got["alt"] == "a"


def test_regular_slide_is_not_picture():
    chunk = "# Topic\n\n- bullet one\n- bullet two\n"
    assert slides.match_picture_slide(chunk) is None


def test_picture_with_extra_text_disqualified():
    chunk = "# T\n\n![a](p.png)\n\nSome trailing prose.\n"
    assert slides.match_picture_slide(chunk) is None


def test_picture_with_trailing_bullet_disqualified():
    chunk = "# T\n\n![a](p.png)\n\n- note\n"
    assert slides.match_picture_slide(chunk) is None


def test_two_images_disqualified():
    chunk = "# T\n\n![a](p1.png)\n\n![b](p2.png)\n"
    assert slides.match_picture_slide(chunk) is None


def test_no_image_disqualified():
    assert slides.match_picture_slide("# Just a title\n") is None


# --- match_diagram_slide ---------------------------------------------------

def test_match_diagram_slide_mermaid():
    chunk = f"# Flow\n\n```mermaid\n{MERMAID_SRC}\n```\n"
    got = slides.match_diagram_slide(chunk)
    assert got == {"title": "Flow", "lang": "mermaid", "source": MERMAID_SRC}


def test_match_diagram_slide_d2():
    chunk = f"# Topology\n\n```d2\n{D2_SRC}\n```\n"
    got = slides.match_diagram_slide(chunk)
    assert got == {"title": "Topology", "lang": "d2", "source": D2_SRC}


def test_match_diagram_slide_preserves_source_verbatim():
    src = "flowchart TD\n    A --> B\n        indented line\n\n    trailing"
    chunk = f"# T\n\n```mermaid\n{src}\n```\n"
    got = slides.match_diagram_slide(chunk)
    assert got is not None and got["source"] == src


def test_match_diagram_slide_trailing_bullet_disqualified():
    chunk = f"# T\n\n```d2\n{D2_SRC}\n```\n\n- note\n"
    assert slides.match_diagram_slide(chunk) is None


def test_match_diagram_slide_trailing_prose_disqualified():
    chunk = f"# T\n\n```mermaid\n{MERMAID_SRC}\n```\n\nSome prose.\n"
    assert slides.match_diagram_slide(chunk) is None


def test_match_diagram_slide_two_fences_disqualified():
    chunk = (
        f"# T\n\n```mermaid\n{MERMAID_SRC}\n```\n\n"
        f"```d2\n{D2_SRC}\n```\n"
    )
    assert slides.match_diagram_slide(chunk) is None


def test_match_diagram_slide_non_diagram_fence_disqualified():
    chunk = "# T\n\n```python\nprint('hi')\n```\n"
    assert slides.match_diagram_slide(chunk) is None


def test_match_diagram_slide_picture_is_none():
    chunk = "# T\n\n![a](p.png)\n"
    assert slides.match_diagram_slide(chunk) is None


def test_match_picture_slide_diagram_is_none():
    # Detectors stay disjoint.
    chunk = f"# T\n\n```mermaid\n{MERMAID_SRC}\n```\n"
    assert slides.match_picture_slide(chunk) is None


def test_match_diagram_slide_info_trailing_whitespace_matches():
    chunk = f"# T\n\n```mermaid   \n{MERMAID_SRC}\n```\n"
    got = slides.match_diagram_slide(chunk)
    assert got is not None and got["lang"] == "mermaid"


def test_match_diagram_slide_extra_info_params_disqualified():
    chunk = f"# T\n\n```d2 layout=elk\n{D2_SRC}\n```\n"
    assert slides.match_diagram_slide(chunk) is None


def test_match_diagram_slide_no_heading_disqualified():
    chunk = f"```mermaid\n{MERMAID_SRC}\n```\n"
    assert slides.match_diagram_slide(chunk) is None


def test_match_diagram_slide_unterminated_fence_disqualified():
    chunk = f"# T\n\n```mermaid\n{MERMAID_SRC}\n"
    assert slides.match_diagram_slide(chunk) is None


# --- _chunk_has_diagram_fence ----------------------------------------------

def test_chunk_has_diagram_fence_parameterised_token():
    # First-token detection (critique MEDIUM-1): a parameterised fence still
    # trips the disqualified-slide warning helper.
    assert slides._chunk_has_diagram_fence("```d2 layout=elk\nx\n```") is True
    assert slides._chunk_has_diagram_fence("```python\nx\n```") is False
    assert slides._chunk_has_diagram_fence("```\nx\n```") is False
    assert slides._chunk_has_diagram_fence("```mermaid\nx\n```") is True

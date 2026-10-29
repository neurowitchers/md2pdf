"""Tests for md2pdf slide splitting and strict picture/diagram detection.

Migrated from the legacy tools/md2pdf/test_md2pdf.py (theme-agnostic subset).
"""
from __future__ import annotations

import pytest

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



# --- match_two_column_slide + classify_region ------------------------------

def test_match_two_column_valid_image_and_bullets():
    chunk = "# T\n\n:::\n![a](p.png)\n:::\n- one\n- two\n:::\n"
    got = slides.match_two_column_slide(chunk)
    assert got == {"title": "T", "left": "![a](p.png)", "right": "- one\n- two"}


def test_match_two_column_valid_text_left_image_right():
    chunk = "# T\n\n:::\n- a\n- b\n:::\n![x](q.png)\n:::\n"
    got = slides.match_two_column_slide(chunk)
    assert got is not None
    assert got["left"] == "- a\n- b"
    assert got["right"] == "![x](q.png)"


def test_match_two_column_diagram_region():
    chunk = f"# T\n\n:::\n```d2\n{D2_SRC}\n```\n:::\n- note\n:::\n"
    got = slides.match_two_column_slide(chunk)
    assert got is not None
    assert slides.classify_region(got["left"])[0] == "diagram"


def test_match_two_column_no_colon_is_none():
    # Ordinary slide: not two-column (R6 opt-in).
    assert slides.match_two_column_slide("# T\n\n- a\n- b\n") is None


def test_match_two_column_pandoc_div_not_hijacked():
    # An ordinary slide carrying a Pandoc fenced div (bare ::: closes it) does
    # NOT open with :::, so it is passed through untouched (R6, task-level P1).
    chunk = "# T\n\nsome prose\n\n::: notes\nspeaker note\n:::\n"
    assert slides.match_two_column_slide(chunk) is None


def test_match_two_column_two_delimiters_fails():
    with pytest.raises(SystemExit):
        slides.match_two_column_slide("# T\n\n:::\na\n:::\nb\n")


def test_match_two_column_four_delimiters_fails():
    with pytest.raises(SystemExit) as ei:
        slides.match_two_column_slide("# T\n\n:::\na\n:::\nb\n:::\nc\n:::\n")
    assert "T" in str(ei.value)


def test_match_two_column_empty_region_fails():
    with pytest.raises(SystemExit) as ei:
        slides.match_two_column_slide("# T\n\n:::\n:::\n- x\n:::\n")
    assert "empty" in str(ei.value)


def test_match_two_column_trailing_content_fails():
    with pytest.raises(SystemExit):
        slides.match_two_column_slide("# T\n\n:::\na\n:::\nb\n:::\ntrailing\n")


def test_match_two_column_trailing_blank_lines_tolerated():
    got = slides.match_two_column_slide("# T\n\n:::\na\n:::\nb\n:::\n\n\n")
    assert got is not None and got["right"] == "b"


def test_match_two_column_unterminated_fence_precedence():
    # Unterminated inner fence must be diagnosed before the delimiter count
    # (task-level E2) — the message names the fence, not "expected 3".
    with pytest.raises(SystemExit) as ei:
        slides.match_two_column_slide(
            "# T\n\n:::\n![a](p.png)\n:::\n```python\nx\n:::\n"
        )
    assert "unterminated" in str(ei.value).lower()


def test_match_two_column_colon_inside_code_fence_is_content():
    # ::: inside a code block is content, not a delimiter (critique E2).
    chunk = "# T\n\n:::\n```python\n:::\nnot a delim\n```\n:::\n- right\n:::\n"
    got = slides.match_two_column_slide(chunk)
    assert got is not None and "not a delim" in got["left"]


def test_match_two_column_indented_delimiter_tolerated():
    # Up to 3 leading spaces on a ::: line is accepted (critique E8).
    chunk = "# T\n\n  :::\na\n  :::\nb\n  :::\n"
    got = slides.match_two_column_slide(chunk)
    assert got is not None and got["left"] == "a" and got["right"] == "b"


def test_match_two_column_duplicate_title_fails():
    with pytest.raises(SystemExit):
        slides.match_two_column_slide("# T\n\n:::\na\n:::\n# T2\nb\n:::\n")


def test_classify_region_image_diagram_markdown():
    assert slides.classify_region("![alt](x.png)") == ("image", "alt", "x.png")
    kind, lang, _ = slides.classify_region(f"```d2\n{D2_SRC}\n```")
    assert kind == "diagram" and lang == "d2"
    assert slides.classify_region("- a\n- b")[0] == "markdown"
    # image mixed with other content -> markdown
    assert slides.classify_region("![a](x.png)\n- note")[0] == "markdown"


def test_match_two_column_pre_heading_content_is_none():
    # Code-review HIGH: non-blank content before `# Title` must NOT be hijacked
    # as a two-column slide (which would drop the title and the prose). The
    # title must be the strict first non-blank line, else -> None.
    chunk = "intro prose\n\n# T\n\n:::\nleft\n:::\nright\n:::\n"
    assert slides.match_two_column_slide(chunk) is None


def test_match_two_column_empty_right_region_fails():
    with pytest.raises(SystemExit) as ei:
        slides.match_two_column_slide("# T\n\n:::\nleft\n:::\n   \n:::\n")
    assert "right" in str(ei.value) and "empty" in str(ei.value)


def test_match_two_column_two_image_columns():
    chunk = "# T\n\n:::\n![a](l.png)\n:::\n![b](r.png)\n:::\n"
    got = slides.match_two_column_slide(chunk)
    assert got is not None
    assert slides.classify_region(got["left"]) == ("image", "a", "l.png")
    assert slides.classify_region(got["right"]) == ("image", "b", "r.png")


def test_match_two_column_mixed_media_diagram_left_image_right():
    chunk = f"# T\n\n:::\n```d2\n{D2_SRC}\n```\n:::\n![b](r.png)\n:::\n"
    got = slides.match_two_column_slide(chunk)
    assert got is not None
    assert slides.classify_region(got["left"])[0] == "diagram"
    assert slides.classify_region(got["right"])[0] == "image"

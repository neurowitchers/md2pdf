"""Task 1 scaffold smoke tests."""
from __future__ import annotations

import importlib.resources

import pytest

from md2pdf import cli


def test_help_exits_zero_and_lists_theme_flags(capsys):
    """`md2pdf --help` exits 0 and advertises --theme and --theme-dir."""
    with pytest.raises(SystemExit) as ei:
        cli.main(["--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "--theme" in out
    assert "--theme-dir" in out


def test_help_lists_core_flags(capsys):
    with pytest.raises(SystemExit) as ei:
        cli.main(["--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "--output" in out
    assert "--keep-tex" in out
    assert "input" in out


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as ei:
        cli.main(["--version"])
    assert ei.value.code == 0
    assert "md2pdf" in capsys.readouterr().out


def test_themes_package_resolves_via_importlib_resources():
    """Bundled themes dir is importable as a resource (critique E1)."""
    themes = importlib.resources.files("md2pdf.themes")
    assert themes.is_dir()

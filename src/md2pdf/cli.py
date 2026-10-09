"""Command-line interface for md2pdf.

Defines the full argparse surface (``input``, ``--output``, ``--keep-tex``,
``--theme``, ``--theme-dir``, ``--version``) and wires theme resolution to the
engine ``build()``.

Theme resolution precedence:
``--theme-dir`` (external path) > ``--theme`` (bundled name) >
front-matter ``theme:`` > ``default``. Decks are thus self-describing: a deck
carrying ``theme: <name>`` renders correctly even without CLI flags. An unknown
bundled theme name fails loudly listing the known bundled themes.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Construct the md2pdf argument parser."""
    parser = argparse.ArgumentParser(
        prog="md2pdf",
        description=(
            "Markdown to branded PDF slides (Pandoc + Beamer) with a "
            "theme-as-data system."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input Markdown deck (.md) with optional YAML front-matter.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output PDF path. Defaults to the input path with a .pdf "
            "extension (beside the input Markdown)."
        ),
    )
    parser.add_argument(
        "--keep-tex",
        action="store_true",
        help=(
            "Keep intermediate .tex and persist a <stem>_diagrams directory "
            "beside the output."
        ),
    )
    parser.add_argument(
        "--theme",
        default=None,
        help=(
            "Bundled theme name (e.g. 'default'). Overrides a "
            "front-matter 'theme:' key; defaults to 'default'."
        ),
    )
    parser.add_argument(
        "--theme-dir",
        type=Path,
        default=None,
        help=(
            "Path to an external theme directory. Takes precedence over "
            "--theme and front-matter 'theme:'."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv=None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Resolve the theme with precedence --theme-dir > --theme > front-matter >
    # default. An external --theme-dir short-circuits the bundled
    # name resolution; otherwise peek at the deck's front-matter `theme:` key
    # only when no --theme flag is given.
    from .engine import build
    from .frontmatter import parse_front_matter

    # Default the output to the input path with a .pdf extension when omitted,
    # placing the PDF beside the input Markdown.
    output = args.output if args.output is not None else args.input.with_suffix(".pdf")

    theme_name = args.theme
    if args.theme_dir is None and theme_name is None:
        # Front-matter theme selection (self-describing deck).
        try:
            text = Path(args.input).read_text(encoding="utf-8")
        except OSError as exc:
            parser.error(f"cannot read input: {exc}")
            return 2  # unreachable: parser.error exits
        fm, _ = parse_front_matter(text)
        fm_theme = (fm.get("theme") or "").strip()
        theme_name = fm_theme or None  # None -> default inside load_theme

    out = build(
        args.input,
        output,
        theme_name=theme_name,
        theme_dir=args.theme_dir,
        keep_tex=args.keep_tex,
    )
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

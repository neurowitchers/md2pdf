---
name: md2pdf
description: Create, edit, render, theme, and troubleshoot Markdown slide decks with md2pdf (Pandoc + Beamer). Use when working with Markdown-to-PDF presentations, branded Beamer decks, picture slides, Mermaid or D2 diagram slides, or md2pdf themes.
---

# md2pdf

Use this skill to produce PDF slide decks from Markdown with the repository's `md2pdf` CLI. Follow the existing deck's front matter and theme unless the task asks to change them. Consult [README.md](../../README.md) for the complete supported format and constraints; use the maintained reference decks in [examples/default-demo.md](../../examples/default-demo.md), [examples/picture-demo.md](../../examples/picture-demo.md), and [examples/diagram-demo.md](../../examples/diagram-demo.md) rather than creating a parallel example.

## Prerequisites

- Run this repository with Python 3.13+ and `uv` (`uv sync`).
- Producing a PDF requires `pandoc` and a XeLaTeX engine (TeX Live or MiKTeX) on `PATH`.
- Diagram-only requirements: `d2` for `d2` fences and `mmdr` for `mermaid` fences. The tool locates binaries on `PATH` and in `~/go/bin` and `~/.cargo/bin`.

If a required external binary is missing, report it clearly rather than attempting to substitute another renderer. In particular, Mermaid diagrams use `mmdr`, not `mmdc`.

## Recommended workflow

1. Inspect the Markdown deck, its front matter, referenced image paths, and any theme selection before editing.
2. Make the smallest requested deck or theme change while preserving ordinary Markdown structure.
3. Render from the repository root:

   ```sh
   uv run md2pdf path/to/deck.md
   ```

   The default output is `path/to/deck.pdf`. Specify another destination when needed:

   ```sh
   uv run md2pdf path/to/deck.md --output path/to/output.pdf
   ```

4. For debugging, or when intermediate TeX/diagram artifacts are wanted, retain them:

   ```sh
   uv run md2pdf path/to/deck.md --output path/to/output.pdf --keep-tex
   ```

5. Confirm the command reports `Wrote <output path>`. When the required toolchain is available, inspect the generated PDF for layout, clipping, and asset resolution.

Run `uv run md2pdf --version` to identify the installed tool version.

## Authoring decks

Start a deck with optional YAML front matter. The bundled `default` theme requires `title`; `author`, `date`, `theme`, `fontsize`, and `short_title` are optional.

```markdown
---
title: Quarterly Review
author: Example Author
date: 2026-10-12
theme: default
fontsize: normal
---

# First slide

- One point
- Another point

---

# Second slide

Ordinary Markdown prose, tables, block quotes, and inline code are supported.
```

- Separate slides with a line containing only `---` (three or more dashes). The initial top-of-file fenced block is front matter, not a slide break.
- A leading level-one heading (`# Heading`) becomes the frame title. Do not use a different heading level when a Beamer frame title is intended.
- Front-matter scalars are coerced to strings and LaTeX-escaped. Use `short_title` to override the footer title.
- `fontsize` must be a named scale provided by the selected theme. If it is absent, the theme's `default_font_scale` applies; an unknown scale fails loudly.

## Strict fit-to-frame slides

Picture and diagram detection is intentionally strict. A qualifying slide contains exactly one `# Heading` and exactly one special content block, with no prose, bullets, tables, second image/block, or other non-blank content.

### Picture slides

Use exactly one Markdown image after the title. Its alt text becomes the caption.

```markdown
# Architecture

![System architecture](assets/architecture.png)
```

Add any other content only when an ordinary (not fit-to-frame) slide is desired.

### Diagram slides

Use exactly one fenced code block whose info string is exactly `d2` or `mermaid`.

````markdown
# Delivery flow

```d2
Producer -> Broker: publish
Broker -> Consumer: deliver
```
````

- `d2` renders to vector PDF with the `d2` CLI.
- `mermaid` renders to PNG with `mmdr`.
- Extra info-string parameters, such as `d2 layout=elk`, do **not** qualify as a diagram slide and emit a non-fatal near-miss warning.
- Diagram render failures (missing CLI, timeout, or non-zero exit) fail the build; correct the source or install the appropriate renderer and retry.

## Themes

Theme selection precedence is:

```text
--theme-dir > --theme > front-matter theme: > default
```

Use the bundled neutral theme explicitly when appropriate:

```sh
uv run md2pdf deck.md --theme default
```

Use an external theme directory when a task supplies branded templates:

```sh
uv run md2pdf deck.md --theme-dir path/to/theme
```

An external theme directory must contain:

```text
theme.yaml
preamble.tex.j2
title.tex.j2
thankyou.tex.j2
assets/  # optional logo/image files
```

`theme.yaml` defines the theme name, palette, font settings, logos, required/optional front-matter fields, `font_scales`, and `default_font_scale`. The templates receive LaTeX-escaped front-matter fields, unescaped `raw_fields`, `palette`, `font`, `logos`, and `assets_dir`. External templates are sandboxed and are validated before rendering. Do not assume a particular custom theme's required fields or scales; inspect its `theme.yaml` first.

## Troubleshooting

- If Pandoc or XeLaTeX fails, md2pdf preserves diagnostic artifacts (`body.md`, `preamble.tex`, and frame `.tex` files) in a diagnostic directory and writes their paths to stderr. Read the reported files and fix the cited source/template issue instead of guessing.
- If a theme is rejected, verify its required files, valid YAML, compilable templates, required front-matter keys, and requested font scale.
- If images or logos fail to resolve, first check that paths are relative to the deck/theme as expected and that the files exist. Theme assets are included in both Pandoc's resource path and LaTeX's graphic path.
- If a bundled theme name is unknown, use one of the bundled names (currently `default`) or supply a valid `--theme-dir`.
- Use `--keep-tex` when reproducible intermediate TeX and a persistent `<stem>_diagrams` directory are needed; otherwise temporary diagram artifacts are cleaned up after rendering.

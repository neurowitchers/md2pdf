# md2pdf

Markdown to branded PDF slides (Pandoc + Beamer) with a theme-as-data system.

`md2pdf` renders a Markdown deck into a PDF slide deck. The engine is
theme-agnostic; branding (palette, fonts, logos, title/thank-you frames,
required front-matter fields, named font-scales) is supplied by a **theme** — a
directory containing a `theme.yaml` plus Jinja2 `.tex.j2` templates. The bundled
`default` theme ships inside the package and loads via `importlib.resources`; an
external theme can be supplied via `--theme-dir`.

## Requirements

- Python ≥ 3.13 and [`uv`](https://docs.astral.sh/uv/).
- [Pandoc](https://pandoc.org/) and a XeLaTeX engine (TeX Live / MiKTeX) on
  `PATH` — required to produce a PDF.
- Optional, only for diagram slides:
  - [`d2`](https://d2lang.com/) for `d2` fences (rendered to vector PDF).
  - [`mmdr`](https://github.com/mermaid-js/mermaid-cli) (mermaid CLI) for
    `mermaid` fences (rendered to PNG).

The binary resolver is cross-platform: it probes the plain name and a
platform-appropriate suffix (`.exe` on Windows, extensionless on POSIX) on
`PATH` and in the common fallback locations `~/go/bin` and `~/.cargo/bin`.

## Install

```sh
uv sync
```

## Usage

```sh
uv run md2pdf INPUT.md [--output OUT.pdf] [--keep-tex] [--theme NAME] [--theme-dir PATH]
```

Flags:

- `INPUT.md` — the Markdown deck (with optional YAML front-matter).
- `--output OUT.pdf` — output PDF path. Optional; defaults to the input path
  with a `.pdf` extension (beside the input Markdown).
- `--keep-tex` — keep the intermediate `.tex` and persist a `<stem>_diagrams`
  directory beside the output (otherwise diagrams render under a temp dir that
  is cleaned up).
- `--theme NAME` — a bundled theme name (`default`).
- `--theme-dir PATH` — an external theme directory (see *Writing a theme*).
- `--version` — print the version and exit.

On a pandoc/xelatex failure the engine preserves the intermediate build
artifacts (`body.md`, `preamble.tex`, frame `.tex`) in a diagnostic directory
and prints their paths to stderr, so XeLaTeX line numbers are inspectable
without re-running with `--keep-tex`.

### Theme selection and precedence

Decks are self-describing: front-matter MAY declare `theme: <name>`. Resolution
precedence is:

```
--theme-dir (CLI)  >  --theme (CLI)  >  front-matter `theme:`  >  default
```

A deck carrying `theme: <name>` therefore renders correctly even when invoked
without CLI flags. An unknown bundled theme name fails loudly, listing the known
bundled themes.

## Markdown dialect

A deck is standard Markdown with an optional YAML front-matter block delimited
by `---`:

```markdown
---
title: My Deck
author: A. Author
date: 2026-10-09
theme: default
fontsize: normal
---

# First slide

- bullet
- bullet

---

# Second slide

Prose and `inline code` work as usual.
```

Conventions:

- **Slide breaks.** Slides are separated by a line containing only `---`
  (three or more dashes). The front-matter block is the first such fenced
  region at the top of the file.
- **Slide titles.** A leading `# Heading` becomes the Beamer frame title
  (`--slide-level=1`).
- **Front-matter scalars** are all coerced to strings, so unquoted YAML values
  such as `wp: 2` or `date: 2026-10-09` are safe. Scalar values are
  LaTeX-escaped automatically before being placed in the template context.
- **`fontsize`.** An optional front-matter key selecting a named body-font
  scale defined by the theme (e.g. `xsmall`, `small`, `normal`, `large`,
  `xlarge`). When absent, the theme's `default_font_scale` is used. An unknown
  scale name fails loudly.
- **`short_title`.** An optional front-matter key overriding the Beamer footer
  short title (defaults to `title`).

### Picture slides (fit-to-frame)

A slide that contains **exactly** one `# Heading` and **exactly** one Markdown
image — and nothing else (no bullets, prose, tables, or a second image) — is
rewritten to a full-frame, fit-to-frame `\includegraphics` layout. The image
alt text becomes a caption.

```markdown
# Architecture

![The system architecture](assets/architecture.png)
```

Any additional non-blank content disqualifies the slide, which then renders as
an ordinary slide.

### Diagram slides (fit-to-frame)

A slide with **exactly** one `# Heading` and **exactly** one fenced code block
whose info string is the lone token `mermaid` or `d2` — and nothing else — is
rendered to an image and placed fit-to-frame.

````markdown
# Flow

```d2
a -> b -> c
```
````

Rendering details:

- `d2` → vector PDF (`--theme 0 --browser 0`).
- `mermaid` → PNG via `mmdr` (`-w 2400 -t default`, opaque white background).
- Rendered diagrams are content-addressed and cached; a zero-byte cache entry
  is re-rendered. Missing CLI, a non-zero exit, or a timeout fails loudly, and
  partial output files are cleaned up.
- Info strings carrying extra parameters (e.g. ` ```d2 layout=elk `) are
  **not** treated as strict diagram slides; a near-miss fence emits a non-fatal
  warning.

### Two-column slides (picture + text, side by side)

A slide can place two things side by side — e.g. a picture or schema on the
left and bullets on the right — using a lightweight `:::` convention. The slide
is a single `# Heading` whose body **opens** with a `:::` delimiter and holds
**exactly two regions** framed by three `:::` lines (opening, separator,
closing):

```markdown
# Picture and text, side by side

:::
![A fit-to-column image; the alt text becomes a caption.](assets/arch.png)
:::
- The left column is a single image, scaled to fit its half.
- The right column is ordinary Markdown: bullets, prose, `inline code`.
:::
```

Rules and behaviour:

- **Strictly two columns, 50/50.** Each region becomes one half-width Beamer
  column; there is no width syntax and no N-column support. Columns are
  constrained to the text width (they respect the theme margins and logos) and
  are top-aligned.
- **Both sides fit.** A region whose sole content is one image **or** one lone
  `d2`/`mermaid` fence is scaled to fit its column (width bounded to the column,
  height bounded, aspect ratio preserved). An image region's alt text renders as
  a small caption. Any other region (bullets, prose, tables, mixed content)
  renders as normal Markdown flowing within its half.
- **Diagrams in a column** render through the same cache as whole-slide diagram
  slides. A diagram region carries **no** caption (there is no alt-text syntax
  for a fence); put any figure label in the companion text column:

  ````markdown
  # Diagram and notes, side by side

  :::
  ```d2
  ingest -> engine -> cache -> serve
  ```
  :::
  - The left column is a `d2` diagram, rendered and fit to the column.
  - Use this column for the figure label or explanation.
  :::
  ````

- **Opt-in and backwards compatible.** The feature triggers **only** when a
  slide's body opens (after the `# Heading`) with a `:::` line. Ordinary slides
  — including those using Pandoc fenced divs such as `::: notes` or
  `::: {.callout}` — are untouched.
- **Fail-loud.** A slide that opts in but is malformed fails the build with an
  actionable, slide-identifying message rather than producing a broken layout.
  Failing cases: not exactly three `:::` delimiter lines; an empty region;
  non-blank content after the closing `:::`; an unterminated code fence inside a
  column; a diagram region that fails to render.
- **Reserved markers.** A horizontal rule `---` is always a *slide* break, so it
  cannot be used inside a column. Nested Pandoc fenced divs (e.g. `::: notes`)
  are not supported inside a two-column body.

See `examples/two-column-demo.md` for a working deck.

## Writing a theme

A theme is a directory with this shape (the bundled themes under
`src/md2pdf/themes/<name>/` follow it, and it is also the valid layout for an
external `--theme-dir`):

```
<theme>/
  theme.yaml          # palette, font, logos[], required/optional fields,
                      # font_scales{}, default_font_scale   (NO headline expr)
  preamble.tex.j2     # colors/fonts/beamer setup (header include)
  title.tex.j2        # title frame; composes the headline from fields
  thankyou.tex.j2     # thank-you frame
  assets/             # logo images (optional)
```

### `theme.yaml` schema

- `name` — human-readable theme name.
- `palette` — map of name → HTML hex. Exposed to templates as `palette.<key>`
  and typically turned into LaTeX colours in `preamble.tex.j2`.
- `font` — `sans` primary family + `fallback`.
- `logos` — ordered list of entries (e.g. `{ file, role, height }`) that drive
  a template loop; may be empty.
- `required_fields` — front-matter keys that MUST be present (loud failure if
  missing). The `default` theme requires only `title`.
- `optional_fields` — recognised optional keys (e.g. `author`, `date`,
  `subtitle`, `fontsize`, `short_title`).
- `font_scales` — map of named scale → point size (e.g. `normal: 11pt`).
- `default_font_scale` — the scale used when `fontsize` is absent.

There is intentionally **no** `headline` expression in `theme.yaml`: the title
headline is composed directly inside `title.tex.j2` from the available fields
(the `default` theme uses `{{ title }}`; a custom theme may lay out additional
fields, e.g. `{{ title }}` plus a `{{ subtitle }}` line).

### Template context

The three `.tex.j2` templates (`preamble`, `title`, `thankyou`) are rendered
with:

- **Each front-matter field by name**, coerced to `str` and **LaTeX-escaped by
  default** — template authors do not need a per-token `| latexescape` filter.
- **`raw_fields`** — the same values **unescaped**, for the rare case where raw
  TeX injection is intended.
- **`palette`**, **`font`**, **`logos`** from `theme.yaml`.
- **`assets_dir`** — the resolved path to the theme's assets, for
  `\includegraphics`.

### Validation and sandboxing

- A theme directory is validated before rendering: the required files
  (`theme.yaml`, `preamble.tex.j2`, `title.tex.j2`, `thankyou.tex.j2`) must be
  present, the YAML must parse, and the templates must compile. Failures emit
  structured, actionable errors naming the theme and the offending file.
- **Bundled** themes are trusted and use a standard Jinja2 environment.
- **External** themes (`--theme-dir`) are rendered through a
  `jinja2.sandbox.SandboxedEnvironment`.
- The theme assets directory is registered in both pandoc's `--resource-path`
  and a brace-protected, forward-slash-normalised LaTeX `\graphicspath`, so
  asset paths containing spaces resolve under XeLaTeX.

## Bundled themes

- **`default`** — neutral, brand-free (MIT). Requires only `title`.

To add your own branding, copy the `default` theme to a new directory, adjust
`theme.yaml` and the `.tex.j2` templates, and point `--theme-dir` at it (or drop
it under `src/md2pdf/themes/<name>/` to bundle it). Proprietary logo assets can
be kept out of the tree via an asset-dir override — set
`MD2PDF_<THEMENAME>_ASSETS_DIR` (or the generic `MD2PDF_ASSETS_DIR`), or an
absolute `assets_dir` key in `theme.yaml`.

## Development

```sh
uv sync
uv run pytest
```

End-to-end `build()` tests are `skipif`-guarded on toolchain availability
(pandoc/xelatex/d2/mmdr). Pandoc-only TeX-generation tests give structural
coverage even without a full LaTeX engine. CI runs on every push/PR (see
[`.github/workflows/ci.yml`](./.github/workflows/ci.yml)).

## Licence

MIT. See [`LICENSE`](./LICENSE). The MIT licence covers the code and the neutral
`default` theme. Any proprietary logo assets added via a custom theme remain
under their own licence and are not covered by this repository's MIT licence.

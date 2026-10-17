---
generated-by: "Brainstorm"
generated-at: 2026-10-17T22:40:32+03:00
status: drafting
---

# Technical Brainstorm: Two-Column / Picture-and-Text Slides

## Problem Statement & Scope

- **Core Objective:** Let a deck author place a picture (or schema/diagram)
  and text *side by side* on one slide — minimally a two-column layout (e.g.
  image left, prose/bullets right) — within md2pdf's existing theme-agnostic,
  convention-driven Markdown dialect.
- **Scope Boundaries:**
  - **IN:** A way to author a slide whose body is split into columns, where one
    (or both) columns may hold an image, a diagram fence (`mermaid`/`d2`), or
    ordinary Markdown (bullets, prose, tables). Minimum viable = two columns;
    the design should not *preclude* N columns if it falls out cheaply.
    Fit-to-column image sizing analogous to today's fit-to-frame. Updated
    README dialect docs + an example deck + tests.
  - **OUT:** Arbitrary free-form absolute positioning / overlays; multi-row
    grid layouts; per-column vertical fine-tuning beyond what Beamer's `align`
    affords; PPTX output (md2pdf targets Beamer PDF only); animation/overlays
    (`\pause`). A full "layout language" is explicitly out — we want the
    *minimal* convention that unblocks picture+text.
- **Key Constraints:**
  - **Theme-agnostic engine.** Column handling must live in the engine/slides
    layer, not in themes. Themes supply branding only (`palette`, `font`,
    `logos`, title/thank-you frames). No new required theme capability.
  - **Convention over new syntax, where feasible.** Today picture/diagram
    slides are detected by *strict convention* (one `# Title` + one image/fence,
    nothing else) with **no new syntax**. A column feature almost certainly
    needs *some* authoring marker; the design tension is how heavy that marker
    is and whether it stays valid CommonMark.
  - **Backwards compatibility.** Existing strict picture slides, strict diagram
    slides, and ordinary slides must render identically. A slide that does not
    opt into columns is untouched.
  - **Pandoc/XeLaTeX pipeline.** Output is Beamer via pandoc `--slide-level=1`.
    Whatever we emit must survive pandoc's frame splitting and the existing
    `\graphicspath` / `--resource-path` asset resolution (incl. paths with
    spaces).
  - **Fail-loud ethos.** Near-miss / malformed column markup should warn or
    fail with an actionable message, consistent with the current diagram
    near-miss warning.

## Technical Baseline & External Research

### Current Architecture (local audit)

- **`src/md2pdf/slides.py`** — pure, theme-agnostic detection:
  - `split_slides(body)` splits on `^-{3,}$` lines.
  - `match_picture_slide(chunk)` → `{title, alt, path}` **iff** exactly one
    `# Heading` + exactly one `![alt](path)` and *nothing else*; any other
    non-blank line disqualifies.
  - `match_diagram_slide(chunk)` → `{title, lang, source}` **iff** exactly one
    `# Heading` + exactly one fenced block whose info string is the lone token
    `mermaid` or `d2`; verbatim body captured; unterminated/extra-param fences
    disqualify.
  - `_chunk_has_diagram_fence(chunk)` drives a non-fatal near-miss warning.
  - Regexes: `_IMAGE_RE`, `_H1_RE`, `_SLIDE_BREAK_RE`, `_FENCE_RE`;
    `_DIAGRAM_LANGS = ("mermaid", "d2")`.
- **`src/md2pdf/engine.py`** — assembly:
  - `picture_body_tex(alt, path)` emits a raw-LaTeX frame body that centres
    `\includegraphics[width=\textwidth,height=0.78\textheight,keepaspectratio]`
    with an optional caption in theme-defined `captioncolor`, wrapped in
    `\vfill … \vfill`.
  - `preprocess_body(body, diagram_dir)` iterates chunks: a strict picture or
    diagram slide becomes `# Title\n\n` + a ```` ```{=latex} ```` raw block
    (the heading stays Markdown so pandoc opens the branded frame; only the
    body is raw LaTeX). Diagrams are rendered to an image via
    `render_diagram(...)` and emitted by filename (relative). Non-strict chunks
    with a diagram fence trigger the warning; everything else passes through
    untouched. Chunks re-joined with `\n\n---\n\n`.
  - `build(...)` writes `body.md`, injects a prologue (`graphicx`, `fontsize`,
    footer `\title[...]`, and a brace-protected `\graphicspath{{diagram_dir/}{assets_dir/}}`),
    runs pandoc→beamer→xelatex, preserves diagnostics on failure.
- **`src/md2pdf/diagrams.py`** — `render_diagram(lang, source, out_dir, title)`;
  content-addressed cache; `d2`→vector PDF, `mermaid`→PNG; fail-loud.
- **Key insight:** picture/diagram handling is *strictly* an all-or-nothing
  per-slide rewrite. There is **no** sub-slide region model today — a slide is
  either a whole picture, a whole diagram, or passed through to pandoc wholesale.
  Columns introduce the first notion of *intra-slide regions*.

### State of the Art / Pandoc capability (external research)

- **Pandoc natively supports columns for Beamer** via *fenced divs*
  ([pandoc User's Guide §10.6](https://pandoc.org/demo/example33/10.6-columns.html)):

  ```markdown
  ::: columns
  :::: {.column width="40%"}
  left contents (markdown processed normally)
  ::::
  :::: {.column width="60%"}
  right contents
  ::::
  :::
  ```

  - Crucially, **pandoc processes Markdown *inside* the column divs** — unlike
    hand-written `\begin{columns}` raw LaTeX, where pandoc leaves the body
    verbatim (confirmed on StackOverflow: raw `columns` env does not get its
    inner markdown processed). This means we can let authors write real bullets
    and even images inside columns and let pandoc do the work.
  - Beamer-only extras: `align=top|center|bottom` on `columns`/`column`,
    `totalwidth`, and the `.onlytextwidth` class (sets totalwidth to
    `\textwidth`). More than two columns work for Beamer.
  - These `:::` fenced divs are standard Pandoc Markdown (not CommonMark-core,
    but part of the dialect pandoc already parses — md2pdf *is* a pandoc deck).
- **Implication:** the heavy lifting (two-column box layout, markdown rendering
  within columns) is *already available in pandoc* and needs **zero** new LaTeX
  from us for the text/bullet case. The only genuinely md2pdf-specific concern
  is **fit-to-column images and diagrams** — i.e. making an image or a rendered
  `mermaid`/`d2` diagram size nicely within a column box, reusing the spirit of
  `picture_body_tex` but scoped to `\columnwidth` instead of `\textwidth`.

## Open Questions & User Clarifications

#### Q1: Authoring surface — native pandoc divs vs. a lighter md2pdf convention?
- **Context:** Pandoc's `::: columns` / `:::: {.column width=...}` already works
  and renders markdown inside columns. We could **(a)** simply *document &
  support* that native syntax (minimal engine work: only make images/diagrams
  inside columns fit the column), or **(b)** invent a lighter md2pdf-specific
  convention (e.g. a `:::` shorthand, or a `## Left / ## Right` split, or a
  single horizontal-rule-like intra-slide separator) that we rewrite into
  pandoc columns. (a) is cheapest and most powerful but exposes raw pandoc div
  syntax to authors; (b) is prettier but adds a parser and a new dialect rule.
- **User Input:**
    <!-- USER_INPUT_START:Q1 -->
    (b) `:::` shorthand will do
    <!-- USER_INPUT_END:Q1 -->

#### Q2: Images/diagrams inside columns — how smart should fit-to-column be?
- **Context:** Today a *whole-slide* image is fit to `\textwidth` /
  `0.78\textheight`. Inside a column we'd want the image to fit `\columnwidth`
  and some bounded height. Options: **(1)** just let pandoc render
  `![alt](path)` normally inside the column (simplest; author controls size via
  normal means, images default to natural size and may overflow); **(2)**
  md2pdf detects an image/diagram that is the sole content of a column and
  rewrites it to a fit-to-`\columnwidth` `\includegraphics` (consistent with
  today's picture slides, needs intra-column detection); **(3)** support a
  diagram fence (`mermaid`/`d2`) inside a column, rendering it to an image and
  fitting it (requires routing `diagram_dir` through the column path).
- **User Input:**
    <!-- USER_INPUT_START:Q2 -->
    Neither: always 50/50, both sides scele to fit
    <!-- USER_INPUT_END:Q2 -->

#### Q3: Column count & width defaults — strictly two, or N?
- **Context:** Your minimum is two columns (pic left / text right). Pandoc
  supports N for Beamer for free. Do we **lock the convention to exactly two**
  (simpler to document, e.g. a single "left ||| right" split with a default
  50/50 or configurable ratio), or **allow N columns** with explicit widths?
  Also: should there be a default width split (e.g. 50/50, or 40/60 for
  pic+text) when the author omits widths?
- **User Input:**
    <!-- USER_INPUT_START:Q3 -->
    strictly two columns, 50/50
    <!-- USER_INPUT_END:Q3 -->

#### Q4: Interaction with the frame title & vertical alignment?
- **Context:** Current picture/diagram slides keep `# Title` as the branded
  frame title band and centre the body beneath it. For a two-column slide we'd
  presumably keep the same `# Title` convention and place the columns in the
  body. Beamer defaults columns to `align=top`. For a pic-left/text-right slide,
  top-aligned usually reads best, but a tall image may want vertical centring.
  Do you want a sensible fixed default (top), or an author-controllable align?
- **User Input:**
    <!-- USER_INPUT_START:Q4 -->
     Keep `# Title` + columns-in-body with a fixed `align=top` 
    <!-- USER_INPUT_END:Q4 -->

#### Q5: Failure / near-miss behaviour?
- **Context:** The diagram feature emits a non-fatal warning on a near-miss
  fence. For columns we may hit: unbalanced `:::` fences, a `.column` without a
  width, widths that don't sum sensibly, or a diagram fence inside a column that
  can't render. Preference: **warn-and-pass-through** (lenient, like the diagram
  near-miss) vs **fail-loud** (like missing required fields / unknown fontsize)?
- **User Input:**
    <!-- USER_INPUT_START:Q5 -->
    fail-loud
    <!-- USER_INPUT_END:Q5 -->

### Baseline Assumptions (used if the questions are left at default)

- **A1 (Q1):** Hybrid leaning to native — *support pandoc's native `::: columns`
  divs directly* (document them as the two-column mechanism), and add **only**
  the md2pdf-specific value of fit-to-column images/diagrams. No bespoke parser.
- **A2 (Q2):** A column whose sole content is a single image **or** a single
  `mermaid`/`d2` fence is auto-rewritten to fit `\columnwidth` (reusing the
  `picture_body_tex` idea, scoped to the column); plain mixed markdown in a
  column is handed to pandoc untouched. Diagram fences inside columns **do**
  render in v1 (routing `diagram_dir` through the column rewrite).
- **A3 (Q3):** Allow N columns (pandoc affords it free) but document two as the
  common case; when a `.column` omits `width`, do not invent one — let pandoc's
  behaviour stand, and warn. No forced default split (keeps us out of layout
  opinions).
- **A4 (Q4):** Keep `# Title` as the frame title; columns live in the body;
  default `align=top`; a column image keeps its alt text as a small caption
  under it, as whole-slide pictures do today.
- **A5 (Q5):** Split — fail-loud on structural breakage that pandoc/xelatex
  would choke on and we can detect cheaply (e.g. a diagram fence in a column
  that fails to render → reuse `render_diagram`'s existing fail-loud); warn
  (non-fatal) on cosmetic issues (missing width, near-miss markers), mirroring
  the diagram near-miss warning.

## Architectural Approaches Evaluated

> *(Populated in Phase 3 after the questions above are answered. Candidate
> directions already visible from the baseline — recorded here as a preview,
> not a decision:)*
>
> - **Approach A — "Pass-through native divs + fit-to-column rewriter":**
>   Document pandoc `::: columns`. In `preprocess_body`, detect columns whose
>   sole content is an image/diagram and rewrite just that content to a
>   `\columnwidth`-fit raw-LaTeX block (diagrams rendered via `render_diagram`).
>   Everything else is pandoc's job. Smallest surface; no new dialect parser.
> - **Approach B — "md2pdf column convention":** A lighter authoring marker
>   (e.g. a dedicated separator or `## Left/## Right`) parsed in `slides.py` and
>   lowered to pandoc column divs. Prettier Markdown, but a new parser + new
>   dialect rule to document and test.
> - **Approach C — "Raw-LaTeX columns template":** Emit `\begin{columns}` raw
>   LaTeX ourselves. Rejected early: pandoc won't process markdown inside raw
>   `columns`, forcing authors into LaTeX — contradicts the dialect ethos.

## Structured Comparison & Methodology

> *(SWOT matrix populated in Phase 3.)*

## Recommendation

> *(Populated in Phase 4.)*

### Key Risks & Mitigations

> *(Populated in Phase 4.)*

### Summary Table

> *(Populated in Phase 4.)*

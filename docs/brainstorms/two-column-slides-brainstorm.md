---
generated-by: "Brainstorm"
generated-at: 2026-10-17T22:40:32+03:00
status: recommended
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

## Resolved User Decisions (Phase 2 answers)

The user's filled `USER_INPUT` answers are **authoritative** and materially
narrow the design:

| Q | Decision | Consequence |
|---|----------|-------------|
| Q1 | **(b) a `:::` shorthand** — a bespoke md2pdf convention, *not* raw pandoc divs | md2pdf owns the authoring marker and lowers it to Beamer columns; authors never type pandoc div attributes. |
| Q2 | **Neither (1) nor (2): always 50/50, both sides scale to fit** | No per-column width syntax. **Both** columns are fit-to-column — images/diagrams scale to the half-frame box; text scales within its half. |
| Q3 | **Strictly two columns, 50/50** | No N-column support, no width attributes. Exactly one left / one right, each `0.5\textwidth`. |
| Q4 | **Keep `# Title` + columns-in-body, fixed `align=top`** | Frame title band preserved; the two-column block is the frame body; vertical `align=top`. No author-exposed alignment. |
| Q5 | **Fail-loud** | Malformed two-column markup (wrong number of regions, empty region, unrenderable diagram) raises `SystemExit` with an actionable message — consistent with required-field / fontsize failures — rather than a lenient warn-and-pass-through. |

These answers **retire the Phase-1 baseline preview**: Approach A (expose native
pandoc divs) is rejected by Q1(b); N-column generality (baseline A3) is rejected
by Q3; the lenient-warning posture (baseline A5) is rejected by Q5. The design
space collapses to *how* to implement the `:::` two-column shorthand.

## Architectural Approaches Evaluated

All three approaches below honour the fixed decisions (one `:::`-delimited
two-column region per slide, strictly 50/50, both sides fit, `# Title` kept,
`align=top`, fail-loud). They differ in **where the `:::` marker is parsed and
what we emit to pandoc**.

### Approach A — Lower `:::` to native pandoc column divs (markdown preserved)

- **Concept:** Treat `:::` as a slide-local separator. In `slides.py`, add
  `match_two_column_slide(chunk)` that recognises a slide of the exact shape
  "`# Title` + a `:::`-fenced two-column region" and returns the two region
  bodies. In `preprocess_body`, lower it to pandoc's **native** column divs:

  ````markdown
  # Title

  ::: columns
  :::: {.column width="50%" align=top}
  <left body, markdown preserved verbatim>
  ::::
  :::: {.column width="50%" align=top}
  <right body, markdown preserved verbatim>
  ::::
  :::
  ````

  Pandoc then renders the markdown inside each column (bullets, prose, tables)
  for free. The md2pdf-specific "both sides scale to fit" is layered **inside**
  each column: if a region's sole content is an image or a `mermaid`/`d2`
  fence, that content is rewritten to a `\columnwidth`-fit raw-LaTeX block
  (reusing a column-scoped variant of `picture_body_tex`, diagrams via
  `render_diagram`). A text region is wrapped so its content scales to the box.
- **Component Changes:** `slides.py` (+`match_two_column_slide`, a `:::` region
  parser, `_COLUMN_RE`); `engine.py` (`preprocess_body` branch + a
  `column_body_tex(...)` helper scoped to `\columnwidth`; route `diagram_dir`
  into the column path); README dialect section; a new example deck; tests.
- **Dependencies Introduced:** None (pandoc's column divs are built in).

### Approach B — Emit raw-LaTeX `columns`/`column` environment directly

- **Concept:** Same `:::` detection in `slides.py`, but `preprocess_body` emits
  a full raw-LaTeX `\begin{columns}[t] … \column{0.5\textwidth} … \end{columns}`
  block, placing each region's content inside. Because pandoc leaves raw-LaTeX
  bodies **unprocessed**, each region's markdown would have to be converted to
  LaTeX by us (or forbidden), so in practice regions would be limited to images
  / diagrams / pre-escaped text.
- **Component Changes:** `slides.py` (detection); `engine.py` (raw columns
  emitter, per-region LaTeX generation); README; example; tests.
- **Dependencies Introduced:** None, but effectively re-implements markdown→TeX
  for column bodies.

### Approach C — Per-region sub-render via pandoc, then splice

- **Concept:** `:::` detection in `slides.py`; for each region, run a **separate
  pandoc invocation** to convert that region's markdown to a LaTeX fragment,
  then splice both fragments into a raw `columns` environment.
- **Component Changes:** `engine.py` (two extra pandoc calls per two-column
  slide, fragment splicing); `slides.py` (detection); README; example; tests.
- **Dependencies Introduced:** None new, but adds N extra pandoc subprocess
  calls per slide and a fragment-assembly surface.

## Structured Comparison & Methodology

### SWOT Matrix

| Approach | Strengths | Weaknesses | Opportunities | Threats/Risks |
|----------|-----------|------------|---------------|---------------|
| **A — lower `:::` to native pandoc columns** | Pandoc renders in-column markdown for free; smallest new code; reuses `picture_body_tex`/`render_diagram` for the fit case; single pandoc pass; matches existing "rewrite chunk → emit markdown+raw-latex" pattern exactly | Must get the lowering string right (balanced `::::`); "both sides fit" needs a column-scoped tex helper | Clean path to future N-column or width override if ever wanted (just unlock what pandoc already does); diagrams-in-columns reuse the cache | Pandoc div-nesting depth / fence-length rules (outer `:::` vs inner `::::`) must be correct or pandoc mis-nests |
| **B — raw-LaTeX columns** | Full control over the emitted TeX; no reliance on pandoc div behaviour | **Loses markdown-in-column** (pandoc won't process raw bodies) → either forbid bullets/prose in columns (contradicts "pic + text") or re-implement md→TeX; most code; brittle escaping | Minimal | High: re-implementing markdown rendering is a large, bug-prone surface; directly fights the dialect ethos |
| **C — per-region sub-render** | Keeps markdown in columns; full control of splicing | Multiple pandoc processes per slide (perf); fragment splicing fragile (preamble/escaping drift between passes); diverges from the single-pass architecture | Could isolate per-region failures | Medium–high: process-count blowup on diagram-heavy decks; two pandoc dialects/versions to keep consistent; new failure modes |

**Methodology note.** The decisive axis is *who renders the in-column markdown*.
Q2/Q4 require real bullets/prose beside a picture, so any approach that forfeits
pandoc's in-column markdown rendering (B) or multiplies pandoc passes (C) pays a
large, recurring cost. Approach A keeps the engine's existing one-pass,
"rewrite-chunk-to-markdown+raw-latex" shape and simply *delegates* the column
box to the one pandoc feature built for it.

## Recommendation

**Adopt Approach A — parse a bespoke `:::` two-column shorthand in `slides.py`
and lower it to pandoc's native `columns`/`column` divs, with both regions
fit-to-column (50/50, `align=top`), failing loud on malformed markup.**

Rationale:

- **Honours every fixed decision directly.** The `:::` marker is md2pdf's own
  (Q1b); we emit exactly two `width="50%"` columns (Q2/Q3); `align=top` is set
  on the block (Q4); detection and lowering validate structure and raise
  `SystemExit` on any deviation (Q5).
- **Minimal, idiomatic code.** It mirrors the existing picture/diagram pipeline:
  `slides.py` gains a strict matcher (`match_two_column_slide`) exactly like
  `match_picture_slide`/`match_diagram_slide`; `engine.py` gains a
  `preprocess_body` branch that emits `# Title` + the lowered columns, reusing a
  `\columnwidth`-scoped variant of `picture_body_tex` and the existing
  `render_diagram` cache for the fit-to-column image/diagram case.
- **Pandoc does the hard part.** In-column bullets/prose/tables render natively
  (confirmed against the pandoc User's Guide §10.6), so "picture + text" works
  without md2pdf re-implementing markdown→TeX (the fatal cost of B and the
  perf/splice cost of C).
- **Single pass, no new dependencies.** Keeps the one pandoc→beamer→xelatex
  invocation and the existing diagnostics/`\graphicspath` machinery intact.

Concretely, the recommended authoring convention (to be finalised in the spec):

````markdown
# Architecture at a glance

:::
![Pipeline overview](assets/pipeline.png)
:::
- Ingest normalises inputs
- The core engine fans out
- Results are cached and served
:::
````

A single slide, a `# Title`, and a `:::`-delimited body with **exactly two
regions** separated by a `:::` line (opening `:::`, left region, `:::`
separator, right region, closing `:::`). Left is an image → fit-to-column; right
is bullets → pandoc-rendered. Both halves are `0.5\textwidth`, top-aligned. The
exact fence/separator grammar (how many `:::` lines, whether a diagram fence may
be a region) is the first thing the spec/questionnaire must pin down, since the
inner regions themselves may contain fenced code (````` ``` `````) — the parser
must not confuse a diagram fence with a region separator.

### Key Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| `:::` grammar ambiguity vs. inner diagram fences / nested `:::` | Define a strict grammar in the spec: a two-column slide is `# Title` + one top-level `:::` block containing exactly two regions split by a single `:::` line; inner ```` ``` ```` fences are captured verbatim and never treated as separators (reuse the fence-aware scanning already in `match_diagram_slide`). |
| Lowering to pandoc divs mis-nests (outer vs inner colon count) | Emit outer `:::`/inner `::::` with distinct lengths exactly per pandoc §10.6; add a pandoc-only TeX-generation test (no XeLaTeX needed) asserting the emitted `\begin{columns}`/`\column` structure. |
| "Both sides scale to fit" is under-specified for text | Spec decides the text-fit mechanism (e.g. wrap in a sized box / let Beamer column flow). Default: text flows naturally in its `0.5\textwidth` column (Beamer handles overflow); only images/diagrams get explicit `\columnwidth` fit. Flag any residual overflow as a documented limitation. |
| Diagram fence inside a column must route `diagram_dir` | Thread `diagram_dir` into the column rewrite path exactly as the whole-slide diagram branch does; reuse `render_diagram` (content-addressed cache, fail-loud). |
| Fail-loud regressions on existing decks | Detection is strict and opt-in (only triggers on the `:::` shape); ordinary, picture, and diagram slides are untouched. Regression-test the three existing example decks still build byte-for-identical TeX structure. |
| Asset paths with spaces in column images | Reuse the existing `\graphicspath` + `--resource-path` handling and relative-filename emission; no new path logic. |

### Summary Table

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Authoring marker | Bespoke `:::` two-column shorthand (Q1b) | md2pdf owns the convention; authors never see pandoc div attributes. |
| Column count / split | Strictly two, 50/50 (Q2/Q3) | No width syntax; each region `0.5\textwidth`. |
| Fit behaviour | Both sides fit; image/diagram → `\columnwidth` fit, text flows in half-width (Q2) | Reuses `picture_body_tex`/`render_diagram`; pandoc renders text. |
| Title & alignment | Keep `# Title`; columns in body; `align=top` (Q4) | Preserves branded frame band; top-aligned reads best for pic+text. |
| Failure posture | Fail-loud `SystemExit` on malformed markup (Q5) | Consistent with required-field/fontsize errors; actionable messages. |
| Implementation | Approach A — parse `:::` in `slides.py`, lower to pandoc columns in `engine.py` | Smallest, idiomatic, single-pass; pandoc renders in-column markdown natively. |
| Rejected | B (raw-LaTeX columns), C (per-region sub-render) | B forfeits in-column markdown; C multiplies pandoc passes and splice risk. |

### Phased Execution Plan (next steps)

1. **Grammar & dialect spec.** Pin the exact `:::` two-column grammar
   (delimiter counts, region count = 2, whitespace rules, interaction with inner
   diagram fences, what disqualifies → fail-loud message text).
2. **`slides.py` detector.** `match_two_column_slide(chunk)` → `{title, left,
   right}` or `None`; strict, fence-aware; a near-but-invalid `:::` slide raises
   (fail-loud) rather than silently passing through.
3. **`engine.py` lowering.** `preprocess_body` branch emitting `# Title` + native
   pandoc `columns` (two `width="50%"`, `align=top`); a `column_body_tex`
   helper for the fit-to-column image/diagram case; route `diagram_dir`.
4. **Tests.** Pandoc-only TeX-generation tests for the emitted column structure
   and the image/diagram fit; unit tests for the detector (valid + each
   fail-loud case); a toolchain-guarded end-to-end `build()` test; regression
   tests that the three existing example decks are unaffected.
5. **Docs & example.** README "Two-column slides" dialect section; a
   `two-column-demo.md` example (pic-left/text-right and a diagram-in-column).


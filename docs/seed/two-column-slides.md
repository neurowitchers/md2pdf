---
generated-by: "Seed"
source: docs/brainstorms/two-column-slides-brainstorm.md
generated-at: 2026-10-17T22:54:43+03:00
draft: false
consumed: true
consumed-at: 2026-10-17T22:54:43+03:00
---

# Seed: Two-Column (Picture + Text) Slides

## Intent

Let a deck author put a picture/schema and text **side by side** on one slide —
a two-column layout (e.g. image left, bullets right). Add a lightweight,
md2pdf-owned `:::` shorthand that the engine lowers to a Beamer two-column
layout. This is the minimal convention that unblocks "pic + text" slides without
exposing raw pandoc/LaTeX column syntax to authors.

## Decisions (locked during brainstorm)

- **Authoring marker:** a bespoke `:::` two-column shorthand (not raw pandoc
  div attributes). md2pdf owns the convention.
- **Columns:** strictly **two**, always **50/50**. No width syntax, no N-column
  support.
- **Fit:** both sides scale to fit their half-frame. An image or a
  `mermaid`/`d2` diagram that is the sole content of a side is scaled to the
  column width (fit-to-column, like today's fit-to-frame picture slides);
  ordinary text/bullets flow within their half-width column.
- **Title & alignment:** keep the leading `# Title` as the branded Beamer frame
  title; the two columns live in the frame body; vertical alignment is fixed
  `align=top`.
- **Failure posture:** **fail-loud**. Malformed two-column markup (not exactly
  two regions, an empty region, an unrenderable diagram, unbalanced delimiters)
  raises a loud, actionable error — consistent with how missing required
  front-matter fields and unknown fontsizes already fail.

## Authoring shape (illustrative)

```markdown
# Architecture at a glance

:::
![Pipeline overview](assets/pipeline.png)
:::
- Ingest normalises inputs
- The core engine fans out
- Results are cached and served
:::
```

One `# Title`, then a `:::`-delimited body holding **exactly two** regions
separated by a `:::` line: opening `:::`, left region, `:::` separator, right
region, closing `:::`. Left (an image) scales to its half; right (bullets) is
rendered by pandoc in its half. Both halves are `0.5\textwidth`, top-aligned.

A diagram fence must also work as a region:

````markdown
# Flow and notes

:::
```d2
a -> b -> c
```
:::
- Step a kicks off ingest
- Step c serves results
:::
````

## Recommended implementation direction (from brainstorm)

Approach A: parse the `:::` two-column shorthand in `src/md2pdf/slides.py`
(a strict, fence-aware `match_two_column_slide` matcher alongside the existing
`match_picture_slide` / `match_diagram_slide`), and in `src/md2pdf/engine.py`
`preprocess_body` lower it to pandoc's **native** `columns` / `column` fenced
divs (two `width="50%"`, `align=top`), so pandoc renders in-column markdown
natively. Reuse a `\columnwidth`-scoped variant of `picture_body_tex` and the
existing `render_diagram` cache for the fit-to-column image/diagram case; route
`diagram_dir` into the column path. Single pandoc pass, no new dependencies.

Rejected alternatives: emitting raw-LaTeX `columns` ourselves (loses pandoc's
in-column markdown rendering) and per-region sub-rendering via extra pandoc
passes (perf + splice fragility).

## Scope boundaries

- **IN:** the `:::` two-column shorthand; fit-to-column for an image/diagram
  region; pandoc-rendered text/bullets in the other region; fail-loud on
  malformed markup; README dialect docs; an example deck; tests.
- **OUT:** N columns, custom width ratios, author-exposed alignment, overlays /
  absolute positioning, animation (`\pause`), PPTX output.

## Follow-up tasks

- README: add a "Two-column slides" subsection to the Markdown dialect docs.
- Add an `examples/two-column-demo.md` (pic-left/text-right + a diagram-in-column
  case) and wire it into the examples-build test.
- Pin the exact `:::` grammar and all fail-loud cases in the Full Spec,
  including how inner ```` ``` ```` diagram fences are distinguished from the
  `:::` region separators (the parser must be fence-aware).

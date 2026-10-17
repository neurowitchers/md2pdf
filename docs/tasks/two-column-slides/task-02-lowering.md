---
generated-by: "Split Tasks"
source: docs/specs/two-column-slides.md
generated-at: 2026-10-17T23:05:00+03:00
inputs-ready: false
completed: false
status: not-started
---

# Task 02: Lower `:::` Two-Column Slides to Pandoc Columns in `engine.py`

- [ ] **Completion**
- **Source spec**: `docs/specs/two-column-slides.md`
- **Depends on**: `task-01-detector.md`
- **Blocks**: `task-03-tests.md`, `task-04-docs-example.md`
- **Parallelism**: `Run sequentially after task-01`

## Objective

Add `column_body_tex` and a two-column branch to `preprocess_body` in
`src/md2pdf/engine.py` that lowers a detected two-column slide to native pandoc
`columns`/`column` divs (two `width="50%"`, `.onlytextwidth`, `align=top`),
rendering image/diagram regions fit-to-column and passing markdown regions
through (R2, R3, R4, R7).

## Scope & Traceability
- **Requirements / acceptance criteria**: R2, R3, R4, R7.
- **Testing & risk strategy items**: lowering structure; colon-nesting risk;
  diagram-in-column routing; critique E1 (`.onlytextwidth`), P2 (no `\vfill`),
  E6 (`0.72\textheight`).
- **Out of scope**: detection (task-01), tests (task-03), docs (task-04).

## Implementation Guidance
- **Files to create or modify**:
  - `src/md2pdf/engine.py`:
    - Refactor the image-fit emission out of `picture_body_tex` into a private
      `_fit_image_tex(width_expr, height_expr, alt, path, *, vcenter)`:
      - `vcenter=True` wraps in `\vfill … \vfill` (whole-slide behaviour,
        unchanged output for `picture_body_tex`);
      - `vcenter=False` emits a top-aligned
        `{\centering\includegraphics[...]\par <caption>}` block (critique
        task-level E1: use the `\centering` **declaration**, **not** the
        `\begin{center}…\end{center}` environment — the `center` environment is
        a `trivlist` that injects `\topsep`/`\parskip` vertical padding at the
        top of the column, pushing the image ~6–10pt below the companion
        bullets in a `columns[T]` layout). No `\vfill` (critique P2).
    - Keep `picture_body_tex(alt, path)` behaviour **byte-identical**: delegate
      to `_fit_image_tex(r"\textwidth", r"0.78\textheight", alt, path,
      vcenter=True)`.
    - Add `column_body_tex(alt, path) -> str = _fit_image_tex(r"\columnwidth",
      r"0.72\textheight", alt, path, vcenter=False)` (critique E6 height).
    - In `preprocess_body`, **before** the `match_picture_slide` branch, call
      `match_two_column_slide(chunk)`. On a dict:
      - For each of `left`/`right`, `classify_region`:
        - `("image", alt, path)` → ```` ```{=latex}\n<column_body_tex>``` ````;
        - `("diagram", lang, source)` → `render_diagram(lang, source,
          diagram_dir, title)` then `column_body_tex("", img.name)` in a raw
          block (reuse the relative-filename pattern from the diagram branch; if
          `diagram_dir is None` raise the same internal-error `SystemExit`);
        - `("markdown", text)` → the region text verbatim.
      - Emit the slide as (note the distinct fence lengths and `.onlytextwidth`,
        critique E1):
        ```text
        # <title>

        :::::: {.columns .onlytextwidth align=top}
        :::: {.column width="50%"}
        <left block>
        ::::
        :::: {.column width="50%"}
        <right block>
        ::::
        ::::::
        ```
      - `continue` to the next chunk (as the picture/diagram branches do).
    - Leave the existing picture/diagram/warning/passthrough logic unchanged.
- **Established patterns to follow**: the existing picture/diagram branches in
  `preprocess_body` (heading kept as markdown + raw-latex body; relative diagram
  filename; `continue`).
- **Constraints and non-goals**: single pandoc pass preserved; no new CLI flags;
  no new dependencies; theme-agnostic (`captioncolor` already defined by themes).

## Verification Requirements
- **Automated tests**: task-03 asserts the emitted structure; this task must
  make `preprocess_body` emit the `.columns .onlytextwidth align=top` block with
  two `width="50%"` columns and a `\columnwidth` `\includegraphics` for an image
  region.
- **Manual / integration checks**: run `preprocess_body` on a two-column chunk
  (image left, bullets right) and confirm the output contains
  `{.columns .onlytextwidth align=top}`, two `{.column width="50%"}`,
  `\includegraphics[width=\columnwidth,height=0.72\textheight,keepaspectratio]`,
  and no `\vfill` inside the column block.
- **Risk coverage**: E1 (margins), P2/E6 (alignment/overflow), colon-nesting.
- **Demo command**: `uv run python -c "from md2pdf.engine import preprocess_body;
  print(preprocess_body('# T\n\n:::\n![a](p.png)\n:::\n- one\n- two\n:::\n'))"`
- **Expected result**: printed body contains the `.columns .onlytextwidth
  align=top` div, two `.column width=\"50%\"` divs, a `\columnwidth`
  includegraphics in the left column, and `- one`/`- two` verbatim in the right.

## Handoff Notes
`picture_body_tex` output must not change (regression guard in task-03).
`column_body_tex` and `picture_body_tex` share `_fit_image_tex`; keep width/height
and the `vcenter` switch the only differences.

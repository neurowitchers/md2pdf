---
generated-by: "Split Tasks"
source: docs/specs/two-column-slides.md
generated-at: 2026-10-17T23:05:00+03:00
inputs-ready: false
completed: false
status: not-started
---

# Task 03: Tests — Unit, Pandoc-only TeX, E2E, Regression

- [ ] **Completion**
- **Source spec**: `docs/specs/two-column-slides.md`
- **Depends on**: `task-01-detector.md`, `task-02-lowering.md`
- **Blocks**: `None`
- **Parallelism**: `Run after task-01 and task-02`

## Objective

Add tests covering detection, fail-loud cases, lowered structure, fit-to-column
image/diagram, and backwards-compat, satisfying the spec's Testing & Risk
Strategy (R1–R7) and the critique's negative-case list (E7).

## Scope & Traceability
- **Requirements / acceptance criteria**: R1–R7.
- **Testing & risk strategy items**: all; especially critique E7 negative cases.
- **Out of scope**: docs/example (task-04), though the example build test lives
  in task-04.

## Implementation Guidance
- **Files to create or modify**:
  - `tests/test_slides.py` — add unit tests for `match_two_column_slide`:
    - valid slide (image left, bullets right) → correct `{title,left,right}`;
    - diagram-fence region recognised by `classify_region`;
    - returns `None` when body has no `:::` (ordinary slide, R6);
    - **fail-loud (`pytest.raises(SystemExit)`)** for each (critique E7):
      (a) 2 delimiters, (b) 4 delimiters, (c) non-blank content before the
      opening `:::` (P1), (d) non-blank content after the closing `:::`,
      (e) empty region, (f) `:::` inside a ```` ```python ```` code block must
      **not** be treated as a delimiter (E2 — a slide with one real pair around
      such a block still parses / fails per its real delimiter count),
      (g) unterminated inner code fence;
    - trailing blank lines after the closing `:::` are tolerated (E4);
    - up to 3 spaces indentation on a `:::` line is accepted (E8).
    - `classify_region` returns `image` / `diagram` / `markdown` correctly,
      including a mixed region (image + bullet) → `markdown`.
  - `tests/test_engine.py` — add pandoc-free tests on `preprocess_body` and
    `column_body_tex`:
    - two-column image+bullets chunk → output contains
      `{.columns .onlytextwidth align=top}`, exactly two `{.column
      width="50%"}`, a `\columnwidth,height=0.72\textheight,keepaspectratio`
      `\includegraphics`, no `\vfill` inside the column block (P2);
    - markdown region passes through verbatim;
    - **regression**: `picture_body_tex` output is unchanged (assert it still
      contains `\vfill` and `width=\textwidth,height=0.78\textheight`);
    - **regression**: `preprocess_body` on the three example decks'
      bodies (default-demo, picture-demo, diagram-demo markdown) is unchanged
      for the non-two-column slides (no `.columns` injected).
  - `tests/test_examples_build.py` — see task-04 for the e2e build of the new
    example (kept with the example so the fixture and test co-locate).
- **Established patterns to follow**: existing `tests/test_slides.py`
  (`test_match_picture_slide_*`) and `tests/test_engine.py` structure; use
  `pytest.raises(SystemExit)`.
- **Constraints and non-goals**: pandoc-only/structural tests must not require
  XeLaTeX; keep e2e builds `skipif`-guarded (task-04 owns the e2e).

## Verification Requirements
- **Automated tests**: the new unit + structural tests.
- **Manual / integration checks**: n/a (automated).
- **Risk coverage**: every fail-loud case (E7), structure (E1), alignment (P2),
  regression (R6).
- **Demo command**: `uv run pytest tests/test_slides.py tests/test_engine.py -q`
- **Expected result**: all tests pass (0 failures), including the new
  two-column cases.

## Handoff Notes
If a structural assertion reveals the emitted div is mis-nested, fix in task-02
(engine), not by weakening the test. Keep the regression assertions on
`picture_body_tex` strict.

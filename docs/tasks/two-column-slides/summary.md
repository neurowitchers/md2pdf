# Task Summary: Two-Column (Picture + Text) Slides

- **Source spec**: `docs/specs/two-column-slides.md`
- **Task directory**: `docs/tasks/two-column-slides/`
- **Status**: `ready`

## Execution Order

1. `task-01-detector.md` — pure `slides.py` detection + classification; no
   dependencies; everything else imports these symbols.
2. `task-02-lowering.md` — `engine.py` lowering; depends on task-01's
   `match_two_column_slide` / `classify_region`.
3. `task-03-tests.md` — unit + pandoc-only structural + regression tests;
   depends on tasks 01–02.
4. `task-04-docs-example.md` — README dialect docs, `examples/two-column-demo.md`,
   and the guarded e2e build; depends on task-02 behaviour.

## Dependencies & Parallel Work

- **Sequential constraints**: 01 → 02 → {03, 04}. Task-02 cannot start until the
  detector's tri-state contract (dict / None / raise) exists.
- **Safe parallel groups**: after task-02, **task-03 and task-04 may run in
  parallel** — they touch disjoint files (`tests/test_slides.py` +
  `tests/test_engine.py` vs. `README.md` + `examples/` + `tests/test_examples_build.py`).
- **Shared-file / integration warnings**: tasks 01 and 02 both are the only
  writers of `slides.py` and `engine.py` respectively — no shared-file conflict.
  `tests/test_examples_build.py` is owned solely by task-04; `tests/test_slides.py`
  and `tests/test_engine.py` solely by task-03.

## Coverage Map

| Spec requirement / acceptance criterion | Risk or testing-strategy item | Task(s) | Verification evidence |
|---|---|---|---|
| R1 `:::` convention | detection critical path | 01, 03 | unit test: valid slide → `{title,left,right}` |
| R2 strictly two 50/50 | colon-nesting risk | 02, 03 | structural test: two `{.column width="50%"}` |
| R3 both sides fit (0.72h, top) | overflow (E6) / alignment (P2) | 02, 03 | structural test: `\columnwidth,height=0.72\textheight`, no `\vfill` |
| R4 title + align=top + onlytextwidth | margin bleed (E1) | 02, 03 | structural test: `{.columns .onlytextwidth align=top}` |
| R5 fail-loud (+P1 pre-delimiter) | fail-loud posture | 01, 03 | `pytest.raises(SystemExit)` for 2/4 delims, pre/post content, empty region, unterminated fence |
| R6 backwards-compat / opt-in | regression | 01, 02, 03 | test: no-`:::` slide → `None`; `picture_body_tex` unchanged; example decks unaffected |
| R7 diagrams in columns | diagram routing | 02, 03, 04 | `classify_region` diagram case; e2e `d2`-in-column build |
| R8 docs + example | e2e | 04 | guarded build of `two-column-demo.md` → non-empty PDF |
| E2 general code-fence scanner | fence ambiguity | 01, 03 | test: `:::` inside ```` ```python ```` not a delimiter |
| E8 indent tolerance / E4 trailing blanks | operational robustness | 01, 03 | tests for ≤3-space indent and trailing blank lines |

## Shared Test and Demo Setup

- Reuse `examples/assets/placeholder.png` for image-region tests and the demo.
- Diagram-in-column uses a tiny inline `d2` source (`a -> b -> c`).
- Unit/structural tests need only pandoc-free Python (`uv run pytest
  tests/test_slides.py tests/test_engine.py`). The e2e build test is
  `skipif`-guarded on pandoc + xelatex + d2.

## Integration Checkpoint

After all tasks:
1. `uv run pytest -q` — full suite green (new + existing, incl. regressions).
2. `uv run md2pdf examples/two-column-demo.md --output examples/two-column-demo.pdf`
   — non-empty PDF, no pandoc/xelatex error, columns within margins, image/diagram
   top-aligned with bullets.
3. Confirm the three existing example decks still build unchanged.

## Open Questions

- None. (Spec-level 💡 Recommendations and 🤔 Questions from
  `docs/critiques/two-column-slides-critique.md` — e.g. P3/P4/P6 doc notes,
  P5 mixed-diagram warning, P7 perf budget, E5/E9 typing — are preserved for
  human review and partially captured as task-04 doc limitations; they do not
  block implementation.)

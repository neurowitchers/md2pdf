---
generated-by: "Split Tasks"
source: docs/specs/two-column-slides.md
generated-at: 2026-10-17T23:05:00+03:00
inputs-ready: false
completed: true
status: done
---

# Task 04: README Dialect Docs + `two-column-demo.md` Example + E2E Build

- [x] **Completion**
- **Source spec**: `docs/specs/two-column-slides.md`
- **Depends on**: `task-02-lowering.md`
- **Blocks**: `None`
- **Parallelism**: `Safe with task-03 (different files), but needs task-02 behaviour`

## Objective

Document the two-column `:::` convention in `README.md`, add
`examples/two-column-demo.md`, and wire a toolchain-guarded end-to-end build test
(R8).

## Scope & Traceability
- **Requirements / acceptance criteria**: R8 (docs + example); exercises R1–R7
  end-to-end.
- **Testing & risk strategy items**: e2e build; critique P3 (diagram caption
  limitation), P4 (`---` reserved for slide breaks), P6 (nested divs
  unsupported) documented as limitations.
- **Out of scope**: engine/detector code (tasks 01–02).

## Implementation Guidance
- **Files to create or modify**:
  - `examples/two-column-demo.md`: front-matter (`title`), one slide with
    pic-left / bullets-right using the `:::` grammar (reuse
    `assets/placeholder.png`), and one slide with a `d2` diagram region +
    bullets region. Keep it minimal and buildable.
  - `README.md`: add a "Two-column slides" subsection under the Markdown dialect
    docs. Document: the `:::` grammar (one `# Title`, exactly three `:::` lines
    = open/separator/close, two regions, strictly 50/50, `align=top`); that a
    lone image or `mermaid`/`d2` fence region is fit-to-column while other
    regions render as normal markdown; and the fail-loud cases. Document the
    limitations (critique): diagram regions have no caption (use the companion
    column) (P3); `---` is reserved for slide breaks and must not appear inside a
    column (P4); nested pandoc divs (e.g. `::: notes`) are not supported inside a
    two-column body in v1 (P6).
  - `tests/test_examples_build.py`: add a `skipif`-guarded (pandoc + xelatex +
    d2) e2e case building `examples/two-column-demo.md` to a temp PDF and
    asserting the output is a non-empty file.
- **Established patterns to follow**: `examples/picture-demo.md` and
  `examples/diagram-demo.md`; the existing `tests/test_examples_build.py`
  skip-guard pattern.
- **Constraints and non-goals**: do not add proprietary assets; reuse the
  existing placeholder image; the README example must match the implemented
  grammar exactly.

## Verification Requirements
- **Automated tests**: the new e2e build case (guarded).
- **Manual / integration checks**: `uv run md2pdf examples/two-column-demo.md`
  produces a 2-slide PDF with a pic-left/text-right slide and a
  diagram-left/text-right slide; columns stay within theme margins; image/diagram
  top-aligned with the bullets.
- **Risk coverage**: full-pipeline validation (R8 + R1–R7 end-to-end).
- **Demo command**: `uv run md2pdf examples/two-column-demo.md --output
  examples/two-column-demo.pdf`
- **Expected result**: a non-empty `examples/two-column-demo.pdf` is produced
  with no pandoc/xelatex error.

## Handoff Notes
Keep the README example byte-consistent with the grammar in task-01; if the
grammar changes during implementation, update both together.

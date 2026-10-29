# Deferred Items — two-column-slides

**Date**: 2026-10-17
**Source spec**: docs/specs/two-column-slides.md
**Mode**: autoflow

## Summary

Shipped the `:::` two-column slide shorthand (strictly two 50/50 columns,
top-aligned, both sides fit-to-column, fail-loud on malformed markup), lowered
to native Pandoc Beamer column divs. All 🎯 Must-Address critique findings
(spec-level and task-level) and the code review's HIGH data-loss bug were
applied; the items below were consciously left for a future iteration (open
💡 Recommendations / 🤔 Questions and non-blocking MEDIUM/LOW review findings).

## Deferred Items

| ID | Origin | Priority | Item | Rationale / Next Step |
|----|--------|----------|------|-----------------------|
| D1 | Code Review MEDIUM | Medium | `classify_region` has a loose `tuple` return annotation | Add a precise `Union`/`NamedTuple` (also raised as spec-level E9 and task-level E4 🤔). Type-only; no runtime effect. Pick up when adding static type-checking (mypy/pyright) to the project. |
| D2 | Code Review LOW | Low | Inner closing code fence longer than its opener is rejected as unterminated | CommonMark §4.5 allows a longer close. Fix together with `match_diagram_slide` for cross-matcher parity, so both behave identically. |
| D3 | Code Review LOW / Critique P5 | Low | Near-miss diagram fence inside a column (e.g. ` ```d2 layout=elk `, or a diagram fence mixed with other content) does not emit the existing stderr near-miss warning | Behaviour change to the warning surface; add a column-aware near-miss warning in `preprocess_body`. |
| D4 | Critique 💡 P3 | Low | Diagram regions in a column carry no caption | Documented as a v1 limitation in README (use the companion text column for figure labels). Revisit only if a fence-caption syntax is desired. |
| D5 | Critique 💡 P7 | Low | No quantitative performance budget / visual-acceptance thresholds | Add a preprocessing-overhead budget and an automated visual-margin check if performance or layout regressions become a concern. |
| D6 | Critique 🤔 P6 | Low | Nested Pandoc fenced divs (e.g. `::: notes`) inside a two-column body are unsupported | Documented as a limitation. If speaker notes inside columns are later needed, design an escaping or nesting rule. |
| D7 | Critique 💡 E5 | Low | Column image path traversal relies on existing `\graphicspath`/`--resource-path` boundary | No new path logic was introduced; the existing audited boundary applies. Note only. |
| D8 | Critique 💡 (task-level) E3 | Low | A task-01 manual-check command used bare `python` | Cosmetic doc nit in the task file; the authoritative demo command already uses `uv run`. |

## Suggested Follow-up

- **D1** (typed `classify_region`) is the strongest candidate for the next
  iteration — small, improves maintainability, and is reinforced by two separate
  critique passes. Natural to bundle with introducing a type checker.
- **D2** and **D3** are small correctness/UX polish items that pair well in a
  single follow-up touching the shared fence-handling and near-miss warning.
- **D4/D6** (caption + nested-div support) would only warrant a new
  Brainstorm/Seed if authors request richer in-column content.

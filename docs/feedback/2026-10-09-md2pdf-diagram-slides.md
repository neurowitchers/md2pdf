# Deferred Items — md2pdf-diagram-slides

**Date**: 2026-10-09
**Source spec**: tooling/specs/md2pdf-diagram-slides.md
**Mode**: autoflow

## Summary

Shipped strict ` ```mermaid `/` ```d2 ` diagram slides for md2pdf: fenced diagram source is rendered at build time (d2 → vector PDF, mermaid → high-resolution PNG via `mmdr`) and placed fit-to-frame like a picture slide, with loud failure on missing CLI, render error, or timeout. The code-review verdict was APPROVE with no CRITICAL/HIGH findings; both MEDIUM findings were applied. The items below were intentionally left for a future iteration.

## Deferred Items

| ID | Origin | Priority | Item | Rationale / Next Step |
|----|--------|----------|------|-----------------------|
| D1 | Code Review LOW | Low | Cross-platform binary fallback hardcodes `.exe` (`~/go/bin/d2.exe`, `~/.cargo/bin/mmdr.exe`). | Build box is Windows, so this is correct today. For Linux/macOS portability, check both the plain binary name and the `.exe` variant in the fallback paths. |
| D2 | Code Review LOW | Low | `<output-stem>_diagrams` directory is created unconditionally under `--keep-tex`, even for decks with no diagram slides. | Harmless (empty dir). Create it lazily on first diagram render to avoid leaving empty directories beside kept `.tex`. |
| D3 | Critique 💡 (P3) | Medium | Diagram slides carry no caption (unlike picture slides, which use image alt text). | Deferred by design for the MVP. A future enhancement could parse an optional caption from the fence info string, e.g. ` ```mermaid "Figure 1" `, and pass it to `picture_body_tex` as the caption. |
| D4 | Critique 💡 (P2) | Low | Diagram internals use each renderer's default theme on a white background; no deep HIVE brand theming of nodes/edges. | Acceptable for the MVP (visual harmony via white background + fit-to-frame). A future pass could supply a d2 theme / `mmdr` config matching HIVE brand colours. |

## Suggested Follow-up

D3 (optional diagram captions) is the strongest candidate for a next iteration, as it closes the one remaining feature gap versus picture slides. D1 would matter only if md2pdf is run on non-Windows hosts. D2 and D4 are minor polish.

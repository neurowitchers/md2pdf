# Task 1: Strict diagram-slide detection

Status: [ ]
Spec: `tooling/specs/md2pdf-diagram-slides.md`
File under change: `tools/md2pdf/md2pdf.py`, tests in `tools/md2pdf/test_md2pdf.py`
Depends on: none (parallel with Task 2)

## Objective

Add `match_diagram_slide(chunk) -> dict | None` returning `{"title", "lang", "source"}` when a slide chunk is exactly one `# Title` heading plus exactly one fenced ` ```mermaid ` or ` ```d2 ` block and nothing else; otherwise `None`. Mirror the existing `match_picture_slide` style and reuse `split_slides`.

## Implementation guidance

- Reuse `split_slides` for chunking; this task only adds the per-chunk matcher.
- Capture the fenced block body **verbatim** (preserve indentation and newlines) — this is the diagram source handed to the renderer.
- Fence info-string rules (critique P5): strip trailing whitespace from the info string; accept only an exact lone language token `mermaid` or `d2`; reject info strings with extra parameters (e.g. ` ```d2 layout=elk `). Ignore blank lines surrounding the fence inside the chunk.
- Strict rejection: any other non-blank content (prose, bullets, tables), a second fence, a non-diagram fence, or a missing heading → `None`.
- Keep heading parsing consistent with `match_picture_slide` (single `# ` H1).
- Detection stays silent; the disqualified-slide warning lives in `preprocess_body` (Task 3).

## Test requirements

Add to `tools/md2pdf/test_md2pdf.py`:
- Strict mermaid slide → `{"lang": "mermaid", ...}` with exact source.
- Strict d2 slide → `lang="d2"`.
- Fence plus a trailing bullet or prose → `None`.
- Two fences → `None`.
- Non-diagram fence (e.g. ` ```python `) → `None`.
- A picture slide → `None` (detectors stay disjoint).
- Info string with trailing whitespace (` ```mermaid   `) → still matches.
- Info string with extra parameters → `None`.

## Demo

`uv run pytest tools/md2pdf/test_md2pdf.py -k diagram_slide -v` — all detection cases pass.

# Task 4: Sample deck + end-to-end build verification

Status: [ ]
Spec: `tooling/specs/md2pdf-diagram-slides.md`
File under change: `tools/md2pdf/examples/`, tests in `tools/md2pdf/test_md2pdf.py`
Depends on: Task 3

## Objective

Provide a runnable example and an end-to-end build test proving diagram slides render in a real PDF.

## Implementation guidance

- Add a sample deck under `tools/md2pdf/examples/` (new `diagram-demo.md`, or extend `picture-demo.md`) with required front-matter, one regular slide, one ` ```mermaid ` slide, and one ` ```d2 ` slide. Keep diagrams small and legible.
- The generated `.pdf` stays gitignored (`*.pdf`).
- End-to-end test builds the deck to a temp PDF, asserts exit 0 and non-empty output, then cleans up artifacts (including any persistent `_diagrams` dir if `--keep-tex` used).
- Optionally render a page to PNG (pdftocairo, as done for the picture slide) to visually confirm the diagrams appear.

## Test requirements

- End-to-end build returns 0 and writes a PDF > 0 bytes (`skipif` `d2`/`mmdr` absent).
- Structural `.tex` assertions from Task 3 cover the rendering wiring.

## Demo

`uv run python tools/md2pdf/md2pdf.py tools/md2pdf/examples/diagram-demo.md --output <tmp>.pdf` — open the PDF: a regular slide, a mermaid diagram slide, and a d2 diagram slide, all branded and fit-to-frame.

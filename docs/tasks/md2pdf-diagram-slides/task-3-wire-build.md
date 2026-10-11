# Task 3: Wire diagram slides into preprocess_body and build()

Status: [ ]
Spec: `tooling/specs/md2pdf-diagram-slides.md`
File under change: `tools/md2pdf/md2pdf.py`, tests in `tools/md2pdf/test_md2pdf.py`
Depends on: Task 1 (detection) and Task 2 (renderer)

## Objective

Integrate diagram slides into the build pipeline: detect them, render them, and emit the fit-to-frame frame via the existing `picture_body_tex`, with correct asset lifecycle and path handling.

## Implementation guidance

- Thread a diagram output directory through the rewrite step, e.g. `preprocess_body(body, diagram_dir)`.
- In the slide loop, after the picture check, test `match_diagram_slide`; for matches call `render_diagram(lang, source, diagram_dir, title)` and emit via `picture_body_tex` (empty caption) pointing at the generated image. Picture and normal slides unchanged.
- **Asset lifecycle (critique E1):** when `keep_tex` is False, `diagram_dir` lives inside the build `TemporaryDirectory()`. When `keep_tex` is True, `diagram_dir` is persistent alongside the output, e.g. `output.parent / f"{output.stem}_diagrams"`, so the kept `.tex` references surviving assets.
- **Path handling (critique E10):** add `diagram_dir` to pandoc `--resource-path` and emit **relative** image filenames so paths with spaces do not break `\includegraphics`.
- **Disqualified-slide diagnostic (critique P1):** in `preprocess_body`, if a chunk contains a ` ```mermaid ` or ` ```d2 ` fence but `match_diagram_slide` returns `None`, emit a non-fatal `sys.stderr` warning that the slide will render as a verbatim code block.

## Test requirements

- `--keep-tex` build test on a temp deck with one d2 slide + one mermaid slide: generated `.tex` contains two fit-to-frame `\includegraphics` blocks pointing at the rendered files; the files exist in the persistent `_diagrams` dir and remain after the build (`skipif` CLIs absent).
- Unit test: a mermaid fence placed alongside a bullet emits the disqualified-slide warning to stderr.

## Demo

Build a temp deck with a d2 slide and a mermaid slide using `--keep-tex`; show the LaTeX referencing both rendered diagram images and the surviving `_diagrams` directory.

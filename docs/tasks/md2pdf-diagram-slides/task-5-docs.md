# Task 5: Documentation update

Status: [ ]
Spec: `tooling/specs/md2pdf-diagram-slides.md`
File under change: `tools/md2pdf/md2pdf.py` (module docstring), `AGENTS.md`
Depends on: Task 3 (may overlap with Task 4)

## Objective

Document the diagram-slide convention for deck authors and agents.

## Implementation guidance

- Update the module docstring in `md2pdf.py` and the AGENTS.md md2pdf entry.
- Document: a slide that is `# Title` plus one ` ```mermaid ` or ` ```d2 ` fence is rendered to an image and placed fit-to-frame; strict detection; d2 → PDF, mermaid → PNG via `mmdr`; the build fails loudly if the required CLI (`d2`/`mmdr`) is missing; diagrams render on a white background with each renderer's default theme; captions are deferred.
- Note `mmdc` is intentionally not used (avoids a Chrome dependency).
- Match the concise style of the existing picture-slide docs; include a short example of each fence.

## Test requirements

None (docs). Verify the documented example matches the sample deck (Task 4) and the tool invocation.

## Demo

Show the updated docstring and AGENTS.md entry; the documented command matches Task 4's working invocation.

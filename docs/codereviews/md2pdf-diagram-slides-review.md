# Commit Review: e4af168 — feat: implement md2pdf-diagram-slides

**Reviewed**: 2026-10-09
**Author**: Boris Resnick <boris@flyver.city>
**Branch**: tooling
**Decision**: APPROVE

## QA & Verification Guidance
- **Risk Assessment & Migration Notes**: No breaking changes to existing Markdown decks or slide syntax. The diagram-slide feature is purely additive and relies on local CLI installations of `d2` and `mmdr`. Decks lacking diagrams require no changes and run without new dependencies. Decks featuring diagram slides require `d2` (for ` ```d2 ` blocks) or `mmdr` (for ` ```mermaid ` blocks) available either on `PATH` or in standard user installation locations (`~/go/bin/d2.exe`, `~/.cargo/bin/mmdr.exe`).
- **Behavioral Changes to Verify**:
  - Slide chunks containing exactly one `# Title` and one fenced ` ```mermaid ` or ` ```d2 ` block render fit-to-frame as high-resolution images on an opaque white background, matching picture-slide geometry.
  - Slide chunks with diagram fences containing extra prose, bullet points, multiple code blocks, or extra info-string attributes fall back to standard verbatim code-block rendering and output a diagnostic warning to `stderr`.
  - When `--keep-tex` is specified, generated diagram assets persist in `<output-stem>_diagrams/` alongside the generated LaTeX file, with valid relative references in the LaTeX source.
  - Missing diagram CLIs, non-zero exit codes from diagram compilers, or compilation timeouts exceeding 30 seconds fail loudly with `SystemExit`, displaying actionable diagnostics, tool names, and slide titles.
- **Testing Hints for QA**:
  1. Execute `uv run python tools/md2pdf/md2pdf.py tools/md2pdf/examples/diagram-demo.md --output test-diagrams.pdf --keep-tex` and confirm that all three slide types (regular bulleted slide, Mermaid flowchart, and D2 sequence diagram) render cleanly, and that `test-diagrams_diagrams/` contains the rendered `.png` and `.pdf` diagram assets.
  2. Introduce deliberate syntax errors into a D2 or Mermaid block and verify that compilation fails immediately with an error identifying the offending slide title and capturing renderer `stderr`.
  3. Append bullet text beneath a diagram code block in a test slide and confirm that compilation succeeds with a warning on `stderr`, rendering the diagram as standard formatted code.

> Note: Product-audience narrative (shipped value, deferred items, next iteration) is
> **not** part of the review — it is posted separately by the `Finalize` command.

## Technical Summary
The implementation delivers robust, strict diagram-slide rendering for Mermaid and D2 blocks via external CLI tools, matching the established design and visual layout of picture slides. The code adheres closely to the specification, passes all unit, integration, and end-to-end regression tests, and includes comprehensive error-handling and documentation updates.

## Findings

### CRITICAL
None

### HIGH
None

### MEDIUM
- **`tools/md2pdf/md2pdf.py#L444-L450` — Warning detection misses near-miss diagram fences with info-string parameters**: In `_chunk_has_diagram_fence`, the code evaluates `fm.group("info").strip() in _DIAGRAM_LANGS`. When a deck author specifies a diagram fence with additional parameters (for example, ` ```d2 layout=elk `), `match_diagram_slide` rejects the slide as expected, but `_chunk_has_diagram_fence` also evaluates to `False`. Consequently, the non-fatal warning on `stderr` intended to alert authors to disqualified diagram fences is suppressed. Consider parsing the primary language token with `fm.group("info").strip().split()[0]` to ensure near-miss parameterised fences trigger the warning.
- **`tools/md2pdf/md2pdf.py#L340-L341` — Cache lookup lacks file-integrity verification and failure cleanup**: In `render_diagram`, cached outputs are reused solely based on `if out_file.exists(): return out_file`. If a previous build was aborted, killed, or timed out leaving an empty or partial zero-byte file on disk, subsequent runs will return the corrupted asset without re-rendering. Furthermore, if `proc.returncode != 0`, any partially written `out_file` is not removed. Adding a non-zero size check (`out_file.stat().st_size > 0`) and removing partially created files upon renderer failure or timeout would prevent cache corruption.

### LOW
- **`tools/md2pdf/md2pdf.py#L304,L308` — Hardcoded Windows `.exe` extensions in fallback resolution paths**: In `_resolve_diagram_binary`, the fallback paths explicitly append `.exe` (`Path.home() / "go" / "bin" / "d2.exe"` and `Path.home() / ".cargo" / "bin" / "mmdr.exe"`). If this tool is executed in a non-Windows environment where binaries reside in these default directories but are not on `PATH`, the fallback check will fail. Checking both the platform-specific binary name and base executable name would improve cross-platform robustness.
- **`tools/md2pdf/md2pdf.py#L641-L645` — Unconditional creation of persistent diagram directory under `--keep-tex`**: When `keep_tex=True`, `diagram_dir.mkdir(parents=True, exist_ok=True)` creates `<output-stem>_diagrams` unconditionally, even when the deck contains no diagram slides. Creating the directory lazily only when at least one diagram slide is rendered would avoid leaving empty directories beside generated `.tex` files.

## Validation Results

| Check | Result |
|---|---|
| Type check | Skipped (Python project; type annotations present and clean) |
| Lint | Skipped (No project linter configured) |
| Tests | Pass (`uv run pytest tools/md2pdf/test_md2pdf.py -q` — 45 passed in 36.47s) |
| Build | Pass (End-to-end PDF builds verified in test suite) |

## Files Reviewed
- `tools/md2pdf/md2pdf.py` — Modified (diagram detection, binary resolution, subprocess rendering, graphicspath integration, and preprocessing)
- `tools/md2pdf/test_md2pdf.py` — Modified (unit tests for detection and rendering, error handling, warning assertions, and end-to-end build tests)
- `tools/md2pdf/examples/diagram-demo.md` — Added (example presentation covering regular, Mermaid, and D2 slides)
- `AGENTS.md` — Modified (tool catalog updated with diagram slide capabilities, renderer notes, and constraints)

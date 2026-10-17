# Code Review: Local Review — Two-Column Slides (deba42b)

**Reviewed**: 2026-10-17  
**Author**: Boris Resnick <boris.resnick@gmail.com>  
**Branch**: `double-slides` → `main` (merge-base `397a7c9`, commit `deba42b`)  
**Mode**: Local-only (no GitHub PR exists)  
**Decision**: REQUEST CHANGES  

## QA & Verification Guidance

- **Risk Assessment & Migration Notes**:
  - The two-column slides feature is designed to be purely additive and backwards compatible (R6). Decks not using the `:::` delimiter syntax after `# Heading` are untouched.
  - Ordinary slides with Pandoc fenced divs (e.g. `::: notes` or `::: {.callout}`) are protected from hijacking by the conservative opt-in trigger: a slide is only treated as two-column if its first non-blank line following `# Title` is a bare `:::` delimiter.
  - However, there is an edge-case bug (Finding 1) where a slide chunk with non-blank content preceding `# Title` can be mistakenly hijacked as an opted-in two-column slide, erasing the title and silently discarding the pre-heading content.
  - Image regions are top-aligned and constrained to `width=\columnwidth,height=0.72\textheight,keepaspectratio`, with alt text rendered as a caption in theme-defined `captioncolor`.
  - Column diagrams render via `render_diagram` using cached PDF (`d2`) or PNG (`mermaid`) assets and require `d2` or `mmdr` present on the system.

- **Behavioral Changes to Verify**:
  - Slide chunks of the form `# Title\n\n:::\n<left>\n:::\n<right>\n:::\n` lower to Pandoc native Beamer columns (`:::::: {.columns .onlytextwidth align=top}` with two `:::: {.column width="50%"}` divs).
  - A region with a single image or lone `d2`/`mermaid` code fence is top-aligned and fit to the column; other regions flow as standard Markdown.
  - Malformed syntax on opted-in slides (fewer or more than three delimiters, empty column regions, trailing content after closing `:::`, or unterminated inner code fences) fails loudly with `SystemExit` displaying actionable slide-identifying diagnostics.
  - Unterminated inner code fences are diagnosed *before* delimiter-count checks.
  - Legacy whole-slide picture (`picture_body_tex`) and diagram slides produce identical LaTeX output to prior revisions.

- **Testing Hints for QA**:
  1. **Basic side-by-side verification**: Run `uv run md2pdf examples/two-column-demo.md --output test-demo.pdf --keep-tex` and confirm that Slide 1 displays an image top-aligned on the left with bullet points on the right, and Slide 2 displays a rendered `d2` diagram on the left with explanatory notes on the right.
  2. **Margin containment check**: Inspect the generated `test-demo.tex` to confirm that `\begin{columns}[T,onlytextwidth]` is emitted, preventing column text from bleeding into slide logos or theme margins.
  3. **Fail-loud error diagnostics**: Create a slide with an unterminated fence inside a column (e.g. `::: \n ```python \n ::: \n right \n :::`) and confirm it aborts with `ERROR: slide '<title>': unterminated inner code fence ('python') inside the two-column body` rather than a misleading delimiter-count error.
  4. **Pre-heading text regression test**: Verify that a slide with introductory text before `# Title` followed by `:::` does not lose its title or introductory text.

> Note: Product-audience narrative (shipped value, deferred items, next iteration) is
> **not** part of the review — it is posted separately by the `Finalize` command.

## Technical Summary

The `two-column-slides` implementation introduces an elegant, opt-in authoring dialect for side-by-side columns that lowers to native Pandoc/Beamer column divs. The fence-aware delimiter scanning avoids delimiter confusion within code blocks, the fail-loud ordering correctly prioritises unterminated code fences, and the refactoring of `_fit_image_tex` preserves whole-slide picture emission without regressions.

However, a logic issue in `match_two_column_slide` allows slide chunks with non-heading content preceding `# Title` to be hijacked as two-column slides with blank titles (`title: ""`), silently dropping the preceding content. Changes are requested to resolve this issue and add missing test permutations before merging.

---

## Findings

### CRITICAL
None

### HIGH

- **`src/md2pdf/slides.py#L270-L327` — Non-blank content preceding `# Title` causes silent text omission and empty title generation**:
  - **Category**: Correctness / Data Loss Risk
  - **Description**: In `src/md2pdf/slides.py`, lines 270–283 attempt to parse the heading up front:
    ```python
    title: str | None = None
    first_non_blank = ""
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        if not first_non_blank:
            first_non_blank = s
        hm = _H1_RE.match(s)
        if hm:
            title = hm.group("title").strip()
        break  # only inspect the first non-blank line here
    ```
    If a slide chunk has any non-blank line before `# Title` (e.g. `intro prose\n# Title\n:::\nleft\n:::\nright\n:::`):
    1. Line 282 breaks immediately without setting `title`, leaving `title = None`.
    2. In the main loop (lines 294–322), `seen_title` starts `False`. Line 0 (`"intro prose"`) is ignored for `first_body_non_blank_is_delim`.
    3. Line 1 (`"# Title"`) sets `seen_title = True`.
    4. Line 2 (`":::"`) sets `first_body_non_blank_is_delim = True`.
    5. `match_two_column_slide` treats the chunk as a valid two-column slide and returns `{"title": "", "left": "left", "right": "right"}`.
    6. In `engine.preprocess_body` (lines 181–191), only `two_col["title"]` (now `""`) and regions between delimiters (`lines[open_i + 1:close_i]`) are emitted.
    7. As a consequence, `"intro prose"` is completely dropped from the rendered output without error or warning, and the slide heading is rendered as an empty `# `!
  - **Violation**: Violates R1 ("A slide of the form `# Title` followed by a body that opens with a `:::` delimiter is a *two-column slide*") and R6 (ordinary slides must remain untouched).
  - **Remediation**: In `match_two_column_slide`, require that `# Title` is strictly the first non-blank line of the chunk (as in `match_picture_slide` and `match_diagram_slide`). If any non-blank line precedes `# Title`, `match_two_column_slide` must return `None`.

### MEDIUM

- **`src/md2pdf/slides.py#L230` — Loose return type annotation on `classify_region`**:
  - **Category**: Type Safety
  - **Description**: `classify_region(region: str) -> tuple` returns an untyped `tuple`. It actually produces one of three distinct tuple shapes:
    `tuple[Literal["image"], str, str] | tuple[Literal["diagram"], str, str] | tuple[Literal["markdown"], str]`.
    Untyped `tuple` obscures the contract and prevents static type checkers or IDEs from validating the unpacked elements in callers like `_column_region_tex` (`kind, *rest = classify_region(region)`).
  - **Remediation**: Annotate with a typed Union or `tuple[str, ...]`.

- **`tests/test_slides.py` / `tests/test_engine.py` — Missing edge-case test coverage**:
  - **Category**: Completeness
  - **Description**: While test coverage for existing scenarios is strong, several key edge cases lack dedicated assertions:
    1. A chunk with non-blank content preceding `# Title` (the bug identified in Finding 1).
    2. Empty right column region (e.g. `:::\nleft\n:::\n:::\n` or `:::\nleft\n:::\n   \n:::\n`).
    3. Permutations with two images (image in left column AND image in right column).
    4. Permutations with mixed media across columns (e.g. diagram left, image right).
  - **Remediation**: Add unit and engine tests for these cases.

### LOW

- **`src/md2pdf/slides.py#L298` — Fence-closing check rejects valid CommonMark closing fences longer than opening fence**:
  - **Category**: Correctness / Maintainability
  - **Description**: In `match_two_column_slide`:
    ```python
    if close.startswith(fence_marker) and close[len(fence_marker):].strip() == "":
    ```
    CommonMark §4.5 specifies that closing fences must use the same character and be *at least as long as* the opening fence. If an inner code fence opens with 3 backticks and closes with 4 backticks, this scanner rejects it as unterminated. While consistent with `match_diagram_slide`, in free-form Markdown column bodies this could reject valid Markdown code fences.
  - **Remediation**: Allow closing fences with length `>= len(fence_marker)` consisting solely of the fence character.

- **`src/md2pdf/engine.py#L173-L192` — Suppressed near-miss diagram fence warnings on two-column slides**:
  - **Category**: Maintainability
  - **Description**: On regular slides, `_chunk_has_diagram_fence` checks for disqualified diagram fences (e.g. ` ```d2 layout=elk `) and emits a helpful `stderr` warning. On two-column slides, `classify_region` falls back to `markdown` for near-miss fences, and `preprocess_body` immediately `continue`s, skipping the warning check.
  - **Remediation**: Check for non-strict diagram fences within column regions and emit the diagnostic warning.

- **`tests/test_examples_build.py#L59-L63` — Over-constrained test guard for two-column example build**:
  - **Category**: Completeness
  - **Description**: `test_build_two_column_example_deck_produces_pdf` is guarded by `_diagram_toolchain()`, which requires `pandoc`, `xelatex`, `d2`, and `mmdr`. However, `examples/two-column-demo.md` only includes a PNG image and a `d2` diagram—it does not use Mermaid (`mmdr`). On systems where `mmdr` is missing but `d2` is present, this end-to-end test is unnecessarily skipped.
  - **Remediation**: Guard with `_pandoc_xelatex() and bool(shutil.which("d2"))`.

---

## Validation Results

| Check | Result | Details |
|---|---|---|
| Type check | Skipped | Python project; no mypy/pyright runner configured in `pyproject.toml` |
| Lint | Skipped | No project linter (ruff/flake8) configured in `pyproject.toml` |
| Tests | **Pass** | `uv run pytest -q` passed 123/123 tests in 51.42s |
| Build | **Pass** | `examples/two-column-demo.md` built cleanly to valid non-empty PDF (verified in `tests/test_examples_build.py`) |

---

## Files Reviewed

- `src/md2pdf/slides.py` — Modified (added `_COLON_FENCE_RE`, `_two_column_error`, `_diagram_fence_only`, `classify_region`, `match_two_column_slide`)
- `src/md2pdf/engine.py` — Modified (added `_fit_image_tex`, `column_body_tex`, `_column_region_tex`, updated `preprocess_body` for two-column slides)
- `tests/test_slides.py` — Modified (added 15 unit tests covering valid slides, delimiter variants, fence tracking, and classification)
- `tests/test_engine.py` — Modified (added structural TeX generation tests for two-column layout, diagram lowering, and backwards compatibility)
- `tests/test_examples_build.py` — Modified (added end-to-end PDF generation test for `examples/two-column-demo.md`)
- `examples/two-column-demo.md` — Added (demo deck showcasing picture + text and diagram + text columns)
- `README.md` — Modified (added dialect documentation for two-column slides syntax, rules, and constraints)
- `docs/specs/two-column-slides.md` — Reference spec (requirements R1–R8, architecture, and applied critiques)
- `docs/tasks/two-column-slides/` — Reference task set (`task-01-detector.md`, `task-02-lowering.md`, `task-03-tests.md`, `task-04-docs-example.md`, `summary.md`)


---

## Applied Fixes (Autoflow `Handoff Code Review --auto`)

Per the `--auto` policy, `CRITICAL`/`HIGH` findings were applied automatically;
ambiguous or behaviour-changing items were recorded for human review.

- **HIGH (applied)** — `match_two_column_slide` now requires `# Title` to be the
  **strict first non-blank line**; if any non-blank content precedes it the
  function returns `None` (slide handled untouched, no title loss / content
  drop). Regression test `test_match_two_column_pre_heading_content_is_none`
  added. Fixes the R1/R6 data-loss bug.
- **MEDIUM/completeness (partially applied)** — added tests for the empty
  right-column region, two-image columns, and mixed diagram-left/image-right
  permutations (`test_match_two_column_empty_right_region_fails`,
  `test_match_two_column_two_image_columns`,
  `test_match_two_column_mixed_media_diagram_left_image_right`).
- **LOW (applied, trivially safe)** — the two-column e2e build test guard was
  loosened from the full diagram toolchain to `pandoc + xelatex + d2` (the demo
  uses no mermaid, so `mmdr` is not required).

Recorded for human review (not auto-applied — ambiguous or behaviour-changing):

- **MEDIUM** — `classify_region` loose `tuple` return annotation (type-only;
  no runtime effect).
- **LOW** — allowing an inner closing code fence longer than its opener
  (would change parity with `match_diagram_slide`; defer for a consistent
  cross-matcher change).
- **LOW** — emitting the near-miss diagram-fence warning for non-strict diagram
  fences inside a column (a behaviour change to the warning surface).

Full suite after fixes: **127 passed**.

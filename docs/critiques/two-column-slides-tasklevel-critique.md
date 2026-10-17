---
status: applied
target: ../specs/two-column-slides.md
target-revision: 2a22809
---

# Task-Level Critique: Two-Column (Picture + Text) Slides

**Document Under Review**: `../specs/two-column-slides.md`  
**Task Set Under Review**: `../tasks/two-column-slides/` (`summary.md`, `task-01-detector.md`, `task-02-lowering.md`, `task-03-tests.md`, `task-04-docs-example.md`)  
**Review Type**: Scartill SDD Task-Level Critique (Autoflow Second Pass: Spec + Task Execution Breakdown)  
**Target Revision**: `2a22809`  
**Scope Note**: This second-pass critique assesses the Full Specification alongside its authoritative task breakdown in `../tasks/two-column-slides/`.

---

## Executive Summary

The Full Specification (`../specs/two-column-slides.md`) and its detailed task breakdown (`../tasks/two-column-slides/`) establish a coherent architecture for implementing two-column Beamer slides in `md2pdf`. The design lowers a bespoke `:::` triple-delimiter shorthand in `../../src/md2pdf/slides.py` to native Pandoc Beamer column divs (`:::::: {.columns .onlytextwidth align=top}`) in `../../src/md2pdf/engine.py`, preserving markdown formatting within columns while providing fit-to-column scaling for lone images and diagrams. The previous spec-level Must-Address findings (P1 pre-delimiter check, P2 vertical alignment, E1 `.onlytextwidth` margin containment, E2 general code-fence scanning) were incorporated into the spec.

However, an adversarial examination of the task execution details against the existing codebase internals reveals **three critical implementation and behavioral defects (Must-Address)** and several testing/orchestration gaps that must be remediated before implementation begins:

1. **Top-Alignment Layout Defect in Task 02 (`\begin{center}` vs `{\centering ...}`)**: While the spec and critique remediation P2 explicitly mandate removing vertical centering and top-aligning column images with `{\centering \includegraphics[...]\par <caption>}`, `task-02-lowering.md` specifies emitting `\begin{center} ... \end{center}`. In LaTeX, `\begin{center}` is a `trivlist` environment that injects vertical whitespace (`\topsep` + `\parskip`) at the top of the column. In top-aligned Beamer frames (`\begin{columns}[T]`), this extra top margin pushes the image down by 6–10pt relative to bullet points in the adjacent column, reintroducing visual misalignment between the image and companion text.
2. **Backwards-Compatibility Violation on Standard Pandoc Fenced Divs**: Critique P1 was intended to fail loud when authors place introductory text before the first `:::` on a two-column slide. However, `task-01-detector.md` implements this by collecting all `:::` delimiter lines and failing loud if non-blank content precedes the first delimiter. In standard Pandoc Markdown, callout divs and speaker notes close with a bare `:::` line (e.g., `::: {.note} ... :::` or `::: notes ... :::`). On any ordinary slide using these standard Pandoc constructs, Task 01 treats the closing `:::` as a delimiter, detects the slide's preceding prose, and aborts the entire build with `SystemExit`. This directly violates Requirement R6 (backwards compatibility for non-two-column slides).
3. **Inversion of Delimiter Count Check and Unterminated Code Fence Diagnostic**: In `task-01-detector.md`, delimiter scanning ignores lines inside code blocks. If an author opens a code fence inside a column (e.g. ```` ```python ````) and omits the closing fence, all subsequent `:::` delimiters are ignored as code content. When reaching EOF, fewer than 3 delimiters are collected and the code fence remains unterminated. If delimiter count is checked before unclosed fence state, the error diagnostic reports `"expected 3 delimiters, found 1"` (or 2), completely obscuring the real defect (the unclosed code fence).

With these critical issues resolved and test coverage expanded, the task set provides an actionable execution plan.

**Verdict**: ⚠️ **PROCEED WITH UPDATES**

---

## Product Lens Findings

### 1a. Problem Validation
- **P1 (🎯 Must-Address — Backwards-Compatibility Breakdown for Pandoc Fenced Divs on Ordinary Slides)**:
  *Affected Artifacts*: `../specs/two-column-slides.md` (§Requirements R1, R6; §Detection Grammar), `../tasks/two-column-slides/task-01-detector.md` (lines 51–57).  
  *Finding*: Requirement R6 specifies that the feature is strictly opt-in: "a slide whose body does not open with a `:::` delimiter is untouched." In response to critique P1 (catching subtitles placed between `# Title` and the two-column block), `task-01-detector.md` prescribes:
  > "Walk lines with fence-aware scanning, collecting `:::` delimiter positions (outside code fences)... If delimiters exist: enforce the grammar and fail loud (`SystemExit`) otherwise: non-blank content between the title and the first delimiter → error 'content preceding the opening `:::` delimiter is not supported'..."
  
  In Pandoc Markdown, authors frequently write fenced divs for callouts or speaker notes (e.g., `::: {.note}\nWarning\n:::` or `::: notes\nSpeaker note\n:::`). The closing line of these divs is a bare `:::`, which matches `_COLON_FENCE_RE`. Under Task 01's current rule, any ordinary slide containing a Pandoc fenced div will have `delimiters exist` (the closing `:::` line). Because the slide has text prior to that closing line, `match_two_column_slide` aborts the build with `SystemExit`. An existing valid deck with Pandoc callouts or speaker notes suddenly fails to compile.  
  *Suggestion*: Condition the pre-delimiter check on clear intent to author a two-column slide. Specifically: if the first non-blank line after `# Title` is `:::`, the slide has opted into two-column layout. If the first non-blank line is not `:::`, check if the slide contains two or more subsequent `:::` delimiters forming a two-column pattern. If so, fail loud with the subtitle error; if not (e.g. isolated bare `:::` closing a Pandoc fenced div), return `None` and let ordinary slide processing continue untouched.

### 1b. User Value Assessment
- **P2 (💡 Recommendation — Incomplete Error Message Assertions in Test Suite)**:
  *Affected Artifacts*: `../tasks/two-column-slides/task-03-tests.md` (lines 36–42).  
  *Finding*: Requirement R5 guarantees that malformed markup produces an "actionable, slide-identifying message." In `task-03-tests.md`, test cases are specified as `pytest.raises(SystemExit)` without checking the exception string or captured stderr. A regression where `match_two_column_slide` calls `sys.exit(1)` with an empty message or fails to include the offending slide title would pass the test suite despite violating the R5 product contract.  
  *Suggestion*: In `task-03-tests.md`, require assertions that inspect `SystemExit` (e.g., `with pytest.raises(SystemExit) as ei: ...; assert "slide 'Title'" in str(ei.value)` or inspecting captured stderr) for all fail-loud cases.

### 1c. Alternative Approaches
- **P3 (💡 Recommendation — Clarify Caption Absence on Diagram Regions in User Docs)**:
  *Affected Artifacts*: `../specs/two-column-slides.md` (§Requirements R3, R7), `../tasks/two-column-slides/task-04-docs-example.md` (lines 38–46).  
  *Finding*: Spec R3 states that Markdown alt text renders as a small caption for images, but diagrams in columns (`mermaid`/`d2`) have no syntax for alt text. In presentations, authors often expect captions for technical figures. While Task 04 mentions noting this limitation, it should also suggest the standard authoring workaround (using a small paragraph or bullet in the companion text column for diagram attribution).  
  *Suggestion*: Ensure `task-04-docs-example.md` includes explicit documentation guidance showing authors how to place figure labels or diagram captions in the adjacent column.

---

## Engineering Lens Findings

### 2a. Architecture Soundness
- **E1 (🎯 Must-Address — Layout Misalignment in Task 02 via `\begin{center}` trivlist)**:
  *Affected Artifacts*: `../specs/two-column-slides.md` (§Proposed Solution — engine.py lowering), `../tasks/two-column-slides/task-02-lowering.md` (lines 36–45).  
  *Finding*: The Full Spec (lines 169–171) correctly amended the lowering logic following critique P2:
  > "It emits a top-aligned `{\centering\includegraphics[...]\par <caption>}` block instead; the `\vfill` vertical centring remains only in the whole-slide `picture_body_tex`."
  
  However, `task-02-lowering.md` diverged from the spec in line 40:
  > "`vcenter=False` emits a top-aligned `\begin{center} … \includegraphics[...]\par <caption> \end{center}` with no `\vfill`"
  
  In LaTeX, `\begin{center}` is implemented as a `trivlist` environment that inserts vertical whitespace (`\topsep` + `\parsep` / `\parskip`) above and below the centered contents. In Beamer's `\begin{columns}[T]` environment, the companion column (containing Markdown bullets or text) starts flush with the top margin of the column. Using `\begin{center}` in the image column introduces an unavoidable 6–10pt vertical displacement, pushing the image down and causing it to appear misaligned with companion bullets.  
  *Suggestion*: Update `task-02-lowering.md` to match the spec: for `vcenter=False`, emit `{\centering \includegraphics[...]\par <caption>}` without `\begin{center}` or `\vfill`. Reserve `\begin{center}` and `\vfill` strictly for `picture_body_tex` (`vcenter=True`).

### 2b. Failure Mode Analysis
- **E2 (🎯 Must-Address — Diagnostic Shadowing on Unterminated Inner Code Fence)**:
  *Affected Artifacts*: `../tasks/two-column-slides/task-01-detector.md` (lines 53–62), `../tasks/two-column-slides/task-03-tests.md` (lines 36–42).  
  *Finding*: Delimiter scanning is fence-aware: lines inside an unclosed code block are ignored. If an author writes:
  ```markdown
  # Slide Title
  :::
  ![Architecture](arch.png)
  :::
  ```python
  def run():
      pass
  :::
  ```
  Here, the author forgot to close the ```` ```python ```` code block. The third `:::` is swallowed as python code. The scanner reaches EOF with `len(delimiters) == 2` and `in_fence == True`. If Task 01 evaluates the delimiter count first (`if len(delimiters) != 3: raise "expected 3 delimiters, found 2"`), the author receives an error stating there are only 2 delimiters when 3 delimiters are plainly visible in the document.  
  *Suggestion*: In `task-01-detector.md`, mandate that unclosed code fence detection takes precedence over delimiter count evaluation: if `in_fence` is true at EOF, immediately raise `SystemExit` reporting the unterminated code fence (and its starting line or language), rather than reporting an incorrect delimiter count.

### 2c. Operational Readiness & Tooling Portability
- **E3 (💡 Recommendation — Bare `python` Command in Task 01 Manual Check)**:
  *Affected Artifacts*: `../tasks/two-column-slides/task-01-detector.md` (line 83).  
  *Finding*: Line 83 gives the manual check:
  `python -c "from md2pdf import slides; print(slides.match_two_column_slide(...))"`
  In this repository's development environment (Windows with `uv`), bare `python` is not available on `PATH`; execution fails with a command-not-found error. Line 89 correctly uses `uv run python`.  
  *Suggestion*: Update line 83 in `task-01-detector.md` to use `uv run python`.

### 2d. Data Model & Typing
- **E4 (🤔 Question — Heterogeneous Return Tuple in `classify_region`)**:
  *Affected Artifacts*: `../specs/two-column-slides.md` (§Interfaces sketch), `../tasks/two-column-slides/task-01-detector.md` (lines 69–73), `../tasks/two-column-slides/task-02-lowering.md` (lines 50–56).  
  *Finding*: `classify_region` returns a 3-tuple `("image", alt, path)`, a 3-tuple `("diagram", lang, source)`, or a 2-tuple `("markdown", region)`. This heterogeneous structure makes manual tuple unpacking error-prone (e.g. `kind, a, b = classify_region(region)` throws `ValueError` on markdown regions). Prior recommendation E9 suggested a structured type.  
  *Suggestion*: Clarify whether implementers should use Python 3.10 `match`/`case` pattern matching, or standardize on a uniform 3-tuple `("markdown", region, "")` or a lightweight `NamedTuple` (`RegionContent(kind, payload, extra="")`).

---

## Task-Level Sections

### Task Traceability

All 8 spec requirements (R1–R8) and the primary testing strategy risks map to tasks in `../tasks/two-column-slides/summary.md`. However, traceability gaps exist in verification evidence:

| Requirement / Risk | Mapped Task(s) | Specified Verification Evidence | Traceability Evaluation |
|---|---|---|---|
| **R1** Authoring convention (`:::`) | 01, 03 | Unit tests in `test_slides.py` | Complete. |
| **R2** Strictly two 50/50 | 02, 03 | Pandoc structural test in `test_engine.py` | Complete. |
| **R3** Both sides fit (top-aligned, 0.72h) | 02, 03 | Pandoc structural test | **Defect**: Task 02 emits `\begin{center}` instead of top-aligned `{\centering ...}` (E1). |
| **R4** Title & `.onlytextwidth` | 02, 03 | Pandoc structural test | Complete. |
| **R5** Fail-loud on malformed markup | 01, 03 | `pytest.raises(SystemExit)` | **Gap**: Does not assert diagnostic messages or slide identification (P2). |
| **R6** Backwards compatibility | 01, 02, 03 | Regression tests on existing decks | **Defect**: Task 01 detector breaks slides with Pandoc callouts (P1). |
| **R7** Diagrams in columns | 02, 03, 04 | `classify_region` test + e2e `d2` build | **Gap**: No pandoc-free unit test for diagram lowering in `preprocess_body` (E5). |
| **R8** Docs and example deck | 04 | `two-column-demo.md` + guarded build | Complete. |
| **Critique P1** Pre-delimiter text | 01, 03 | `pytest.raises(SystemExit)` | Over-broad detection trips on Pandoc divs (P1). |
| **Critique E2** General fence scanner | 01, 03 | Unit test with `python` code fence | Complete. |
| **Critique E7** Delimiter permutations | 03 | Unit tests for 2/4 delims, post-text | **Gap**: Missing test for duplicate/missing `# Title` (E7). |

### Implementation Readiness

- **File Ownership**: Clearly partitioned. `slides.py` is modified solely by Task 01; `engine.py` solely by Task 02; `test_slides.py` and `test_engine.py` solely by Task 03; `README.md`, `examples/two-column-demo.md`, and `test_examples_build.py` solely by Task 04. No concurrent file write hazards exist.
- **Interfaces & Data Flow**: 
  - `match_two_column_slide(chunk) -> dict | None`: clean tri-state contract.
  - `column_body_tex(alt, path) -> str`: clean interface reusing `_fit_image_tex`.
  - `classify_region`: functional, though heterogeneous tuple requires care (E4).
- **Grounded in Codebase**:
  - The fence regex `_FENCE_RE` and heading regex `_H1_RE` in `../../src/md2pdf/slides.py` are reused cleanly.
  - Emission in `engine.py` follows the existing pattern (`out_parts.append(...)` and `\n\n---\n\n.join(...)`).

### Verification Readiness

Three specific verification gaps weaken implementation readiness:

- **E5 (💡 Recommendation — Missing Pandoc-Free Unit Test for Diagram Lowering in `preprocess_body`)**:
  *Affected Artifacts*: `../tasks/two-column-slides/task-03-tests.md` (lines 47–58).  
  *Finding*: In `task-03-tests.md`, the tests for `preprocess_body` in `tests/test_engine.py` only cover `image+bullets` and markdown pass-through. The diagram-in-column path (`render_diagram` call, relative filename emission, `column_body_tex("", img.name)`) is only tested in Task 04's end-to-end build test (`test_examples_build.py`), which is skip-guarded on `d2`. On CI without `d2`, the diagram lowering branch has zero test coverage.  
  *Suggestion*: In `task-03-tests.md`, add a test in `tests/test_engine.py` that mocks or monkeypatches `render_diagram` (e.g. returning `Path("diagram_d2_abc.pdf")`) to verify that `preprocess_body` correctly routes diagram regions to `column_body_tex` without requiring external binaries.

- **E6 (💡 Recommendation — Fragile Regression Fixture for `diagram-demo.md` in Task 03)**:
  *Affected Artifacts*: `../tasks/two-column-slides/task-03-tests.md` (lines 56–58).  
  *Finding*: Task 03 instructs testing `preprocess_body` against the markdown bodies of all three example decks (including `diagram-demo.md`). However, in `src/md2pdf/engine.py` lines 105–109, `preprocess_body(body, diagram_dir=None)` immediately raises `SystemExit` if a diagram slide is encountered without a `diagram_dir`. Running `preprocess_body` directly on `diagram-demo.md` without passing `tmp_path / "diagrams"` will cause an unexpected test failure.  
  *Suggestion*: Explicitly instruct in `task-03-tests.md` to pass `diagram_dir=tmp_path / "diagrams"` when running the regression assertion on `diagram-demo.md`.

- **E7 (💡 Recommendation — Test Matrix Coverage for Layout Permutations & Duplicate Titles)**:
  *Affected Artifacts*: `../tasks/two-column-slides/task-03-tests.md` (lines 32–58).  
  *Finding*: The test plan only exercises `image-left / bullets-right`. Real decks frequently use `bullets-left / image-right`, `pic-left / pic-right`, or `diagram-left / bullets-right`. Furthermore, while Task 01 implements fail-loud logic for missing `# Title` and multiple `# Title` headings, Task 03 omits tests for these conditions.  
  *Suggestion*: Add unit and lowering test cases for: (1) `bullets-left / image-right`, (2) missing `# Title` with `:::`, and (3) multiple `# Title` lines in a two-column slide chunk.

### Orchestration Risks

- **O1 (💡 Recommendation — Intermediate Regression Verification in Tasks 01 and 02)**:
  *Affected Artifacts*: `../tasks/two-column-slides/summary.md` (§Dependencies & Parallel Work), `../tasks/two-column-slides/task-01-detector.md` (§Verification Requirements), `../tasks/two-column-slides/task-02-lowering.md` (§Verification Requirements).  
  *Finding*: Tasks 01 and 02 modify core parsing and lowering modules but only specify one-line smoke tests, deferring all regression testing to Task 03. If Task 01 accidentally regresses `match_picture_slide` or `match_diagram_slide`, the error will go undetected until Task 03.  
  *Suggestion*: Require `uv run pytest tests/test_slides.py` as an exit criterion for Task 01, and `uv run pytest tests/test_engine.py` for Task 02, ensuring zero regressions on existing functionality at each intermediate stage.
- **Safe Parallel Groups Viability**: The dependency graph `01 → 02 → {03, 04}` is well-structured. Tasks 03 and 04 touch strictly disjoint files (`tests/test_slides.py` + `tests/test_engine.py` vs. `README.md` + `examples/` + `tests/test_examples_build.py`), enabling safe concurrent execution.

---

## Cross-Lens Insights

- **X1 [Layout Precision × Rendering Engine Invariants (E1 + P2)]**:
  The failure to eliminate `\begin{center}` in Task 02 illustrates how high-level layout requirements ("top-aligned columns") can be subtly compromised by LaTeX environment mechanics. In Beamer, `\begin{center}` is not a neutral container; it is a list environment with inherent vertical padding. Enforcing `{\centering ... \par}` in Task 02 is essential to achieving professional, pixel-aligned slides.
- **X2 [Fail-Loud Posture × Dialect Extensibility (P1 + E2)]**:
  Enforcing strict validation must not compromise valid existing constructs. In attempting to catch pre-delimiter subtitles (P1), Task 01 inadvertently criminalized standard Pandoc fenced divs. A robust parser must distinguish between an author attempting two-column layout with illegal preamble text versus an author writing standard markdown with Pandoc callouts.

---

## Findings Summary Table

| ID | Lens | Severity | Category | Finding | Suggestion | Affected Files |
|:---|:---|:---:|:---|:---|:---|:---|
| **E1** | Engineering | 🎯 | Implementation Readiness | Task 02 emits `\begin{center}` in `_fit_image_tex` (`vcenter=False`), adding `\topsep` vertical padding that breaks top-alignment with adjacent bullets. | Emit `{\centering \includegraphics[...]\par <caption>}` without `\begin{center}` or `\vfill`, matching Spec §Lowering. | `docs/tasks/two-column-slides/task-02-lowering.md` |
| **P1** | Product | 🎯 | Architecture Soundness | Task 01 fails loud on any non-two-column slide containing a Pandoc fenced div (whose closing bare `:::` is mistreated as a delimiter). | Condition pre-delimiter validation on two-column intent (body opens with `:::`, or 2+ subsequent delimiters match two-column pattern). | `docs/specs/two-column-slides.md`, `docs/tasks/two-column-slides/task-01-detector.md` |
| **E2** | Engineering | 🎯 | Failure Modes | Delimiter count check precedes unclosed fence check; an unclosed code block inside a column reports a confusing "expected 3 delimiters, found 1/2". | Check `in_fence` at EOF and report unterminated code fence before evaluating delimiter count. | `docs/tasks/two-column-slides/task-01-detector.md` |
| **P2** | Product | 💡 | Verification Readiness | Task 03 tests `pytest.raises(SystemExit)` without asserting error message contents or slide identification. | Assert exception messages contain the offending slide title and expected diagnostic text. | `docs/tasks/two-column-slides/task-03-tests.md` |
| **P3** | Product | 💡 | User Value Assessment | Diagram regions lack caption syntax; documentation lacks suggested workaround. | Document pattern of using the companion text column for diagram labels and captions. | `docs/tasks/two-column-slides/task-04-docs-example.md` |
| **E3** | Engineering | 💡 | Implementation Readiness | Task 01 manual verification command uses bare `python`, which is absent from `PATH` in this environment. | Update manual check command to `uv run python`. | `docs/tasks/two-column-slides/task-01-detector.md` |
| **E4** | Engineering | 🤔 | Architecture / Typing | `classify_region` returns a heterogeneous 2-tuple / 3-tuple, creating unpacking hazards. | Standardize on a uniform 3-tuple (`("markdown", region, "")`) or a typed `NamedTuple`. | `docs/specs/two-column-slides.md`, `docs/tasks/two-column-slides/task-01-detector.md` |
| **E5** | Engineering | 💡 | Verification Readiness | No pandoc-free unit test for diagram lowering in `preprocess_body`; CI without `d2` leaves diagram routing untested. | Add unit test in `test_engine.py` with monkeypatched `render_diagram`. | `docs/tasks/two-column-slides/task-03-tests.md` |
| **E6** | Engineering | 💡 | Verification Readiness | Task 03 regression test running `preprocess_body` on `diagram-demo.md` will crash if `diagram_dir` is omitted. | Explicitly pass `diagram_dir=tmp_path / "diagrams"` in regression tests. | `docs/tasks/two-column-slides/task-03-tests.md` |
| **E7** | Engineering | 💡 | Verification Readiness | Test matrix omits inverse layout (`text-left / pic-right`) and missing/duplicate `# Title` failure modes. | Add unit and structural tests for layout permutations and heading errors. | `docs/tasks/two-column-slides/task-03-tests.md` |
| **O1** | Engineering | 💡 | Orchestration | Tasks 01 and 02 lack regression gates, risking accumulated failures before Task 03. | Require existing unit test suites (`pytest tests/test_slides.py`, `pytest tests/test_engine.py`) to pass at end of Tasks 01 and 02. | `docs/tasks/two-column-slides/summary.md`, `task-01-detector.md`, `task-02-lowering.md` |

---

## Verdict

⚠️ **PROCEED WITH UPDATES**

The core design (parsing `:::` in `slides.py` and lowering to native Pandoc Beamer column divs in `engine.py`) is sound, lean, and fits the codebase. Addressing the three Must-Address findings (**E1** image centering trivlist, **P1** Pandoc div false-positives on ordinary slides, and **E2** unclosed fence diagnostic precedence) along with the verification readiness improvements will ensure a reliable implementation.

# Critique: Mermaid & D2 Diagram Slides for md2pdf

**Document Under Review**: `tooling/specs/md2pdf-diagram-slides.md`  
**Review Date**: 2026-10-09  
**Review Type**: Pre-implementation Spec Critique (Dual-lens: Product & Engineering)

---

## Executive Summary

The proposed specification extends `tools/md2pdf/md2pdf.py` to support automated generation and fit-to-frame placement of Mermaid and D2 diagrams directly from Markdown code fences. The core concept directly mirrors the existing picture-slide pattern, maintaining a consistent mental model for deck authors and keeping the toolchain lightweight by selecting `d2` (vector PDF) and `mmdr` (pure-Rust PNG renderer, sidestepping the headless-Chrome dependency of `mmdc`).

Overall, the specification is focused, well-scoped, and aligns cleanly with the repository's existing architecture. However, several critical technical and product edge cases require resolution prior to implementation:
1. **Intermediate asset lifecycle breaks `--keep-tex`**: Storing rendered diagram assets exclusively in a transient `TemporaryDirectory()` causes any kept `.tex` document to reference non-existent files immediately after compilation.
2. **Subprocess execution risks unbounded hangs**: Shelling out to external rendering binaries without explicit timeouts or `stdin=subprocess.DEVNULL` risks hanging the CLI build indefinitely on malformed input or interactive prompts.
3. **Unspecified Mermaid raster parameters**: The spec calls for high-resolution PNG generation via `mmdr` without specifying raster width or aspect ratio flags, risking visual distortion or pixelation on high-DPI slide outputs.
4. **Silent fallback for disqualified diagram slides**: Code blocks placed alongside other slide content fail strict detection and fall back silently to verbatim code blocks without author diagnostics.

With targeted updates to resolve intermediate asset retention, subprocess failure boundaries, and raster parameter specifications, this design is ready for implementation.

**Verdict**: ⚠️ **PROCEED WITH UPDATES**

---

## Product Lens Findings

### 1a. Problem Validation
- **P1 (💡 Recommendation — Disqualified Diagram Slide Feedback)**: The strict slide definition (exactly one `# Title` and one fenced diagram block) mirrors picture slides. However, while an image token on a normal slide still renders as an embedded image in standard Pandoc Beamer, a diagram code fence on a normal slide (e.g. accompanied by bullet points or explanatory prose) will silently render as a verbatim text code block. Authors expecting automatic rendering may assume a silent tool defect rather than a deliberate rejection by strict detection rules.
  - *Suggestion*: Add a diagnostic warning during slide preprocessing when a non-matching slide contains a Mermaid or D2 fenced block, alerting authors that the diagram was rendered verbatim because the slide did not meet strict single-diagram criteria.

### 1b. User Value Assessment
- **P2 (💡 Recommendation — Slide Background & Theme Consistency)**: HIVE slide decks follow strict brand guidelines (deep blue `#00306F`, signature cyan `#009DD9`, grey, and white background). `d2` defaults to its classic palette (theme 0) and `mmdr` defaults to Mermaid's standard palette (pastel greens, teals, and dark borders). Without explicit styling guidelines or default flags, rendered diagrams may appear visually discordant with the surrounding slide chrome.
  - *Suggestion*: Specify explicit default styling flags in the renderer invocation (e.g. `--theme 0` or neutral for `d2`, `-t default` or `-t neutral` for `mmdr`), and mandate an opaque white background to ensure visual harmony with the white Beamer frame body.
- **P3 (💡 Recommendation — Caption and Figure Attribution Mechanism)**: Picture slides support figure captions through standard Markdown alt text (`![caption](path)`). The diagram slide spec explicitly states: "There is no caption (diagrams carry no alt text)." For technical presentations, diagrams frequently require a caption, data source attribution, or figure label.
  - *Suggestion*: Clarify whether diagram captions are permanently out of scope or deferred to a follow-on phase. If deferred, define an optional future path (such as parsing an optional string argument from the code fence header: ```` ```mermaid "Figure caption" ````).

### 1c. Alternative Approaches
- **P4 (💡 Recommendation — Evaluation of Pandoc Lua Filter vs Python Regex)**: The spec proposes a custom Python regex detector and string rewriting step (`match_diagram_slide` and `preprocess_body`). A Pandoc Lua filter could intercept `CodeBlock` AST elements directly inside Pandoc, avoiding custom Markdown splitting and regex parsing.
  - *Suggestion*: Explicitly document the rationale for choosing the Python preprocessor pipeline over a Lua filter (namely, consistency with the existing `match_picture_slide` and `picture_body_tex` architecture, zero additional Lua dependencies, and single-file maintainability in `tools/md2pdf/md2pdf.py`).

### 1d. Edge Cases & User Experience
- **P5 (🤔 Question — Fence Whitespace and Syntax Permutations)**: Authors may introduce slight formatting variations, such as trailing whitespace after language identifiers (` ```mermaid   `), info strings with options (` ```d2 layout=elk `), or blank lines surrounding the block.
  - *Suggestion*: Specify that `match_diagram_slide` normalises and strips trailing whitespace from info strings, and explicitly restrict accepted info strings to exact matches on `mermaid` and `d2` for MVP.

### 1e. Success Measurement
- **P6 (💡 Recommendation — Performance Budget and Visual Acceptance Criteria)**: The spec lacks concrete acceptance thresholds for rendering latency and output crispness.
  - *Suggestion*: Introduce an explicit build latency target (e.g. < 250 ms per diagram slide on standard developer hardware) and verify that generated PNG text remains crisp when projected at full slide width (1920×1080 equivalent).

---

## Engineering Lens Findings

### 2a. Architecture Soundness
- **E1 (🎯 Must-Address — Intermediate Asset Retention with `--keep-tex`)**: In Task 3, `render_diagram` is specified to write rendered image files into a build-scoped temporary directory managed by `tempfile.TemporaryDirectory()`. However, `md2pdf.py` provides a `--keep-tex` flag designed to preserve intermediate LaTeX files for debugging, archival, or manual XeLaTeX compilation. If generated diagrams reside only in the temporary directory, the kept `.tex` file will reference deleted image files the moment the Python process terminates.
  - *Suggestion*: When `--keep-tex` is active, write or copy generated diagram images to a persistent directory adjacent to the generated `.tex` file (e.g. `output.parent / f"{output.stem}_assets/"` or directly next to `output`), and ensure the LaTeX `\includegraphics` paths accurately resolve to those persistent assets.
- **E2 (🎯 Must-Address — Unspecified Raster Dimensions in Mermaid Renderer)**: Task 2 specifies `mmdr -i <src.mmd> -o <out.png> -e png (with a high raster size/scale)` without specifying the exact CLI flags. In `mmdr`, `-w` controls width and `-H` controls height. If an implementer specifies both without maintaining diagram aspect ratios, rendering will distort. If an implementer omits width, `mmdr` renders at natural diagram dimensions, which may result in severe pixelation on high-DPI slides.
  - *Suggestion*: Explicitly specify the CLI command parameters in Task 2 to pass `-w 2400` (and omit `-H`), allowing `mmdr` to rasterise at high resolution while automatically preserving the diagram's intrinsic aspect ratio.

### 2b. Failure Mode Analysis
- **E3 (🎯 Must-Address — Subprocess Execution Hanging and Input Deadlocks)**: Task 2 invokes `subprocess.run` to execute external CLIs. If `d2` or `mmdr` hangs on complex input, triggers an internal layout deadlock, or halts waiting for interactive stdin input (e.g. unexpected prompt), the entire `md2pdf` build will hang indefinitely.
  - *Suggestion*: Enforce `timeout=30` (or 60) and `stdin=subprocess.DEVNULL` on all `subprocess.run` calls in `render_diagram`. Wrap calls in a `try...except subprocess.TimeoutExpired` block that raises `SystemExit` with the offending slide title and timeout duration.
- **E4 (💡 Recommendation — Decoding and Reporting of Stderr on Failure)**: On Windows platforms, subprocess output may be emitted in diverse code pages. If diagram compilation fails and error messages contain special characters or non-ASCII identifiers, unhandled decoding can raise a secondary `UnicodeDecodeError`, obscuring the real compiler diagnostic.
  - *Suggestion*: Specify that subprocess stdout and stderr streams are explicitly decoded using `encoding="utf-8", errors="replace"` prior to formatting user error messages.

### 2c. Security & Privacy Review
- **E5 (💡 Recommendation — Local Execution Boundaries and External Fetching)**: `d2` has features for importing external icon assets or remote links. In automated or CI slide generation workflows, unexpected outbound network requests introduce latency or security risks.
  - *Suggestion*: Document that diagram rendering runs in an offline, local-only context, and ensure that arguments passed to `d2` disable remote browser opening (`--browser 0`) and avoid network dependencies.

### 2d. Performance & Scalability
- **E6 (💡 Recommendation — Deterministic Content Hashing Scheme)**: Task 2 mentions "hash of source to avoid collisions." If hash generation only hashes the diagram text, two different diagram types (or future configuration changes) could collide if their source text happened to match.
  - *Suggestion*: Standardise the cache key and output filename convention to include both language and content hash, e.g. `f"diagram_{lang}_{sha256(source.encode()).hexdigest()[:16]}.{ext}"`.

### 2e. Testing Strategy
- **E7 (💡 Recommendation — Missing Negative Testing for Render Failures in Task 2)**: Task 2 test requirements describe happy-path rendering and unit testing for missing CLI binaries. It omits testing diagram syntax errors and non-zero exit codes.
  - *Suggestion*: Add explicit test assertions for invalid Mermaid and D2 syntax, verifying that malformed source triggers `SystemExit` containing the slide title, renderer name, and captured stderr.
- **E8 (💡 Recommendation — Mocked CLI Resolution in CI Environments)**: CI build runners may not have `d2` or `mmdr` installed. Tests relying on these binaries will be skipped if gated only by `shutil.which`.
  - *Suggestion*: Structure tests with pure unit tests (using mocked subprocesses to test command formation, error parsing, and timeout handling) and separate integration tests gated by `pytest.mark.skipif(not _has_cli("d2"), ...)`.

### 2f. Operational Readiness & Tool Resolution
- **E9 (💡 Recommendation — Path Resolution Fallbacks for Developer Environments)**: Section "Toolchain findings" observes that `d2` resides in `~/go/bin/d2.exe` and `mmdr` in `~/.cargo/bin/mmdr.exe`. On Windows systems, user Go and Cargo bin directories are not always universally present in ambient subshell `PATH` variables.
  - *Suggestion*: In the CLI resolution helper, implement a search hierarchy that checks `shutil.which` first, followed by known standard tool paths (`Path.home() / ".cargo" / "bin" / "mmdr.exe"` and `Path.home() / "go" / "bin" / "d2.exe"`). On failure, output explicit installation guidance (e.g. `cargo install mmdr`, `go install oss.terrastruct.com/d2@latest`).

### 2g. Dependencies & Integration Risks
- **E10 (💡 Recommendation — Path Handling in LaTeX Inclusion)**: On Windows, paths inside `TemporaryDirectory()` can contain spaces (e.g. `C:\Users\John Doe\AppData\...`). LaTeX's `\includegraphics` fails on paths with unescaped spaces unless wrapped or passed via relative resource directories.
  - *Suggestion*: Ensure diagram output files are written to paths without spaces, or pass the temporary output directory to Pandoc via `--resource-path` so that `picture_body_tex` can emit relative filenames.

---

## Cross-Lens Insights

- **X1 [Scope × Asset Lifecycle (E1 & P3)]**: Deck authors who inspect or reuse intermediate LaTeX output (`--keep-tex`) expect a self-contained, reproducible document. If diagram assets vanish with the temporary directory, the output is broken for human handoff or post-processing. Persisting assets alongside the `.tex` file satisfies both product usability and technical reproducibility.
- **X2 [Reliability × User Diagnostics (E3 & P1)]**: A build tool must never fail silently nor hang unpredictably. Enforcing subprocess execution timeouts paired with clear diagnostics for disqualified or malformed diagram slides ensures authors understand immediately whether a slide was disqualified by formatting or rejected by a syntax error.

---

## Findings Summary Table

| ID | Lens | Severity | Category | Finding | Suggestion |
|:---|:---|:---:|:---|:---|:---|
| **E1** | Engineering | 🎯 | Architecture Soundness | Diagram assets written to `TemporaryDirectory` disappear after build, breaking `--keep-tex` output. | Persist diagram assets in `output.parent / f"{output.stem}_assets/"` when `--keep-tex` is specified. |
| **E2** | Engineering | 🎯 | Performance & Scalability | `mmdr` invocation lacks explicit raster dimension and aspect ratio specifications, risking blurriness or distortion. | Specify `-w 2400` in `mmdr` arguments to enforce high-resolution rendering with automatic aspect preservation. |
| **E3** | Engineering | 🎯 | Failure Mode Analysis | Subprocess calls lack timeouts and `stdin=subprocess.DEVNULL`, risking indefinite build hangs. | Add `timeout=30`, `stdin=subprocess.DEVNULL`, and catch `TimeoutExpired` to raise clean `SystemExit`. |
| **P1** | Product | 💡 | User Experience | Slides failing strict diagram criteria fall back silently to verbatim code blocks without warning. | Emit a non-fatal warning during preprocessing when a non-matching slide contains Mermaid or D2 blocks. |
| **P2** | Product | 💡 | Branding & Visuals | Renderers default to arbitrary internal palettes that may clash with HIVE slide styling. | Set default renderer flags (`--theme 0` for D2, `-t default` for mmdr) and enforce opaque white backgrounds. |
| **P3** | Product | 💡 | User Value Assessment | Diagram slides omit figure captions, preventing source attribution or explanatory notes. | Clarify caption roadmap and evaluate optional caption parsing via fence info string arguments. |
| **P4** | Product | 💡 | Alternative Approaches | Rationale for Python regex preprocessor over Pandoc Lua filter is not explicitly documented. | Document the architectural decision to keep md2pdf single-file and consistent with `match_picture_slide`. |
| **P5** | Product | 🤔 | Edge Cases | Permissible whitespace and info string variations in code fence detection are ambiguous. | Explicitly define fence parsing rules: strip whitespace and reject unknown info parameters for MVP. |
| **P6** | Product | 💡 | Success Measurement | Lack of quantitative performance and visual rendering quality metrics. | Add target rendering latency (< 250 ms per diagram) and full-width legibility criteria. |
| **E4** | Engineering | 💡 | Failure Mode Analysis | Subprocess stderr decoding without explicit error handling may trigger `UnicodeDecodeError` on Windows. | Decode subprocess output with `utf-8` and `errors="replace"` before formatting error messages. |
| **E5** | Engineering | 💡 | Security & Boundaries | Potential network requests by D2 for external assets in CI/offline builds. | Explicitly enforce local-only rendering parameters (e.g. `--browser 0`) and document offline constraints. |
| **E6** | Engineering | 💡 | Architecture Soundness | Cache key convention relies solely on content hash without language namespacing. | Structure output filenames as `diagram_{lang}_{sha256(source)[:16]}.{ext}` to eliminate collisions. |
| **E7** | Engineering | 💡 | Testing Strategy | Task 2 test requirements omit negative testing for syntax errors and non-zero exit codes. | Add test cases verifying that invalid diagram syntax triggers `SystemExit` with slide title and stderr. |
| **E8** | Engineering | 💡 | Testing Strategy | Tests without mocks will skip in environments lacking `d2` or `mmdr` binaries. | Separate mocked unit tests (testing command formation and error handling) from CLI integration tests. |
| **E9** | Engineering | 💡 | Operational Readiness | CLIs in user Go/Cargo bin folders may not resolve if ambient `PATH` lacks them. | Add fallback checks for `~/.cargo/bin` and `~/go/bin`, and provide clear installation hints on failure. |
| **E10** | Engineering | 💡 | Architecture Soundness | Temporary paths containing spaces can break LaTeX `\includegraphics` commands on Windows. | Use relative graphic paths via Pandoc `--resource-path` or ensure output paths are sanitized. |

---

## Recommended Spec Remediations

To address the findings before implementation, the following updates are recommended for `tooling/specs/md2pdf-diagram-slides.md`:

### 1. Remediation for E1 (Asset Persistence with `--keep-tex`)
In **Task 3**, update the temp directory and asset handling specification:
```markdown
### Task 3: Wire diagram slides into `preprocess_body` and `build()`

Thread a dedicated diagram output directory through `preprocess_body(body, diagram_dir)`. When `keep_tex` is False, `diagram_dir` points inside the build's `TemporaryDirectory()`. When `keep_tex` is True, `diagram_dir` is created persistently alongside the output (e.g. `output.parent / f"{output.stem}_diagrams"`), ensuring that intermediate `.tex` files retain valid references to all rendered diagram assets. Add `diagram_dir` to Pandoc's `--resource-path` so image references remain relative and portable.
```

### 2. Remediation for E2 & E3 (CLI Parameters, Timeouts, and Error Handling)
In **Task 2**, replace the command sketch with exact execution requirements:
```markdown
### Task 2: Diagram renderer with loud failure (test-first where possible)

Add `render_diagram(lang: str, source: str, out_dir: Path, slide_title: str) -> Path`.
- Filename convention: `out_dir / f"diagram_{lang}_{hashlib.sha256(source.encode()).hexdigest()[:16]}.{ext}"` (`.pdf` for d2, `.png` for mermaid). If the file already exists in `out_dir`, return it immediately.
- Commands:
  - For D2: `["d2", "--theme", "0", "--browser", "0", str(src_file), str(out_file)]`
  - For Mermaid: `["mmdr", "-i", str(src_file), "-o", str(out_file), "-e", "png", "-w", "2400"]`
- Subprocess invocation: Execute with `subprocess.run(cmd, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)`.
- Error handling: Catch `subprocess.TimeoutExpired` and raise `SystemExit(f"ERROR: Diagram rendering timed out on slide '{slide_title}' ({lang})")`. If `proc.returncode != 0`, decode stderr using `utf-8` (`errors="replace"`) and raise `SystemExit` naming the tool, the slide title, and the compiler diagnostic.
- Binary resolution: Use `shutil.which` with fallback checks in `~/.cargo/bin` (`mmdr`) and `~/go/bin` (`d2`).
```

### 3. Remediation for E7 (Test Coverage for Syntax Failures)
In **Task 2**, expand testing requirements:
```markdown
Tests:
- Integration test rendering a valid D2 diagram to PDF and a valid Mermaid diagram to PNG (skipif CLIs absent).
- Integration test passing invalid syntax (e.g. malformed syntax in Mermaid/D2) asserting `SystemExit` is raised with the slide title, tool name, and captured stderr.
- Unit test mocking `subprocess.run` to assert that `TimeoutExpired` raises `SystemExit` naming the timeout.
- Unit test mocking missing binaries asserting actionable installation instructions in `SystemExit`.
```

### 4. Remediation for P1 (Disqualified Slide Diagnostics)
In **Task 1 & Task 3**, add diagnostic logging:
```markdown
In `preprocess_body`, if a slide chunk contains a ` ```mermaid ` or ` ```d2 ` fence but `match_diagram_slide` returns `None` (disqualified by extra prose, bullet points, or multiple blocks), emit a diagnostic warning to `sys.stderr` indicating that the slide will render as a standard text slide rather than an auto-rendered diagram slide.
```

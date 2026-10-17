---
status: applied
target: ../specs/two-column-slides.md
target-revision: ae31279
---

# Specification Critique: Two-Column (Picture + Text) Slides

**Document Under Review**: `../specs/two-column-slides.md`  
**Review Type**: Pre-split Specification-Level Critique (Product & Engineering Lenses)  
**Target Revision**: `ae31279`  

---

## Executive Summary

The Full Specification at `../specs/two-column-slides.md` designs a two-column slide layout mechanism for `md2pdf`. It directly builds upon the decisions locked in `../brainstorms/two-column-slides-brainstorm.md` (Q1–Q5) and `../seed/two-column-slides.md`: a bespoke `:::` authoring shorthand, strictly two columns in a 50/50 split, top-aligned, fit-to-column scaling for lone images and diagrams, and a strict fail-loud posture for malformed markup. The proposed architecture adopts Approach A from the brainstorm: parsing `:::` in `../../src/md2pdf/slides.py` and lowering it to native Pandoc Beamer column divs in `../../src/md2pdf/engine.py`, preserving native Markdown rendering inside columns while avoiding extra Pandoc passes or raw-LaTeX markdown re-implementation.

The overall architectural direction is sound, lean, and fits the existing codebase cleanly. However, an adversarial specification-level review reveals several critical gaps, visual layout hazards, and edge cases that must be addressed before proceeding to task splitting and implementation:

1. **Beamer Frame Margin Bleed (Missing `.onlytextwidth`)**: Lowering to `:::::: {.columns align=top}` without `.onlytextwidth` causes Beamer to expand columns to `\paperwidth` instead of `\textwidth`, causing column content to bleed into and overlap theme-branded frame margins.
2. **Broken Vertical Alignment (`\vfill` in `column_body_tex`)**: Reusing `picture_body_tex`'s `\vfill` wrapper inside `column_body_tex` forces vertical centering inside the column, directly breaking the locked `align=top` contract and causing companion bullet points in the adjacent column to look visually detached and unaligned.
3. **Silent Bypass of Two-Column Layout on Pre-Delimiter Content**: Defining the trigger as "first non-blank line after `# Title` must be `:::`" means that if an author writes a subtitle or intro sentence before `:::`, `match_two_column_slide` returns `None`. The slide falls through to Pandoc as raw text, silently corrupting the slide output without raising the promised fail-loud error.
4. **Defective Code Fence Scanner in `slides.py`**: The spec prescribes reusing `match_diagram_slide`'s fence scanner to prevent `:::` inside code fences from tripping region splits. However, `match_diagram_slide` only recognizes `mermaid` and `d2` fences; any generic code fence (e.g. `python`, `json`, or untagged) would be ignored by that scanner, causing delimiter collisions.

With these concrete issues resolved, the design is robust and ready for task splitting.

**Verdict**: ⚠️ **PROCEED WITH UPDATES**

---

## Product Lens Findings

### 1a. Problem Validation
- **P1 (🎯 Must-Address — Silent Bypass on Pre-Delimiter Text / Subtitles)**:
  *Finding*: R1 and Section "slides.py — detection" specify that after `# Title`, the first non-blank line must be a `:::` delimiter; if not, `match_two_column_slide` returns `None`. In technical slide decks, authors commonly add a subtitle, lead paragraph, or context note directly under the `# Title` before splitting into columns:
  ```markdown
  # System Architecture
  High-level overview of ingest and storage layers.

  :::
  ![Architecture](assets/arch.png)
  :::
  - Ingest service normalises payloads
  - Storage engine partitions time series
  :::
  ```
  Because the line following `# Title` is not `:::`, the matcher returns `None`. The slide falls through to Pandoc as standard Markdown, where Pandoc parses the bare `:::` lines as malformed divs. The author receives no actionable error message, violating R5 ("no lenient warn-and-pass-through").
  *Suggestion*: Amend the grammar rule: a two-column slide must not allow arbitrary text between `# Title` and the opening `:::`. If a slide chunk contains `:::` delimiter lines anywhere outside code fences, but has text preceding the first `:::`, `match_two_column_slide` must fail loud with an explicit diagnostic (`"ERROR: slide '{title}': content preceding the opening ':::' delimiter is not supported in two-column slides"`), preventing silent malformed fall-through.

### 1b. User Value Assessment
- **P2 (🎯 Must-Address — Broken Vertical Top-Alignment via `\vfill`)**:
  *Finding*: Locked decision Q4 and Requirement R4 mandate fixed `align=top`. Section "engine.py — lowering" defines `column_body_tex(alt, path)` as "identical to `picture_body_tex` but scoped to the column". In `../../src/md2pdf/engine.py`, `picture_body_tex` encloses the image in `\vfill ... \vfill` to vertically center whole-frame images. In a Beamer `\begin{columns}[T]` layout, `\vfill` above the image pushes the image down or expands flexibly, while the adjacent text/bullet column aligns to the top margin. This creates an awkward vertical displacement between the picture and its accompanying bullets.
  *Suggestion*: Remove `\vfill` from `column_body_tex`. The column image block should top-align cleanly with companion text using `{\centering \includegraphics[width=\columnwidth,height=0.72\textheight,keepaspectratio]{...}\par ...}`. Reserve vertical centering solely for whole-slide picture frames.

- **P3 (💡 Recommendation — Diagram Captioning and Attribution Parity)**:
  *Finding*: Images in columns support captions via Markdown alt text (`![Caption](path)`). Diagram code fences (`mermaid`/`d2`) do not afford alt text, so column diagrams render with no caption or attribution mechanism. Technical presentations frequently require figure numbers or diagram labels.
  *Suggestion*: Document in R3 and the README dialect section that diagram regions in v1 do not carry captions (consistent with whole-slide diagram slides), but note that authors can provide explanatory labels in the companion text column.

### 1c. Alternative Approaches
- **P4 (💡 Recommendation — Dialect Constraint Documentation for `---` Slide Breaks)**:
  *Finding*: In `md2pdf`, `split_slides` splits the document on `^-{3,}$`. If an author uses a horizontal rule (`---`) inside a text column (e.g. to divide two bullet groups), the slide chunk will be severed mid-column, resulting in two broken slide chunks and an unexpected delimiter error.
  *Suggestion*: Explicitly document in the dialect specification and user docs that horizontal rule dividers (`---`) are slide delimiters and cannot be used inside column regions.

### 1d. Edge Cases & User Experience
- **P5 (💡 Recommendation — Warning Suppression on Disqualified Diagram Fences in Columns)**:
  *Finding*: Currently, `engine.py` emits a warning when a slide has a `mermaid`/`d2` fence that is not a strict diagram slide (`_chunk_has_diagram_fence`). In a two-column slide, if an author places a diagram fence alongside bullets in the same column, `classify_region` classifies it as `"markdown"`. The slide is rewritten to Pandoc divs and bypassed from the rest of `preprocess_body`, silently bypassing the near-miss warning.
  *Suggestion*: In `preprocess_body`, if a two-column slide contains a `mermaid` or `d2` fence that was classified as `"markdown"` (i.e. mixed with other text), emit a diagnostic warning explaining that diagrams inside columns must be the sole content of the region to be rendered automatically.

- **P6 (🤔 Question — Nested Pandoc Divs inside Columns)**:
  *Finding*: Pandoc Markdown allows authors to write fenced divs (such as `::: notes` for speaker notes or `::: {.warning}`). Because Pandoc divs close with a bare `:::`, an author writing speaker notes inside a column will inadvertently introduce a 4th delimiter line, triggering a fail-loud syntax error.
  *Suggestion*: Clarify in the spec whether nested Pandoc divs (e.g. `::: notes`) are unsupported inside two-column regions in v1, and explicitly document this constraint in the dialect documentation.

### 1e. Success Measurement
- **P7 (💡 Recommendation — Build Performance & Visual Acceptance Criteria)**:
  *Finding*: The Testing & Risk Strategy tests functionality and structure, but defines no quantitative performance budget or visual acceptance thresholds. Diagram rendering and multi-column lowering should not degrade compilation time.
  *Suggestion*: Add explicit acceptance criteria: (1) two-column preprocessing overhead < 15ms per slide (excluding external diagram CLI runtime); (2) visual verification that 16:9 slides with 50/50 split maintain theme margins and do not exhibit text or diagram clipping.

---

## Engineering Lens Findings

### 2a. Architecture Soundness
- **E1 (🎯 Must-Address — Missing `.onlytextwidth` Class in Emitted Pandoc Divs)**:
  *Finding*: Section "engine.py — lowering" specifies emitting:
  ```text
  :::::: {.columns align=top}
  :::: {.column width="50%"}
  ...
  ::::
  ::::::
  ```
  Pandoc lowers `:::::: {.columns align=top}` to Beamer's `\begin{columns}[T]`. In Beamer, `\begin{columns}` defaults to `totalwidth=\paperwidth` unless `onlytextwidth` is supplied. Without `onlytextwidth`, the column environment spans the entire slide width, ignoring the left and right theme margins (`\setbeamersize{text margin left=...}`). The left column collides with slide margins, title band alignment, and theme logos.
  *Suggestion*: Update the emitted Pandoc div header in `engine.py` to:
  ```text
  :::::: {.columns .onlytextwidth align=top}
  ```
  Pandoc lowers this directly to `\begin{columns}[T,onlytextwidth]`, constraining the two columns strictly within `\textwidth` and preserving theme margins.

- **E2 (🎯 Must-Address — Code Fence Tracking Defect in Delimiter Scanner)**:
  *Finding*: Section "slides.py — detection" states: "scanned outside any inner ```` ``` ````/`~~~` fence (reuse `match_diagram_slide`'s fence tracking so a `:::` inside a code block is content, not a delimiter)."
  However, examining `../../src/md2pdf/slides.py` lines 111–120 shows that `match_diagram_slide` only tracks fences whose info string matches `_DIAGRAM_LANGS` (`mermaid`, `d2`). It rejects and does not track generic code fences (e.g. ```` ```python ````, ```` ```sh ````, or untagged code blocks). If an author places a code block containing `:::` inside a column, `match_diagram_slide`'s existing scanner will not track it, treating the inner `:::` as a delimiter.
  *Suggestion*: Do not refer to reusing `match_diagram_slide` directly. Specify a dedicated fence tracker helper in `slides.py` (e.g. `_is_code_fence_delimiter`) that tracks any opening backtick or tilde fence (3+ characters) regardless of language tag, and ignores all lines until the matching closing fence.

### 2b. Failure Mode Analysis
- **E3 (💡 Recommendation — Contextual Slide Identification on Missing Titles)**:
  *Finding*: R5 requires "an actionable, slide-identifying message" on failure. `match_two_column_slide(chunk: str)` only receives the raw chunk string. If a slide opens with `:::` but omits the `# Title`, or if the title is malformed, the detector cannot extract a slide title for the error message.
  *Suggestion*: Define a fallback slide identification strategy: if `_H1_RE` cannot find a title, format the error using the chunk's first non-empty line or slide index: `ERROR: malformed two-column slide (near '::: <snippet>'): missing required '# Title' heading`.

- **E4 (💡 Recommendation — Stricter Trailing Whitespace vs. Content Detection)**:
  *Finding*: The grammar states: "content after the closing delimiter ... -> fail-loud." In Markdown documents, trailing blank lines frequently precede the `---` slide separator. If an implementer checks `lines[close_idx:]` without checking `line.strip()`, benign blank lines will trigger a false-positive failure.
  *Suggestion*: Clarify the rule: any *non-blank* line following the closing delimiter triggers `SystemExit`. Trailing blank lines and whitespace are discarded.

### 2c. Security & Privacy Review
- **E5 (💡 Recommendation — Relative Resource Isolation for Column Images)**:
  *Finding*: `column_body_tex` processes image paths via `latex_path(Path(path))`. If an author references an absolute path or parent traversal (`../../etc/passwd`), the path is embedded into `\includegraphics`.
  *Suggestion*: Note in the spec that path resolution for column images adheres to the existing `\graphicspath` and Pandoc `--resource-path` boundaries already audited for whole-slide picture slides.

### 2d. Performance & Scalability
- **E6 (💡 Recommendation — Bounded Height for Column Images with Captions)**:
  *Finding*: The spec specifies `height=0.78\textheight` for `column_body_tex`. On a 16:9 Beamer slide with a title header band, the total available vertical space is ~0.80\textheight. If an image has portrait aspect ratio and hits the `0.78\textheight` limit, adding a multi-line caption (`\vskip0.4em{\small ...\par}`) causes vertical frame overflow (`Overfull \vbox`).
  *Suggestion*: Set the maximum height in `column_body_tex` to `height=0.72\textheight` (or conditionally `0.70\textheight` when `alt` is non-empty), ensuring the combined image and caption never exceed the frame boundary.

### 2e. Testing Strategy
- **E7 (💡 Recommendation — Explicit Negative Tests for Delimiter Permutations)**:
  *Finding*: The Testing & Risk Strategy outlines unit and pandoc-only tests, but lacks explicit negative cases for: (a) 4 delimiters; (b) 2 delimiters; (c) content preceding opening delimiter; (d) content following closing delimiter; (e) code block containing `:::`; (f) unclosed code fence inside a column.
  *Suggestion*: Explicitly list these 6 test cases in the test matrix for `match_two_column_slide` to guarantee comprehensive branch coverage of all fail-loud conditions.

### 2f. Operational Readiness
- **E8 (💡 Recommendation — Indentation Tolerance on Delimiters)**:
  *Finding*: `_COLON_FENCE_RE = re.compile(r'^:{3,}\s*$')` requires colons to start at index 0. Authors writing indented markdown lists or nested structures often inadvertently indent fences by 1–3 spaces. Pandoc and CommonMark permit up to 3 spaces of indentation on fences.
  *Suggestion*: Define delimiter matching using `raw.lstrip()` or `r'^\s{0,3}:{3,}\s*$'` so that minor indentation does not trigger an unexpected failure.

### 2g. Dependencies & Integration Risks
- **E9 (💡 Recommendation — Region Classifier Data Model)**:
  *Finding*: In Section "Interfaces (sketch)", `classify_region(region: str) -> tuple` returns a heterogeneous tuple `("image"|"diagram"|"markdown", ...)`. This loosely-typed structure is error-prone when unpacked across callers.
  *Suggestion*: Use a lightweight dataclass or `NamedTuple` (e.g. `RegionContent(kind: str, payload: tuple)` or a typed dictionary) to provide clear, type-safe field access in `engine.py`.

---

## Cross-Lens Insights

- **X1 [Visual Polish × Layout Boundaries (E1 + P2)]**:
  The two most significant layout flaws converge here: omitting `.onlytextwidth` causes the columns to spread across `\paperwidth` (violating theme margins), while retaining `\vfill` causes the image to detach from the top alignment of the companion text. Addressing both issues ensures that two-column slides respect theme branding and deliver clean, professional typography out of the box.
- **X2 [Author Trust × Fail-Loud Contract (P1 + E2 + E3)]**:
  The core value proposition of md2pdf's slide conventions is predictability. If pre-delimiter text causes silent passthrough to Pandoc (P1), or if an inner Python code block trips the delimiter parser (E2), authors will be frustrated by inscrutable build failures. A robust fence scanner paired with strict rejection of pre-delimiter text ensures the fail-loud promise is honored reliably.

---

## Findings Summary Table

| ID | Lens | Severity | Category | Finding | Suggestion |
|:---|:---|:---:|:---|:---|:---|
| **P1** | Product | 🎯 | Problem Validation | Introductory text between `# Title` and `:::` causes silent fall-through and corrupted slides. | Fail loud if non-blank content precedes the opening `:::` delimiter. |
| **P2** | Product | 🎯 | User Value Assessment | `\vfill` in `column_body_tex` breaks top-alignment with companion text in Beamer. | Remove `\vfill` from `column_body_tex`; top-align image box. |
| **P3** | Product | 💡 | User Value Assessment | Diagram fences in columns do not support captions/attribution. | Document as v1 limitation; companion text column provides context. |
| **P4** | Product | 💡 | User Experience | Horizontal rule `---` inside a column severs slide chunks. | Document that `---` is reserved for slide breaks and disallowed in columns. |
| **P5** | Product | 💡 | User Experience | Diagram fence mixed with text inside a column silently bypasses near-miss warnings. | Emit diagnostic warning when a non-lone diagram fence is encountered in a column. |
| **P6** | Product | 🤔 | Edge Cases | Nested Pandoc fenced divs (`::: notes`) collide with column delimiters. | Clarify whether nested divs are prohibited in two-column bodies. |
| **P7** | Product | 💡 | Success Measurement | Lack of build performance budget and visual acceptance criteria. | Define <15ms preprocessing overhead and visual margin verification. |
| **E1** | Engineering | 🎯 | Architecture Soundness | Emitted Pandoc div lacks `.onlytextwidth`, bleeding columns past theme margins to `\paperwidth`. | Emit `:::::: {.columns .onlytextwidth align=top}` in `engine.py`. |
| **E2** | Engineering | 🎯 | Architecture Soundness | `match_diagram_slide` fence scanner only tracks `mermaid`/`d2`, failing on generic code blocks. | Implement a general code-fence scanner in `slides.py` for all languages. |
| **E3** | Engineering | 💡 | Failure Modes | Missing `# Title` leaves error message unable to identify offending slide. | Fall back to snippet or slide index in error message when title is absent. |
| **E4** | Engineering | 💡 | Failure Modes | Delimiter check might treat trailing blank lines as illegal content. | Explicitly ignore blank lines and whitespace when checking trailing content. |
| **E5** | Engineering | 💡 | Security | Asset path traversal in column images. | Explicitly note reuse of existing validated `\graphicspath` boundary. |
| **E6** | Engineering | 💡 | Performance | Image `height=0.78\textheight` plus multi-line caption risks vertical overflow on 16:9 frames. | Reduce max height in `column_body_tex` to `0.72\textheight` to accommodate captions. |
| **E7** | Engineering | 💡 | Testing Strategy | Incomplete negative test coverage for delimiter permutations. | Add explicit unit tests for 2/4 delimiters, trailing text, and inner code blocks. |
| **E8** | Engineering | 💡 | Operational Readiness | Delimiter regex strictly requires 0 indentation, tripping on standard 1–3 space indentation. | Allow up to 3 spaces of leading whitespace on `:::` lines. |
| **E9** | Engineering | 💡 | Architecture Soundness | Untyped `tuple` return type for `classify_region`. | Define a structured `NamedTuple` or dataclass for region classification. |

---

## Verdict

⚠️ **PROCEED WITH UPDATES**

The core design (Approach A: lower bespoke `:::` shorthand to native Pandoc column divs) is the right architectural choice for `md2pdf`. Updating the spec to address the four Must-Address items (**P1**, **P2**, **E1**, **E2**) and incorporating the key recommendations will establish a watertight blueprint for task splitting.

---

## Remediation Proposals

To prepare the specification for `Split Tasks`, the following updates to `../specs/two-column-slides.md` are recommended:

1. **Fix Pandoc Lowering Div Header (E1)**:
   In Section "engine.py — lowering", change:
   ```text
   :::::: {.columns align=top}
   ```
   to:
   ```text
   :::::: {.columns .onlytextwidth align=top}
   ```

2. **Fix Vertical Alignment in `column_body_tex` (P2)**:
   Specify that `column_body_tex` does not emit `\vfill` above or below the image. Center horizontally with `{\centering \includegraphics[width=\columnwidth,height=0.72\textheight,keepaspectratio]{...}\par ...}`.

3. **Prevent Silent Bypass on Pre-Delimiter Text (P1)**:
   In Section "slides.py — detection", specify that any non-blank line between `# Title` and the opening `:::` delimiter raises `SystemExit` (`"ERROR: slide '{title}': content preceding the opening ':::' delimiter is not supported"`).

4. **Implement General Code-Fence Scanner (E2)**:
   Specify a dedicated helper `_scan_code_fences` in `slides.py` that tracks backtick and tilde fences regardless of language, ensuring `:::` inside any code block is ignored during delimiter scanning.

5. **Accommodate Captions within Height Limits (E6)**:
   Cap column image height at `0.72\textheight` (rather than `0.78\textheight`) to ensure multi-line captions do not overflow 16:9 Beamer slides.

6. **Allow 1–3 Spaces Leading Indentation on Delimiters (E8)**:
   Match delimiter lines using `raw.lstrip()` or `r'^\s{0,3}:{3,}\s*$'`.

---

Would you like me to apply these changes to `docs/specs/two-column-slides.md`? (all / select / none)

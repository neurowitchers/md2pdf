---
generated-by: "Split Tasks"
source: docs/specs/two-column-slides.md
generated-at: 2026-10-17T23:05:00+03:00
inputs-ready: false
completed: false
status: not-started
---

# Task 01: Two-Column Detector + Region Classifier in `slides.py`

- [ ] **Completion**
- **Source spec**: `docs/specs/two-column-slides.md`
- **Depends on**: `None`
- **Blocks**: `task-02-lowering.md`, `task-03-tests.md`
- **Parallelism**: `Run before task-02 (engine lowering imports these symbols)`

## Objective

Add a strict, fence-aware `match_two_column_slide(chunk)` and a
`classify_region(region)` helper to `src/md2pdf/slides.py`, implementing the
`:::` two-column grammar (R1, R2, R5, R6) with fail-loud behaviour.

## Scope & Traceability
- **Requirements / acceptance criteria**: R1 (convention), R2 (two 50/50), R5
  (fail-loud), R6 (backwards-compat / opt-in).
- **Testing & risk strategy items**: detection critical path; fence-ambiguity
  risk; regression risk; critique P1 (pre-delimiter), E2 (general fence
  scanner), E3 (slide id in error), E4 (trailing blank-line tolerance), E8
  (indent tolerance).
- **Out of scope**: any LaTeX emission (task-02), tests (task-03), docs
  (task-04).

## Implementation Guidance
- **Files to create or modify**:
  - `src/md2pdf/slides.py`:
    - Add `_COLON_FENCE_RE = re.compile(r'^\s{0,3}:{3,}\s*$')` (critique E8:
      tolerate up to 3 leading spaces).
    - Add `_scan_code_fences`-style tracking: a **general** code-fence scanner
      that opens on any `_FENCE_RE` match (```` ``` ````/`~~~`, 3+, **any**
      language or none) and treats all lines until the matching close as
      content. Do **not** reuse `match_diagram_slide`'s diagram-only tracking
      (critique E2). The existing `_FENCE_RE` already captures the fence run and
      info; a line is a delimiter only when it matches `_COLON_FENCE_RE` **and**
      the scanner is not inside a code fence.
    - `match_two_column_slide(chunk) -> dict | None`:
      - Parse the single `# Title` via `_H1_RE` (first heading). A second
        heading on an otherwise-two-column slide → fail-loud.
      - Walk lines with fence-aware scanning, collecting `:::` delimiter
        positions (outside code fences).
      - **Opt-in trigger (critique task-level P1 — do not break R6).** Determine
        two-column *intent* conservatively so ordinary slides that merely
        contain a Pandoc fenced div (e.g. `::: {.note}`/`::: notes` closing with
        a bare `:::`) are **not** hijacked:
        - If **no** `:::` delimiter exists → return `None`.
        - If the **first non-blank line after the title is a `:::` delimiter**
          → the slide has opted in; enforce the full grammar below (fail-loud on
          violation).
        - Else (there are `:::` lines but the body does **not** open with one):
          the slide has **not** opted in → return `None` and let ordinary /
          picture / diagram processing handle it. This is the key fix: an
          isolated bare `:::` that closes a Pandoc callout/notes div on a normal
          slide must *not* trigger the pre-delimiter error. Pre-delimiter
          content is only an error on a slide that *did* open with `:::` (which
          cannot have pre-delimiter content by definition) — so the practical
          rule is simply: opt in **iff** the first non-blank post-title line is
          a delimiter; otherwise pass through untouched.
      - **Grammar enforcement (only once opted in), fail-loud (`SystemExit`):**
        - **Unterminated inner code fence takes precedence (critique task-level
          E2):** if the fence scanner reaches end-of-chunk still inside an open
          code fence, raise the *unterminated-fence* error (naming the fence's
          language/opening line) **before** any delimiter-count check, so the
          author is not misled by a wrong "expected 3 delimiters" message.
        - not exactly three delimiter lines (open / separator / close) → error
          naming the actual count;
        - either region (open→sep, sep→close) empty of non-blank lines → error;
        - non-blank content after the closing delimiter → error (trailing blank
          lines are ignored — critique E4);
        - a second `# Title` → error.
      - Error messages identify the slide: use the parsed title, else a
        near-`:::` snippet / first non-blank line (critique E3). Prefix `ERROR:`
        and mirror the existing diagram/field error style.
      - On success return `{"title": str, "left": str, "right": str}` with
        `left`/`right` as the verbatim inner lines (joined with `\n`,
        outer blank lines trimmed, inner content preserved).
    - `classify_region(region) -> tuple`: return `("image", alt, path)` if the
      region's sole non-blank content is one `_IMAGE_RE` match; `("diagram",
      lang, source)` if it is one lone `mermaid`/`d2` fence (reuse the diagram
      fence parse used by `match_diagram_slide`); otherwise `("markdown",
      region)`.
- **Established patterns to follow**: mirror `match_picture_slide` /
  `match_diagram_slide` structure, docstrings, and the `_FENCE_RE` fence-close
  logic already in `match_diagram_slide`.
- **Constraints and non-goals**: pure/stdlib only; no engine or LaTeX concerns;
  deterministic; no I/O.

## Verification Requirements
- **Automated tests**: covered by task-03, but this task must leave the two
  functions importable and self-consistent.
- **Manual / integration checks**: `python -c "from md2pdf import slides;
  print(slides.match_two_column_slide('# T\n\n:::\n![a](p.png)\n:::\n- x\n:::\n'))"`
  prints a dict with `title='T'`, `left` containing the image, `right`
  containing the bullet.
- **Risk coverage**: fence-ambiguity (E2), pre-delimiter silent bypass (P1),
  opt-in backwards-compat (R6).
- **Demo command**: `uv run python -c "from md2pdf import slides; import sys;
  r=slides.match_two_column_slide('# T\n\n:::\n![a](p.png)\n:::\n- x\n:::\n');
  print(r); sys.exit(0 if r and r['title']=='T' else 1)"`
- **Expected result**: prints the dict and exits 0.

## Handoff Notes
`match_two_column_slide` returns `None` for non-two-column slides and **raises**
for malformed `:::` slides — task-02 relies on this tri-state (dict / None /
raise). `classify_region`'s tuple shape is consumed by task-02's lowering
branch; keep the first element the discriminator string.

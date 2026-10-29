---
generated-by: "Plan Spec"
spec: docs/specs/two-column-slides.md
generated-at: 2026-10-17T22:54:43+03:00
status: resolved
round: 1
---

# Plan Questionnaire: Two-Column (Picture + Text) Slides

- **Seed(s)**: `docs/seed/two-column-slides.md`
- **Refining notes**: None (invoked via Autoflow; brainstorm answers Q1–Q5 are authoritative upstream decisions)

> Non-interactive (Autoflow) run. The seed's five locked decisions already
> resolve the major design axes (marker = `:::`, strictly two 50/50 columns,
> both sides fit, keep `# Title` + `align=top`, fail-loud). The questions below
> cover the *residual implementation-grammar* unknowns the seed left to the
> spec. Each is resolved by its **Recommended default** and marked
> `default-applied`.

## Round 1 — 2026-10-17

### Q1: Exact `:::` region grammar — how many fence lines delimit the two regions?
- **Why it matters**: Pins the parser and the fail-loud cases; must not collide with inner diagram fences.
- **Recommended default**: A two-column slide body is **exactly three `:::` lines**: an opening `:::`, a single `:::` separator between the two regions, and a closing `:::`. The two regions are the text between opener↔separator (left) and separator↔closer (right). Lines consisting solely of three-or-more colons (`^:{3,}\s*$`) are the only region delimiters. Inner ```` ``` ````/`~~~` fenced blocks are scanned fence-aware and never treated as delimiters. Any count other than exactly three `:::` lines → fail-loud.
- **Status**: `default-applied`
- **Answer**:
    <!-- USER_INPUT_START:Q1 -->
    [REPLACE THIS TEXT WITH YOUR ANSWER / PREFERENCE]
    <!-- USER_INPUT_END:Q1 -->

### Q2: What qualifies a slide as a two-column slide (vs. passthrough)?
- **Why it matters**: Defines the strict matcher boundary and backwards-compat guarantee.
- **Recommended default**: Exactly one leading `# Title` **and** a body that opens with a `:::` line (first non-blank, non-title line is a `:::` delimiter). Only then is the strict grammar enforced (fail-loud on violation). A slide whose body does not open with a `:::` delimiter is untouched (ordinary/picture/diagram paths unchanged). This keeps the feature strictly opt-in.
- **Status**: `default-applied`
- **Answer**:
    <!-- USER_INPUT_START:Q2 -->
    [REPLACE THIS TEXT WITH YOUR ANSWER / PREFERENCE]
    <!-- USER_INPUT_END:Q2 -->

### Q3: "Both sides scale to fit" — exact mechanism per region?
- **Why it matters**: Determines the emitted LaTeX for each region.
- **Recommended default**: A region whose **sole non-blank content** is one Markdown image **or** one lone `mermaid`/`d2` fence is rewritten to a `\columnwidth`-fit raw-LaTeX block (`\includegraphics[width=\columnwidth,height=0.78\textheight,keepaspectratio]`, centred), reusing a column-scoped variant of `picture_body_tex`; diagrams render via `render_diagram`. Any other region (bullets/prose/table/mixed) is emitted as Markdown inside the pandoc column and flows naturally at `0.5\textwidth` (pandoc/Beamer render it; natural text does not need forced scaling). Image alt text becomes a small caption, as whole-slide pictures do today.
- **Status**: `default-applied`
- **Answer**:
    <!-- USER_INPUT_START:Q3 -->
    [REPLACE THIS TEXT WITH YOUR ANSWER / PREFERENCE]
    <!-- USER_INPUT_END:Q3 -->

### Q4: Lowered pandoc output — exact div nesting?
- **Why it matters**: Wrong colon nesting makes pandoc mis-parse the columns.
- **Recommended default**: Emit `# Title` as Markdown (branded frame), then a native pandoc columns block using **distinct fence lengths**: outer `::::::` `{.columns align=top}` wrapping two inner `::::` `{.column width="50%"}` blocks, each closed, then the outer closed — exactly matching pandoc User's Guide §10.6. Each region's rewritten/raw content sits inside its `.column` div.
- **Status**: `default-applied`
- **Answer**:
    <!-- USER_INPUT_START:Q4 -->
    [REPLACE THIS TEXT WITH YOUR ANSWER / PREFERENCE]
    <!-- USER_INPUT_END:Q4 -->

### Q5: Fail-loud cases and message style?
- **Why it matters**: Q5 of the brainstorm locked fail-loud; the spec must enumerate what fails and how.
- **Recommended default**: Raise `SystemExit` with an actionable, slide-identifying message for: (a) not exactly three `:::` delimiter lines; (b) an empty region (no non-blank content between delimiters); (c) a region whose lone diagram fence fails to render (reuse `render_diagram`'s existing fail-loud); (d) an unterminated inner fence. Messages name the offending slide title (or its index if untitled) and the specific violation, mirroring the required-field/fontsize/diagram error style. No near-miss "warn-and-pass-through" for the `:::` shape.
- **Status**: `default-applied`
- **Answer**:
    <!-- USER_INPUT_START:Q5 -->
    [REPLACE THIS TEXT WITH YOUR ANSWER / PREFERENCE]
    <!-- USER_INPUT_END:Q5 -->

## Assumptions (applied if questions are left at their defaults)

- **A-Q1**: Grammar = exactly three `^:{3,}$` delimiter lines (open / separator / close); fence-aware inner-block scanning; any other count fails loud.
- **A-Q2**: Trigger = one `# Title` + body opening with a `:::` delimiter; otherwise untouched (opt-in, backwards compatible).
- **A-Q3**: Image/lone-diagram region → `\columnwidth` fit (reuse column-scoped `picture_body_tex` + `render_diagram`); any other region → Markdown passed to pandoc at 50% width; image alt → caption.
- **A-Q4**: Lower to pandoc `::::::  {.columns align=top}` + two `:::: {.column width="50%"}` per §10.6, distinct fence lengths.
- **A-Q5**: Fail-loud `SystemExit` on wrong delimiter count, empty region, diagram render failure, unterminated inner fence; actionable, slide-identifying messages.

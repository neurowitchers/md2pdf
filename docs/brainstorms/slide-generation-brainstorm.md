# Brainstorm — Fast, Branded Slide Generation from Agent Sessions

Status: exploratory brainstorm for study. Not a decision.
Date: 2026-09-18
Scope: How to generate HIVE-branded slides quickly from within agent sessions, and which pipeline to standardise on.

---

## 1. Problem statement

We have a branded slide template and we want agent sessions to turn prepared content (currently authored as Markdown, e.g. `fleet-opscon/report/fleet-operational-concept-intro-slides.md`) into on-brand decks **fast**, without leaving the terminal or hand-building each deck.

Two hard truths shape everything below:

1. **Output will always require human post-processing.** The tool produces a strong first draft (structure + branding + content in the right layouts); a human finalises aesthetics, visuals, and editorial cuts. We are optimising the *draft-to-90%* step, not the finishing step.
2. **The template as supplied is a Google-Slides export.** Every shape is named `Google Shape;NNN`. This has concrete technical consequences (below).

---

## 2. What the current template actually is (measured, not assumed)

Inspected `G:\Shared drives\HIVE\WP2\WP2 Common\Slides Template.pptx` with python-pptx:

- **16:9**, 13.33 × 7.5 in.
- **1 slide master, 21 named layouts** — a genuinely rich, well-structured layout set (not freeform). Key layouts:
  - `11_Title Slide` — CENTER_TITLE + SUBTITLE + PICTURE
  - `TITLE_ONLY` — TITLE + footer/number (ideal for freeform bodies)
  - `Thank you` — a single PICTURE placeholder; effectively static chrome
  - plus `OBJECT`, `2 columns`, `Text + picture left/right`, `Section + Full Frame Picture`, `Project Partners`, `Publications …`, etc.
- **3 example slides** already present (Title, an OBJECT body slide, Thank You) carrying the real background art.

**Critical technical finding:** reading existing text via python-pptx (`paragraph.text`) **hangs** on this file — a known quirk with Google-exported PPTX. Writing is a different code path and works fine. Any PPTX approach must therefore be **write-only** (add slides from layouts, set fresh text; never read back template text). We also hit and fixed a **duplicate slide-part bug**: removing slides from the id-list alone left orphaned `slideN.xml` parts that collided with newly added ones (`Duplicate name: ppt/slides/slide1.xml`). Fixed by dropping each slide's package relationship, not just the list entry.

**Implication for the "clean original" idea:** obtaining a genuine (non-Google) PowerPoint template would remove the read-hang, the `Google Shape;` cruft, and the duplicate-part fragility. It de-risks *every* PPTX-based path and is a prerequisite for a clean Beamer extraction too. Worth doing regardless of which pipeline we pick.

---

## 3. What already exists (built during this brainstorm)

- **`tools/md2pptx.py`** — a Markdown → branded-PPTX converter (uv-managed, `python-pptx`).
  - Parses: front-matter `title:`, `---` slide breaks, `#`/`##`/`###` headings, `-`/`*` bullets (2-space indent = sub-level), `1.` ordered lists, `>` blockquote callouts, GitHub pipe tables, inline `**bold**`/`*italic*`/`` `mono` ``.
  - Layout mapping: slide 1 → `11_Title Slide`; last → `Thank you`; all others → `TITLE_ONLY` with a freeform body text box.
  - Write-only (sidesteps the read-hang). Strips sample slides while keeping masters/layouts.
- **Generated artifact:** `fleet-opscon/report/fleet-operational-concept-intro.pptx` — 10 slides, verified: correct layouts, titles, bodies; the concept slide rendered a real PPTX table; Thank-You static. No package-corruption warnings after the fix.

So the python-pptx path is not hypothetical — it works end-to-end today.

---

## 4. The options, honestly compared

The decision is **not** "which tool is best in the abstract." It is: **where does the human post-processing happen?** That single question orders everything.

### 4.1 python-pptx (reuse the real template) — *current, working*

- **Author:** Markdown → script.
- **Output:** **editable `.pptx`**.
- **Brand match:** exact — chrome inherited from the real template layouts.
- **Human finishing:** WYSIWYG in PowerPoint/Google Slides (drag, resize, restyle).
- **Costs/warts:** Google-export quirks (read-hang, duplicate-part) — already handled; no autofit (dense slides overflow and need manual reflow).
- **Best when:** the deliverable is editable slides finalised in PowerPoint/Slides.

### 4.2 Beamer (LaTeX) — *"extract once, happy forever"*

The user's instinct deserves a fair steelman. Their three constraints materially strengthen this option:

1. **Not pixel-perfect** → removes the hardest, most thankless part of Beamer theming (exact spacing/kerning). We only need "clearly HIVE": colours, logo, background, title/section/thank-you frames. Very achievable.
2. **Willing to invest one-time extraction** → this is precisely the trade Beamer rewards: pay once for a `beamerthemeHIVE.sty`, then author content forever in plain text.
3. **Can source a clean, non-Google original** → removes the ugliest technical wart and de-risks a from-scratch theme.

- **Author:** Markdown/LaTeX → compile. *Cleaner than python-pptx for agent sessions* — pure text, no binary manipulation, no library quirks.
- **Output:** **PDF** (not editable as slides). ← the crux.
- **Brand match:** "clearly on-brand," defined once as a real, versioned artifact.
- **Human finishing:** edit LaTeX and recompile — **not** WYSIWYG dragging.
- **Costs/warts:** overfull-box tuning on dense slides (`\small`, `allowframebreaks`); tables and rich visuals are more effort than in PPTX; the deliverable can't be hand-nudged in PowerPoint.
- **Best when:** the deliverable is a PDF and finishing happens in a text editor.

### 4.3 Google Slides API — *situational*

- Source *is* Google Slides, so a duplicate-deck + `{{token}}`-replace flow would sidestep the read-hang and yield shareable links.
- Costs: OAuth/service-account friction; network dependency.
- **Best when:** the deck must live in Google Workspace and be shared as a link.

### 4.4 Marp — *recommend dropping*

Reconsidered and rejected. It's Markdown-in (nice) but its PPTX export is essentially image-per-slide (not editable), and CSS theming matches the brand *worse* than either reusing the real template (python-pptx) or a purpose-built Beamer theme. It has no niche advantage here; it only appeared because it's the "obvious" Markdown-to-slides tool.

---

## 5. Comparison table

| Dimension | python-pptx (current) | Beamer | Google Slides API | Marp |
|---|---|---|---|---|
| Author surface | MD → script | MD/LaTeX → compile | MD → API tokens | MD |
| Output | **editable .pptx** | **PDF** | editable Google deck | image-ish .pptx/PDF |
| Human finishing | drag/resize in PPT | edit LaTeX + recompile | drag/resize in Slides | limited |
| Brand fidelity | exact (reuses template) | "clearly on-brand" (built once) | close (conversion drift) | weakest |
| Tables / rich visuals | easy | more effort | easy | limited |
| Offline / deterministic | yes | yes | no (network+auth) | yes |
| Setup cost | **done** | one-time theme extraction | OAuth setup | low |
| Known warts | Google-export quirks (patched); no autofit | overfull boxes; PDF not draggable | auth/network | non-editable output |
| Agent ergonomics | good | **best** (pure text) | medium (auth) | good |

---

## 6. The reframing that matters

Both viable long-term pipelines (python-pptx and Beamer) are driven by the *same* deciding factor: **the medium in which decks are finalised.**

- If finishing = **PowerPoint/Google Slides WYSIWYG** → python-pptx wins; Beamer's PDF output is actively worse for that workflow.
- If finishing = **text edit + recompile**, and a **PDF deliverable** is acceptable → Beamer is the cleaner long-term artifact and worth the one-time extraction, *especially* with a clean non-Google template.

Given the earlier acknowledgement that human post-processing is inevitable, the nature of that post-processing is the whole ballgame. "Extract once, happy forever" is real — but "forever happy" only holds if forever's edits are text edits, not drag-and-drop.

---

## 7. Design principles (whichever pipeline wins)

Because output is a first draft for human finishing, optimise for **predictable, easily-editable output**, not cleverness:

- Keep each slide body as one tidy, grabbable unit.
- Under-style rather than over-style (don't fight the human's manual formatting).
- Fail loudly on ambiguous content instead of guessing.
- Keep the generator a thin, readable script that can be tweaked per deck.
- **Avoid** auto-fit heuristics, overflow detection, multi-column autoflow — they tend to make output *harder* to hand-correct.

Low-cost, high-value addition (applies to PPTX path): **emit the source Markdown into each slide's speaker notes**, so the editor always has source-of-truth content beside the slide while reshaping it.

---

## 8. Recommendation (provisional, pending the open questions)

1. **Regardless of pipeline:** obtain a **clean, non-Google-Slides original** of the template. It de-risks every option.
2. **Run a head-to-head experiment** rather than deciding on paper: build a minimal `beamerthemeHIVE` (colours, logo, background, title/section/thank-you frames) and compile the *same* intro deck through it. Then compare the existing `.pptx` and the Beamer PDF side by side and choose based on which one you'd rather hand-finish.
3. **Drop Marp.** Keep Google Slides API in reserve for Workspace-link deliverables only.
4. If finishing is WYSIWYG → standardise on `tools/md2pptx.py` and invest in speaker-notes + a documented layout-name mapping. If finishing is text-based and PDF is acceptable → standardise on Beamer and treat the `.sty` as the durable asset.

---

## 9. Open questions (for study)

**Deciding factor**
- Q1. Where must the **final deliverable** live — editable slides opened in PowerPoint/Google Slides, or a PDF? (This alone likely picks python-pptx vs Beamer.)

> PDF is OK

- Q2. What does a typical **human finishing pass** actually consist of — dragging/resizing/restyling (WYSIWYG), or editing text and recompiling? Be concrete.

> There will no human text editing. At most, repositioning.

**Template & assets**
- Q3. Can we obtain a **clean, non-Google original** template? If yes, from whom/where?

> `"G:\Shared drives\HIVE\Templates & Design\DES presentation template (1_1)-2.pptx`

- Q4. What are the brand primitives we'd need for a Beamer theme: background image(s), logo asset, exact hex colours, font names/licences? Are the fonts freely embeddable/available to LaTeX?

> Just background, logos, font colors.

**Usage & scale**
- Q5. How often will decks be generated — one-off, or many per week? (Frequency justifies an MCP wrapper and more polish.)

> Approximately ones per week

- Q6. Who generates them — only agents, or also humans writing Markdown by hand? Affects the authoring dialect and error-handling strictness.

> Humans will tweek on the markdown level

**Content richness**
- Q7. How important are **tables, diagrams, and images** in typical decks? (Rich visuals favour PPTX; text-heavy favours Beamer.) 

> Tables and images are important

- Q8. Do we need **speaker notes** carried through from source? (Cheap on the PPTX path; worth confirming as a requirement.)

> No

**Workflow & sharing**
- Q9. Is **Google Workspace sharing** (live links, comments) a real requirement for any deck class? If so, the Slides API path may be needed for that subset.

> Not necessary

- Q10. Should generation be wrapped as an **MCP tool** so any session calls `create_deck` directly, or is a CLI (`uv run …`) sufficient?

> `uv run` is suffecient 

**Maintenance**
- Q11. Who owns the theme/template asset over time, and where does it live in the repo (`tools/` for the generator; where for the `.sty`/template)?

> The template never changes

- Q12. What is the acceptable **dependency footprint** — a LaTeX toolchain (TeX Live/Tectonic) vs the existing python-pptx/uv setup?

> No problem with deps: anything that runs for Windows 11

---

## 10. Appendix — artifacts from this brainstorm

- `tools/md2pptx.py` — working Markdown → branded PPTX converter (uv + python-pptx).
- `fleet-opscon/report/fleet-operational-concept-intro.pptx` — generated 10-slide sample, verified.
- Measured template facts in §2 (layout inventory, read-hang, duplicate-part fix).

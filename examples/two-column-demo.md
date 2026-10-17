---
title: Two-Column Slide Demo
author: md2pdf
date: 2026-10-17
---

# Picture and text, side by side

:::
![A fit-to-column image with this alt text shown as a caption.](assets/placeholder.png)
:::
- The left column is a single image, scaled to fit its half.
- The right column is ordinary Markdown: bullets, prose, and
  `inline code` all render as usual.
- Both columns are exactly half the text width and top-aligned.
:::

---

# Diagram and notes, side by side

:::
```d2
ingest -> engine -> cache -> serve
```
:::
- The left column is a `d2` diagram, rendered and fit to the column.
- Diagrams in a column carry no caption; use this companion column for
  any figure label or explanation.
- The right column flows as normal Markdown.
:::

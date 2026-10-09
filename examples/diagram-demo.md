---
title: Diagram Slide Demo
author: md2pdf
date: 2026-10-09
---

# Regular Slide

- Regular slides keep bullets, tables, and prose as before.
- Diagram slides are detected by convention, with no new syntax.
- A slide counts as a diagram slide only when it is a single heading plus one `mermaid` or `d2` fence.

---

# Mermaid Diagram Slide

```mermaid
flowchart LR
    A[Slide chunk] --> B{Strict diagram slide?}
    B -- yes --> C[Render to image]
    B -- no --> D[Normal frame]
    C --> E[Fit-to-frame includegraphics]
```

---

# D2 Diagram Slide

```d2
Producer -> Broker: publish
Broker -> Consumer: deliver
Consumer -> Broker: ack
```

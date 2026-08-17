---
title: "Printable handouts"
linkTitle: "Printable handouts"
weight: 20
hidden: true
---

One linear page per deployment path, containing only that path's steps. Generated
from the workshop pages by `scripts/gen_handouts.py` — do not edit the handouts by hand.

| Handout | Path |
|---|---|
| [Handout — Docker Compose](handout-docker/) | `docker` |
| [Handout — Kubernetes / Helm](handout-k8s/) | `k8s` |

Each handout also renders a print-optimised variant at `index.print.html`, which is
what CI turns into a PDF artifact.

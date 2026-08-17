
# AI 101 - Agents, MCP & the Agentic Security Model

To view the workshop, please go here: [GitHub Pages Link](https://fortinetcloudcse.github.io/ai-101/index.html)

---

## Deployment paths and printable handouts

The workshop runs on two deployment paths — **Docker Compose** and
**Kubernetes / Helm**. Readers pick one on the Introduction page and every later
page follows that choice, because all path-specific instructions live inside a
`{{< pathtabs >}}` block.

Print output renders only the *active* tab, so a printed lab page would silently
omit the other path. Instead, one linear single-path handout is generated per
path under `content/09Reference/handouts/`.

**Those handouts are generated files — do not edit them.** Edit the workshop
pages, then regenerate:

```bash
python3 scripts/gen_handouts.py           # rewrite the handouts
python3 scripts/gen_handouts.py --check   # exit 1 if they are stale (what CI runs)
python3 scripts/lint_paths.py             # full path lint, includes the staleness check
```

Commit the regenerated files along with your content change. CI fails the PR if
they are stale, if a path-specific command appears outside a path block, or if a
path-like tab title is used in a plain `tabs` group.

`.github/workflows/handout-pdf.yml` renders each handout to PDF on push to
`main` and uploads them as build artifacts.

---

For more information on creating these workshops, visit [FortinetCloudCSE User Repo](https://fortinetcloudcse.github.io/UserRepo/)

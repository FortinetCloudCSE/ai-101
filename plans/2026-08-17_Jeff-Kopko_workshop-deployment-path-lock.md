# Plan: Deployment-Path Lock for Workshop Guides
Date: 2026-08-17
Owner: Jeff Kopko
Slug: workshop-deployment-path-lock
Plan File: plans/2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.md
Log File: plans/2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.log.md
Spec File: plans/2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.spec.md

## Goal

A participant chooses a deployment path once, and every later technical step in the
workshop shows only that path — persistently, visibly, and verifiably. Applies to
`ai-101` (two live paths) and, as prevention only, to `k8s-101-workshop`.

## Context / Links

- Spec: `plans/2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.spec.md`
- Theme: `hugo-theme-relearn` (inside `public.ecr.aws/k4n6m5h8/fortinet-hugo:latest`,
  mounted at `/home/CentralRepo`)
- Relearn tabs docs: `CentralRepo/themes/hugo-theme-relearn/docs/content/shortcodes/tabs.en.md`
- Related code paths (ai-101):
  - `content/01Intro/_index.md` (gate), `content/01Intro/{1_prereqs_docker,2_prereqs_k8s}/index.md`
  - `content/0{2,3,4,5}*/1_lab/index.md` (all four labs)
  - `content/09Reference/` (path-scoped troubleshooting)
  - `layouts/shortcodes/` (repo-local overrides), `scripts/repoConfig.json`
  - `.github/workflows/` (new lint + PDF workflows)
- Related code paths (k8s-101-workshop): `CLAUDE.md`, `.github/workflows/`, `scripts/`

## Mechanism — verified theme behaviour

Read from `CentralRepo/themes/hugo-theme-relearn` on 2026-08-17. These facts drive
every design decision below; all are confirmed in source, not inferred.

| Fact | Source | Consequence |
|---|---|---|
| `tabs` accepts `groupid`; groups sharing a `groupid` synchronize their selected tab **site-wide** | `layouts/shortcodes/tabs.html:3`, `docs/.../tabs.en.md` parameter table | This is the "lock the path" primitive — no custom JS needed |
| Selection stored as `localStorage["<absBaseUri>/tab-selections"] = {groupid: itemid}` and replayed by `restoreTabSelections()` on every page init | `assets/js/theme.js:144-170,1835` | Persistence is free; keyed per site, so an `ai-101` choice is **not** shared with `k8s-101-workshop` |
| Storage is written **only** on a real click (`isButtonEvent`) | `assets/js/theme.js:118,144` | The path gate must be clickable tabs. A page of links cannot record a choice |
| `itemid = anchorize(plainify(RenderString(title))) + anchorize(icon)` | `layouts/partials/shortcodes/tabs.html:42` | `"Kubernetes / Helm"` → `kubernetes--helm`, `"Kubernetes/Helm"` → `kuberneteshelm`. Adding an `icon` to one tab changes its id |
| If the stored `itemid` is absent from a group, the group falls back to its **first** tab, silently | `switchTab` filter, `layouts/partials/shortcodes/tabs.html:68` (`$idx 0` gets `active`) | A single typo or stray icon reintroduces the original bug with no warning. Must be prevented structurally **and** linted |
| In `print` output only the `.active` tab renders | `assets/css/format-print.css:163-176` | A printed page silently omits the other path — hence generated per-path handouts |
| `print` output format is declared by the theme (`baseName = index.print`, `noUgly = true`) but `hugo.jinja` enables it for `home` only | `themes/hugo-theme-relearn/hugo.toml:10-16`; `CentralRepo/scripts/templates/hugo.jinja` `[outputs]` | Handout pages opt in per page via front matter `outputs: ["html","print"]` — **verify in Phase 0** |
| `include` shortcode resolves a page/resource, else `readFile` + `safeHTML` (raw, unrendered) | `layouts/partials/shortcodes/include.html:8-20` | Rejected as the handout mechanism (see Decisions), but noted |

## Constraints / Assumptions

- **Layout code stays repo-local for now.** `ai-101/layouts/` overrides the theme.
  A CentralRepo PR is a follow-up, after the pattern is proven.
- **Do not modify `static.yml`.** It is in the template tool's `FILES_TO_COPY` and this
  repo's copy is already ahead of the 12-repo consensus version (see `CLAUDE.md`). New
  CI work goes in **new** workflow files, which the upgrade tool does not touch.
- **Do not put anything under `docs/`.** Machine-owned and deleted by
  `batch_repo_update.py`.
- `errorLevel` is `warning`, so Hugo warnings never fail the build. Verification means
  reading the build log for `WARN`, not trusting exit 0.
- `uglyURLs = true` (hardcoded in the image) — relative image/link paths resolve one
  level higher than the source layout suggests.
- Two paths only in `ai-101`: `Docker Compose` and `Kubernetes / Helm`.
- `k8s-101-workshop` gets convention + CI only; no content restructuring.
- No test suite in either repo. Verification = local CI-equivalent Hugo build + manual
  browser check of persistence.

## Design

### 1. Canonical path vocabulary (locked strings)

```
groupid    : deploy-path
tab titles : "Docker Compose"   → itemid docker-compose
             "Kubernetes / Helm" → itemid kubernetes--helm
icons      : none on path tabs (an icon mutates the itemid)
tab order  : Docker Compose first — it is the fallback for any visitor with no
             stored choice, and the majority path
```

### 2. `pathtabs` shortcode (repo-local) — makes mismatch structurally impossible

`layouts/shortcodes/pathtabs.html` wraps `partial "shortcodes/tabs.html"` with the
`groupid` and both tab titles hardcoded, taking the two bodies as named parameters.
Authors cannot mistype a title or add an icon, because they never write them.

```
{{< pathtabs >}}
{{% pathtab path="docker" %}}
...markdown for the Docker Compose path...
{{% /pathtab %}}
{{% pathtab path="k8s" %}}
...markdown for the Kubernetes path...
{{% /pathtab %}}
{{< /pathtabs >}}
```

This is also the unit the handout generator and the linter parse, and the artifact to
upstream to CentralRepo later.

### 3. Path gate — `content/01Intro/_index.md`

Replace the "Choose your path" bullet list with a `pathtabs` block. Each tab holds a
short requirements summary, a time estimate, and a link onward to that path's existing
setup page. Clicking records the path site-wide. `1_prereqs_docker` and `2_prereqs_k8s`
keep their URLs and content unchanged, so instructor deep links still work.

Residual gap, accepted: a participant who bookmarks a lab page and enters mid-workshop
never passes the gate, so their path defaults to `Docker Compose`. Mitigated by item 4 —
the badge at the top of every lab page is itself a clickable path selector.

### 4. Path badge + preflight, top of every lab page

One `pathtabs` block per lab page, immediately after the H1, containing per path:

- `Path: <name>` — the visible indicator
- the preflight command for that path plus its expected output
  (`docker compose ps` vs `kubectl get pods -l app=ai101`, and for Kubernetes the
  `jobs` / port-forward check the labs already depend on)
- one line: "These steps are for `<name>`. On the other path? Select the other tab."
  — works with JavaScript disabled and in print

### 5. Convert every unbranched path-specific instruction

| Location | Current problem | Change |
|---|---|---|
| `content/02Inference/1_lab/index.md:11-17` | Lab 1 has no tabs; Kubernetes branch is a `notice`, scripts assume `localhost:11434` | Replace with `pathtabs`; Docker tab states no port-forward needed |
| `content/03Agents/1_lab/index.md:59` | "(Docker) or ... (Kubernetes)" inline URLs | `pathtabs` with one URL per tab |
| `content/04MCP/1_lab/index.md:52` | same | same |
| `content/05Security/1_lab/index.md:42` | same | same |
| `content/05Security/1_lab/index.md:142-145` | Kubernetes-only recovery step in prose | move into `pathtabs` |
| 6 existing tab pairs (`03Agents:15`, `04MCP:15,118`, `05Security:15,124,201`) | no `groupid` | convert to `pathtabs` |

Leave all non-path tab groups alone (15 "Expected Output" style groups in `ai-101`) —
they are a different axis and must **not** share `deploy-path`.

### 6. Path-scoped troubleshooting — `content/09Reference/`

`cloud-shell-web-preview` is Kubernetes-only. Add a front-matter marker plus an
opening notice, and turn `09Reference/_index.md` into a `pathtabs` index listing only
the reference pages relevant to each path.

### 7. Handout generator — `scripts/gen_handouts.py`

Lab pages stay the single source. The generator walks `content/` in `weight` order,
and for each path emits one linear page:

```
content/09Reference/handouts/handout-docker/index.md
content/09Reference/handouts/handout-k8s/index.md
  front matter: outputs: ["html","print"], generated-file banner, hidden from menu
  body: each lab's content with every pathtabs block flattened to that path's body
        and the other path's body dropped entirely; non-path tab groups preserved
```

Modes: default writes the files; `--check` exits non-zero if regenerating would change
anything (CI freshness gate). Generated files are committed so the site builds without
running Python.

### 8. PDF generation — `.github/workflows/handout-pdf.yml` (new file)

Runs on push to `main` and on manual dispatch. Builds the site with the same
`fortinet-hugo` image invocation the CI build uses, then renders each handout's
`index.print.html` to PDF with headless Chrome, uploads both PDFs as workflow
artifacts, and links them from `scripts/repoConfig.json` shortcuts. New file on
purpose: `static.yml` would be clobbered by the next template upgrade.

### 9. Lint workflow — `.github/workflows/path-lint.yml` + `scripts/lint_paths.py`

Runs on PRs. Fails on any of:

1. a `tabs` group whose titles include a path name but which is not a `pathtabs` block
2. a `pathtabs` block missing either path
3. any literal `groupid="deploy-path"` written by hand (must go through `pathtabs`)
4. a path-specific token outside a path-scoped block: `docker compose`, `docker exec`,
   `kubectl`, `helm `, `localhost:8080`, `localhost:8100`, `localhost:11434`,
   `port-forward`, `NodePort` — with an explicit, commented allowlist for conceptual
   prose (e.g. section overviews that mention `kubectl` without instructing)
5. `gen_handouts.py --check` reporting stale handouts

The path vocabulary lives in a small config block at the top of the script so
`k8s-101-workshop` can use the identical script with zero path groups defined.

### 10. Documentation

- `ai-101/CLAUDE.md`: new "Deployment paths" section — the vocabulary, the `pathtabs`
  requirement, the print limitation, the generator, the linter.
- `k8s-101-workshop/CLAUDE.md`: same convention documented preventively, stating that
  the repo currently has zero path branches and that any second path must use it.
- `README.md` in both repos: how to regenerate handouts.

## Implementation Method

**Phase 0 direct in-conversation** (single POC page, ~4 files, local Hugo build only),
then **tmux sequential in a git worktree** for Phases 1-5.

Reason: the phases interlock — the linter parses the shortcode from Phase 0, the
handout generator parses the same blocks, and the k8s-101 slice reuses the Phase 3
script. Fan-out would have every branch waiting on the same two files. The one
genuinely independent unit is the `k8s-101-workshop` slice (Phase 5), which can run in
a parallel tmux session once `scripts/lint_paths.py` is final.

Worktree: `~/pythonProjects/worktrees/ai-101-workshop-deployment-path-lock`, branched
from `jkopkoEdits`.

## Plan

### Phase 0 — Proof of concept (direct, before the rest is approved to proceed)
- [ ] Write `layouts/shortcodes/pathtabs.html` + `layouts/shortcodes/pathtab.html`
- [ ] Convert `content/01Intro/_index.md` to the `pathtabs` gate
- [ ] Convert `content/03Agents/1_lab/index.md` fully (badge + preflight + the tab pair
      at :15 + the inline URLs at :59)
- [ ] Verify: CI-equivalent build clean of new `WARN`s; `fortihugorunner launch-server`;
      click Kubernetes on the gate, confirm Lab 3 renders Kubernetes on load and after
      a hard reload; confirm with JavaScript disabled the page is still followable
- [ ] Verify `outputs: ["html","print"]` in page front matter actually produces
      `index.print.html` with this image (blocks Phase 3 if it does not)
- [ ] Jeff previews and signs off on the UX before Phase 1

### Phase 1 — Convert remaining ai-101 content
- [ ] `content/02Inference/1_lab/index.md` (no tabs today)
- [ ] `content/04MCP/1_lab/index.md` (2 tab pairs + inline URLs)
- [ ] `content/05Security/1_lab/index.md` (3 tab pairs + inline URLs + prose recovery step)
- [ ] Badge + preflight block on all four lab pages
- [ ] Sweep for any remaining unbranched path token; fix
- [ ] Fix the two pre-existing broken images while in these files
      (`01Intro/2_prereqs_k8s/index.md:207` doubled extension,
      `04MCP/1_lab/index.md:199` out-of-bundle path) — both currently ship broken
- [ ] Verify: full build, zero `is not a resource` WARNs, all four labs path-locked

### Phase 2 — Path-scoped troubleshooting
- [ ] Mark `09Reference/cloud-shell-web-preview` as Kubernetes-only
- [ ] Rebuild `09Reference/_index.md` as a path-scoped index

### Phase 3 — Handouts + PDF
- [ ] `scripts/gen_handouts.py` with `--check`
- [ ] Generate and commit both handout pages
- [ ] `.github/workflows/handout-pdf.yml`
- [ ] Link handout PDFs from `scripts/repoConfig.json` shortcuts
- [ ] Verify: each handout contains only its own path's commands; print view renders;
      PDF artifact downloads and is readable

### Phase 4 — Enforcement + docs (ai-101)
- [ ] `scripts/lint_paths.py`
- [ ] `.github/workflows/path-lint.yml`
- [ ] Prove the linter fails on a deliberately broken branch, then passes on `HEAD`
- [ ] `CLAUDE.md` + `README.md` updates
- [ ] `RELEASE_NOTES.md` entry if the repo adopts one (it currently has none)

### Phase 5 — k8s-101-workshop prevention
- [ ] Copy `scripts/lint_paths.py` with an empty path vocabulary
- [ ] Add `.github/workflows/path-lint.yml`
- [ ] Document the convention in `k8s-101-workshop/CLAUDE.md`
- [ ] Verify: workflow passes on current `main` content

### Close-out
- [ ] PR per repo; merge after CI green
- [ ] Kill tmux session, remove worktree, delete branch
- [ ] Update memory files and mark this plan's boxes

## Plan Changes
- (none)

## Decisions & Commentary

- **Relearn `groupid` over custom JS** — the synchronize-site-wide + persist behaviour
  already exists in the theme and is exactly the requested "lock the tabs for the whole
  path". Custom JS would duplicate it and add a no-JS and a print failure mode.
- **A `pathtabs` shortcode instead of hand-written `groupid="deploy-path"`** — the theme
  fails *silently* (falls back to tab 1) when a title or icon differs by one character.
  Hand-writing the same block 12+ times across two repos guarantees that eventually
  happens. Wrapping it means authors cannot express the broken form. This also gives the
  linter and the handout generator a single unambiguous token to parse.
- **Gate as tabs, setup pages kept separate** — persistence only records on a click, so
  the gate must be tabs; but the two setup guides are long and genuinely divergent, and
  instructors deep-link them. Short selector tabs that link onward gets both.
- **Badge implemented as a `pathtabs` block rather than a JS status banner** — merges the
  path indicator, the preflight check, and the "wrong path?" pointer into one construct
  that needs no JavaScript, survives print, and doubles as an in-place path switcher for
  anyone who entered mid-workshop.
- **Docker Compose stays the first tab** — first tab is what an unknown visitor sees, so
  the default must be the majority path.
- **Handouts generated from lab pages, not authored** — the tab structure is
  machine-readable, so "flatten to one path" is a deterministic transform. Rejected
  headless-bundle `include` snippets (`~15` new files, every lab page becomes indirection)
  and hand-written handouts (guaranteed drift, which is the bug being fixed).
- **New workflow files, never `static.yml`** — this repo's `static.yml` is ahead of the
  template and in `FILES_TO_COPY`; anything added there dies at the next upgrade.
- **k8s-101-workshop gets prevention only** — it has no live branch today, so there is
  nothing to convert; the value is that a returning AKS path cannot be built wrong.

## Files Changed
- (none yet)

## Session Summary
- (write at end)

## Follow-ups
- [ ] Upstream `pathtabs` to CentralRepo so the other ~5 workshop repos inherit it
      (`k8s-101-workshop`, `faig-training-workshop`, `fortiweb-api-mcp-protection`,
      `AWS-FGT-301`, `Public-Cloud-104-CNAPP`)
- [ ] Push this repo's improved `static.yml` upstream to CentralRepo so a template
      upgrade stops regressing it
- [ ] `k8s-101-workshop`: remove dead AKS references (`01_introduction/_index.md:41`,
      commented block in `02_quickstart_overview_faq/_index.md`) — deferred by decision
- [ ] `k8s-101-workshop`: fix beginner/experienced routing text, whose section numbers
      do not match the actual nav — deferred by decision
- [ ] `k8s-101-workshop`: preflight verify blocks on hands-on pages — deferred by decision
- [ ] Decide whether `k8s-101-workshop/content/k8s-101.pdf` is retired in favour of
      generated handouts
- [ ] Reconsider AKS as an `ai-101` path once someone can validate it on a real cluster

## Risks / Open Questions

- **Silent tab fallback** — highest risk, since it is invisible. Mitigated twice:
  `pathtabs` removes the ability to write the broken form, and the linter fails PRs.
- **Handout freshness** — a generated artifact in git drifts unless checked. Mitigated by
  `--check` in the PR workflow.
- **`outputs: ["html","print"]` per page may not work** with the pinned Hugo/relearn in
  the image, since `hugo.jinja` enables `print` for `home` only. Verified in Phase 0; if
  it fails, fall back to a repo-local `layouts/_default/single.print.html` or to a
  print-friendly stylesheet on the handout pages.
- **Generated handout pages appear in the sidebar** unless suppressed. Need to confirm the
  relearn front-matter flag for menu exclusion during Phase 3. *Open question: sidebar or
  reference-section-only?*
- **PDF step needs headless Chrome in CI** — adds a dependency and ~1 min to the `main`
  workflow. Isolated in its own workflow so a failure cannot block the Pages deploy.
- **Path choice does not carry from `k8s-101-workshop` to `ai-101`** — localStorage is
  keyed by `baseURL`. The `ai-101` gate must therefore always be passed; acceptable, but
  worth an explicit line in the `ai-101` Kubernetes tab for continuing participants.
- **Concurrent sessions** — Jeff runs parallel Claude sessions against these repos; all
  work happens in a dedicated worktree, and files outside this plan's scope are left
  alone.

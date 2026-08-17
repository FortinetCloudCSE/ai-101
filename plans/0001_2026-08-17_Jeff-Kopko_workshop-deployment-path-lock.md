# Plan: Deployment-Path Lock for Workshop Guides
Date: 2026-08-17
Owner: Jeff Kopko
Slug: workshop-deployment-path-lock
Status: Complete
Supersedes: none
Superseded-By: none
Plan File: plans/0001_2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.md
Log File: plans/0001_2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.log.md
Spec File: plans/0001_2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.spec.md

## Goal

A participant chooses a deployment path once, and every later technical step in the
workshop shows only that path — persistently, visibly, and verifiably. Applies to
`ai-101` (two live paths) and, as prevention only, to `k8s-101-workshop`.

## Context / Links

- Spec: `plans/0001_2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.spec.md`
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
- [x] Write `layouts/shortcodes/pathtabs.html` + `layouts/shortcodes/pathtab.html`
- [x] Convert `content/01Intro/_index.md` to the `pathtabs` gate
- [x] Convert `content/03Agents/1_lab/index.md` fully (badge + preflight + the tab pair
      at :15 + the inline URLs at :59)
- [x] Verify: CI-equivalent build — 36 pages (unchanged), zero new `WARN`s, only the two
      pre-existing broken-image warnings
- [x] Verify rendered output: Lab 2 emits 3 `deploy-path` groups, the gate emits 1, each
      with itemids `docker-compose` / `kubernetes--helm`; the 4 non-path groups on Lab 2
      keep their random ids and are untouched
- [x] Negative test: a `pathtabs` block missing one path fails the build with exit 1 and
      names the file — protection does not depend on the linter
- [x] Verify `outputs: ["html","print"]` in page front matter produces
      `zztmptest/index.print.html` with this image — **Phase 3 unblocked**
- [x] Jeff previews in a browser and signs off on the UX before Phase 1 — **approved
      2026-08-17**. He clicked Kubernetes / Helm on the gate, followed the tab's link to
      `01intro/2_prereqs_k8s.html`, and confirmed all three `deploy-path` groups on
      `03agents/1_lab.html` were synced to Kubernetes / Helm. Ticked after the branch
      merged, to avoid a conflict with the worktree session editing this file.

### Phase 1 — Convert remaining ai-101 content
- [x] `content/02Inference/1_lab/index.md` (no tabs today)
- [x] `content/04MCP/1_lab/index.md` (2 tab pairs + inline URLs)
- [x] `content/05Security/1_lab/index.md` (3 tab pairs + inline URLs + prose recovery step)
- [x] Badge + preflight block on all four lab pages
- [x] Sweep for any remaining unbranched path token; fix
- [x] Fix the two pre-existing broken images while in these files
      (`01Intro/2_prereqs_k8s/index.md:207` doubled extension,
      `04MCP/1_lab/index.md:199` out-of-bundle path) — both currently ship broken
- [x] Verify: full build, zero `is not a resource` WARNs, all four labs path-locked

### Phase 2 — Path-scoped troubleshooting
- [x] Mark `09Reference/cloud-shell-web-preview` as Kubernetes-only
- [x] Rebuild `09Reference/_index.md` as a path-scoped index

### Phase 3 — Handouts + PDF
- [x] `scripts/gen_handouts.py` with `--check`
- [x] Generate and commit both handout pages
- [x] `.github/workflows/handout-pdf.yml`
- [ ] **Not done — not achievable without a permanent WARN.** Link handout PDFs from
      `scripts/repoConfig.json` shortcuts. `hugo.jinja` emits only `url =` for shortcuts,
      never `pageRef`, and relearn's `menuPermalink.gotmpl` runs the value through
      `relLangURL`, which strips the baseURL off a fully-qualified self-URL — so the
      result is classified "local" and warns on every page (verified: 2 WARNs, reverted).
      Handouts are instead linked from each path's table in `09Reference/_index.md`.
      Follow-up: add `pageRef` support to `hugo.jinja` upstream.
- [x] Verify: each handout contains only its own path's commands; print view renders;
      PDF artifact downloads and is readable

### Phase 4 — Enforcement + docs (ai-101)
- [x] `scripts/lint_paths.py`
- [x] `.github/workflows/path-lint.yml`
- [x] Prove the linter fails on a deliberately broken branch, then passes on `HEAD`
- [x] `CLAUDE.md` + `README.md` updates
- [ ] N/A — `RELEASE_NOTES.md` entry if the repo adopts one (it still has none)

### Phase 5 — k8s-101-workshop prevention

**Out of scope for this session** — handled by a separate session, by instruction.

- [ ] Copy `scripts/lint_paths.py` with an empty path vocabulary
- [ ] Add `.github/workflows/path-lint.yml`
- [ ] Document the convention in `k8s-101-workshop/CLAUDE.md`
- [ ] Verify: workflow passes on current `main` content

### Close-out
- [ ] PR per repo; merge after CI green
- [ ] Kill tmux session, remove worktree, delete branch
- [ ] Update memory files and mark this plan's boxes

## Plan Changes

- 2026-08-17, Jeff: handout pages live in the **reference section only**, not the sidebar.
- 2026-08-17, Jeff: `k8s-101-workshop/content/k8s-101.pdf` **stays as-is** for now;
  handout PDFs do not replace it.
- 2026-08-17, Jeff: confirmed **visible-and-correctable** over a hard path lock — a reader
  can always switch paths; the design makes the wrong path obvious, not impossible.
- 2026-08-17, Jeff: `k8s-101-workshop` scope stays minimal (Phase 5 as written).
- 2026-08-17, added during Phase 0: `pathtabs` calls `errorf`, so a missing or duplicated
  path **fails the Hugo build**, not just the linter. Verified: exit 1 with the offending
  filename. The linter remains for the checks Hugo cannot make (path tokens outside path
  blocks, handout freshness).
- 2026-08-17, added during Phase 0: **fix `cd "~/ai-101/..."`** everywhere. Bash does not
  expand `~` inside double quotes, so all 14 occurrences fail with "No such file or
  directory" when copy-pasted, on both paths. Fixed in `03Agents/1_lab` during Phase 0;
  the remaining 12 (`04MCP/1_lab` ×4, `05Security/1_lab` ×6, `01Intro/2_prereqs_k8s` ×2)
  are Phase 1, plus a lint rule for the pattern.

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

Phase 0:
- `layouts/shortcodes/pathtabs.html` (new) — path-tab wrapper, hardcoded `groupid`, both
  titles, no icons; `errorf` on a missing or duplicated path
- `layouts/shortcodes/pathtab.html` (new) — collects one path body into the parent's
  Scratch, mirroring the theme's own `tab.html`; `errorf` on an unknown path key or when
  used outside `pathtabs`
- `content/01Intro/_index.md` — "Choose your path" list replaced by the `pathtabs` gate
- `content/03Agents/1_lab/index.md` — badge + preflight block added; Deploy tabs and the
  UI-URL parenthetical converted to `pathtabs`; two `cd "~/…"` commands fixed

Phase 1 — `8adc164`:
- `content/02Inference/1_lab/index.md` — Kubernetes-only `notice` replaced by a badge +
  preflight `pathtabs` block; Step 1's verify `curl` wrapped with per-path recovery advice
- `content/04MCP/1_lab/index.md` — badge + preflight; Deploy tabs, the inline UI-URL
  parenthetical, and Step 3's three-way group converted to `pathtabs`; 4 `cd "~` fixed;
  `../searchweb.png` → bundle resource; unterminated `echo "UI: …` quote fixed
- `content/04MCP/searchweb.png` → `content/04MCP/1_lab/searchweb.png` (`git mv`) so it is
  a real page resource of the bundle that references it
- `content/05Security/1_lab/index.md` — badge + preflight; 3 tab pairs + the inline URL
  converted; the Kubernetes-only port-forward recovery step moved out of unbranched prose
  into the path block, with the reason it dies (`helm upgrade` replaces the agent pod);
  6 `cd "~` fixed; unterminated `echo` quote fixed
- `content/01Intro/1_prereqs_docker/index.md`, `content/01Intro/2_prereqs_k8s/index.md` —
  `deploymentPath` front matter + an opening notice linking the other path;
  `browser.png.png` → `browser.png`; 2 `cd "~` fixed
- `content/03Agents/_index.md` — path tokens removed from conceptual prose rather than
  allowlisted ("Lab 2 gives the URL for your deployment path")

Phase 2 — `80baf28`:
- `content/09Reference/cloud-shell-web-preview/index.md` — `deploymentPath: k8s` + notice
- `content/09Reference/_index.md` — per-path reference index; Day-2 swap converted to
  `pathtabs`; new `### Path-specific issues` block absorbing the two path-specific
  troubleshooting entries; endpoint table de-pathed to `http://<ollama-host>:11434/v1`

Phase 3 — `ece618c`:
- `scripts/gen_handouts.py` (new, 508 lines) — walks `content/` in weight order, flattens
  each `pathtabs` block to one path, copies bundle images into the handout bundle under a
  `<dir-slug>-<name>.png` prefix, rewrites page links to `/`-rooted content refs, and owns
  `OUT_DIR` outright (orphans deleted). `--check` is the CI freshness gate.
- `content/09Reference/handouts/` (generated) — `_index.md` + two bundles (1143 and 1446
  line pages, 8 copied PNGs), `hidden: true`, `outputs: ["html", "print"]`
- `content/09Reference/_index.md` — a handout row per path's reference table
- `.github/workflows/handout-pdf.yml` (new) — serves the built site under the `/ai-101`
  prefix (all assets are baseURL-rooted) and renders each `index.print.html` with
  headless Chrome; uploads the PDFs and the print HTML as artifacts

Phase 4 — `1242cbf`:
- `scripts/lint_paths.py` (new, 356 lines) — five checks, vocabulary in a CONFIG block at
  the top, allowlist entries each carrying a written reason
- `.github/workflows/path-lint.yml` (new) — runs the linter on PRs
- `CLAUDE.md` — new "Deployment paths" section; the broken-images gotcha rewritten now
  that both are fixed (WARN baseline is 0); new gotcha on `menu.shortcuts` and internal
  links; file map updated
- `README.md` — how to regenerate handouts and what CI enforces

The path vocabulary can be overridden per repo via `site.Params.deploymentPaths`
(`scripts/repoConfig.json`), so the same two shortcodes work unchanged in a repo with
different path names — relevant to the CentralRepo follow-up.

## Session Summary

Phases 1-4 implemented in the worktree on branch `workshop-deployment-path-lock`, four
commits (`8adc164`, `80baf28`, `ece618c`, `1242cbf`), nothing pushed. Phase 5
(`k8s-101-workshop`) was out of scope by instruction. Phase 0's remaining box — Jeff's
browser sign-off on the UX — is still open and is the only thing standing between this
branch and a PR.

All four labs, both prereq pages, the gate and the reference section are now path-locked:
every path-specific instruction is inside a `pathtabs` block or on a page carrying a
`deploymentPath` marker. Verified per phase with the CI-equivalent build: **42 pages,
0 WARN, 0 ERROR** at the end (36 pages / 0 WARN after Phases 1-2; the jump to 42 is the
three generated pages, two of which render an extra `print` output).

Three things turned up that were not in the plan:

1. **The build was never clean to begin with.** Beyond the two known broken images there
   were two unterminated `echo "UI: …` commands (a copy-paste of either would hang the
   shell waiting for a closing quote) and 13 `cd "~` occurrences, not the 12 the plan
   counted. All fixed; the WARN baseline is now 0, which is what makes "read the log for
   WARN" a usable verification rule going forward.
2. **A `repoConfig.json` shortcut cannot link an internal page without warning.**
   `hugo.jinja` emits only `url =` for shortcuts, and relearn runs it through
   `relLangURL`, which strips the baseURL off a fully-qualified self-URL — so even the
   published absolute URL comes back "local" and warns on every page. Adding the two
   handout shortcuts cost 2 permanent WARNs, so they were reverted and the handouts are
   linked from the reference tables instead. Banking known-benign WARNs would have
   defeated the verification rule above.
3. **Handout PDF rendering needs `--disable-dev-shm-usage`.** Without it the longer
   (Kubernetes) handout dies with `Printing failed.` on the default 64 MB `/dev/shm`
   while the shorter one succeeds — a failure mode that only shows up on the bigger input.

Verification actually performed, not assumed: handouts absent from every other page's
rendered HTML (`hidden: true` confirmed by grep over the built site, not by reading the
theme docs); both `index.print.html` render (120 KB / 151 KB); both PDFs render locally
via containerised Chrome (22 pages / 991 KB, 26 pages / 1.49 MB); each handout contains
only its own path's commands (the three surviving cross-path hits are all prose that
explicitly tells the reader the other path does not apply); and each of the linter's five
checks was proven by breaking a page, observing exit 1 with the right check name, and
restoring — `HEAD` lints clean at 14 pages.

### Close-out session (same day, after the merge into `jkopkoEdits`)

Everything the two implementation sessions reported was re-run independently rather than
taken on trust — builds, greps, the linter's negative proofs, HTTP fetches of every changed
link, and a visual read of the PDF pages. That posture is what earned its keep twice:

- It **found the print defect** (non-path tab groups unflattened, 12/17 dropped panels) that
  neither implementation session caught and that a green build, a clean linter, and a
  successfully-rendering PDF all failed to reveal. See the ticked follow-up below.
- It **disproved one of my own earlier risk flags.** I had committed to checking that
  `/`-rooted internal links like `/01Intro/2_prereqs_k8s` would break; they do not —
  relearn's render-link hook rewrites them to `/ai-101/01intro/2_prereqs_k8s.html`. Reported
  as a non-issue rather than left standing as a scary-sounding caveat.
- It also caught a wrong number I had given the Phase 5 session (31 `tabs` groups in
  `k8s-101-workshop`; the real count is 33 live plus 18 in disabled `.md.txt` files).

Additional work done in this session, beyond verification:

1. **`flatten_plain_tabs()` in `gen_handouts.py`** (`ace4d0c`) — the print fix.
2. **`k8s-101-workshop` build WARNs 3 → 1** — the two `is not a page or a resource` link
   WARNs fixed with `/`-rooted content refs. This **contradicted that repo's own
   `CLAUDE.md`**, which said the WARNs were cosmetic and not to fix them; that note was
   right that a third `../` breaks the link but missed the `/`-rooted form, so it was
   rewritten rather than left contradicting the code.
3. **Kubernetes prereq page headings renumbered** (`4a67bb9`) — eight `## - Title` headings
   brought onto the Docker page's `## N. Title` spine, so the two halves of the same step
   stop looking like different documents. Each substitution asserted unique before applying;
   no anchor links referenced them; the `# Lab 1 —` lines are bash comments inside a fenced
   block and were deliberately left alone.
4. **Both repos merged to `main`** — `ai-101` PR #16, `k8s-101-workshop` PR #104. All checks
   green, Pages deploy and the Handout-PDF workflow green, published pages spot-checked over
   HTTP. `k8s-101-workshop`'s merge also published the pre-existing 37-file page-bundle
   migration `a55f83c`, flagged prominently in the PR body rather than slipped in.
5. **Worktrees and tmux sessions removed**, both plans set to `Status: Complete`, and durable
   facts promoted into each repo's `CLAUDE.md` per the lifecycle's step 12.

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
- [x] ~~Decide whether `k8s-101-workshop/content/k8s-101.pdf` is retired~~ — it stays,
      decided 2026-08-17
- [ ] Reconsider AKS as an `ai-101` path once someone can validate it on a real cluster
- [ ] Add `pageRef` support to `menu.shortcuts` in `CentralRepo/scripts/templates/hugo.jinja`
      so a workshop repo can put an internal page in the sidebar shortcuts without a WARN
- [x] Phase 5 (`k8s-101-workshop` prevention) — handled by a separate session; merged there
      via PR #104 on 2026-08-17. `PATH_TITLE_RE` is deliberately disabled in that repo (its
      pattern matches two ordinary existing tab titles), with a do-not-re-enable note.
- [x] **Flatten non-path tab groups in the handouts too — done 2026-08-17.** Found during
      post-merge verification of the PDFs: the generator flattened `pathtabs` correctly but
      left the remaining tab groups as tabs, and relearn's print CSS renders only the
      *active* (first) tab, so every second/third panel was missing from the PDF. Measured
      on the then-committed handouts: `handout-docker` hid 12 panels, `handout-k8s` 17.
      Sixteen were "Expected Output"/"Example Output" (readers could not check their work on
      paper) and one was a genuine instruction — the "Follow the logs" tab in the k8s
      three-tab group. Fixed with `flatten_plain_tabs()` in `gen_handouts.py`: each tab
      becomes a bold label plus its body. Bold, not a heading — depth is already four to
      five levels after `demote_headings`, and these labels do not belong in the TOC.
      Verified: 0 tab groups and 0 hidden panels in both print HTML files, PDFs grew 22→23
      and 26→28 pages, and "Follow the logs" plus every expected-output block is on paper.
- [x] Drop the obsolete `repoConfig.json` shortcut item from Phase 3 — Jeff's decision that
      handouts live in the reference section only makes a sidebar shortcut unwanted, so the
      `pageRef` limitation blocks nothing. Closed as not-needed 2026-08-17.
- [x] **Merged and published 2026-08-17.** `ai-101` PR #16 and `k8s-101-workshop` PR #104
      both merged to `main`; Pages deploy and the Handout-PDF workflow ran green on both, and
      the published pages were spot-checked over HTTP (200s, correct rewritten hrefs). Worth
      recording for the next reader: while #16 was open, `main` moved (Robert's
      `08acc34 fix helm chart values.yaml ui settings`, adding a `NodePort 30280` UI service
      to `values-lab3/4.yaml`). Merged forward, rebuilt (42 pages, 0 WARN), and confirmed the
      change makes the chart *match* content that already documented NodePort 30280 — so the
      Lab 3/4 k8s instructions were correct before the chart was.
- [ ] **Add a `push: branches: [main]` trigger to `path-lint.yml`.** Surfaced 2026-08-17 right
      after the merge: Robert's direct push `d512c5c` hand-edited the generated handouts and
      left four occurrences in `handout-k8s` stale. The freshness gate caught it — but only
      because `gen_handouts.py --check` is *also* wired into `handout-pdf.yml`, which does run
      on `main`. The linter's other four checks (`cd "~`, path tokens, hand-written groupid,
      path titles in plain tabs) run on `pull_request` only, so a direct push to `main` skips
      them entirely. Cheap fix, and the guardrail is worth little if the busiest path around it
      is unguarded.
- [ ] `errorignore` as the cheaper alternative to `pageRef` upstream: relearn's
      `urlErrorReport.gotmpl` already honors `site.Params.errorignore` (a list of regexes
      matched against the URL). `hugo.jinja` emits neither it nor `pageRef`, and has no
      arbitrary-params passthrough, so either one is an upstream CentralRepo change — but
      `errorignore` is a one-line template addition where `pageRef` needs menu-shape changes.

## Risks / Open Questions

- **Silent tab fallback** — highest risk, since it is invisible. Mitigated twice:
  `pathtabs` removes the ability to write the broken form, and the linter fails PRs.
- **Handout freshness** — a generated artifact in git drifts unless checked. Mitigated by
  `--check` in the PR workflow.
- ~~**`outputs: ["html","print"]` per page may not work**~~ — **resolved in Phase 0**: it
  works with the pinned image; `zztmptest/index.print.html` was produced.
- **Generated handout pages must not appear in the sidebar** (decided): they live in the
  reference section only. Need the relearn front-matter flag for menu exclusion in
  Phase 3; if none is reliable, nest them under `09Reference` and exclude via the section's
  own menu handling.
- **PDF step needs headless Chrome in CI** — adds a dependency and ~1 min to the `main`
  workflow. Isolated in its own workflow so a failure cannot block the Pages deploy.
- **Path choice does not carry from `k8s-101-workshop` to `ai-101`** — localStorage is
  keyed by `baseURL`. The `ai-101` gate must therefore always be passed; acceptable, but
  worth an explicit line in the `ai-101` Kubernetes tab for continuing participants.
- **Concurrent sessions** — Jeff runs parallel Claude sessions against these repos; all
  work happens in a dedicated worktree, and files outside this plan's scope are left
  alone.

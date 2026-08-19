# CLAUDE.md — ai-101

> Global preferences (planning workflow, code quality, operations): `~/.claude/CLAUDE.md`

## Project in One Line

A FortinetCloudCSE hands-on workshop — "AI 101 — Agents, MCP & the Agentic Security Model" — published as a Hugo static site to GitHub Pages, plus a self-contained multi-container lab app (Ollama + FastAPI agent + MCP server + nginx UI) that students deploy via Docker Compose profiles or Helm.

## Stack Quick Reference

| Layer | Tech | Port |
|-------|------|------|
| Site generator | Hugo v0.162.1 via `public.ecr.aws/k4n6m5h8/fortinet-hugo:latest` | 1313 (local dev) |
| Site theme/config | [CentralRepo](https://github.com/FortinetCloudCSE/CentralRepo) — mounted at build time, **not** in this repo | — |
| Local dev driver | [fortihugorunner](https://github.com/FortinetCloudCSE/fortihugorunner) CLI | — |
| Hosting | GitHub Pages (`https://fortinetcloudcse.github.io/ai-101/`) | — |
| Lab: inference | Ollama | 11434 |
| Lab: agent | FastAPI (`agent`, `agent-mcp`) | 8001 |
| Lab: MCP server | `mcp-server` | — |
| Lab: UI | nginx (`ui`, `ui-mcp`) | 8080 |
| Lab images | `ghcr.io/fortinetcloudcse/ai-101/<component>` | — |

## Key File Map

```
content/                   — workshop pages (page bundles, ordered by `weight`)
  _index.md
  01Intro/{1_prereqs_docker, 2_prereqs_k8s}/
  02Inference/1_lab/   03Agents/1_lab/   04MCP/1_lab/   05Security/1_lab/
  09Reference/cloud-shell-web-preview/
instructor_content/        — instructor-only notes (not part of the student path)
solution/Makefile          — solution shortcuts
layouts/                   — repo-local Hugo overrides
  shortcodes/{ContainerFlow,FTNThugoFlow,fortihugorunner}.html   — all 3 currently unused by content
  shortcodes/{pathtabs,pathtab}.html   — the deployment-path switch (see below)
  partials/dependencies.html
scripts/gen_handouts.py    — generates content/09Reference/handouts/ (--check = CI freshness gate)
scripts/lint_paths.py      — deployment-path linter (run by path-lint.yml on PRs)
scripts/repoConfig.json    — site chrome: title, author, banner, sidebar shortcuts
plans/                     — plan/spec/log files, `NNNN_` prefixed (NOT docs/plans — see gotcha)
lab-app/
  compose/docker-compose.yaml  — 6 services, profile-gated (`--profile lab1`…`lab4`)
  helm/ai101/                  — Chart.yaml, templates/, values.yaml + values-lab1..4.yaml
  images/{ollama,agent,mcp-server,ui}/   — one Dockerfile per component
  scripts/                     — lab drivers (lab1_inference.sh, lab1_injection.sh, _lab1_common.py)
.github/workflows/
  static.yml                     — build + deploy to Pages on push to main (DIVERGED — see gotcha)
  build-images.yml               — build/push lab images to GHCR; triggers on push to main
                                   touching lab-app/images/** or the workflow itself
  handout-pdf.yml                — renders the generated handouts to PDF (push to main + dispatch)
  path-lint.yml                  — runs scripts/lint_paths.py on PRs
  lacework-code-security-pr.yml  — Lacework scan on PRs
  codex-advisory-review.yml      — advisory LLM diff review on PRs
Jenkinsfile                — content-lint pipeline
fdevsec.yaml               — FortiDevSec config (app id unfilled — see gotcha)
migration_log.csv, migration_log_dry_run.csv  — Hugo-v2.1 migration artifacts, historical only
repo_upgrade_spec.json     — template-sync manifest (documentation only — see gotcha)
.repo_upgrade_version      — `Hugo-v2.1`
```

## Build & Run Commands

```bash
# Preview the site locally (requires Docker + fortihugorunner on PATH)
fortihugorunner pull-image --env author-dev
fortihugorunner launch-server \
  --docker-image fortinet-hugo:latest \
  --host-port 1313 --container-port 1313 --watch-dir .
# open http://localhost:1313 — live-reloads on content changes

# Reproduce the CI static build exactly
docker run --rm -v "$PWD:/home/UserRepo" fortinet-hugo:latest build

# Test an UNMERGED CentralRepo change against this repo — mount both sides
docker run --rm -v "$PWD:/home/UserRepo" \
  -v ~/pythonProjects/worktrees/CentralRepo-<slug>:/home/CentralRepo \
  fortinet-hugo:latest build

# Lab app — Docker Compose (per-lab profiles)
cd lab-app/compose && docker compose --profile lab2 up -d

# Lab app — Helm
cd lab-app/helm && helm upgrade --install ai101 ./ai101 -f ai101/values-lab2.yaml
```

There is no test suite. Content changes are validated by rendering locally.

Three traps when mounting a CentralRepo worktree to test an unmerged change, all of which cost real time once:

- **"Byte-identical output" cannot be measured directly.** Four tokens change on *every* build: the `?178…` asset cache-buster, `R-image-<md5>`, `last-updated-time-utc`, and the anonymous `data-tab-group=<md5>`. Normalise those before diffing, and sanity-check by building the **baseline twice** — if baseline-vs-rerun produces the same diff set as baseline-vs-change, the diff is noise.
- **`local_copy.sh:3-4` copies this repo's `layouts/shortcodes/*` and `layouts/partials/*` over CentralRepo's — including into the mounted worktree.** So a local build can silently deposit this repo's files into a CentralRepo checkout and shadow the shared originals. Run `git status` **inside the worktree** after every local build.
- **A fresh `git worktree add` leaves `themes/hugo-theme-relearn` empty**, and relearn is what defines the `print` output format, so the build dies with `unknown output format "print" for kind "home"` — an error that looks like a config regression and is not. `cp -a` the theme in from a populated checkout.

Current build state (verified 2026-08-17, branch `jkopkoEdits`): exit 0, 36 pages, 7 non-page files, 13 static files, 19 HTML files. 2 WARNs, both real broken images — see below.

## Critical Patterns & Gotchas

- **Hugo warnings never fail the build, so the build log is the only real check.** `errorLevel` is `warning` in `scripts/repoConfig.json`, so an `is not a resource` WARN still exits 0 and ships a broken image. Two such images shipped for months (`browser.png.png`, and `../searchweb.png` referenced from outside its bundle); both are fixed as of the deployment-path work. Verification means `grep -cE '^(WARN|ERROR)'` on the build log, not the exit code. The baseline is **0 WARN**.
- **`static.yml` here is AHEAD of the template, and a template upgrade will silently regress it.** This repo's copy adds a `trap cleanup EXIT`, captures `docker wait` status, echoes `docker logs`, and fails the job with `::error::` on a non-zero build. The 12-repo consensus version (md5 `1583cc7583b39c3b43c152aec99fda94`, used by k8s-101-workshop, faig, fortiweb, AWS-FGT-301, PC104 and others) does **none** of that — it discards the build exit code, so a failed Hugo build deploys an empty/stale site silently. `static.yml` is in the template's `FILES_TO_COPY`, so running the upgrade tool overwrites this improvement. Re-apply it, or better, push it upstream into CentralRepo.
- **`docs/` is machine-owned — never put plan files there.** `.gitignore` excludes `docs/`, and `CentralRepo/scripts/batch_repo_update.py` hardcodes `FOLDERS_TO_DELETE = ["docs"]` with `BRANCH = "main"`, deleting every blob under it via the GitHub tree API and pushing that deletion straight to `main`. Plan/spec/log files go in root-level **`plans/`** (see `plans/README.md`), which is inert to Hugo and outside the delete list.
- **`repo_upgrade_spec.json` is documentation, not the executed contract.** `batch_repo_update.py` never reads it — the script's own hardcoded `FILES_TO_COPY` / `FILES_TO_DELETE` / `FOLDERS_TO_DELETE` constants are what run. The two can drift silently. Read the script, not the spec, when predicting what an upgrade will do.
- **No `hugo.toml` or `config.toml` here — on purpose.** Hugo config, theme, and layouts come from CentralRepo, mounted alongside this repo; both files are in the template's delete list. Site title, banner text, author, and sidebar shortcuts live in **`scripts/repoConfig.json`**.
- **There is no `Dockerfile` in this repo,** but `Dockerfile` is in the template's `FILES_TO_COPY` — a template upgrade will introduce one. Don't be surprised by it appearing.
- **All three local shortcodes are currently unreferenced by content** (`ContainerFlow`, `FTNThugoFlow`, `fortihugorunner`). `FTNThugoFlow.html` is additionally in the template's `FILES_TO_DELETE`, so an upgrade removes it — harmless while unused, breaking if someone starts using it first.
- **Container mount layout:** repo mounts at `/home/UserRepo`; CentralRepo at `/home/CentralRepo`; Hugo output at `/home/CentralRepo/public`, which CI copies to `./docs` and uploads as the Pages artifact.
- **The site uses `uglyURLs`** — hardcoded `uglyURLs = true` at `CentralRepo/scripts/templates/hugo.jinja:20`, inside the image, so it is **not overridable from this repo** (no workshop repo sets it). A leaf bundle `04MCP/1_lab/index.md` renders to `04mcp/1_lab.html`, not `04mcp/1_lab/index.html`. This is why `../`-relative image paths that look right in source resolve one level too high in output. Reference images as bundle resources instead of relative paths.
- **Shortcodes come from the CentralRepo theme:** `{{% notice %}}` and `{{< tabs >}}` / `{{% tab title="…" %}}`. Grep existing content before inventing one; new ones go under `layouts/shortcodes/`.
- **Page ordering is `weight` in front matter,** not filename. Directory prefixes (`01Intro`, `02Inference`) are cosmetic.
- **Every lab step in content must match the actual `lab-app` code.** Content hardcodes paths (`~/ai-101/lab-app/compose`), profile names, service names, and ports. Compose profiles are `lab1`–`lab4` across 6 services: `ollama` (all labs), `agent` + `ui` (lab2), `agent-mcp` + `mcp-server` + `ui-mcp` (lab3, lab4). Changing a profile or a Helm values file without updating the matching `content/*/1_lab/index.md` silently breaks the lab.
- **`package.json` / `package-lock.json` are tracked despite being listed in `.gitignore`** (lines 6–7). They predate the ignore rule. Don't assume the ignore is effective.
- **`fdevsec.yaml` has an unfilled `app: <insert app id here>`** — `org` is a real UUID, scanners are `sast, secret, sca, iac, container`, and `fail_pipeline.risk_rating: 7`. The app id is genuinely missing here (unlike some sibling repos, where it is populated). Leave it unless asked.
- **Deploy triggers only on push to `main`.** Work on `jkopkoEdits` publishes nothing until merged.
- **`codex-advisory-review.yml` uses `pull_request_target` deliberately** so `OPENAI_API_KEY` comes from the trusted base branch and the PR head is never checked out. Do not convert it to `pull_request`.
- **A `menu.shortcuts` entry in `scripts/repoConfig.json` cannot point at a page in this site without producing a WARN.** `hugo.jinja` only ever emits `url =` for shortcuts, never `pageRef`, and relearn's `menuPermalink.gotmpl` runs the value through `relLangURL` — which strips the baseURL off a fully-qualified self-URL, so the result is classified "local" and warns on every page. Link internal pages from content bodies instead. Fixing it properly means adding `pageRef` support to `hugo.jinja` upstream in CentralRepo — or `errorignore`: relearn's `urlErrorReport.gotmpl` honors `site.Params.errorignore` / a page's own `errorignore`, a list of regexes matched against the URL, which would suppress the warn cleanly. `hugo.jinja` emits neither, and it has no arbitrary-params passthrough from `repoConfig.json`, so both fixes are upstream-only. (Same WARN, same dead end, in `k8s-101-workshop`.)

## Deployment paths

The workshop has two deployment paths. Readers choose once and every later page follows that choice.

- **The choice is a gate, not a tab default, and the gate is default-deny.** Until a reader picks a path, **no** path's steps render on any page — a blocking chooser appears instead. This is not cosmetic: participants were carrying out both the Docker steps and the Kubernetes steps because both tabs were on screen, and relearn marks tab #1 active server-side (`shortcodes/tabs.html:69,80`), so any "hide the inactive tab" scheme without default-deny would present Docker as *the* path to a Kubernetes reader. There is no default path — `deploymentPaths` order now only sets button order.
- **The mechanism is pre-paint CSS, and it all lives in CentralRepo's `custom-header.html`.** An inline synchronous `<script>` in `<head>` sets `<html data-deployment-path="…">` from `localStorage` before `<body>` exists (the same pattern relearn uses for `themeVariant`), and CSS keyed off that attribute does the gating. Nothing mutates the DOM after load. Consequences worth knowing before changing any of it: the flag must go on `document.documentElement`, since `document.body` does not exist yet; `pathtabs` no longer carries a `<style>` or `<script>` of its own; and per-page assets must not go back into the shortcode — `.Page.Store` is per-**output-format**, so a shortcode-side once-per-page guard gave the `print` format the markup and never the assets, silently shipping ungated tabs in every `index.print.html`.
- **Gating selects `.pathgate[data-path="…"]`, never relearn's `data-tab-item`.** `pathtabs` wraps each path's body in that element precisely so the CSS never has to re-derive `anchorize(plainify(title))` — which CSS cannot express and which a title rename would break. `pathonly` reuses the same wrapper, so there is one gating mechanism in the codebase, not two.
- **No `!important` in the gate, deliberately, and `@media` adds no specificity.** The theme's `#R-body .tab-content.active` is (1,2,0); the hide rule is (1,3,1) and the `:has()` show rule (1,6,1), so specificity alone wins. That matters because `!important` here would leak into print and the handout PDFs. The corollary bites: `@media print { .pathlock__banner { display: none } }` is (0,1,0) and **loses** to the per-path show rules, so the print overrides are written as `html[data-deployment-path] .pathlock__banner` at (0,2,1) and win on source order instead.
- **The `<noscript>` state is the one place both paths appear, and it must announce itself.** JavaScript off means nothing sets the attribute, so a `<noscript>` rule un-hides everything behind a warning naming the paths in order. Showing both silently is the original bug; a blank lab page would be worse than either. Do not "simplify" this into a plain un-hide.

- **`pathtabs` / `pathtab` live in CentralRepo, not here.** The local copies were deleted once the shared versions landed upstream (CentralRepo PR #71). Do not re-add `layouts/shortcodes/pathtab*.html` — `local_copy.sh` would silently shadow the shared shortcode and an upstream fix would stop reaching this repo with no warning.
- **Vocabulary is fixed.** `groupid: deploy-path`; tab keys `docker` / `k8s`; tab titles **"Docker Compose"** and **"Kubernetes / Helm"**, in that order. The vocabulary is declared in three places that must agree: `deploymentPaths` in `scripts/repoConfig.json` (the site param the shared shortcode reads — it `errorf`s if absent), `PATHS` in `scripts/gen_handouts.py`, and the CONFIG block in `scripts/lint_paths.py`.
- **Never rename a `deploymentPaths` title.** relearn derives `itemid = anchorize(plainify(title)) + anchorize(icon)`, and the stored cross-page selection is keyed on that id. Rename a title and every returning reader's saved choice becomes unmatchable, dropping them onto the first tab — no warning, no build error. Renaming a `key` is the safe, loud kind of change: every `pathtab path=` must follow or the build fails. The shared shortcode passes no icon, so the icon half of the itemid is empty and must stay that way.
- **Drive relearn with a real `.click()`, never by calling `switchTab()`.** It reads the implicit global `event` (`theme.js:120`), so a programmatic call silently fails to persist. `fortiPath.set()` dispatches `.click()` on the matching `.tab-nav-button` instead.
- **The gate is the one thing allowed to write relearn's `tab-selections` key.** The general rule still holds — duplicating the theme's storage contract drifts from it — but the gate must, and for a non-obvious reason: a panel the gate reveals while relearn still believes it is inactive never gets `initMermaid()` run against it, so any mermaid diagram inside renders at **zero width**. So the head script reconciles relearn's key *to* the gate's `/deployment-path` key on every load, before the deferred `restoreTabSelections()` (`theme.js:1835`) runs. Two keys, one direction of truth.
- **The locked-path banner is server-rendered, not observed.** One `.pathlock__value` per path is emitted and CSS-gated. An earlier revision used a `MutationObserver` on the `.active` class; that is gone, along with the flash it implied, and it should not come back — the observer necessarily fires after paint.
- **Never emit reader-facing prose from a shortcode in this theme.** Anything a shortcode writes lands in `.Content`, and relearn plainifies that into `<meta name="description">` (`themes/hugo-theme-relearn/layouts/partials/meta.html:44`) *and* indexes it for lunr. A chooser emitted from `pathtabs` put "JavaScript is disabled, so all 2 deployment paths are shown below" into the description and search snippet of every lab page and added 120 words each. Page-level chrome belongs in `content-header.html`, gated on `.HasShortcode "pathtabs"` — which also collapses one-per-block duplicates to one per page.
- **Don't "fix" the print CSS to un-hide the other tab panels.** It looks like the obvious fix for panels vanishing from PDFs, but for `pathtabs` it is actively wrong — printing both paths is the exact failure the per-path handouts exist to prevent. For ordinary `Command`/`Expected Output` groups it is a separate question with its own blast radius, since the rule is shared theme CSS (`theme.css:2659-2673`), not something this repo owns.
- **Every path branch goes through `{{< pathtabs >}}` / `{{% pathtab path="…" %}}`.** Never hand-write `groupid="deploy-path"` on a plain `{{< tabs >}}` group — the linter rejects it. `pathtabs` **fails the build** (`errorf`, not `warnf`) if a block omits a path or defines one twice, which is the one place in this repo where a content mistake is a hard error rather than a WARN.
- **A whole page can be path-scoped** with `deploymentPath: docker` or `deploymentPath: k8s` in front matter, plus an opening `notice` linking the other path's page. Used by the two prereq pages, the Cloud Shell page, and the generated handouts. The linter treats such a page as one big path block.
- **Only the active tab is ever rendered, in every medium** — `theme.css:2659-2673` sets `#R-body .tab-content { display: none }` with `.tab-content.active { display: block }`. So printing a tabbed lab page silently drops the other path. This is **not** a print-specific rule: `format-print.css:163-176` touches tabs only to recolour them for paper (black text, white backgrounds) and hides nothing. Earlier revisions of this file and of `gen_handouts.py` cited `format-print.css` as the cause; that was wrong, and it matters because the same rule is what makes a *screen*-rendered handout lose panels too. That is why handouts exist rather than a "print this page" link.
- **A generated print artifact must flatten EVERY tab group, not just the path tabs.** `theme.css:2659-2673` hides all non-active panels regardless of `groupid`, so any tab group left intact loses content on paper. This bit once: `gen_handouts.py` flattened `pathtabs` but left the command-vs-"Expected Output" groups alone, and the PDFs silently dropped 12 panels (docker) / 17 (k8s) — 16 informational plus one real instruction ("Follow the logs"). `flatten_plain_tabs()` now converts each tab to a **bold label** plus body; bold rather than a heading because depth is already 4–5 levels after `demote_headings` and these labels do not belong in the TOC. Verifying a handout means counting tab markup and hidden panels in `index.print.html` (expect 0 of each) — a clean build and a rendering PDF prove nothing here.
- **`scripts/gen_handouts.py` generates `content/09Reference/handouts/`** — one linear single-path page per path, walking `content/` in weight order, flattening each pathtabs block to that path and dropping the other entirely, then flattening every remaining tab group to labelled subsections. Bundle images are copied into the handout bundle under a `<dir-slug>-<name>.png` prefix so they stay genuine page resources. `OUT_DIR` is fully generator-owned: orphans are deleted. Handouts carry `hidden: true` (keeps them out of the sidebar — verified in rendered HTML) and `outputs: ["html", "print"]` (gives each an `index.print.html`, which `handout-pdf.yml` turns into a PDF).
- **Never hand-edit `content/09Reference/handouts/` — edit the source page and re-run the generator.** Hit for real on 2026-08-17: `d512c5c` changed the source pages and hand-edited the handouts, but four occurrences in `handout-k8s` kept the old form. The freshness gate caught it (`gen_handouts.py --check` in `handout-pdf.yml` failed on `main` in 6s, so no stale PDF shipped) and it was fixed by regenerating.
- **`path-lint.yml` runs on `pull_request` only, so a direct push to `main` bypasses the linter.** The one check duplicated on the `main` path is handout freshness, via `handout-pdf.yml` — the `cd "~`, path-token, and groupid checks are not. Either route content changes through a PR, or add a `push: branches: [main]` trigger to `path-lint.yml`.
- **`scripts/lint_paths.py` is the guardrail**, run on PRs by `path-lint.yml`. It fails on: a path-like title in a plain `tabs` group; a hand-written `deploy-path` groupid; a path-specific token outside a path block; `cd "~` anywhere (bash does not expand `~` inside double quotes, so that command always fails); and stale handouts. Prose that legitimately names both paths goes in the `ALLOWLIST`, which requires a written reason per entry.
- **Rendering a handout to PDF needs `--disable-dev-shm-usage`.** Without it the longer (Kubernetes) handout dies with `Printing failed.` on Chrome's default 64 MB `/dev/shm` while the shorter Docker one succeeds — so **never verify handouts on one path only**; the failure mode only appears on the bigger input. `handout-pdf.yml` passes the flag; pass it too when rendering locally. Reading the PDF back also needs `poppler-utils` on the host.
- **After any content edit, run `python3 scripts/lint_paths.py`** and commit regenerated handouts with the change.

## Environment Variables

None required for authoring. CI-only secrets: `LW_ACCOUNT_NAME`, `LW_API_KEY`, `LW_API_SECRET` (Lacework), `OPENAI_API_KEY` (advisory review), `GITHUB_TOKEN` (Pages + GHCR).

Optional locally: `DOCKER_CONTEXT` / `DOCKER_HOST` — fortihugorunner honors the active Docker context.

## Common Tasks

**Add a workshop module**: create `content/NNName/_index.md` with `title`, `linkTitle`, `weight`; add lab pages as leaf bundles (`1_lab/index.md`) with their images co-located in the same directory. Preview with `launch-server`, then run the CI build to catch `is not a resource` warnings.

**Change site chrome** (title, banner, sidebar links): edit `scripts/repoConfig.json`. Nothing in `layouts/` or a config file.

**Add or change a lab component**: edit `lab-app/images/<component>/`, then update both `lab-app/compose/docker-compose.yaml` and `lab-app/helm/ai101/` (including the relevant `values-labN.yaml`). Pushing to `main` rebuilds and pushes to `ghcr.io/fortinetcloudcse/ai-101/<component>`.

**Write a plan**: `plans/NNNN_YYYY-MM-DD_<git-username>_<slug>.md`, plus an optional `.log.md` and `.spec.md`. Not `docs/plans/`. `NNNN` is a per-repo sequence; the log is optional; on completion, durable facts get promoted into this file and the plan is left to decay. See `plans/README.md`.

**Debug a broken published page**: run the CI build command locally — the dev server is more forgiving than the static build. `errorLevel` in `scripts/repoConfig.json` is `warning`, so Hugo warnings never fail the build; read the log for `WARN` lines rather than trusting the exit code.

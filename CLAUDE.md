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
plans/                     — plan/spec/log files (NOT docs/plans — see gotcha)
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

# Lab app — Docker Compose (per-lab profiles)
cd lab-app/compose && docker compose --profile lab2 up -d

# Lab app — Helm
cd lab-app/helm && helm upgrade --install ai101 ./ai101 -f ai101/values-lab2.yaml
```

There is no test suite. Content changes are validated by rendering locally.

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
- **A `menu.shortcuts` entry in `scripts/repoConfig.json` cannot point at a page in this site without producing a WARN.** `hugo.jinja` only ever emits `url =` for shortcuts, never `pageRef`, and relearn's `menuPermalink.gotmpl` runs the value through `relLangURL` — which strips the baseURL off a fully-qualified self-URL, so the result is classified "local" and warns on every page. Link internal pages from content bodies instead. Fixing it properly means adding `pageRef` support to `hugo.jinja` upstream in CentralRepo.

## Deployment paths

The workshop has two deployment paths. Readers choose once on the Introduction gate page and every later page follows that choice.

- **Vocabulary is fixed.** `groupid: deploy-path`; tab keys `docker` / `k8s`; tab titles **"Docker Compose"** and **"Kubernetes / Helm"**, in that order, with **no icons**. The vocabulary is declared in three places that must agree: `layouts/shortcodes/pathtab.html`, `PATHS` in `scripts/gen_handouts.py`, and the CONFIG block in `scripts/lint_paths.py`.
- **Never add an icon to a path tab.** relearn computes `itemid = anchorize(plainify(title)) + anchorize(icon)`, so an icon changes the itemid, the group no longer matches other pages, and selection silently falls back to the first tab.
- **Every path branch goes through `{{< pathtabs >}}` / `{{% pathtab path="…" %}}`.** Never hand-write `groupid="deploy-path"` on a plain `{{< tabs >}}` group — the linter rejects it. `pathtabs` **fails the build** (`errorf`, not `warnf`) if a block omits a path or defines one twice, which is the one place in this repo where a content mistake is a hard error rather than a WARN.
- **A whole page can be path-scoped** with `deploymentPath: docker` or `deploymentPath: k8s` in front matter, plus an opening `notice` linking the other path's page. Used by the two prereq pages, the Cloud Shell page, and the generated handouts. The linter treats such a page as one big path block.
- **Print renders only the active tab** (`format-print.css`), so printing a tabbed lab page silently drops the other path. That is why handouts exist rather than a "print this page" link.
- **`scripts/gen_handouts.py` generates `content/09Reference/handouts/`** — one linear single-path page per path, walking `content/` in weight order, flattening each pathtabs block to that path and dropping the other entirely. Bundle images are copied into the handout bundle under a `<dir-slug>-<name>.png` prefix so they stay genuine page resources. `OUT_DIR` is fully generator-owned: orphans are deleted. Handouts carry `hidden: true` (keeps them out of the sidebar — verified in rendered HTML) and `outputs: ["html", "print"]` (gives each an `index.print.html`, which `handout-pdf.yml` turns into a PDF).
- **`scripts/lint_paths.py` is the guardrail**, run on PRs by `path-lint.yml`. It fails on: a path-like title in a plain `tabs` group; a hand-written `deploy-path` groupid; a path-specific token outside a path block; `cd "~` anywhere (bash does not expand `~` inside double quotes, so that command always fails); and stale handouts. Prose that legitimately names both paths goes in the `ALLOWLIST`, which requires a written reason per entry.
- **After any content edit, run `python3 scripts/lint_paths.py`** and commit regenerated handouts with the change.

## Environment Variables

None required for authoring. CI-only secrets: `LW_ACCOUNT_NAME`, `LW_API_KEY`, `LW_API_SECRET` (Lacework), `OPENAI_API_KEY` (advisory review), `GITHUB_TOKEN` (Pages + GHCR).

Optional locally: `DOCKER_CONTEXT` / `DOCKER_HOST` — fortihugorunner honors the active Docker context.

## Common Tasks

**Add a workshop module**: create `content/NNName/_index.md` with `title`, `linkTitle`, `weight`; add lab pages as leaf bundles (`1_lab/index.md`) with their images co-located in the same directory. Preview with `launch-server`, then run the CI build to catch `is not a resource` warnings.

**Change site chrome** (title, banner, sidebar links): edit `scripts/repoConfig.json`. Nothing in `layouts/` or a config file.

**Add or change a lab component**: edit `lab-app/images/<component>/`, then update both `lab-app/compose/docker-compose.yaml` and `lab-app/helm/ai101/` (including the relevant `values-labN.yaml`). Pushing to `main` rebuilds and pushes to `ghcr.io/fortinetcloudcse/ai-101/<component>`.

**Write a plan**: `plans/YYYY-MM-DD_<git-username>_<slug>.md` plus `.log.md`. Not `docs/plans/`.

**Debug a broken published page**: run the CI build command locally — the dev server is more forgiving than the static build. `errorLevel` in `scripts/repoConfig.json` is `warning`, so Hugo warnings never fail the build; read the log for `WARN` lines rather than trusting the exit code.

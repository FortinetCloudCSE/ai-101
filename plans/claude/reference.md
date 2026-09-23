# ai-101 — Reference

Read this when: you need the file map or the detailed local-build commands/traps
(mounting a CentralRepo worktree, cleaning `public/`, etc.) — not needed for ordinary
content edits.

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

Four traps when mounting a CentralRepo worktree to test an unmerged change, all of which cost real time once:

- **"Byte-identical output" cannot be measured directly.** Four tokens change on *every* build: the `?178…` asset cache-buster, `R-image-<md5>`, `last-updated-time-utc`, and the anonymous `data-tab-group=<md5>`. Normalise those before diffing, and sanity-check by building the **baseline twice** — if baseline-vs-rerun produces the same diff set as baseline-vs-change, the diff is noise. The last-updated stamp needs **two** patterns, not one: it renders as a weekday string (`Wed, Aug 19, 2026 18:19:54 UTC`), so an ISO-only regex silently leaves it in and reports every page as differing. That is what a 17-file "regression" turned out to be.
- **The container writes `public/` as root, so `rm -rf public` from the host fails with a screenful of `Permission denied`** — and a *partly* failed delete is worse than none, because the next repo's build lands on top of the previous repo's stale files and the copied output is unusable while looking fine. Clean it in a container: `docker run --rm -v "$PWD":/home/CentralRepo alpine:latest sh -c 'rm -rf /home/CentralRepo/public'`.
- **`local_copy.sh:3-4` copies this repo's `layouts/shortcodes/*` and `layouts/partials/*` over CentralRepo's — including into the mounted worktree.** So a local build can silently deposit this repo's files into a CentralRepo checkout and shadow the shared originals. Run `git status` **inside the worktree** after every local build.
- **A fresh `git worktree add` leaves `themes/hugo-theme-relearn` empty**, and relearn is what defines the `print` output format, so the build dies with `unknown output format "print" for kind "home"` — an error that looks like a config regression and is not. `cp -a` the theme in from a populated checkout.

Current build state (verified 2026-08-19, `main` at `a419517`, prod `:latest`): exit 0, 42 pages, 15 non-page files, 13 static files, 24 HTML files, **0 WARN**. The Hugo version behind `:latest` no longer drifts — CentralRepo's `Dockerfile` pins `FROM hugomods/hugo:std-0.165.0`, so a base-image release cannot change the renderer under you mid-workshop.

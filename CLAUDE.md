# CLAUDE.md — ai-101

> Global preferences (planning workflow, code quality, operations): `~/.claude/CLAUDE.md`
>
> On-demand docs (this is a Hugo workshop repo — `docs/` is machine-owned/wiped, so
> these live in `plans/claude/`, not `docs/claude/`):
>
> | Doc | Read it when |
> |---|---|
> | [plans/claude/reference.md](plans/claude/reference.md) | You need the full file map, or local-build commands/traps (mounting a CentralRepo worktree, cleaning `public/`, theme setup) |
> | [plans/claude/gotchas.md](plans/claude/gotchas.md) | Debugging CI/deploy, editing a workflow file, `repoConfig.json`, or `fdevsec.yaml`, or predicting a template-upgrade effect |
> | [plans/claude/deployment-paths.md](plans/claude/deployment-paths.md) | Touching `pathtabs`/`pathtab`/`pathonly`, `deploymentPaths` config, `lint_paths.py`, `gen_handouts.py`, or any Docker-vs-Kubernetes path content, search, nav, or handout PDFs |

## Project in One Line

A FortinetCloudCSE hands-on workshop — "AI 101 — Agents, MCP & the Agentic Security Model" — published as a Hugo static site to GitHub Pages, plus a self-contained multi-container lab app (Ollama + FastAPI agent + MCP server + nginx UI) that students deploy via Docker Compose profiles or Helm.

## Stack Quick Reference

| Layer | Tech | Port |
|-------|------|------|
| Site generator | Hugo v0.165.0 via `public.ecr.aws/k4n6m5h8/fortinet-hugo:latest` | 1313 (local dev) |
| Site theme/config | [CentralRepo](https://github.com/FortinetCloudCSE/CentralRepo) — mounted at build time, **not** in this repo | — |
| Local dev driver | [fortihugorunner](https://github.com/FortinetCloudCSE/fortihugorunner) CLI | — |
| Hosting | GitHub Pages (`https://fortinetcloudcse.github.io/ai-101/`) | — |
| Lab: inference | Ollama | 11434 |
| Lab: agent | FastAPI (`agent`, `agent-mcp`) | 8001 |
| Lab: MCP server | `mcp-server` | — |
| Lab: UI | nginx (`ui`, `ui-mcp`) | 8080 |
| Lab images | `ghcr.io/fortinetcloudcse/ai-101/<component>` | — |

## Build & Run — Quick Start

```bash
fortihugorunner pull-image --env author-dev
fortihugorunner launch-server --docker-image fortinet-hugo:latest \
  --host-port 1313 --container-port 1313 --watch-dir .
# open http://localhost:1313 — live-reloads on content changes

# Reproduce the CI static build exactly
docker run --rm -v "$PWD:/home/UserRepo" fortinet-hugo:latest build

# Lab app
cd lab-app/compose && docker compose --profile lab2 up -d          # Compose
cd lab-app/helm && helm upgrade --install ai101 ./ai101 -f ai101/values-lab2.yaml   # Helm
```

No test suite — content changes are validated by rendering locally. Full commands, the
CentralRepo-worktree-mount traps, and current verified build state: `plans/claude/reference.md`.

## Critical Rules (one line each — detail in the linked doc)

- Never write the skip-CI token (square-bracket `skip` `ci`) literally in a commit message or PR body/title here — it silently kills the Pages deploy even in explanatory prose; after merging any PR, confirm a `Deploy static content to Pages` run exists for the merge SHA. Recovery + full mechanism: `plans/claude/gotchas.md`.
- Hugo warnings never fail the build (`errorLevel: warning`) — check the build log for `WARN`/`ERROR`, not the exit code. Baseline is 0 WARN.
- `static.yml` here is intentionally ahead of the CentralRepo template (fails the job on a bad build); a template upgrade will silently regress it — re-apply the divergence after any upgrade. Detail: `plans/claude/gotchas.md`.
- Never put plan/spec/log files under `docs/` — it's deleted wholesale by `CentralRepo/scripts/batch_repo_update.py`. They go in root-level `plans/` (`plans/NNNN_YYYY-MM-DD_<git-username>_<slug>.md`, see `plans/README.md`).
- `repo_upgrade_spec.json` is documentation only — `batch_repo_update.py` never reads it; its own hardcoded constants govern what a template upgrade actually copies/deletes.
- No `hugo.toml`/`config.toml` in this repo on purpose — config/theme/layouts come from CentralRepo; site chrome (title, banner, sidebar) lives in `scripts/repoConfig.json`.
- Site uses `uglyURLs` (hardcoded upstream) — a leaf bundle renders one level shallower than its source path (e.g. `04MCP/1_lab/index.md` → `04mcp/1_lab.html`). Reference images as bundle resources, not `../`-relative paths.
- Page order is front-matter `weight`, not filename/directory prefix.
- Every lab step in content must match the real `lab-app` code (paths, compose profile names `lab1`–`lab4`, service names, ports) — changing compose/Helm without updating `content/*/1_lab/index.md` silently breaks the lab.
- `package.json`/`package-lock.json` are tracked despite being gitignored (predate the rule) — don't assume the ignore is effective.
- Deploy triggers only on push to `main`; other branches publish nothing until merged.
- `codex-advisory-review.yml` deliberately uses `pull_request_target` (trusted-branch secret, PR head never checked out) — do not convert to `pull_request`.
- A `menu.shortcuts` entry in `repoConfig.json` cannot point at an in-site page without a WARN on every page — link internal pages from content bodies instead. Root cause + upstream-only fixes: `plans/claude/gotchas.md`.
- Every path-specific content block must go through `{{< pathtabs >}}`/`{{% pathtab path="…" %}}`/`{{% pathonly %}}` (never hand-written `groupid="deploy-path"` on a plain `tabs`, never `{{< pathonly >}}` with angle brackets) — the linter and/or Hugo itself hard-fail violations. Full gating mechanism, relearn internals, search/nav/print interactions: `plans/claude/deployment-paths.md`.
- Never rename a `deploymentPaths` title (breaks every returning reader's saved choice, silently); renaming a `key` is safe but loud (build fails until every `pathtab path=` follows).
- `pathtabs`/`pathtab` live in CentralRepo now, not here — do not re-add local copies, `local_copy.sh` would silently shadow upstream fixes.
- After any content edit, run `python3 scripts/lint_paths.py` and commit regenerated handouts with the change. Never hand-edit `content/09Reference/handouts/` — edit the source and regenerate.
- Rendering a handout to PDF needs `--disable-dev-shm-usage`; verify both paths (Docker succeeds without it, Kubernetes doesn't).

## Environment Variables

None required for authoring. CI-only secrets: `LW_ACCOUNT_NAME`, `LW_API_KEY`, `LW_API_SECRET` (Lacework), `OPENAI_API_KEY` (advisory review), `GITHUB_TOKEN` (Pages + GHCR).

Optional locally: `DOCKER_CONTEXT` / `DOCKER_HOST` — fortihugorunner honors the active Docker context.

## Common Tasks

**Add a workshop module**: create `content/NNName/_index.md` with `title`, `linkTitle`, `weight`; add lab pages as leaf bundles (`1_lab/index.md`) with their images co-located in the same directory. Preview with `launch-server`, then run the CI build to catch `is not a resource` warnings.

**Change site chrome** (title, banner, sidebar links): edit `scripts/repoConfig.json`. Nothing in `layouts/` or a config file.

**Add or change a lab component**: edit `lab-app/images/<component>/`, then update both `lab-app/compose/docker-compose.yaml` and `lab-app/helm/ai101/` (including the relevant `values-labN.yaml`). Pushing to `main` rebuilds and pushes to `ghcr.io/fortinetcloudcse/ai-101/<component>`.

**Write a plan**: `plans/NNNN_YYYY-MM-DD_<git-username>_<slug>.md`, plus an optional `.log.md` and `.spec.md`. Not `docs/plans/`. `NNNN` is a per-repo sequence; the log is optional; on completion, durable facts get promoted into this file and the plan is left to decay. See `plans/README.md`.

**Debug a broken published page**: run the CI build command locally — the dev server is more forgiving than the static build. `errorLevel` in `scripts/repoConfig.json` is `warning`, so Hugo warnings never fail the build; read the log for `WARN` lines rather than trusting the exit code.

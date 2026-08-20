# Plan: Auto-fix stale handouts on PR, close the admin bypass, and make the mechanism globally usable
Date: 2026-08-20
Owner: Jeff Kopko
Slug: handout-ci-and-branch-protection-hardening
Status: Approved
Supersedes: none
Superseded-By: none
Plan File: plans/0004_2026-08-20_Jeff-Kopko_handout-ci-and-branch-protection-hardening.md

## Goal

Three things, in one plan because the first two are the same root cause seen twice (2026-08-20,
`ai-101` PR #29 merged with a Hugo build failure that only surfaced post-merge, then a direct admin
push repeated the "changes reached `main` without a real CI gate" pattern while fixing it):

1. **Streamline**: a PR that leaves the generated handouts stale should fix itself, not fail and wait
   for a human to run `gen_handouts.py` by hand.
2. **Harden**: `main` on `ai-101`, `CentralRepo` and `UserRepo` currently lets an admin push directly,
   bypassing the PR requirement entirely, and the one *required* status check on all three is a
   Jenkins stage that does nothing. Normal authors/editors already use branch → PR → merge; this plan
   must not change that flow, only make it the only flow — including for admins.
3. **Generalize**: the handout-generation tooling (`gen_handouts.py`, `lint_paths.py`, the two
   workflows) exists only in `ai-101` today. Make it safe to sit — inert — in every new workshop repo
   from day one, and document it in `UserRepo`'s published authoring guide, which currently has zero
   mention of it.

## Context / Links

- Prior incident: `ai-101` Deploy workflow failure, run
  [32383607442](https://github.com/FortinetCloudCSE/ai-101/actions/runs/32383607442) — an empty
  `pathtab` body from PR #27 (`3bb3801`, merged via #27→#28→#29) reached `main` and broke the Pages
  deploy. Fixed same day by two direct pushes to `main` (`566aa42`, `ce1e993`), both logged by GitHub
  as *"Bypassed rule violations for refs/heads/main: Changes must be made through a pull request."*
- Related plan: `plans/0003_2026-08-19_Jeff-Kopko_single-path-workshop-view.md` — built the
  `deploymentPaths` gate, `pathonly`, and the current `gen_handouts.py`/`lint_paths.py`. Its own Risks
  section anticipated the staleness failure mode and named `gen_handouts.py --check` as the mitigation
  — that gate did its job; nothing upstream of it forced the check to run before merge.
- `UserRepo`'s existing authoring page: `content/02Hugo/6_deployment_paths/index.md` — thorough
  documentation of the gate mechanism itself, already links to `ai-101` as the live example, already
  contains the gotcha *"Don't hardcode your path list anywhere else... Scripts and workflows that need
  the list should read it from there"* — but says nothing about the handout generator this plan
  documents.
- Key files: `ai-101/scripts/{gen_handouts.py,lint_paths.py}`,
  `ai-101/.github/workflows/{path-lint.yml,handout-pdf.yml,static.yml}`,
  `CentralRepo/scripts/batch_repo_update.py` (`FILES_TO_COPY`), `UserRepo/scripts/repoConfig.json`,
  `UserRepo/content/02Hugo/6_deployment_paths/index.md`, `UserRepo/CLAUDE.md`.

## Constraints / Assumptions

Verified this session, each one measured rather than assumed:

- **`enforce_admins` is `false` on all three repos** (`ai-101`, `CentralRepo`, `UserRepo`) — confirmed
  via `branches/main/protection`. This is the actual bypass; it is what let two hand-pushes onto
  `ai-101`'s `main` through with only a warning.
- **The one *required* status check on all three repos is `ci/jenkins/build-status`, and the Jenkins
  pipeline behind it is a no-op.** Its `Jenkinsfile` has exactly one real stage, disabled with
  `when { expression { false } }`, plus a `deleteDir()` stage and an always-success `post` block. It
  reports `SUCCESS` on every run, unconditionally. Today, nothing an author does can fail the one check
  that actually gates a merge.
- **`handout-pdf.yml` and `static.yml` do not run on `pull_request` at all** — both trigger only on
  `push: branches: [main]` (plus `workflow_dispatch`). Only `path-lint.yml` runs on PRs today. This is
  *why* PR #29 merged clean: `lint_paths.py` passed (an empty `pathtab` is legal markup to a
  line-scanning linter; only Hugo's own `errorf` catches it), and the two checks that *do* run a real
  Hugo build — which would have caught it — never ran until after merge, on the push to `main`.
  Confirmed on PR #29's merge commit: `lint` succeeded, `deploy` and `handouts` both failed, all three
  after the merge had already landed.
- **`handout-pdf.yml` already runs a full Hugo build** (`docker run ... build`, fails loud on nonzero
  exit) before it renders PDFs. Making it PR-triggered, not just adding a new check, is what closes the
  gap — it is the cheapest path to a real pre-merge build gate, reusing a step that already exists
  rather than adding a third copy of the build-and-fail-on-error logic.
- **`handout-pdf.yml` is not template-owned.** Its header says so explicitly — unlike `static.yml`
  (`FILES_TO_COPY`-owned by `CentralRepo`, silently reverted on template upgrade), `handout-pdf.yml` is
  free for `ai-101` to edit.
- **`gen_handouts.py` currently treats a missing/empty `deploymentPaths` as fatal** (`SystemExit`,
  `scripts/gen_handouts.py:73-76`). `lint_paths.py` imports `PATHS` from it, so it inherits the same
  failure. This is correct for `ai-101` (which always sets `deploymentPaths`) and is exactly wrong for
  a repo that has never opted in — it must become a clean no-op before these scripts can sit safely in
  every new workshop repo.
- **`CentralRepo`'s `FILES_TO_COPY` is two entries today**: `scripts/static.yml` and `Dockerfile`. It
  is what `batch_repo_update.py` pushes to all ~65 existing workshop repos on every batch run — a much
  larger blast radius than "available to new repos." Nothing else is copied automatically.
- **`UserRepo` is the literal template new workshop repos are created from** — confirmed via its
  `README.md` ("Fortinet Template Repo for TECWorkshops") and its own `CLAUDE.md` ("It is a template —
  that is the constraint that governs everything"). It is also a published Hugo site itself (the
  authoring guide), which is why documentation belongs in its `content/`, not just its `CLAUDE.md`.
- **No existing bot-credential infrastructure.** Grepped all five locally-cloned Fortinet Hugo repos'
  workflows for `GH_PAT`/`BOT_TOKEN`/`APP_ID`/`create-github-app-token`/`git-auto-commit` — nothing.
  An auto-commit-on-PR mechanism needs a new credential; there is nothing to reuse.
- **Neither `k8s-101-workshop` nor `faig-training-workshop` sets `deploymentPaths`** (checked directly,
  2026-08-20) — `ai-101` remains the only repo using this mechanism today. "Globally usable" therefore
  means *available and safe*, not *active elsewhere yet*.

## Decisions & Commentary

### Auto-fix needs a real push credential, not `GITHUB_TOKEN` — and that is a decision, not a default

A step that regenerates stale handouts and pushes the fix back to the PR branch only closes the loop if
that push re-triggers the PR's checks against the new head. A push made with the workflow's own default
`GITHUB_TOKEN` deliberately does **not** trigger further workflow runs (GitHub's own recursion guard) —
so the required `lint`/`handouts` checks would still be pinned to the *pre-fix* commit, and the
PR would sit un-mergeable (or merge on a stale status, depending on settings) despite being fixed.

The standard way around this is a credential GitHub does not recognize as "the workflow itself" —
a fine-grained PAT, scoped to `contents: write` on `ai-101` only, stored as a single repo secret.
**Recommended default.** Alternative, if a new credential is unwanted: keep the check as fail-loud only
(today's behavior) and stop there — no auto-fix, just the branch-protection and pull_request-trigger
work in Phases 2-3 stand alone and are worth doing either way. This is a real fork in the plan and
should be confirmed at approval, not assumed.

### What "tightening the bypass" changes for you specifically

`enforce_admins: true` on `ai-101` means your own future pushes to `main` go through the same PR gate
as everyone else's — which is the explicit ask ("if I weren't an admin, we would've had to use a
branch/PR/merge anyway"). It does not add required reviews (`required_approving_review_count` stays
`0`, unchanged) and does not touch how anyone opens or merges a PR — only who can skip having one.
Reversible in seconds by any admin via the same API call, so it is not a hard lockout if CI itself is
ever the thing that's broken.

### Required-check scope: concrete for `ai-101`, conservative for `CentralRepo`/`UserRepo`

For `ai-101` I have direct evidence: `lint` and `handouts` together would have caught the actual
incident (the second via the Hugo build it already runs, once it's PR-triggered). Adding both as
required contexts is a precise fix for a measured gap.

For `CentralRepo` and `UserRepo` I do not have equivalent evidence — I know their real jobs
(`hugo-build`, `lint-and-validate` on `CentralRepo`; `run-analysis` (Lacework), `codex_review` on
`UserRepo`) but not their false-positive rates or whether the teams already treat them as advisory on
purpose. This plan closes the actual hole (`enforce_admins`) on all three and leaves the
which-checks-are-required question open for those two rather than guessing — see Open Questions.

### Not adding the tooling to `CentralRepo`'s `FILES_TO_COPY`

That would push `gen_handouts.py`, `lint_paths.py`, and the two workflows to all ~65 *existing* repos
on the next batch sync — every one of them, whether or not they will ever use `deploymentPaths`. Even
made inert (Phase 3), that is a materially bigger, unrequested blast radius than "make it available."
Putting the canonical copies in `UserRepo` means every *new* repo gets them for free, and an existing
repo that wants them opts in by copying from `UserRepo` or `ai-101` — exactly what this plan itself is
doing for `ai-101` → `UserRepo`. Flagged as an open question if the wider push is wanted later.

## Plan

### Phase 1 — `ai-101`: auto-fix stale handouts on PR, and make Hugo build failures visible pre-merge

- [x] P1.1. **Decision, confirm at approval**: mint a fine-grained PAT (`contents: write`, `ai-101`
      only) and store as a repo secret — or skip auto-fix and keep Phase 1 to just P1.3 (fail-loud PR
      gate). Default recommendation: mint the PAT.
- [x] P1.2. `path-lint.yml`'s `lint` job: before running `lint_paths.py`, run `gen_handouts.py`
      (not `--check`). If it produces a diff, commit and push to the PR's head ref using the PAT from
      P1.1, with a clear bot commit message. Then run `lint_paths.py` as today — it catches what
      auto-fix cannot (unclosed blocks, unknown path keys, nesting). Guard the push step on the secret
      actually being present and non-empty — this same file lands in `UserRepo` (Phase 4) without the
      PAT, and a repo with no `deploymentPaths` never produces a diff to push anyway (P3.1's no-op), but
      a future adopter who sets `deploymentPaths` before provisioning their own PAT must get a clear
      "stale, run `gen_handouts.py` locally" failure from the existing `--check`/`lint_paths.py` path,
      not an opaque git-auth error from a push attempt with an empty credential.
- [x] P1.3. Add `pull_request` to `handout-pdf.yml`'s `on:` block, mirroring `path-lint.yml`'s existing
      `paths:` filter. This is what makes a real Hugo build failure (the actual incident) visible
      before merge instead of after.
- [x] P1.4. Guard `handout-pdf.yml`'s expensive steps (image pull, Hugo build, Chrome PDF render)
      behind a cheap first step that exits clean when `gen_handouts.py --list-slugs` prints nothing —
      needed for Phase 4, where this same file lands in repos with no `deploymentPaths` at all.
- [x] P1.5. Verify end-to-end on a real throwaway PR: (a) hand-stale a handout, confirm the auto-fix
      commit lands and both checks go green afterward; (b) reproduce the original empty-`pathtab`
      defect, confirm `handouts` fails on the PR itself, pre-merge.

### Phase 2 — Close the admin bypass on `ai-101`, `CentralRepo`, `UserRepo`

- [ ] P2.1. `ai-101`: `enforce_admins: true`; `required_status_checks.contexts` becomes
      `["ci/jenkins/build-status", "lint", "handouts"]`.
- [ ] P2.2. `CentralRepo`: `enforce_admins: true`. Required-check contexts unchanged pending the Open
      Question below.
- [ ] P2.3. `UserRepo`: `enforce_admins: true`. Required-check contexts unchanged pending the Open
      Question below.
- [ ] P2.4. Verify: attempt a direct push to `ai-101`'s `main` post-change and confirm it is hard
      rejected, not warned-and-allowed.

### Phase 3 — Make the tooling safe to exist in a repo that hasn't opted in

- [x] P3.1. `gen_handouts.py`: missing/empty `deploymentPaths` becomes a clean no-op (log a line, exit
      0, write and delete nothing) instead of `SystemExit`.
- [x] P3.2. `lint_paths.py`: same, since it imports `PATHS` from `gen_handouts.py`.
- [x] P3.3. Regression-verify on `ai-101` itself (which always sets `deploymentPaths`): full local
      build, `lint_paths.py`, `gen_handouts.py --check` — all identical to pre-change behavior.
- [x] P3.4. Verify the no-op path directly against a `repoConfig.json` with no `deploymentPaths` key
      (e.g. `UserRepo`'s current one) — confirm exit 0, no crash, no files touched.

### Phase 4 — Propagate the opt-in tooling into `UserRepo`, inert by default

- [ ] P4.1. Copy `scripts/gen_handouts.py` + `scripts/lint_paths.py` (post-Phase-3) into `UserRepo`.
- [ ] P4.2. Copy `.github/workflows/path-lint.yml` + `.github/workflows/handout-pdf.yml` (post-Phase-1)
      into `UserRepo`.
- [ ] P4.3. Verify: build `UserRepo` as it stands today (no `deploymentPaths`) — both new workflows
      must short-circuit near-instantly and report success, not silently skip in a way that looks like
      a failed check.
- [ ] P4.4. Verify the opt-in path: temporarily add `deploymentPaths` and a `pathtabs` block to a
      throwaway page, confirm both workflows behave exactly as they do on `ai-101`, then revert the
      throwaway content — only the four tooling files stay.

### Phase 5 — Document the mechanism in `UserRepo`'s authoring guide

- [ ] P5.1. New page `content/02Hugo/7_printable_handouts/index.md` (Task 7, weight 70), matching the
      depth and style of `6_deployment_paths/index.md`: the problem (print CSS renders only the active
      tab, so a printed dual-path page silently drops one path), what each of the four files does, how
      to opt in (they already sit inert in every clone as of Phase 4), the CI freshness gate and what
      "stale" means, and `ai-101` linked as the one live example.
- [ ] P5.2. Cross-link from `6_deployment_paths/index.md`'s existing "don't hardcode your path list"
      gotcha and its Reference section.
- [ ] P5.3. One-line pointer added to `UserRepo/CLAUDE.md`'s Gotchas section.

### Phase 6 — Close out

- [ ] P6.1. `ai-101/CLAUDE.md`: promote — the empty-`pathtab` `errorf` is intentional, not a linter
      bug; the CI staleness gate and what now auto-fixes vs. still fails loud; the branch-protection
      change and its effect on direct pushes going forward.
- [ ] P6.2. Commit messages / each repo's own changelog convention carry the rest — `UserRepo` has
      `content/00ChangeLog`; check its existing format before adding an entry rather than guessing one.
- [ ] P6.3. `Status:` set to `Complete`.

## Implementation Method

**Two parallel tmux sessions, one per repo, each producing a normal branch → PR → merge** — `ai-101`
(Phases 1, 3) and `UserRepo` (Phases 3 copy-through, 4, 5), independent worktrees, no shared files.
Deliberately dogfoods the exact flow this plan is enforcing rather than hand-pushing the fix.

`CentralRepo`'s share (Phase 2 only, no file changes) and all three repos' Phase 2 API calls are direct
`gh api` calls, run inline after Phase 1 is merged and verified working on `ai-101` — flipping
`enforce_admins` before the new required checks are proven green would risk locking `main` behind a
check nobody has confirmed passes cleanly. Per global prefs, branch-protection changes get their own
go-ahead at that point even though the plan itself is approved here.

## Plan Changes
- 2026-08-20, `Proposed` → `Approved`. PAT approach confirmed for P1.1; `HANDOUT_AUTOFIX_PAT` created
  as a fine-grained PAT (`contents: write`, `ai-101` only, 90-day expiry) and stored as an `ai-101`
  repository secret — not on `CentralRepo` (repo secrets don't cascade across repos; there was no
  mechanism there for other repos to reach it anyway) and not on `UserRepo` (confirmed out of scope —
  no printing need there). P1.2 gained an explicit empty-secret guard, added before implementation
  started, per the note above.

## Files Changed
- `scripts/gen_handouts.py` — `load_paths()` returns `[]` instead of `SystemExit` on a missing/empty
  `deploymentPaths`; `main()` gained an early no-op return (log line, exit 0) when `PATHS` is empty.
- `.github/workflows/path-lint.yml` — `lint` job: checkout now pins `ref` to `github.head_ref` on PRs
  (`persist-credentials: false`); added "Regenerate handouts" (runs `gen_handouts.py`, detects a diff
  via `git status --porcelain`) and "Push regenerated handouts" (commits + pushes via
  `HANDOUT_AUTOFIX_PAT` over an explicit HTTPS URL, or reverts the working tree and no-ops if the
  secret is empty), both gated to `github.event_name == 'pull_request'`.
- `.github/workflows/handout-pdf.yml` — added a `pull_request` trigger (paths list mirrors the existing
  `push` list); added a "Check whether any deployment paths are configured" step (`id: paths`, based on
  `gen_handouts.py --list-slugs`) and gated every subsequent step behind
  `if: steps.paths.outputs.has_paths == 'true'`.
- `plans/0004_...md` — this file (checkboxes, verification results).

## Session Summary
Implemented and verified Phases 1 and 3 on branch `handout-ci-autofix`, PR
[#31](https://github.com/FortinetCloudCSE/ai-101/pull/31).

**Phase 3 (no-op tooling) verification:**
- `gen_handouts.py --check` and `lint_paths.py` unchanged on `ai-101` itself (which always sets
  `deploymentPaths`): "Handouts up to date (11 files)" / "lint_paths: clean (14 pages, handouts up to
  date)".
- Full CI-equivalent Hugo build: 42 pages, 15 non-page, 13 static, **0 WARN/ERROR** — matches the
  documented baseline exactly.
- No-op path verified directly against a scratch fixture built from
  `/home/ubuntu/pythonProjects/UserRepo/scripts/repoConfig.json` (no `deploymentPaths` key): default,
  `--check`, and `--list-slugs` modes of `gen_handouts.py`, plus `lint_paths.py`, all exit 0, write
  nothing, crash nothing.

**Phase 1 (CI auto-fix + pre-merge gate) verification — both done as real, not manufactured, incidents:**
- **P1.5(a)**: PR #30 ("update port", merged same day) removed content from the k8s `pathtab` on
  `content/05Security/1_lab/index.md` without regenerating `handout-k8s`, and merged anyway because
  `lint` failing isn't a required check pre-Phase-2 — confirmed via `gh pr view 30`
  (`"name":"lint","conclusion":"FAILURE"`), a live instance of the exact problem this plan targets.
  Merging `main` into `handout-ci-autofix` (commit `157b031`) picked up that drift; the `lint` job's new
  auto-fix step detected the diff, committed, and pushed via `HANDOUT_AUTOFIX_PAT` (commit `9aa2aa4`,
  message `chore: auto-regenerate stale handouts [handout-autofix]`). That PAT push retriggered PR
  checks (proving the `GITHUB_TOKEN`-doesn't-retrigger concern was correctly designed around) — both
  `lint` and `handouts` are green on the new head (runs `32416989029` / `32416989043`).
- **P1.5(b)**: throwaway PR [#32](https://github.com/FortinetCloudCSE/ai-101/pull/32), branched from
  `handout-ci-autofix` so the new workflow logic was in effect, reproduced the original incident shape
  by emptying the same k8s `pathtab` body. `handouts` failed pre-merge with the actual Hugo build error
  (`ERROR ... the "k8s" pathtab in this pathtabs block is empty ...`, run `32417227478`) — `lint` passed,
  as expected, since neither the auto-fix nor `lint_paths.py` validates non-empty tab bodies; only
  Hugo's own `errorf` catches it, which is exactly why P1.3 (running the real build on `pull_request`)
  is the fix. PR #32 closed unmerged and the throwaway branch deleted.

Plan stays `Approved` — Phase 2 (branch protection) and Phases 4/5 (`UserRepo` propagation) are
out of scope for this session and handled separately.

## Promotion
- [ ] `Decisions & Commentary` walked
- [ ] Durable facts promoted to `ai-101/CLAUDE.md` and `UserRepo/CLAUDE.md` — list them
- [ ] `Status:` set to `Complete`

## Follow-ups
- [ ] `ci/jenkins/build-status` is a no-op required check on all three repos (disabled stage,
      always-success `post` block). Left in place — out of scope here — but worth deciding whether to
      fix, repurpose, or remove.
- [ ] Whether `CentralRepo`'s `hugo-build`/`lint-and-validate` and `UserRepo`'s `run-analysis`
      (Lacework) / `codex_review` should become required checks, now that `enforce_admins` no longer
      lets a bad merge through some other way. Deliberately not decided in this plan — see Open
      Questions.
- [ ] Whether to eventually push the (by-then inert) tooling to all ~65 existing repos via
      `CentralRepo`'s `FILES_TO_COPY`, vs. leaving it opt-in-by-copy as this plan does.

## Risks / Open Questions

- **Open: PAT vs. check-only for Phase 1.** See Decisions above — confirm before P1.1.
- **Open: should `CentralRepo`/`UserRepo` gain new required-check contexts, and which ones?** Left
  unresolved on purpose — I don't have evidence on those checks' reliability the way I do for
  `ai-101`'s `lint`/`handouts`.
- Risk: a fine-grained PAT is a new credential to track and eventually rotate. Mitigation: scoped to
  `contents: write` on `ai-101` alone, nothing broader.
- Risk: `enforce_admins: true` could lock out an emergency fix if CI itself is broken. Mitigation:
  reversible in seconds by any admin via the same API call; not a hard lockout.
- Risk: adding `pull_request` to `handout-pdf.yml` roughly doubles its CI cost (paid at PR time and
  again at merge-to-main time instead of once). Accepted — the Hugo build itself is sub-second: the
  dominant costs are the Docker image pull and headless-Chrome PDF render, both fixed per run and small
  in absolute terms.
- Risk: Phase 4's inert-workflow guard (P1.4) is new, untested logic — a bug there could make a
  freshly-created workshop repo's CI silently pass without ever having checked anything. Mitigation:
  P4.3 verifies success is for the right reason (a real short-circuit), not an accidental no-op.

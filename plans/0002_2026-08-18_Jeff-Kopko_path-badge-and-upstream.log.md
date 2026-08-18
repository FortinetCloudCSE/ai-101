# Session Log: Synced-path badge + close out plan 0001's upstream follow-ups
Date: 2026-08-18
Owner: Jeff Kopko
Related Plan: plans/0002_2026-08-18_Jeff-Kopko_path-badge-and-upstream.md

Written because this work has blast radius outside `ai-101` (a CentralRepo `main` merge
rebuilds the prod image that ~12 workshop repos build against), it cannot finish in one
sitting (the WARN fix needs that rebuild), and several rejected options below are not
recoverable from the commits.

## Milestones
- [x] M0. Establish that no badge was ever implemented — the complaint is accurate
- [ ] M1. WS-A: `pathtabs` + badge, `errorignore`/`deploymentPaths`, `static.yml` split, **and
      author-facing docs** upstream in CentralRepo — the only copy of the shortcode anywhere
- [ ] M2. S2: CentralRepo `main` merged, prod image rebuilt, digest confirmed moved
- [ ] M3. WS-B: `ai-101` local `pathtab*.html` **deleted**, `deploymentPaths` added, badge live,
      doc corrections
- [ ] M4. WS-C: `k8s-101` path-lint trigger, `errorignore` effective, routing text, preflight
      blocks, re-verified at 0 WARN

Milestone order changed mid-session: M2 (the gate) moved ahead of both repo workstreams. See the
two Plan Changes entries — first the sequencing call, then the upstream-only mandate.

## Commentary Stream

### Session open — resuming plan 0001
- What I'm doing: verifying the state plan 0001 left behind before adding to it.
- Notes: everything from 0001 is merged and live; `main` == `jkopkoEdits` in both repos, no
  worktrees, no tmux sessions, no open PRs. The one open follow-up was the PR-only
  `path-lint.yml` trigger, so I wrote the `push: branches: [main]` addition in both repos
  before the badge work was even scoped. Both linters pass; YAML parses with both triggers.
- Decision: duplicate the `paths:` list rather than use a YAML anchor — GitHub Actions does
  not expand anchors.

### Exploration — three parallel agents
- What I'm doing: mapping `ai-101`'s pathtabs feature, CentralRepo's theme/template plumbing,
  and the exact `k8s-101` WARN, concurrently.
- Why: the badge question and all four follow-ups touch different layers of the same stack,
  and none of it was in context.
- Notes / findings, in order of how much they changed the plan:
  1. **There is no badge, and never was.** No `badge`/`chip`/`pill`/`locked` string anywhere in
     `ai-101`'s content or layouts; no `assets/`, no `static/`, zero CSS or JS in the repo.
     What plan 0001 called "the badge" is a `pathtabs` block whose `.tab-nav-title` reads
     "Your path" plus bold prose inside the panel. It renders identically to the 16 ordinary
     `Command`/`Expected Output` tab groups on the same pages.
  2. **The prod image bakes CentralRepo from `#main`** (`Dockerfile:61`), and workshop CI pulls
     that image from ECR. So upstream-only changes are invisible to published sites until
     `image-build-push-prod.yaml` reruns. This is what forced the badge into the shortcode.
  3. **`local_copy.sh:3-4` makes a repo-local shortcode shadow the upstream one** — a
     non-recursive `cp` that overwrites same-named CentralRepo files. Upstreaming `pathtabs`
     alone would change nothing for `ai-101`; deleting the local copy early would break it.
  4. `switchTab()` persists to `localStorage` only on a real click (it reads the implicit
     global `event`, `theme.js:120`). Directly relevant: it rules out a badge that drives tab
     state.
  5. The k8s WARN is fixable upstream after all. Relearn's `urlErrorReport.gotmpl:5` honors
     `site.Params.errorignore`; `hugo.jinja` has simply never emitted it.
- Two claims in the repos' own docs turned out to be wrong about mechanism:
  - `format-print.css:163-176` is cited in `ai-101/CLAUDE.md:113-114` and
    `gen_handouts.py:8,275` as the rule hiding non-active tab panels. It only sets print
    colors. The hiding is `theme.css:2659-2673`, which applies in print because nothing
    overrides `display` there. The handout generator's *conclusion* was right, its cited
    cause wasn't — worth fixing so the next reader doesn't go looking in the wrong file.
  - `k8s-101/CLAUDE.md:120` says relearn warns "unconditionally" on a local menu `url`. It
    gates on `params.link.errorlevel`, which `hugo.jinja:205` sets from `repoConfig.json`.
- Notes: the WARN had never been captured verbatim in either repo. It is now:
  `config option 'url' "k8s-101.pdf" for 'menu' entry "<i class='fas fa-graduation-cap'></i>
  Workshop PDF" is a local URL; if it references a page or a resource use 'pageRef' instead`.

### Recon — CentralRepo write access and branch shape
- Notes: admin on the repo; `main` requires only `ci/jenkins/build-status`, 0 approvals,
  `strict: false`. The local checkout sits on `prreviewJune23`, **4 commits behind
  `origin/main`** — so new work branches off `origin/main`. Recent PRs all merge a long-lived
  `prreviewJune23` into `main`, which is also the branch the *dev* image builds from
  (`Dockerfile:24`), giving a real pre-merge test path via `image_variant: dev`.

### Direction change — upstream-only, and documentation as a deliverable
- What I'm doing: reworking the plan so CentralRepo holds the *only* copy of `pathtabs`, and so
  the session's how-to knowledge lands in CentralRepo docs rather than only in plan files.
- Why: Jeff's call — "DO NOT finalize with a local shortcode in only ai-101 repo."
- Notes: he is right, and the reason is specifically `local_copy.sh:3-4`. A hand-synced copy is
  not merely redundant here; the local one *wins silently*, so the moment the two drift the
  upstream fix stops being the thing that renders and nothing tells you. Two nastier consequences
  I had underweighted:
  1. Deleting the local copy is a wholesale implementation **swap**, not an additive change. Every
     difference between `ai-101`'s version and the upstream one lands in one commit. That drove a
     verification change (B4 now checks unchanged behaviors, not just the new banner).
  2. A global shortcode must not carry `ai-101`'s vocabulary. Its inline `docker`/`k8s` default and
     hardcoded `groupid "deploy-path"` were fine in one repo and are traps upstream — another
     workshop would silently inherit `ai-101`'s paths. Both become parameters, and a missing
     `deploymentPaths` becomes an `errorf`. That in turn forces `deploymentPaths` into `ai-101`'s
     `repoConfig.json` in the same commit as the deletion.
- Cost, recorded honestly: the plan loses all its front-end parallelism and its one property that
  produced a visible result quickly. Wall-clock goes from `max(A,B) + rebuild + C` to
  `A + rebuild + max(B,C)`.

### Recon — CentralRepo branch shape, corrected
- What I'm doing: verifying which branch is actually "dev" before planning a test path.
- Notes: `prreviewJune23` is dev, confirmed in two independent places
  (`image-build-push-dev.yaml:6` trigger, `Dockerfile:24` `ADD …#prreviewJune23`). Jeff's
  recollection was right. But the branch topology is a trap:
  - `prreviewJune23` is **4 commits behind `origin/main`** (2026-07-16 vs 2026-07-20).
  - `prreviewJuly23` sounds newer and is a decoy: 13 behind `main`, last commit **2026-06-11**,
    referenced by no workflow and no Dockerfile stage.
  So the published dev image is not a superset of prod, and testing a main-bound change by pushing
  to `prreviewJune23` would publish an image carrying 4 commits of unrelated staleness. That kills
  the `image_variant: dev` verification idea and leaves `LOCAL=true` as the only honest pre-merge
  test. Recorded in the plan under WS-A rather than left as tribal knowledge.
- Also: CentralRepo is already in `python.code-workspace:4`, so no workspace change needed.

## Commands (high-level)
- `git log/status/rev-list` across `ai-101`, `k8s-101-workshop`, `CentralRepo` — confirm 0001's
  end state and how far the local CentralRepo branch has drifted
- `gh api repos/FortinetCloudCSE/CentralRepo{,/branches/main/protection}` — write access and
  required checks before planning any upstream change
- `python3 -c "import yaml; ..."` + `python3 scripts/lint_paths.py` (both repos) — validate the
  `path-lint.yml` push trigger parses and neither linter regresses
- `docker run -d -v "$PWD:/home/UserRepo:ro" fortinet-hugo:latest build` — reproduce CI exactly
  and capture the literal WARN. Read-only mount is safe: `local_copy.sh` only copies *out* of
  the repo
- `docker build --build-arg LOCAL=true --target dev -t hugotester-local .` (planned, A6) — the
  only way to test CentralRepo edits before merging to `main`

## Dead-ends / Rejected Options
- Option: put the badge CSS in CentralRepo's `layouts/partials/custom-header.html` (the
  obvious home — it is the one site-wide `<style>` block, already in `<head>`, no FOUC).
  - Why rejected: it would not appear on any published site until the prod image rebuilt, and
    the whole complaint is that nothing is visible *now*.
  - Lesson learned: in this estate "where does CSS belong" is a *deployment* question, not a
    styling one. The answer depends on which artifact carries the file to the build.
- Option: ship the CSS repo-local via `ai-101/layouts/partials/custom-header.html`.
  - Why rejected: `local_copy.sh:4` copies `layouts/partials/*` too, so this silently replaces
    CentralRepo's 715-line header — losing every Fortinet color token, the support widget and
    the video header. Catastrophic, and it would look like a CSS bug.
  - Lesson learned: repo-local `partials/` overrides are whole-file, not additive. Only
    `shortcodes/` is safe to add to freely.
- Option: a YAML anchor to share the `paths:` list between the two `path-lint.yml` triggers.
  - Why rejected: GitHub Actions does not expand YAML anchors. Duplicated with a comment
    saying why.
- Option: fix the k8s WARN with `pageRef` (what the warning itself suggests, and what plan
  0001 tracked).
  - Why rejected: the target is `k8s-101.pdf`, a non-page file — `pageRef` resolves pages.
    `errorignore` is one jinja line plus a schema key and actually applies.
  - Lesson learned: the remediation a tool suggests in its own warning text is not always the
    one that fits the case.
- Option: add a print rule un-hiding non-active tab panels, so PDFs stop dropping content.
  - Why rejected: for `pathtabs` printing both panels is actively wrong — showing a reader
    both the Docker and the Kubernetes steps is the exact failure the per-path handouts exist
    to prevent. Separate question, separate blast radius.
- Option: keep a hand-synced copy of `pathtabs.html` in `ai-101` alongside the upstream one, so
  the badge ships on the *current* prod image instead of waiting for a rebuild. This is what the
  plan said until Jeff overruled it.
  - Why rejected: `local_copy.sh:3-4` makes the local copy win silently, so drift is not a
    cosmetic duplication problem — it is a "the upstream fix you just merged does nothing and
    nothing tells you" problem. A comment and a follow-up checkbox are not a synchronization
    mechanism.
  - Lesson learned: "ships sooner" was doing a lot of work in that decision, including propping up
    the choice to emit CSS/JS from inside the shortcode. When the deadline pressure was removed the
    in-shortcode decision still held (self-containment, clobber-safety) but for different reasons
    than originally written down — worth noticing when a rationale outlives its argument.
- Option: verify the CentralRepo changes by pushing to `prreviewJune23` and using the published
  dev image (`image_variant: dev`).
  - Why rejected: that branch is 4 commits behind `main`, so the resulting image would differ from
    the eventual prod image in ways unrelated to this change. `LOCAL=true` builds from the working
    tree and is exact.
- Option: push `ai-101`'s `static.yml` upstream verbatim, as plan 0001's follow-up worded it.
  - Why rejected: `ai-101` has no Dockerfile and pulls the image from ECR; CentralRepo's own
    workflow builds it with `docker build --target=prod`. Verbatim would break CentralRepo's
    build. Split the roles instead — `scripts/static.yml` as the template, which
    `update_scripts.sh:14` already assumed.
  - Lesson learned: that follow-up was written without noticing the file has two jobs.

## Risks & Mitigations
- Risk: a CentralRepo `main` merge auto-republishes the image all ~12 workshop repos build
  against — blast radius far wider than the two repos in this plan.
  - Mitigation: verify with the local `LOCAL=true` dev image first (A6), and prefer the
    `image_variant: dev` dispatch over a speculative main merge.
- Risk: reporting `k8s-101` as 0 WARN on the strength of the `repoConfig.json` edit, before the
  image carries the `hugo.jinja` change that reads the key.
  - Mitigation: WS-C's stated end state is "1 WARN, fix staged". M4 is a separate milestone.
- Risk: ~~`ai-101`'s local and upstream `pathtabs.html` drift apart~~ — eliminated, not mitigated.
  Upstream-only means there is no second copy. This is the clearest argument for Jeff's call: the
  previous mitigation was "remember to copy it verbatim", which is not a mitigation.
- Risk: nothing user-visible ships until the prod image rebuilds, since the local-copy escape
  hatch is gone.
  - Mitigation: A6's `LOCAL=true` build renders the badge locally, so it is demonstrable by
    screenshot pre-merge; `image-build-push-prod.yaml` is manually dispatchable if the push
    trigger misfires.
- Risk: `ai-101` `main` moves mid-PR (Robert pushes directly; it moved twice during plan 0001).
  - Mitigation: merge forward and rebuild before merging. Do not read a pending
    `Lacework (IAC)` / `UNSTABLE` as a failure — the only required check is
    `ci/jenkins/build-status`.
- Risk: C3/C4 are prose describing lab steps; a subagent can produce fluent but wrong commands.
  - Mitigation: draft-then-review. No auto-commit on those two items.

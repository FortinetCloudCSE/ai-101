# Plan: Synced-path badge + close out plan 0001's upstream follow-ups
Date: 2026-08-18
Owner: Jeff Kopko
Slug: path-badge-and-upstream
Status: Proposed
Supersedes: none
Superseded-By: none
Plan File: plans/0002_2026-08-18_Jeff-Kopko_path-badge-and-upstream.md
Log File: plans/0002_2026-08-18_Jeff-Kopko_path-badge-and-upstream.log.md

**Cross-repo plan.** Master copy lives here because it closes plan `0001`'s follow-ups, but
the work spans three repos: `ai-101`, `CentralRepo`, `k8s-101-workshop`.

## Goal

- Give the deployment-path tab groups a **visible** indicator that the choice is locked and
  synced site-wide. Today there is none: `pathtabs` renders as a plain relearn tab bar,
  visually identical to the 16 ordinary `Command`/`Expected Output` groups on the same pages.
- Close every remaining follow-up from plan `0001` that is not a deliberate deferral:
  upstream `pathtabs`, upstream the improved `static.yml`, and kill `k8s-101-workshop`'s last
  build WARN via `errorignore` support in `hugo.jinja`.
- Land two `k8s-101-workshop` content items previously deferred by decision: the
  beginner/experienced routing text, and preflight verify blocks on the hands-on pages.

## Context / Links

- Predecessor: `plans/0001_2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.md` (`Complete`)
- Sibling: `k8s-101-workshop/plans/0001_2026-08-17_Jeff-Kopko_path-lint-prevention.md` (`Complete`)
- Shipped in 0001: `ai-101` PRs #16/#17/#18, `k8s-101-workshop` PRs #104/#105
- Related code paths:
  - `ai-101/layouts/shortcodes/pathtabs.html`, `pathtab.html`
  - `CentralRepo/layouts/shortcodes/`, `CentralRepo/scripts/templates/hugo.jinja`,
    `CentralRepo/scripts/repoConfig.schema.json`, `CentralRepo/scripts/batch_repo_update.py`,
    `CentralRepo/scripts/static.yml`, `CentralRepo/.github/workflows/static.yml`
  - `CentralRepo/themes/hugo-theme-relearn/layouts/partials/shortcodes/tabs.html:61-89` (DOM)
  - `CentralRepo/themes/hugo-theme-relearn/assets/js/theme.js:94-171` (`switchTab`,
    `restoreTabSelections`)
  - `k8s-101-workshop/scripts/repoConfig.json:13-19` (the WARN source)

## Constraints / Assumptions

- **CentralRepo changes do not reach workshop CI until the prod image is rebuilt.**
  `Dockerfile:61` does `ADD https://github.com/FortinetCloudCSE/CentralRepo.git#main
  /home/CentralRepo`, and workshop `static.yml` pulls
  `public.ecr.aws/k4n6m5h8/fortinet-hugo:latest`. `image-build-push-prod.yaml` triggers on
  push to `main`, so the rebuild is automatic — but it is a second hop with its own latency.
  Anything that must ship *today* has to ship repo-local.
- **A workshop repo's local shortcode shadows the upstream one.**
  `CentralRepo/scripts/local_copy.sh:3-4` does a non-recursive `cp ../UserRepo/layouts/shortcodes/*
  layouts/shortcodes`, overwriting same-named CentralRepo files. So upstreaming `pathtabs`
  alone changes nothing for `ai-101` until its local copy is deleted — and deleting it early
  breaks the site until the image rebuilds.
- **No SCSS pipeline exists.** Relearn 8 is plain CSS; `assets/css/theme-*.css` are
  per-`themeVariant` and only one applies per workshop. There is no `_custom.scss` hook.
- **`layouts/partials/custom-header.html` is a trap for repo-local CSS.** `local_copy.sh:4`
  copies `layouts/partials/*` too, so an `ai-101` copy would silently replace CentralRepo's
  715-line header. Repo-local CSS must not go there.
- Relearn's tab identity is the **anchorized title text** (`tabs.html:42`), not an index, and
  cross-page sync is `localStorage[absBaseUri + '/tab-selections']` keyed by `data-tab-group`
  (`theme.js:145-153`). `pathtabs.html:29` hardcodes `groupid: "deploy-path"`.
- `switchTab()` only persists on a real click — it reads the implicit global `event`
  (`theme.js:120`). Programmatic calls save nothing. Therefore the badge must **observe**
  state, never drive it.
- `batch_repo_update.py` has `BRANCH = "main"` and pushes directly to each target repo's
  `main`, no PR. Its `REPOS = ['']` is an empty placeholder — it only runs when an operator
  fills it in. We are not running it.
- Assumption: nobody else is mid-flight in these three repos. `ai-101` `main` is actively
  pushed to by Robert Reris, so expect it to move during the PR window (it moved twice during
  plan 0001's merge).

## Plan

### WS-A — CentralRepo (upstream). Branch off `origin/main`, not the local `prreviewJune23` (4 commits behind).

- [ ] A1. Add `layouts/shortcodes/pathtabs.html` + `layouts/shortcodes/pathtab.html`,
      upstreamed from `ai-101` and extended with the badge. Badge design (approved):
      a banner above the tab nav reading `🔒 Your path: <NAME>` + `Locked in — every lab page
      follows this choice.`, where `<NAME>` is **live text** that updates on switch.
      - CSS and JS are emitted **by the shortcode itself**, once per page, guarded with
        `.Page.Store`. Rationale under Decisions.
      - JS is a `MutationObserver` on `.tab-panel[data-tab-group="deploy-path"]` watching
        `class` changes on `.tab-nav-button`; it reads the active button's text and writes it
        into the banner. No wrapping of `switchTab`, no writes to `localStorage`.
      - Degrades to the server-rendered first-tab name with JS off.
      - `@media print` hides the banner — handouts flatten `pathtabs` in markdown, so the
        banner would be noise on paper.
- [ ] A2. `scripts/templates/hugo.jinja`: emit two new optional params inside `[params]`,
      before `[params.include]` at `:201`.
      - `errorignore` (list of regexes) — relearn's `urlErrorReport.gotmpl:5` already honors
        `site.Params.errorignore`; nothing in CentralRepo has ever emitted it.
      - `deploymentPaths` — makes the `pathtabs` path vocabulary repo-configurable instead of
        relying on the shortcode's hardcoded `docker`/`k8s` fallback.
- [ ] A3. `scripts/repoConfig.schema.json`: add `errorignore` and `deploymentPaths`.
      Required — `additionalProperties: false` at `:6` means an unlisted key fails validation.
- [ ] A4. Split the two roles of `static.yml` (approved option):
      - Make `scripts/static.yml` the canonical workshop template and put `ai-101`'s
        improvements in it: ECR pull with exponential backoff, `trap cleanup EXIT`, capture
        `docker wait` status, echo `docker logs`, fail with `::error::` on non-zero,
        `image_variant` prod/dev input.
      - Point `batch_repo_update.py:19` at `scripts/static.yml` instead of
        `.github/workflows/static.yml`.
      - Leave `.github/workflows/static.yml` as CentralRepo's own build (it uses
        `docker build --target=prod` against its own Dockerfile; `ai-101` has no Dockerfile,
        so the two cannot be one file).
- [ ] A5. `RELEASE_NOTES.md` entry — every recent CentralRepo commit has one.
- [ ] A6. Verify locally: `docker build --build-arg LOCAL=true --target dev -t hugotester-local .`
      (`Dockerfile:14-15`), then build both workshop repos against that image and diff the log
      against each repo's known-good baseline.

### WS-B — ai-101

- [ ] B1. Commit the already-written `push: branches: [main]` trigger in
      `.github/workflows/path-lint.yml` (closes 0001's cheapest open follow-up; the gap was
      proven live by Robert's `d512c5c`).
- [ ] B2. Update the local `layouts/shortcodes/pathtabs.html` to the A1 version, byte-identical
      to upstream. This is what actually ships the badge — it works on the current prod image
      and does not wait on the rebuild.
- [ ] B3. Correct two documented-but-wrong mechanism claims. `CLAUDE.md:113-114` and
      `scripts/gen_handouts.py:8,275` both cite `format-print.css:163-176` as the rule that
      hides non-active tab panels. It is not — that block only sets print colors. The hiding is
      `theme.css:2659-2673` (`.tab-content{display:none}` / `.tab-content.active{display:block}`),
      which applies in print because nothing overrides `display` there. The conclusion the
      handout generator draws is right; the cited cause is wrong.
- [ ] B4. Verify: `python3 scripts/lint_paths.py`, `python3 scripts/gen_handouts.py --check`,
      container build (baseline: 42 pages, **0 WARN**), and grep the rendered HTML to confirm
      the banner is present on all 6+ `pathtabs` blocks and absent from `index.print.html`.
      Handouts should need no regeneration — `gen_handouts.py` flattens from markdown source,
      so shortcode markup never reaches them. Confirm via `--check`, do not assume.
- [ ] B5. `CLAUDE.md`: record the badge, the local-copy-shadows-upstream rule, and the
      "delete the local copies once the prod image carries them" trigger.
- [ ] B6. PR → `main`.

### WS-C — k8s-101-workshop

- [ ] C1. Commit the already-written `push: branches: [main]` trigger in `path-lint.yml`.
- [ ] C2. Add `errorignore` to `scripts/repoConfig.json` targeting the Workshop PDF shortcut.
      **Inert until A2 lands on CentralRepo `main` and the prod image rebuilds** — the key is
      simply dropped by the current `hugo.jinja`. Land it anyway so the WARN clears itself on
      the next image refresh; state the sequencing plainly rather than claiming a fix.
- [ ] C3. Fix the beginner/experienced routing text whose section numbers do not match the
      actual nav. Report the proposed wording for review before committing — this is content
      judgment, not a mechanical edit.
- [ ] C4. Add preflight verify blocks to the hands-on pages. Same rule: propose before
      committing, and every command must be lab-accurate.
- [ ] C5. Verify: `python3 scripts/lint_paths.py`, container build. Expect 48 pages and **1
      WARN before** the image rebuild, **0 after**. Do not report the WARN as fixed on the
      strength of the repoConfig edit alone.
- [ ] C6. PR → `main`.

### Sync points

- [ ] S1. A1 → B2. The shortcode is authored once in WS-A and copied verbatim into `ai-101`.
      Byte-identical, or the local copy silently diverges from upstream forever.
- [ ] S2. A2 + merge to CentralRepo `main` → prod image rebuild → re-run `k8s-101-workshop`'s
      build to confirm 0 WARN. This is the only step that cannot complete in one sitting.

## Implementation Method

**Workflow fan-out, then inline review.** WS-A, WS-B and WS-C touch three different repos with
one real dependency (S1), so wall-clock is the slowest branch rather than the sum. Each
workstream gets its own branch in its own repo; no worktree isolation needed since the
concurrency is across repos, not within one.

Two carve-outs:
- A1's shortcode is authored **first and once**, because B2 is a verbatim copy of it.
- C3 and C4 are content judgment. Agents draft; every diff is reviewed inline before any PR
  opens. No auto-commit of prose that describes lab steps.

## Plan Changes
- (none)

## Decisions & Commentary

- **Badge CSS+JS live inside the shortcode, not in `custom-header.html`/`custom-footer.html`.**
  Three reasons, in order of weight: (1) a shortcode is copied into the build by
  `local_copy.sh`, so it ships on the *current* prod image — a `custom-header.html` edit
  upstream would not appear until the image rebuilds; (2) a repo-local
  `layouts/partials/custom-header.html` would clobber CentralRepo's 715-line one, which is a
  much worse failure than a little inline CSS; (3) one file is the single source of truth for
  both repos instead of markup upstream + styling somewhere else.
  Accepted cost: a `<style>`/`<script>` pair mid-`<body>`, emitted once per page via a
  `.Page.Store` guard.
- **The badge observes, it never drives.** `switchTab()` persists to `localStorage` only when
  invoked from a real click, because it reads the implicit global `event` (`theme.js:120`). A
  badge that called `switchTab` programmatically would silently fail to persist, and one that
  wrote `localStorage` itself would duplicate the theme's contract. A `MutationObserver` on
  `.active` sees both clicks and `restoreTabSelections()` on load, with no coupling.
- **Live text over a static chip.** A static "synced" chip says the group is special but not
  *what* is selected; the whole complaint is that the locked choice is invisible. Naming it —
  and updating the name on switch — is the part that carries information.
- **`errorignore` over `pageRef` for the k8s WARN.** `errorignore` is a one-line jinja
  addition plus a schema key. `pageRef` needs a shape change to `menu.shortcuts` and would not
  even apply cleanly here: the target is `k8s-101.pdf`, a non-page file, not a page. The
  `pageRef` follow-up from plan 0001 stays open as a separate nice-to-have.
- **`scripts/static.yml` becomes the canonical template; CentralRepo's own workflow stays put.**
  One file cannot serve both roles: CentralRepo builds the image from its own Dockerfile,
  workshop repos pull it from ECR and `ai-101` has no Dockerfile at all. `scripts/static.yml`
  already exists and `update_scripts.sh:14` already treats it as the template — pointing
  `batch_repo_update.py:19` at it removes an inconsistency rather than inventing a convention.
- **Dead AKS references stay deferred**, per decision, even though the other two `k8s-101`
  content deferrals are being picked up in this plan.
- **Not touching the print CSS to un-hide tab panels.** Tempting, since only the active panel
  reaches the PDF — but for `pathtabs` specifically, printing both panels is *wrong*: that is
  exactly what the per-path handouts exist to avoid. Fixing it for ordinary tab groups is a
  separate question with its own blast radius.

## Files Changed
- (none yet)

## Session Summary
- (write at end)

## Promotion
- [ ] `Decisions & Commentary` walked
- [ ] Durable facts promoted to `CLAUDE.md` — list them: <...>
- [ ] `Status:` set to `Complete`

## Follow-ups
- [ ] Delete `ai-101`'s local `layouts/shortcodes/pathtab*.html` once the prod image carries
      the upstream copies — until then the local copy shadows upstream and both must move
      together.
- [ ] Once upstream `pathtabs` is live, drop the "copy from `ai-101`" pointer in
      `k8s-101-workshop/CLAUDE.md` and fill in its `PATH_KEYS` (carried from that repo's plan
      0001). Do **not** re-enable `PATH_TITLE_RE` there — it matches two ordinary tab titles.
- [ ] `pageRef` support for `menu.shortcuts` in `hugo.jinja` — still open, still a nice-to-have,
      no longer blocking anything now that `errorignore` exists.
- [ ] Roll `pathtabs` out to the other four workshop repos once it is upstream
      (`faig-training-workshop`, `fortiweb-api-mcp-protection`, `AWS-FGT-301`,
      `Public-Cloud-104-CNAPP`).
- [ ] `k8s-101-workshop`: dead AKS references — still deferred by decision.
- [ ] Reconsider AKS as an `ai-101` path once someone can validate it on a real cluster.

## Risks / Open Questions

- **`k8s-101-workshop`'s WARN does not go to zero in this plan's own timeframe.** It needs the
  CentralRepo merge *and* the prod image rebuild. The honest end state for WS-C is "1 WARN,
  fix staged" until S2 completes.
- **A CentralRepo `main` merge auto-rebuilds and republishes the prod image every workshop repo
  builds against.** That is the intended mechanism, but the blast radius of A1–A4 is all ~12
  repos, not just these two. Verify with the local `LOCAL=true` dev image first (A6), and
  prefer the `image_variant: dev` dispatch path over a speculative main merge.
- **`ai-101` `main` moves under us.** Robert pushes to it directly. Also `Lacework (IAC)`
  routinely sits pending 10–20 min and holds `mergeStateStatus` at `UNSTABLE` while the only
  *required* check is `ci/jenkins/build-status` — do not read `UNSTABLE` as failure.
- **Mid-`<body>` `<style>`/`<script>` from a shortcode.** Works (goldmark `unsafe = true`,
  `hugo.jinja:72`) and the block is `{{< >}}` so its output is not markdown-processed, but it
  is not pretty. If it causes trouble, the fallback is a CentralRepo-only `custom-header.html`
  rule, which costs the ship-today property.
- Open: does any other workshop repo already define a `deploymentPaths` param or a
  same-named shortcode that A1 would collide with? Checked `pathtabs` (only `ai-101`); worth a
  sweep for `deploymentPaths` before A2.

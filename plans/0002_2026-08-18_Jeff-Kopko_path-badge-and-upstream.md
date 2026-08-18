# Plan: Synced-path badge + close out plan 0001's upstream follow-ups
Date: 2026-08-18
Owner: Jeff Kopko
Slug: path-badge-and-upstream
Status: Approved
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

Checkout is at `~/pythonProjects/CentralRepo` and already in the VS Code workspace (`python.code-workspace:4`).

**Branch facts, verified 2026-08-18 — the naming is actively misleading:**
`prreviewJune23` **is** the dev branch (`image-build-push-dev.yaml:6` triggers on it *and*
`Dockerfile:24` bakes `#prreviewJune23` into the dev stage), and the local checkout sits on it.
But it is **4 commits behind `origin/main`** (last commit 2026-07-16 vs main's 2026-07-20), so it
is *not* a superset of prod. `prreviewJuly23` looks newer and is a decoy: 13 behind `main`, last
commit 2026-06-11, referenced by no workflow and no Dockerfile stage. Consequences: (1) branch off
`origin/main`; (2) pushing to `prreviewJune23` to test would publish a dev image whose CentralRepo
is 4 commits stale in unrelated ways, so `LOCAL=true` is the real verification path, not the dev
image (A6).

- [ ] A1. Add `layouts/shortcodes/pathtabs.html` + `layouts/shortcodes/pathtab.html`,
      upstreamed from `ai-101` and extended with the badge. **This is the only copy that will
      exist anywhere** — `ai-101`'s local files are deleted in B2, so this must be a functional
      superset of them, not a lookalike. Deleting the local copy swaps implementations wholesale.
      Two changes from `ai-101`'s version, both required to make it genuinely global:
      - `groupid` becomes a parameter, `(.Get "groupid" | default "deploy-path")`. Hardcoding
        `deploy-path` was fine in one repo; upstream it prevents a workshop from having two
        independent locked choices, and bakes `ai-101`'s vocabulary into a shared component.
      - **No hardcoded `docker`/`k8s` fallback.** `ai-101`'s version defaults the vocabulary
        inline; upstream that is a booby trap — another repo would silently get `ai-101`'s paths.
        `errorf` instead, naming `deploymentPaths` in `repoConfig.json`. Hard-failing the build is
        consistent with what the shortcode already does for a missing/duplicate path, and it is
        why B2 must add `deploymentPaths` to `ai-101`'s `repoConfig.json` in the same PR.
      Badge design (approved):
      a banner above the tab nav reading `🔒 Your path: <NAME>` + `Locked in — every lab page
      follows this choice.`, where `<NAME>` is **live text** that updates on switch.
      - Markup: `pathtabs.html` wraps the existing `partial "shortcodes/tabs.html"` call in
        `div.pathlock` and prepends `div.pathlock__banner`. The theme partial is untouched.
      - **Stop passing `title` through to the theme partial.** The authored title becomes the
        banner's label instead, otherwise "Your path" renders twice (banner + relearn's
        `.tab-nav-title`). The partial already emits `&#8203;` for an empty title
        (`tabs.html:65`), so nav layout is preserved.
      - CSS and JS are emitted **by the shortcode itself**, once per page, guarded with
        `.Page.Store`. Rationale under Decisions.
      - JS: one delegated handler for **all** `.pathlock` blocks on the page (each finds its own
        `.tab-panel[data-tab-group]` sibling), rather than a per-`groupid` selector — required now
        that `groupid` is a parameter. A `MutationObserver` per block, watching
        `class` on `.tab-nav-button`, **plus an initial read at install time**. The initial read
        is not optional — `restoreTabSelections()` (`theme.js:1835`) may already have run, and
        the observer cannot see a mutation that happened before it was installed. Together they
        cover both orderings. No wrapping of `switchTab`, no writes to `localStorage`.
      - Accent color: `rgba(var(--theme-color), …)`. `--theme-color` is a raw `r,g,b` triplet
        set per `themeVariant` by CentralRepo's `assets/css/theme-*.css`, so the banner picks up
        the right brand color in all 9 variants with no `color-mix` and no per-variant rules.
        For `ai-101` (`themeVariant: Workshop`) that resolves to Fortinet red `218,41,28`.
      - Icon: `<i class="fa-fw fas fa-lock">`. FontAwesome is vendored in the theme
        (`assets/fonts/fontawesome/webfonts/fa-solid-900.woff2`) and the theme itself uses
        `fas fa-home`, so no new dependency.
      - `aria-live="polite"` on the live value so a screen reader announces the switch.
      - Degrades to the server-rendered first-tab name with JS off (Hugo marks `$idx == 0`
        active, so the static text always matches what is displayed).
      - `@media print` hides the banner — handouts flatten `pathtabs` in markdown, so it would
        be noise on paper.
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
      **`LOCAL=true` is the only viable pre-merge test** — see the branch note below. Do not try
      to verify via a `image_variant: dev` dispatch.
- [ ] A7. **Author-facing documentation — a deliverable, not a nicety.** A shared component no
      other workshop author can discover is not actually shared.
      - `README.md`, new `### pathtabs / pathtab` under `## Shortcodes and usage` (:52), matching
        the existing per-shortcode format (`### figure`, `### quizframe`, …): what it is, a
        complete copy-pasteable example, the `deploymentPaths` prerequisite, the `groupid`
        parameter, the cross-page sync behavior, and the print behavior.
      - `README.md`, `## Site params referenced` (:155): add `deploymentPaths` and `errorignore`.
      - `README.md`, `## Notes & gotchas` (:172): document the `local_copy.sh` shadowing rule —
        a repo-local `layouts/shortcodes/<name>.html` **overrides** CentralRepo's silently, and a
        repo-local `layouts/partials/custom-header.html` **replaces** CentralRepo's 715-line one
        wholesale (losing every brand token and the support widget). This is not written down
        anywhere today and it is the single easiest way for an author to break their site while
        believing they added something.
      - `CLAUDE.md`: this session's durable mechanism facts — the two-hop deploy path
        (edit → merge `main` → prod image rebuild → workshop CI picks it up), `dev` =
        `prreviewJune23` in two places while `prreviewJuly23` is a decoy, `static.yml`'s two
        roles and the A4 split, `errorignore` vs `pageRef`, and the corrected
        `theme.css:2659-2673` citation for non-active tab-panel hiding.

### WS-B — ai-101. **Gated on S2 — same hard gate as WS-C.**

- [ ] B1. Commit the already-written `push: branches: [main]` trigger in
      `.github/workflows/path-lint.yml` (closes 0001's cheapest open follow-up; the gap was
      proven live by Robert's `d512c5c`).
- [ ] B2. **Delete** `layouts/shortcodes/pathtabs.html` and `layouts/shortcodes/pathtab.html`.
      Upstream-only: no local copy, no hand-synced duplicate. Deleting is what makes the A1
      version take effect — until then `local_copy.sh:3-4` shadows it.
      In the same commit, add `deploymentPaths: ["docker", "k8s"]` to `scripts/repoConfig.json`,
      because the upstream shortcode `errorf`s rather than defaulting (A1). The two edits are
      inseparable: deleting without adding hard-fails the build; adding without deleting is inert.
      Cross-check the vocabulary against `gen_handouts.py`'s `PATHS` and `lint_paths.py`'s
      `PATH_KEYS` — three places now agree on `docker`/`k8s` and must keep agreeing.
      Note `path-lint.yml` triggers on `layouts/shortcodes/pathtab*.html`, so this deletion
      itself fires the linter. Intended: it proves the linter still passes with no local copy.
- [ ] B3. Correct two documented-but-wrong mechanism claims. `CLAUDE.md:113-114` and
      `scripts/gen_handouts.py:8,275` both cite `format-print.css:163-176` as the rule that
      hides non-active tab panels. It is not — that block only sets print colors. The hiding is
      `theme.css:2659-2673` (`.tab-content{display:none}` / `.tab-content.active{display:block}`),
      which applies in print because nothing overrides `display` there. The conclusion the
      handout generator draws is right; the cited cause is wrong.
- [ ] B4. Verify against the **rebuilt** image: `python3 scripts/lint_paths.py`,
      `python3 scripts/gen_handouts.py --check`, container build (baseline: 42 pages,
      **0 WARN**), and grep the rendered HTML to confirm the banner is present on all 6+
      `pathtabs` blocks and absent from `index.print.html`.
      Because B2 swaps implementations rather than patching one, verify the *unchanged* behavior
      too, not just the banner: tab count per block, `data-tab-group`, `data-tab-item` values,
      and that the missing-path / duplicate-path `errorf`s still fire (test by temporarily
      breaking one block locally).
      Handouts should need no regeneration — `gen_handouts.py` flattens from markdown source,
      so shortcode markup never reaches them. Confirm via `--check`, do not assume.
- [ ] B5. `CLAUDE.md`: `pathtabs` now comes from CentralRepo — record that the repo has **no**
      local copy by design, point at CentralRepo's `README.md` for usage, note the
      `deploymentPaths` dependency, and fix the `format-print.css` citation from B3.
      Delete the old "local copy shadows upstream" guidance for this file; it no longer applies
      here and leaving it invites someone to re-add a local copy.
- [ ] B6. PR → `main`.

### WS-C — k8s-101-workshop. **Gated on S2 — do not open this PR until the rebuilt prod image is live.**

- [ ] C1. Commit the already-written `push: branches: [main]` trigger in `path-lint.yml`.
      (Written already; held with the rest of WS-C so this repo gets one PR, not two.)
- [ ] C2. Add `errorignore` to `scripts/repoConfig.json` targeting the Workshop PDF shortcut.
      Only meaningful once A2 is on CentralRepo `main` and the prod image has rebuilt — the key
      is silently dropped by the current `hugo.jinja`. Sequenced after S2 so the WARN is
      actually gone when this lands, rather than staged.
- [ ] C3. Fix the beginner/experienced routing text whose section numbers do not match the
      actual nav. Report the proposed wording for review before committing — this is content
      judgment, not a mechanical edit.
- [ ] C4. Add preflight verify blocks to the hands-on pages. Same rule: propose before
      committing, and every command must be lab-accurate.
- [ ] C5. Verify against the **rebuilt** image: `python3 scripts/lint_paths.py` + container
      build. Target 48 pages / **0 WARN**. If it still reads 1 WARN, A2 did not take — debug
      that before merging, do not merge and explain it away.
- [ ] C6. PR → `main`.

### Sync points

- [x] ~~S1. A1 → B2, byte-identical copy.~~ **Gone.** There is no second copy to keep in sync —
      that is the entire point of the upstream-only mandate.
- [ ] S2. **Hard gate, now for both B and C.** A merged to CentralRepo `main` →
      `image-build-push-prod.yaml` runs → new `public.ecr.aws/k4n6m5h8/fortinet-hugo:latest` in
      ECR → *then* B and C start. Confirm the image actually moved (compare digest, not just a
      green workflow) before treating B2 or C2 as effective.
      **The interim window is safe, which is why this ordering is acceptable.** Between the merge
      and B2, `ai-101` still has its local copy, which shadows upstream, so it renders exactly
      what it renders today — no badge, nothing broken. B2's deletion flips it to
      upstream-with-badge in one step. There is no state in which the page is half-migrated.

## Implementation Method

**Serialize A, then fan out B ∥ C behind the image rebuild.** Upstream-only put B on the same
hard gate as C, so the three-way and even the two-way concurrency at the front is gone: WS-A is
the critical path and nothing else can be verified until it lands. Once S2 clears, B and C touch
different repos and share nothing, so they run concurrently — one branch per repo, no worktree
isolation needed since the concurrency is across repos rather than within one.

The honest cost: this trades all the parallelism for verifiability. Wall-clock is now
A + (image rebuild) + max(B, C) instead of max(A, B) + rebuild + C. Accepted deliberately —
both of Jeff's directives (finish CentralRepo first; no local copy) point the same way, and the
alternative was shipping claims that could not be checked.

Where fan-out still pays inside WS-A: A1 (shortcode + badge, the only hard part), A4
(`static.yml` split), and A7 (documentation) are independent of each other and of A2/A3, which
are a two-line pair. Draft those three concurrently, then integrate and verify once at A6.

Two carve-outs:
- C3 and C4 are content judgment. Agents draft; every diff is reviewed inline before any PR
  opens. No auto-commit of prose that describes lab steps.
- The wait at S2 is dead wall-clock and there is now no work to hide it behind. Do not start B or
  C early "to save time" — starting early is exactly what produces an unverifiable claim, and for
  B it would mean a build that hard-fails on the missing `deploymentPaths`.

## Plan Changes
- **2026-08-18, before approval — WS-C is now gated on WS-A shipping, not run alongside it.**
  Jeff's call: finish the CentralRepo work *and* let the prod image rebuild before re-pushing
  `k8s-101-workshop`, so the WARN actually clears in one pass instead of landing as a staged
  edit that reads as a no-op. Consequences: WS-C moves behind S2 rather than in front of it;
  WS-C's end state becomes 48 pages / **0 WARN** instead of "1 WARN, fix staged"; and the
  fan-out narrows to A ∥ B, with C serialized after. Costs wall-clock, buys a verifiable
  result. The three-way fan-out this plan originally described is gone.
- **2026-08-18, before approval — the shortcode is CentralRepo-only. `ai-101`'s local copies get
  DELETED, not kept in sync.** Jeff's call, and it removes a wart the plan had accepted: a
  hand-synced duplicate drifts eventually, and `local_copy.sh` makes the local copy win
  silently when it does. Upstream-only makes drift structurally impossible.
  Consequences: (1) the "badge ships today on the current prod image" property is gone — the
  badge cannot appear in `ai-101` until the rebuilt image is live, so **WS-B is now gated on S2
  too**; (2) the fan-out becomes A alone, then B ∥ C after the gate; (3) the upstream shortcode
  must be a functional superset of `ai-101`'s, because deleting the local copy swaps
  implementations wholesale — not just adds a banner; (4) `ai-101` must declare
  `deploymentPaths` in `repoConfig.json`, since the global shortcode `errorf`s rather than
  defaulting to `docker`/`k8s` (see A1); (5) author-facing documentation in CentralRepo becomes
  a deliverable, not a nicety — a global component nobody can find is not global.
  Also revised: the in-shortcode CSS/JS decision now rests on self-containment and clobber-
  safety alone. Its original main justification (ships without an image rebuild) no longer
  applies. It survives the loss of that argument, but the record should show the reason changed.

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
- [x] ~~Delete `ai-101`'s local `layouts/shortcodes/pathtab*.html` once the prod image carries the
      upstream copies.~~ **Promoted into the plan as step B2** — with upstream-only this is no
      longer a follow-up to be remembered later, it is a required step of the work itself.
- [ ] Once upstream `pathtabs` is live, drop the "copy from `ai-101`" pointer in
      `k8s-101-workshop/CLAUDE.md` and fill in its `PATH_KEYS` (carried from that repo's plan
      0001). Do **not** re-enable `PATH_TITLE_RE` there — it matches two ordinary tab titles.
- [ ] `pageRef` support for `menu.shortcuts` in `hugo.jinja` — still open, still a nice-to-have,
      no longer blocking anything now that `errorignore` exists.
- [ ] Roll `pathtabs` out to the other four workshop repos once it is upstream
      (`faig-training-workshop`, `fortiweb-api-mcp-protection`, `AWS-FGT-301`,
      `Public-Cloud-104-CNAPP`). Cheaper after A7 — each repo needs only `deploymentPaths` in its
      `repoConfig.json` plus the shortcode in content; no files to copy.
- [ ] Reconcile `prreviewJune23` with `main` (4 commits behind) or retire the branch, and delete
      or document `prreviewJuly23` (13 behind, referenced by nothing, misleadingly named). Not in
      scope here — flagged because it makes CentralRepo's dev image untrustworthy as a test
      target for anything main-bound.
- [ ] `k8s-101-workshop`: dead AKS references — still deferred by decision.
- [ ] Reconsider AKS as an `ai-101` path once someone can validate it on a real cluster.

## Risks / Open Questions

- **Nothing visible ships until the prod image rebuilds — the badge included.** Upstream-only
  removed the one path that would have shown a result on the current image. If the rebuild
  stalls, this plan produces reviewed-and-merged CentralRepo code and *no* user-visible change,
  which is a worse-looking outcome than the earlier shape even though it is a better-built one.
  Mitigation: A6's `LOCAL=true` build renders the badge locally, so it can be demonstrated with a
  screenshot before the rebuild; and `image-build-push-prod.yaml` is manually dispatchable.
- **B2 swaps implementations, it does not patch one.** Deleting `ai-101`'s local copy in favor of
  upstream means every difference between the two versions lands at once, silently. Mitigation:
  A1 explicitly enumerates the two intended differences, and B4 verifies the *unchanged*
  behaviors (tab counts, `data-tab-item` values, both `errorf` guards) rather than only the new
  banner.
- **WS-C now blocks on an ECR image build finishing.** Sequencing it after S2 (Jeff's call) is
  what makes the WARN verifiable, but it means the plan cannot finish if the prod image build
  fails or the ECR push is throttled. Mitigation: `image-build-push-prod.yaml` is dispatchable
  manually, and the local `LOCAL=true` dev image proves the `hugo.jinja` change independently
  of ECR — so a stuck image build delays C, it does not invalidate A.
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

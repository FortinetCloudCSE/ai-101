# Plan: Single-path workshop view — replace tab-sync with a pre-paint path gate
Date: 2026-08-19
Owner: Jeff Kopko
Slug: single-path-workshop-view
Status: Approved
Supersedes: none
Superseded-By: none
Plan File: plans/0003_2026-08-19_Jeff-Kopko_single-path-workshop-view.md
Spec File: plans/0003_2026-08-19_Jeff-Kopko_single-path-workshop-view.spec.md
Log File: plans/0003_2026-08-19_Jeff-Kopko_single-path-workshop-view.log.md (not yet created — warranted
  here because the work spans sessions and lands in CentralRepo, but written at implementation, not now)

## Goal

A participant chooses Docker Compose or Kubernetes/Helm once, and from then on the workshop shows
**only** that path — in the page body, in the sidebar, in prev/next navigation, and in search — with
the active path visible on every page and changeable in one click from anywhere. Tab-sync stops
being the mechanism and becomes only the no-JavaScript fallback.

## Root cause, confirmed by Jeff 2026-08-19

**Participants attempted to do both the Docker steps and the Kubernetes steps, because both tabs were
on the page.** Not a persistence failure, not a subtle mis-read — they executed both paths.

This narrows the five leaks in the spec from "five things of unknown relative weight" to one dominant
cause with four lesser ones, and it reorders the work: gating the tab panels is the fix for the
reported incident and moves into Phase 1. The sidebar, prose, search and tooling leaks are the same
class of defect and still get fixed, but they are not what happened.

It also raises the bar on the fallback. "Degrades to showing both paths" was written as the *safe*
fallback in the spec. Given what actually went wrong, showing both paths **is** the failure mode. Any
state that shows both — no choice yet, JavaScript off — must say so loudly rather than look normal.

### Decisions taken with it

- **Runtime pre-paint gate, not build-time variants.** Jeff: "As long as the user can make and change
  their choice, it's clear to them which path they're on, and we don't break other repos, we should go
  with your recommendation." Comparison below.
- **Changing CentralRepo is approved.** Jeff: "If we change CentralRepo that's fine. The remaining 65
  repos only ever touch it when they rebuild...not immediately." The no-op-when-`deploymentPaths`-absent
  requirement still stands — that is what makes the staggered rebuild safe rather than merely slow.
- **A reader with no stored choice is blocked, not shown both.** Jeff chose the blocking chooser:
  "it's likely if the instructor is sending a link the participant has already chosen a path, but this
  will eliminate that potential pitfall." This inverts the CSS to **default-deny**: gated content is
  hidden until an explicit choice exists. Consequence for JS-off, which cannot set the attribute and
  would therefore be blocked out entirely — a `<noscript>` rule un-hides everything *and* renders an
  explicit "both paths are shown below, follow only one" warning. That is the one state where both
  paths appear, and it announces itself.

## Context / Links

- Spec: `plans/0003_2026-08-19_Jeff-Kopko_single-path-workshop-view.spec.md`
- Predecessors: `plans/0001_…_workshop-deployment-path-lock.md` (tab sync via shared `groupid`),
  `plans/0002_…_path-badge-and-upstream.md` (locked-path banner, upstreamed)
- **Blast radius of the gate: 65 repos, not ~12.** `gh api search/code -f q='org:FortinetCloudCSE
  "public.ecr.aws/k4n6m5h8/fortinet-hugo" path:.github/workflows'` returns 65 distinct repos pulling
  the floating `:latest` prod image tag (measured 2026-08-19). Plans 0001 and 0002 both say "~12";
  that figure was wrong by 5x and is corrected here and in CentralRepo's `README.md`. It bounds the
  *image* merge, not this plan's content changes.
- **Blocking dependency:** CentralRepo PR
  [#71](https://github.com/FortinetCloudCSE/CentralRepo/pull/71) — draft, all 7 checks pass. It
  moves `pathtabs`/`pathtab` upstream and adds `site.Params.deploymentPaths`. This plan builds
  directly on that shortcode and on that param. Do not start implementation until #71 merges and the
  prod image rebuilds (plan 0002's S2 gate).
- Key code paths:
  - `CentralRepo/layouts/partials/custom-header.html` — CentralRepo-owned, last thing in `<head>`
    (`layouts/_default/baseof.html:41`), synchronous → **pre-paint**
  - `CentralRepo/layouts/partials/content-header.html` — CentralRepo-owned, renders above content on
    every page
  - `CentralRepo/layouts/partials/topbar/button/prev.html`, `next.html` — CentralRepo-owned
  - `CentralRepo/layouts/partials/dependencies/search-lunr.html` — CentralRepo-owned
  - `themes/hugo-theme-relearn/layouts/partials/dependencies/theme.html:62-117` — the theme's own
    pre-paint variant switcher; the pattern this plan copies
  - `themes/hugo-theme-relearn/layouts/partials/menu.html:149,184` — sidebar `<li>`, carries
    `data-nav-id="<permalink>"`
  - `themes/hugo-theme-relearn/assets/_relearn_searchindex.js:17` — indexes `.Plain`
  - `ai-101/scripts/gen_handouts.py`, `ai-101/scripts/lint_paths.py`

## Constraints / Assumptions

Verified this session; each one killed or shaped an option.

- **A workshop repo can only ship `layouts/shortcodes/*` and `layouts/partials/*`, non-recursively.**
  `CentralRepo/scripts/local_copy.sh:3-4`. So no repo can supply `layouts/_default/`, `i18n/`,
  `static/`, `assets/`, or `layouts/partials/sidebar/element/*`. Everything site-wide in this plan
  must live in CentralRepo. A repo-local `custom-header.html` is not an option — it replaces
  CentralRepo's 715-line header wholesale.
- **The build is one hardcoded Hugo pass.** `CentralRepo/scripts/hugo_build.sh` is four lines with no
  parameters; `local_copy.sh:33-42` dispatches on `$1` and drops extra args. `--cleanDestinationDir`
  means a second pass into the same `public/` deletes the first. Both files are baked into the image
  (`Dockerfile:61`).
- **The publish path assumes a single site root.** `docker cp $CONT_ID:/home/CentralRepo/public`
  → `docs/` → `upload-pages-artifact path: './docs'` (`ai-101/.github/workflows/static.yml:100-132`),
  one Pages deployment per repo.
- **`baseURL` derives from `repoName` (`hugo.jinja:4`), which is also the analytics workshop ID and
  quiz-score key (`hugo.jinja:102-103`).** This matters only if a variant changes `baseURL` itself.
  A path carried as a *subdirectory* under the existing `baseURL` (`/ai-101/k8s/01Intro/`) leaves
  `repoName`, analytics and quiz reporting untouched. Corrected from an earlier overstatement.
- **Hugo compute is not the constraint.** 639 ms for `ai-101`'s 42 pages, inside a 40–60 s pipeline
  dominated by image pull (~14 s) and Pages deploy (~22 s). Any cost argument against a second pass
  is about plumbing and URLs, not time.
- **Tab restore is post-paint by construction.** `theme.js` is `defer` at end of body
  (`dependencies/theme.html:127-133`) and `restoreTabSelections()` runs on `DOMContentLoaded`
  (`theme.js:1835`), while the server renders tab #1 active (`shortcodes/tabs.html:69,80`). A
  tab-based mechanism cannot avoid the flash.
- **Hiding non-active tab nav buttons with CSS is safe.** No theme JS measures, focuses, or
  scroll-positions a non-active `.tab-nav-button`; there is no tab-overflow logic (`.tab-nav` is
  `flex-wrap: wrap`, `theme.css:2594-2597`); `switchTab` only touches `event.target`
  (`theme.js:120,123,141`) and `fixCodeTabs` only reads `classList` (`theme.js:73-92`).
- **`display:none` must be scoped to path blocks only.** `ai-101` has **16 non-path tab groups** on a
  command-vs-output axis, including a 3-tab group whose middle tab is an instruction
  (`content/01Intro/2_prereqs_k8s/index.md:127-157`, `Follow the logs`). A global rule would suppress
  all of them — the defect already documented for print at `ai-101/CLAUDE.md:114`.
- **`deploymentPath` front matter already exists** and is already consumed by
  `gen_handouts.py:167-172`. Three pages use it. Reuse it; do not invent a second marker.
- **Only `params.hidden` reaches the sidebar `<li>`**, and it is build-time and also strips the page
  from search, SEO, and prev/next (`_relearn/pageIsHidden.gotmpl`, `menu.html:89,119,172`). Unusable
  for per-visitor gating. The usable lever is `data-nav-id` (the permalink) on the `<li>`.
- **`gen_handouts.py:93` is anchored:** `^\s*\{\{%\s*pathtab\s+path="([^"]+)"\s*%\}\}\s*$`. Adding
  any second attribute to `pathtab` silently breaks handout flattening. Treat that signature as
  frozen.
- **`lint_paths.py` is regex line-scanning with one-marker-per-line state machines**
  (`:145-149`, `:254-261`); nesting a `pathtabs` block inside a plain `tabs` group mis-tracks state,
  and `gen_handouts.py:308` rejects nesting outright.
- **The search index leaks unconditionally** (`_relearn_searchindex.js:17` indexes `.Plain`) but the
  template is overridable via `params.search.index.template` (`dependencies/search.html:22-24`).
- **Workshop `repoConfig.json` files are never schema-validated.** `validate_config.py:21-24` checks
  only CentralRepo's own config and one fixture, and `generate_toml.py` validates nothing — so an
  unknown key is silently ignored rather than rejected, despite
  `repoConfig.schema.json:6` `additionalProperties: false`.
- Assumption: participants' reported difficulty is caused by some mix of the five leaks in the spec's
  Problem section. Their **relative weight is unmeasured** — see Open Questions.

## Decisions & Commentary

### Hiding the non-selected tab: necessary, and now first — but still not sufficient alone

This is what "is there a way to hide tabs for the non selected choice?" literally asks for, it is a
one-line CSS rule, and it is safe: no theme JS measures, focuses or scroll-positions a non-active
`.tab-nav-button`, there is no tab-overflow logic, `switchTab` only touches `event.target` and
`fixCodeTabs` only reads `classList`.

Given the confirmed root cause it is also the single highest-value change in this plan, so it moves
from Phase 2 to Phase 1. Three things still have to ship with it rather than after it:

- **A replacement switcher.** Today the tab *is* how a student changes their mind. Hide it with
  nothing in its place and a student who picked wrong has no visible way out — which converts a
  recoverable mistake into a stuck one.
- **The pre-paint attribute.** With both tabs on screen, a brief wrong-tab-active state reads as UI
  settling. With one tab, the student briefly sees the *wrong path's content as the only content*,
  which reads as authoritative. Hiding the tab without fixing the flash makes the flash more
  dangerous, not less.
- **Default-deny, so no-choice never renders a path.** Server-side, relearn marks tab #1 active
  (`shortcodes/tabs.html:69,80`), i.e. Docker. Hiding non-active tabs with no stored choice would
  present Docker as *the* path to a Kubernetes student — exactly the reported failure, inverted.

It reaches 6 of 14 pages, so the remaining leaks (three whole path-scoped pages,
`content/09Reference/_index.md:54-61`, `content/04MCP/_index.md:86,91`) still need Phase 2. But those
are "irrelevant content is visible", not "two contradictory instruction sets are visible".

### Build-time variants vs runtime gate — the full comparison

Build-time means two Hugo passes producing two output trees, one per path, and the student is routed
to one (`/ai-101/k8s/01Intro/`). Runtime means one tree, with a `data-deployment-path` attribute set
on `<html>` before paint and CSS gating everything off it.

| | Build-time variants | Runtime pre-paint gate |
|---|---|---|
| Other path present in delivered HTML | **No — genuinely absent** | Yes, `display:none` |
| Works with JavaScript disabled | **Yes** | No — falls back to both paths + explicit warning |
| Fixes the confirmed root cause (both step sets visible) | Yes | Yes |
| Search scoping | **Free, including within-page** | Page-granular, needs an index-template override |
| Print / PDF | **Free** | Fine — CSS-hidden content does not print; handouts already single-path |
| Shareable link carries the path | **Yes** | No |
| URL churn | ~14 `ai-101` URLs gain a segment; breaks existing deep links, slide decks, QR codes, handout internal links | **None** |
| "Change your choice" | Needs a current-URL → sibling-URL map + redirect on every page | **Flip an attribute; instant, no navigation, works from any page** |
| Switching *from* a path-scoped page | **Broken by construction** — `2_prereqs_k8s` exists only in the k8s tree, so there is no sibling to switch to; needs a bespoke fallback | Page says "this page is for the other path", switcher still present |
| CentralRepo pipeline work | Two passes, `--cleanDestinationDir` conflict, `local_copy.sh` arg passthrough, `static.yml` publishing two trees into one `docs/` | **None — one pass, one `docker cp`, one Pages artifact, unchanged** |
| Effect on the other 64 repos | No-op if they never set `deploymentPaths`, but the pipeline they run is rewritten | **No-op, and the pipeline is untouched** |
| Hugo build cost | 2 x 639 ms — irrelevant | 639 ms |
| Reversibility | URL scheme is a public contract; hard to walk back | **Delete a partial and a CSS block** |

**Chosen: runtime.** Against Jeff's three stated criteria it wins on two and ties on one:

- *"the user can make and change their choice"* — runtime wins decisively. An attribute flip changes
  the current page in place from anywhere. Build-time needs a URL mapping, and that mapping has no
  answer at all on the three path-scoped pages, which is precisely where a mis-chosen student is most
  likely to notice their mistake.
- *"it's clear to them which path they're on"* — tie. Both support a persistent indicator.
- *"we don't break other repos"* — runtime wins. It changes no pipeline file, so the other 64 repos
  rebuild against an image whose build path is identical. Build-time rewrites `hugo_build.sh`,
  `local_copy.sh` and `static.yml`, which every one of those repos executes; a bug there is a
  64-repo outage discovered one repo at a time as they happen to rebuild.

Build-time's real advantages are JS-off support and free search/print scoping. The first is
mitigated (`<noscript>` un-hides with a warning — the current behaviour plus an explanation, so
strictly better than today) and the second is Phase 3 work rather than an impossibility. Neither is
worth the URL contract or a rewrite of the pipeline all 65 repos run.

**What would change the decision:** an answer of "yes, the path belongs in the URL" — i.e. instructors
must be able to send a path-specific link. Jeff's Q3 answer points the other way (participants
receiving links have typically already chosen), so this is settled unless that turns out to be wrong.

### Rejected: Hugo multilingual as the variant carrier (one "language" per path)

Superficially free — Hugo already segregates languages by URL, builds them in one pass, and gives a
switcher. It is a trap here:

- The namespace is already occupied and half-broken. `hugo.jinja` emits `defaultContentLanguage`,
  `defaultContentLanguageInSubdir` as a **quoted string**, `additionalContentLanguage`,
  `disableLanguageSwitchingButton = true`, and a `[Langauges]` table — a typo, so it is an inert
  block Hugo ignores. Correcting that spelling later would turn it into a real `[languages]` table
  with a bogus child key.
- Defining a second language flips `hugo.IsMultilingual`, which is what
  `sidebar/element/languageswitcher.html:1` gates on; the switcher stays hidden only because of the
  `disableLanguageSwitchingButton` flag.
- The theme ships 28 `i18n/*.toml` files, so any invented code that collides with a real language
  inherits that language's UI strings, and CentralRepo's `i18n/en.toml` is the only real one.
- A workshop repo cannot ship `i18n/` at all (`local_copy.sh:3-4`).

Semantic abuse with three separate failure modes, to buy URL segregation we have not decided we
want.

### Chosen: a pre-paint document-level path attribute, mirroring the theme's own variant switcher

The theme already solves this exact problem shape for colour schemes: an inline synchronous script in
`<head>` reads localStorage and sets `document.documentElement.dataset.rThemeVariant` before
`<body>` is parsed, and a sidebar `<select>` changes it
(`dependencies/theme.html:62-117`, `sidebar/element/variantswitcher.html:1-27`). Copy that, with
`data-deployment-path` on `<html>`, and everything else is CSS.

Why this shape wins here specifically:

- **It is pre-paint, so the flash is gone** — not reduced, structurally absent. `custom-header.html`
  is emitted at `baseof.html:41` with no `defer`, one line after `dependencies.html`, so
  `window.relearn` and `absBaseUri` are already available and `<body>` does not exist yet. That last
  detail is why the flag goes on `document.documentElement`, not `body`.
- **It gates arbitrary content, not just tab panels** — a paragraph, a section, a whole page's
  sidebar entry, all with the same attribute.
- **Most of the CSS is generated at build time**, so the sidebar needs no JavaScript either. Page
  permalinks are known at build time, and the sidebar `<li>` carries
  `data-nav-id="<permalink>"` (`menu.html:149,184`), so `custom-header.html` can iterate pages with a
  `deploymentPath` and emit exact `display:none` rules per path. Zero flash in the nav as well.
- **It reuses `deploymentPath`**, which already exists and already drives the handout generator.
- **It costs nothing for the other repos.** No `deploymentPaths` declared → no attribute, no CSS, no
  UI, byte-identical output.
- Tab markup stays, so the no-JS and pre-choice fallback is exactly today's behaviour: both paths
  visible as tabs. We degrade to *more* information, never to silently one path.

Accepted costs, stated plainly:

- **JavaScript-off users get no gating.** Acceptable: they get today's behaviour, which is the
  current baseline, and the printable handouts are already single-path and unaffected.
- **The choice is client-side, so a pasted link carries no path.** This is the one real regression
  against build-time variants and it is a genuine workshop scenario — an instructor cannot send "the
  Kubernetes version of this page". Unresolved; see Open Questions.
- **Within-page search leakage stays** on genuinely mixed pages. Page-granular scoping is in scope,
  sub-page is not.
- **`pathonly` adds a fourth shortcode the handout generator and linter must both understand**, and
  their parsers are line-based regex state machines. Its markup must be a single line at open and
  close, matching how `pathtab` is already parsed.

### Prev/next is a real gap, not an afterthought

Relearn's prev/next honours `params.hidden` (`_relearn/pageNext.gotmpl:88,98`,
`pagePrev.gotmpl:65,76`) but knows nothing about `deploymentPath`. So after the sidebar hides
`1_prereqs_docker` from a Kubernetes reader, "next" from the Intro page still walks them straight
into it. Hiding a page from the nav while leaving it on the linear path is worse than not hiding it —
the student ends up somewhere the sidebar says does not exist. CentralRepo already overrides
`topbar/button/prev.html` and `next.html`, so this is fixable in the right place, but it must ship in
the same phase as the sidebar rule, never after it.

### Phasing, and why Phase 1 is deliberately small

The five leaks are all real and verified, but their relative contribution to the reported difficulty
is unmeasured. Phase 1 fixes the three concrete leaks anyone can point at today and delivers the
indicator and switcher; Phases 2–4 generalise. If Phase 1 turns out to resolve the complaints, the
rest is optional rather than half-finished.

## Plan

### Phase 0 — gate

- [x] P0.1. The URL question is settled: **no**, the path stays out of the URL. Runtime gate chosen.
- [ ] P0.2. CentralRepo PR #71 merged, prod image rebuilt, digest confirmed moved (plan 0002 S2).
      Nothing below can be verified before this. Approved by Jeff 2026-08-19.

### Phase 1 — stop both instruction sets being visible

Everything in this phase exists to fix the confirmed root cause. Nothing here is optional and nothing
ships alone; P1.1-P1.5 are one deliverable in five files.

- [ ] P1.1. CentralRepo `layouts/partials/custom-header.html`: pre-paint initialiser. Reads
      localStorage key `window.relearn.absBaseUri + '/deployment-path'`, validates against the keys in
      `site.Params.deploymentPaths`, sets `document.documentElement.dataset.deploymentPath`. No-ops
      entirely when `deploymentPaths` is unset. Set it on `documentElement` — `document.body` does not
      exist at this point. Emitted at `baseof.html:41`, synchronous, after `dependencies.html`, so
      `window.relearn.absBaseUri` is available and nothing has painted.
- [ ] P1.2. Same file: the **default-deny** CSS. Path-gated content is hidden when
      `html` has no `data-deployment-path`, and shown only for the matching path. Must be scoped to
      path blocks — a global non-active-tab rule would suppress the 16 command-vs-output tab groups,
      including the 3-tab group at `content/01Intro/2_prereqs_k8s/index.md:127-157` whose middle tab
      is an instruction. Verify the selector beats `#R-body .tab-content.active`
      (`theme.css:2659-2673`) on specificity without `!important` — measure, do not assume, because
      `!important` here leaks into print and the handout PDFs.
- [ ] P1.3. `pathtabs` emits a per-path wrapper inside each tab's content, so the CSS gates on the
      path key rather than on relearn's derived `data-tab-item` (`anchorize(title)+anchorize(icon)`,
      so "Docker Compose" → `docker-compose`, not `docker`). **Do not add an attribute to `pathtab`** —
      `gen_handouts.py:93` is anchored on its exact current signature and breaks silently.
      Hide `.tab-nav` inside path blocks once a path is chosen.
- [ ] P1.4. CentralRepo `content-header.html`: the persistent indicator and switcher, on every page
      including the 8 with no `pathtabs` block. Names the active path; changes it in one interaction;
      writes localStorage and updates the attribute live with no reload. Renders nothing when
      `deploymentPaths` is unset.
- [ ] P1.5. The **no-choice chooser** (Jeff's Q3 answer: block, do not show both). With no stored
      path, gated content stays hidden and the page presents the choice instead. Plus a `<noscript>`
      block that un-hides everything *and* renders an explicit warning — "JavaScript is off, so both
      paths are shown below; follow only one". That is the sole state where both instruction sets
      appear and it must announce itself, because showing both silently is the exact reported failure.
- [ ] P1.6. `ai-101` `scripts/repoConfig.json`: `deploymentPaths` (also plan 0002 B2 — land it once).
- [ ] P1.7. Verify: 42 pages / 0 WARN. The correct path paints first with no post-`DOMContentLoaded`
      content mutation. With storage cleared, no lab page shows any path's steps. With JS disabled,
      both paths show *and* the warning is present. The 16 non-path tab groups byte-identical in the
      built HTML. `k8s-101-workshop` output byte-identical, no new warnings. Handout PDFs still build.

### Phase 2 — the four lesser leaks

Same class of defect, lower harm: irrelevant content visible, rather than two contradictory
instruction sets visible.

- [ ] P2.1. Build-time CSS in `custom-header.html` iterating `site.Pages` where `.Params.deploymentPath`
      is set, hiding each page's sidebar `<li>` for every other path, keyed on
      `#R-sidebar li[data-nav-id="<permalink>"]`. No JS, no flash — permalinks are known at build time.
- [ ] P2.2. A direct-linked reader on a page for the other path gets "this page is for the other path",
      with the switcher present — not a blank page.
- [ ] P2.3. CentralRepo `topbar/button/prev.html` + `next.html`: skip pages whose `deploymentPath` does
      not match. **Ships with P2.1, never after it** — relearn's prev/next honours only `params.hidden`
      (`_relearn/pageNext.gotmpl:88,98`, `pagePrev.gotmpl:65,76`), so hiding a page from the sidebar
      while leaving it on the linear path walks the student into a page the sidebar says does not exist.
- [ ] P2.4. New `pathonly` shortcode for path-specific prose and sections outside tabs. Single-line
      open and close markers, `path=` its only attribute, `errorf` on a key not in `deploymentPaths`.
- [ ] P2.5. `ai-101` content: `content/09Reference/_index.md:54-61` (`## Compose profiles`) into
      `pathonly`; `content/04MCP/_index.md:86,91` gated or reworded; `content/_index.md:66` reworded to
      read correctly before any choice exists.
- [ ] P2.6. Verify: the three path-scoped pages absent from the sidebar and from prev/next for the
      other path; indicator present on all 14 authored pages.

### Phase 3 — search scoping

- [ ] P3.1. Override `params.search.index.template` (`dependencies/search.html:22-24`) to emit each
      page's `deploymentPath` alongside its content.
- [ ] P3.2. Filter results client-side by the active path, page-granular. CentralRepo already
      overrides `dependencies/search-lunr.html`.
- [ ] P3.3. Verify: searching a Docker-only term as a Kubernetes reader returns no path-scoped Docker
      pages; searching with no choice stored returns everything.

### Phase 4 — make the leaks unrepeatable

- [ ] P4.1. `ai-101/scripts/lint_paths.py`: a check that would have caught
      `content/04MCP/_index.md:86` ("Docker service hostname") and `content/_index.md:66`
      ("Compose v2") — both slip today because `PATH_TOKENS` matches only
      `docker compose|exec|volume` (`:65-81`).
- [ ] P4.2. Close or explicitly record the fence blind spot: check 3 runs after
      `if in_fence: continue` (`:240-241`), so path tokens in bare code fences outside a `pathtabs`
      block are never checked. Zero occurrences today, so this is prevention.
- [ ] P4.3. Teach `gen_handouts.py` to flatten `pathonly` blocks. Verify `--check` passes and both
      PDFs still build (`--disable-dev-shm-usage` remains non-optional,
      `handout-pdf.yml:129-130`).
- [ ] P4.4. Recheck the tab/nesting state machines: `lint_paths.py:254-261` is an `if/elif` chain
      that mis-tracks a `pathtabs` block nested in a plain `tabs` group, and `gen_handouts.py:308`
      rejects nesting. Make `pathonly` nesting either supported or a hard error — not silently wrong.
- [ ] P4.5. Decide whether to unify the four path-vocabulary declarations (`pathtab.html`,
      `gen_handouts.py:42-55`, `lint_paths.py:57`, `site.Params.deploymentPaths`). `CLAUDE.md:109`
      already flags three of them as needing to agree.

### Phase 5 — document and close out

- [ ] P5.1. CentralRepo `README.md` + `CLAUDE.md`: the mechanism, the three authoring forms
      (`pathtabs`, `pathonly`, `deploymentPath` front matter), and the pre-paint requirement.
- [ ] P5.2. `ai-101/CLAUDE.md` + `k8s-101-workshop/CLAUDE.md:164` (which still says "copy `ai-101`'s
      shortcodes") updated to point at the upstream mechanism.
- [ ] P5.3. Promotion step, per global prefs step 12.

## Implementation Method

**Hybrid: sequential tmux for Phase 1, then fan out.**

Phase 1 is one CentralRepo file (`custom-header.html`) touched by four steps plus two partials that
must ship together — sequential, single session, own worktree. Phases 2, 3 and 4 are independent
once Phase 1 lands (body gating, search, tooling touch disjoint files) and are a natural three-way
fan-out with Phase 5 as the sync point.

The whole plan sits behind PR #71 and the image rebuild, so nothing here is verifiable until that
clears. Do not start P1 before P0.

## Plan Changes

- 2026-08-19, `Proposed` → `Approved`. Root cause confirmed (participants ran both step sets because
  both tabs were visible), so the plan was restructured before approval: tab-panel gating moved from
  Phase 2 into Phase 1 as the fix for the actual incident, and the sidebar/prose/prev-next leaks moved
  down to Phase 2. The CSS was inverted to default-deny and a blocking no-choice chooser plus a
  `<noscript>` escape hatch added, per Jeff's Q3 answer. The build-time-vs-runtime rejection was
  replaced with a full comparison table. Substance edits are legitimate here because the plan was
  still `Proposed` when they were made.
- 2026-08-19, still `Proposed`: two factual corrections after measuring rather than recalling.
  (1) The shared-image blast radius is **65 repos**, not "~12" as plans 0001-0002 said. (2) The
  build-time-variant option's cost was overstated — a path carried as a URL *subdirectory* does not
  touch `baseURL`, `repoName`, analytics or quiz keys, and only opted-in repos (today: `ai-101`
  alone) see any URL change. The rejection now rests on the open URL question, not on cost.

## Files Changed

- (none yet)

## Session Summary

- (write at end)

## Promotion

- [ ] `Decisions & Commentary` walked
- [ ] Durable facts promoted to `CLAUDE.md` — list them: <...>
- [ ] `Status:` set to `Complete`

## Risks / Open Questions

- ~~**Open question, blocking Phase 0: does the path belong in the URL?**~~ **Answered: no.** Client-side storage means a
  pasted link carries no path and an instructor cannot send "the Kubernetes version of this page" —
  a real workshop scenario. Putting it in the URL fixes sharing and makes search scoping trivial, but
  changes every published URL across the estate and collides with `baseURL` being derived from
  `repoName`, which doubles as the analytics ID and quiz key. A "yes" supersedes this plan rather
  than amending it.
- ~~**Open question: has anyone asked what the participants actually did?**~~ **Answered: they ran
  both the Docker and the Kubernetes steps, because both tabs were on the page.** The text below is
  kept because its reasoning still holds for the four *lesser* leaks, whose relative weight remains
  unmeasured.
- (superseded) has anyone asked what the participants actually did? All five leaks are verified
  in code; their relative weight is not. If the dominant cause is the sidebar listing both prereq
  pages, Phase 1 alone is the fix and Phases 2–3 are polish. Worth asking whoever collected the
  reports before building the general mechanism.
- ~~**Open question: what does a deep-linked reader with no stored choice see on a lab page?**~~
  **Answered: blocked, with a chooser.** Jeff: "it's likely if the instructor is sending a link the
  participant has already chosen a path, but this will eliminate that potential pitfall." Original
  framing: Showing
  both is safe but is today's confusing state; redirecting to the chooser is opinionated and traps
  browsers. Phase 1 now blocks; the "show both" state survives only behind `<noscript>`, with a warning.
- Risk: the CSS specificity fight with `theme.css:2659-2673` needs `!important`, which then leaks
  into print and the handouts. Mitigation: P2.2 measures before committing; the handout PDFs are the
  regression test.
- Risk: `pathonly` breaks `gen_handouts.py`'s or `lint_paths.py`'s line-based state machines in a way
  that only shows up as a silently wrong handout. Mitigation: P4.3/P4.4 ship with Phase 1's shortcode
  or immediately after, and `gen_handouts.py --check` is already a CI gate
  (`path-lint.yml`, `handout-pdf.yml:44-45`).
- Risk: a CentralRepo merge rebuilds the image every workshop repo builds against. Mitigation: the
  no-`deploymentPaths` no-op path is a stated success criterion, verified on `k8s-101-workshop`.
- Risk: `batch_repo_update.py` reverts workshop-side files. Note `FILES_TO_COPY` sources
  CentralRepo's **own** `.github/workflows/static.yml` (`:18-21`) while `update_scripts.sh:14` and
  `repo_upgrade_spec.json:9-13` both say `scripts/static.yml` — two divergent sources for one
  destination. PR #71 repoints the script; confirm that landed before relying on either.
  Separately: `ai-101/layouts/shortcodes/FTNThugoFlow.html` is on `FILES_TO_DELETE` and will be
  deleted by the next batch run, and `README.md` is overwritten with a two-line stub whenever Pages
  is enabled (`:155-163`, `:324-336`).

## Follow-ups

- `k8s-101-workshop` sidebar has two `Task 1` and two `Task 2` entries — `Task 1 - K8s Installation`
  / `Task 2 - Scaling Application` under "K8s install", and `Task 1 - Pods` / `Task 2 - configmap`
  under "Kubernetes in depth". Same follow-along confusion class, no path involvement. Renaming risks
  breaking prose cross-references (e.g. plan 0002's C4a block cites "Task 2's Cleanup Addons").
- `hugo.jinja:74-75` `[Langauges]` is a typo for `[languages]`. Inert today; fixing the spelling
  would activate a table with a bogus `landingPageName` child. Leave it or fix it deliberately.
- `repoConfig.schema.json` has `additionalProperties: false` but workshop configs are never
  validated (`validate_config.py:21-24`). Either wire up validation or drop the false promise.
- `generate_toml.sh:4-6` recreates a venv and `pip install Jinja2` from the network on every build —
  a larger per-build cost than Hugo itself (639 ms).
- `CentralRepo/layouts/_default/allpages.html` and `ap-print-*.hugo` are wired to nothing (no output
  format, no `layout:` front matter anywhere). Either wire them up or delete them.

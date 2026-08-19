# Spec: Single-path workshop view — a student sees only the path they chose
Date: 2026-08-19
Owner: Jeff Kopko
Slug: single-path-workshop-view
Spec File: plans/0003_2026-08-19_Jeff-Kopko_single-path-workshop-view.spec.md
Plan File: plans/0003_2026-08-19_Jeff-Kopko_single-path-workshop-view.md

## Problem

`ai-101` asks a student to choose a deployment path — Docker Compose or Kubernetes/Helm — and
then presents both paths' instructions side by side for the rest of the workshop, as two tabs in
each of 18 `pathtabs` blocks. Plans 0001 and 0002 made the choice *persist* (relearn tab sync via a
shared `groupid`) and, in 0002, *visible* (a locked-path banner). **Participants still report
difficulty following along.**

Persistence was never the whole problem. What a student on the Kubernetes path can still see today:

1. **Both prerequisite pages, always, in the sidebar.** `content/01Intro/1_prereqs_docker/index.md`
   (117 lines, all Docker) and `content/01Intro/2_prereqs_k8s/index.md` (239 lines, all Kubernetes)
   are both listed for every reader, as is `content/09Reference/cloud-shell-web-preview/index.md`
   (Kubernetes-only). These are marked `deploymentPath:` in front matter, which today only affects
   handout generation — nothing hides them from the nav. Path choice does not reach the sidebar at
   all.
2. **A Docker-only section, in plain markdown, on a page both paths read.**
   `content/09Reference/_index.md:54-61` — the `## Compose profiles` heading and its whole table.
   The only hint that it does not apply is a sentence inside the *other* tab of a different block
   (`:36-37`), which a Kubernetes reader never opens.
3. **Docker-only prose with no indicator of any kind.** `content/04MCP/_index.md:86,91` ("using the
   Docker service hostname", "Docker network"). No notice, no front-matter marker, no tabs. Also
   `content/_index.md:66` on the home page.
4. **The other path's text in every search result.** The theme indexes `.Plain` — the full rendered
   page including non-active tab panels
   (`themes/hugo-theme-relearn/assets/_relearn_searchindex.js:17`). Searching `docker compose up`
   returns pages that will then display Kubernetes instructions.
5. **The wrong path, briefly, on every page load.** Tab restore runs on `DOMContentLoaded` from a
   `defer`red script at end of body (`theme.js:1835`; `dependencies/theme.html:127-133`) while the
   server renders tab #1 (Docker) active. This is the theme's normal behaviour, not a race.

Only 6 of 14 authored pages contain a `pathtabs` block, so a tab-scoped fix cannot reach items 1–3
by construction.

**Why now:** plan 0002's CentralRepo PR (#71) is open and puts `pathtabs` upstream as the shared
implementation for ~12 workshop repos. Whatever mechanism we choose gets adopted by all of them, so
choosing it before that spreads is much cheaper than changing it after. `k8s-101-workshop`'s
`CLAUDE.md:164` already names `ai-101` as the reference implementation to copy.

## Users & Stakeholders

- **Workshop participant (primary).** Follows the lab live, often on a shared screen, under time
  pressure, frequently in Azure Cloud Shell. Has picked one path and does not care that the other
  exists. Cost of confusion is immediate: a wrong command, then a support interruption.
- **Participant who chose wrong, or is handed a machine mid-workshop.** Needs to switch paths
  without knowing anything about localStorage, tabs, or the site's mechanics.
- **Instructor / lab proctor.** Needs to answer "which path are you on?" by looking at the
  student's screen, not by asking. Also needs the printable handouts to stay correct.
- **Workshop author (Tom Walsh, Jeff Kopko, and whoever writes the next repo).** Needs one obvious
  way to mark content as path-specific — for tabs, for a paragraph, and for a whole page.
- **CentralRepo maintainers / the other ~11 workshop repos.** Inherit whatever lands upstream,
  including its failure modes. Most of those repos have exactly one path today and must be
  unaffected.

## User Journeys

1. **First contact — the choice is made deliberately.** A participant opens the workshop and reaches
   `content/01Intro/_index.md`.
   - Trigger: first page load, nothing stored.
   - Steps: the page presents the two paths as a choice. Nothing else in the workshop has silently
     assumed a default yet. The participant picks Kubernetes/Helm.
   - Outcome: the choice is recorded. Every subsequent page shows Kubernetes content only, and shows
     which path is active.

2. **Following the lab — one set of instructions.** The participant works through Labs 1–4.
   - Trigger: navigating to any lab page.
   - Steps: the page renders with Kubernetes steps and no Docker steps — on first paint, not after a
     correction. The sidebar does not list the Docker prerequisites page. Sections that apply only
     to Docker are absent rather than present-and-irrelevant.
   - Outcome: every command on screen is one the participant should run. Nothing on the page needs
     to be mentally filtered.

3. **Changing the choice.** The participant realises they are on the wrong path, or an instructor
   switches a demo machine.
   - Trigger: the participant uses the path control, which is visible on every page.
   - Steps: one interaction, on the page they are already reading. No page-specific hunting, no
     browser settings, no clearing site data.
   - Outcome: the current page and every later page switch immediately. The change persists.

4. **Searching.** The participant searches for something they half-remember.
   - Trigger: a query in the site search box.
   - Steps: results are scoped to their path. A Kubernetes participant does not get the
     Docker prerequisites page as a hit.
   - Outcome: every result leads to a page whose visible content matches the query.

5. **Working from the handout / PDF.** The participant prints or opens the per-path handout.
   - Trigger: the handout link, or browser print.
   - Steps: unchanged from today — `scripts/gen_handouts.py` already flattens each path into its own
     linear page and `.github/workflows/handout-pdf.yml` renders per-path PDFs.
   - Outcome: single-path output, exactly as now. This journey must not regress.

6. **Authoring path-specific content.** An author adds a Docker-only paragraph, a Kubernetes-only
   section, and a whole Docker-only page.
   - Trigger: writing content.
   - Steps: one documented markup for each case. `scripts/lint_paths.py` fails the build if
     path-specific wording is left ungated.
   - Outcome: the three leaks in the Problem section become build failures rather than things a
     participant discovers.

7. **A single-path workshop repo builds unchanged.** `k8s-101-workshop` (and 10 others) rebuild
   against the new CentralRepo image.
   - Trigger: the prod image rebuild after CentralRepo merges.
   - Steps: nothing in those repos declares a path vocabulary.
   - Outcome: byte-identical output, no new warnings, no path UI. Zero adoption cost for repos that
     do not opt in.

## Success Criteria

- [ ] With a path stored, no content belonging to the other path is present in the rendered view of
      any page — measured by grepping the built HTML with the gate applied, not by eyeballing a
      browser.
- [ ] **No flash.** The correct path is what paints first. Verifiable by the gate being applied
      before `<body>` is parsed, with no post-`DOMContentLoaded` content mutation.
- [ ] The three path-scoped pages (`1_prereqs_docker`, `2_prereqs_k8s`,
      `cloud-shell-web-preview`) are absent from the sidebar for the path they do not belong to.
- [ ] A path indicator is visible on **every** page, including the 8 pages with no `pathtabs`
      block, and it names the active path.
- [ ] The path can be changed from any page in one interaction, and the change persists across
      navigation and across a browser restart.
- [ ] Search results are scoped to the active path at page granularity — the three path-scoped pages
      do not appear for the other path.
- [ ] `content/09Reference/_index.md:54-61` (Compose profiles) and `content/04MCP/_index.md:86,91`
      are gated, and `content/_index.md:66` reads correctly pre-choice.
- [ ] **The 16 non-path tab groups are untouched.** 14 `Expected Output`, 2 `Example Output`, plus
      the 3-tab group at `content/01Intro/2_prereqs_k8s/index.md:127-157` whose middle tab
      (`Follow the logs`) is an instruction, not output. Any global "hide non-active tabs" rule
      would suppress all of these — the same defect already documented for print at `CLAUDE.md:114`.
- [ ] With JavaScript disabled, or before any choice is made, the page degrades to showing both
      paths — never to showing one path silently.
- [ ] `python3 scripts/gen_handouts.py --check` passes and both PDFs still build. In particular the
      anchored regex at `gen_handouts.py:93`
      (`^\s*\{\{%\s*pathtab\s+path="([^"]+)"\s*%\}\}\s*$`) still matches every `pathtab` — adding
      any second attribute to that shortcode breaks handout flattening silently.
- [ ] `python3 scripts/lint_paths.py` passes, and gains a check that would have caught
      `04MCP/_index.md:86`. Its current blind spot — path tokens inside bare code fences outside a
      pathtabs block are never checked (`lint_paths.py:240-241`) — is closed or explicitly recorded.
- [ ] `k8s-101-workshop` builds byte-identical output with no new warnings, and `ai-101` still
      builds 42 pages / 0 WARN.

## Out of Scope

- Adding a deployment path to any other workshop repo. `k8s-101-workshop` stays single-path
  (`CLAUDE.md:156`); AKS remains dead prose (`CLAUDE.md:160`).
- Reviving the AKS path (`content/02_quickstart_overview_faq/02_02_k8s_overview/*.md.txt`).
- Changing what the handouts contain or how the PDFs are produced. The generator already solves
  single-path output; this work must not regress it.
- Within-page search leakage on genuinely mixed pages. Page-granular search scoping is in; teaching
  the index about sub-page path boundaries is not.
- `instructor_content/` and `solution/Makefile` — outside `content/`, never linted
  (`lint_paths.py:45`), instructor-facing.
- The duplicate `Task 1`/`Task 2` sidebar labels in `k8s-101-workshop` (two sections each numbering
  their own tasks from 1). Same *class* of follow-along confusion, different repo and no path
  involvement — recorded as a finding, tracked separately.

## Open Questions

- **Does the choice belong in the URL?** Storing it client-side means a link a student pastes into
  chat carries no path, and an instructor cannot send "the Kubernetes version of this page". A
  URL-carried path fixes sharing and makes search scoping trivial, but changes every published URL
  across ~12 repos. Needs a decision before implementation, not during.
- **What does a student with no stored choice see on a lab page they deep-linked into?** Showing
  both is safe but is exactly today's confusing state. Redirecting to the chooser is more
  opinionated and can trap someone who wants to browse.
- **Is the reported difficulty actually dominated by any of items 1–5?** All five are real and
  verified in code, but their relative weight is unmeasured. If the dominant cause is the sidebar
  listing both prereq pages (item 1), that is a much smaller fix than a general gating mechanism.
  Worth asking the people who collected the participant reports what they actually observed before
  committing to the largest option.
- **Do the four path vocabulary declarations get unified?** `layouts/shortcodes/pathtab.html`,
  `gen_handouts.py:42-55`, `lint_paths.py:57`, and now `site.Params.deploymentPaths` from PR #71 all
  encode docker/k8s independently. `CLAUDE.md:109` already flags three of them as needing to agree.
  Unifying is in the spirit of this work but is a separable refactor.

---
*After this spec is approved, create the plan file to define the technical approach.*

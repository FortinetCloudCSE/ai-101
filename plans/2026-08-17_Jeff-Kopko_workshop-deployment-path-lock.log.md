# Session Log: Deployment-Path Lock for Workshop Guides
Date: 2026-08-17
Owner: Jeff Kopko
Related Plan: plans/2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.md

## Milestones
- [x] Audit both repos for actual path-branching state
- [x] Verify relearn tab persistence mechanics in theme source
- [x] Resolve design decisions with Jeff (3 question rounds)
- [x] Spec + plan + log written and committed
- [ ] Phase 0 proof of concept
- [ ] Phase 1 remaining ai-101 content
- [ ] Phase 2 path-scoped troubleshooting
- [ ] Phase 3 handouts + PDF
- [ ] Phase 4 enforcement + docs
- [ ] Phase 5 k8s-101-workshop prevention

## Commentary Stream

### 21:20
- What I'm doing: auditing `ai-101` and `k8s-101-workshop` content for deployment-path
  branching.
- Why: Jeff reported participants losing their path mid-workshop; needed the real shape
  of the problem before proposing a mechanism.
- Notes / findings:
  - `ai-101` has 6 `Docker Compose` / `Kubernetes / Helm` tab pairs and **none** sets
    `groupid` — every group independently defaults to `Docker Compose` and resets on each
    page load. This alone explains the reported symptom.
  - `k8s-101-workshop` has **no live deployment branch**. AKS is commented out at
    `01_introduction/_index.md:41`; its overview pages exist only as `*.md.txt`. Jeff's
    premise about a live AKS choice there is historical.
  - Both repos use `tabs` heavily for a *different* axis (command vs "Expected Output":
    15 groups in `ai-101`, 31 in `k8s-101-workshop`). Those must not share the path group id.

### 21:28
- What I'm doing: reading `hugo-theme-relearn` source for tab persistence.
- Why: the proposed "lock tabs for the whole path" may already exist natively; needed to
  know exactly, not approximately.
- Notes / findings:
  - `groupid` synchronizes tab selection **site-wide** and persists it —
    `layouts/shortcodes/tabs.html:3`, docs parameter table.
  - Storage: `localStorage["<absBaseUri>/tab-selections"]`, JSON `{groupid: itemid}`,
    replayed by `restoreTabSelections()` (`assets/js/theme.js:158-170`, called at :1835).
  - Written **only** on a genuine click (`isButtonEvent`, `theme.js:118,144`).
  - `itemid = anchorize(plainify(RenderString(title))) + anchorize(icon)`
    (`layouts/partials/shortcodes/tabs.html:42`).
  - Missing `itemid` in a group → falls back to first tab, **silently**.
  - Print CSS renders only the `.active` tab (`assets/css/format-print.css:163-176`).
  - `print` output format declared in the theme's own `hugo.toml:10-16` (`noUgly = true`),
    but `hugo.jinja` enables it for `home` only.
- Decision: use the native mechanism, but never let authors hand-write it — wrap it in a
  repo-local `pathtabs` shortcode so a title/icon mismatch is unexpressible.

### 21:35
- What I'm doing: auditing for path-specific instructions that sit *outside* tabs.
- Why: tab syncing cannot fix instructions that were never branched at all.
- Notes / findings:
  - `03Agents/1_lab/index.md:59`, `04MCP/1_lab/index.md:52`, `05Security/1_lab/index.md:42`
    all carry "(Docker) or ... (Kubernetes)" inline URL parentheticals.
  - `02Inference/1_lab/index.md` has zero tabs; its Kubernetes branch is one `notice`.
  - `05Security/1_lab/index.md:142-145` is a Kubernetes-only recovery step in plain prose.
- Decision: item 5 of the plan converts each of these; the linter enforces that no
  path-specific token stays outside a path block.

### 21:40
- What I'm doing: settling the print-handout mechanism with Jeff.
- Why: he confirmed printed handouts matter, and print output silently drops the
  unselected path.
- Decision: generate per-path linear pages from the lab pages with a script
  (`scripts/gen_handouts.py`), CI-checked for freshness; PDF generation included in this
  effort rather than deferred, per Jeff.

### 21:45
- What I'm doing: writing spec, plan, and log; committing before any further tool calls.
- Why: global workflow step 5a — uncommitted plan files in a shared checkout get swept
  into a concurrent session's `git add -A`.

## Commands (high-level)
- `grep -rn 'tab title=' content/` (both repos) — tally which tab groups are path branches vs output panes
- `grep -rn 'docker compose\|kubectl\|helm \|localhost:8080\|port-forward' content/*/1_lab/index.md` — find unbranched path-specific instructions
- `sed -n '70,200p' CentralRepo/themes/hugo-theme-relearn/assets/js/theme.js` — confirm tab persistence and storage key
- `cat CentralRepo/themes/hugo-theme-relearn/layouts/partials/shortcodes/tabs.html` — confirm `itemid` derivation and first-tab fallback
- `grep -n 'tab' CentralRepo/themes/hugo-theme-relearn/assets/css/format-print.css` — confirm print renders only the active tab

## Dead-ends / Rejected Options
- Option: custom JS/CSS path lock that hides non-matching content entirely.
  - Why rejected: duplicates a native theme feature; introduces no-JS and print failure
    modes; more code to upstream later.
  - Lesson learned: read the theme before designing around it — `groupid` was already the
    requested feature.
- Option: duplicate page trees, one per path.
  - Why rejected: doubles every shared paragraph; prose drifts between paths, which is the
    same class of failure being fixed.
- Option: headless-bundle snippets + `{{% include %}}` to single-source handouts.
  - Why rejected: ~15 new files and every lab page becomes an assembly of includes;
    `include` of a raw file is `readFile | safeHTML` (unrendered markdown), so it only
    works via headless *pages*, adding more moving parts than a generator.
  - Lesson learned: the tab markup is already machine-readable — transform it rather than
    restructuring the content.
- Option: print CSS override so every tab renders on paper.
  - Why rejected: Jeff chose per-path handouts; printing both paths reproduces "which
    steps are mine?" on paper.
- Option: AKS as a third `ai-101` path.
  - Why rejected: zero existing content; an unvalidated path is how participants get stuck.

## Risks & Mitigations
- Risk: a one-character title/icon difference silently reverts a group to tab 1.
  - Mitigation: `pathtabs` shortcode makes the broken form unwritable; `lint_paths.py`
    fails PRs; both, because either alone can be bypassed.
- Risk: committed handouts drift from the lab pages they were generated from.
  - Mitigation: `gen_handouts.py --check` in the PR workflow.
- Risk: per-page `outputs: ["html","print"]` may not work with the pinned image, since
  `hugo.jinja` enables `print` for `home` only.
  - Mitigation: verified in Phase 0 before Phase 3 depends on it; fallback is a repo-local
    `single.print.html` or a print stylesheet on the handout pages.
- Risk: a template upgrade overwrites CI work.
  - Mitigation: all new CI lands in new workflow files; `static.yml` untouched.
- Risk: participants entering mid-workshop from a bookmark never pass the gate and default
  to Docker Compose.
  - Mitigation: the per-lab badge is itself a clickable path selector, so the wrong path is
    both visible and fixable in place.

# Session Log: Deployment-Path Lock for Workshop Guides
Date: 2026-08-17
Owner: Jeff Kopko
Related Plan: plans/2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.md

## Milestones
- [x] Audit both repos for actual path-branching state
- [x] Verify relearn tab persistence mechanics in theme source
- [x] Resolve design decisions with Jeff (3 question rounds)
- [x] Spec + plan + log written and committed
- [x] Phase 0 proof of concept (awaiting browser sign-off)
- [x] Phase 1 remaining ai-101 content
- [x] Phase 2 path-scoped troubleshooting
- [x] Phase 3 handouts + PDF (repoConfig shortcut link not achievable — see 23:05)
- [x] Phase 4 enforcement + docs
- [ ] Phase 5 k8s-101-workshop prevention — out of scope this session, separate session

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

### 21:55
- What I'm doing: Phase 0 — `pathtabs`/`pathtab` shortcodes, the gate page, and a full
  conversion of Lab 2.
- Why: Jeff resolved the last open questions; prove the pattern on one page before
  converting the rest.
- Notes / findings:
  - `CentralRepo/scripts/local_copy.sh` copies `../UserRepo/layouts/shortcodes/*` into the
    theme's layouts at container start — repo-local shortcodes work with no config.
  - Build output lives at `/home/CentralRepo/public` **inside the container** and is not
    written to the host by `build`; had to inspect it from within the container.
  - `hugo --minify` strips attribute quotes, so grepping rendered HTML needs
    `data-tab-group=[^ >]*`, not a quoted pattern.
  - Rendered Lab 2: 3 `deploy-path` groups (badge, deploy, UI URL) with itemids
    `docker-compose` / `kubernetes--helm`; the 4 non-path groups kept random ids.
  - Live confirmation of the icon hazard: the "Expected Output" tabs render as
    `data-tab-item="expected-outputfa-fw-fas-fa-info-circle"` — the icon is concatenated
    into the id, exactly why `pathtabs` forbids icons on path tabs.
  - Found and fixed a copy-paste blocker unrelated to pathing: `cd "~/ai-101/..."` appears
    14 times across four pages. Bash does not expand `~` inside double quotes, so every one
    fails. Fixed the two in Lab 2; the rest are Phase 1.
- Decision: `pathtabs` uses `errorf`, so a missing path fails the build rather than only
  the linter. Verified: exit 1, message names the file. Defence in depth — the linter can
  be bypassed, the build cannot.
- Decision: path vocabulary is overridable via `site.Params.deploymentPaths`, so the same
  shortcodes drop into another repo with different path names (CentralRepo follow-up).

### 22:05
- What I'm doing: verifying the Phase 3 blocker — per-page `print` output.
- Why: `hugo.jinja` enables the `print` output format for `home` only; if a page cannot opt
  in, the whole handout design needs a different mechanism.
- Notes / findings: `outputs: ["html","print"]` in page front matter produced
  `zztmptest/index.print.html`. Phase 3 proceeds as planned. Temp probe page removed;
  rebuild confirms 36 pages and only the two pre-existing image WARNs.

### 22:35 — Phase 1: convert the remaining content
- What I'm doing: Labs 1/3/4 to `pathtabs`, badge + preflight on all four labs, both prereq
  pages marked whole-page, broken images fixed.
- Why: Lab 2 alone proves the mechanism but leaves three labs where a reader on the wrong
  path gets commands that cannot work. The badge matters most on the labs a bookmarked
  reader lands on without passing the gate.
- Findings:
  - 13 `cd "~` occurrences, not the 12 the plan counted.
  - Two **unterminated** `echo "UI: http://…:30280` commands (04MCP and 05Security k8s
    blocks) — a missing closing double quote. Pasting either hangs the shell waiting for
    the quote. Pre-existing, unrelated to paths, fixed while in the file.
  - `../searchweb.png` could not be fixed in place: with `uglyURLs` the page renders to
    `04mcp/1_lab.html`, so a `../` path leaves the bundle. `git mv`'d the PNG into
    `1_lab/` and referenced it bare, which makes it a real page resource — the same fix
    the handout generator later needed for every image it copies.
  - Cross-page links between sibling leaf bundles warn (`is not a page or a resource`)
    whether or not they carry a trailing slash. `/`-rooted content refs
    (`/01Intro/2_prereqs_k8s`) resolve cleanly and render baseURL-prefixed. Reused in
    `gen_handouts.py`.
- Decisions:
  - Whole-page `deploymentPath:` front matter for pages that are entirely one path (both
    prereq pages, later the Cloud Shell page and the handouts) rather than wrapping a
    whole page in a single-path tab block. The generator and the linter both read it.
  - Reworded `03Agents/_index.md`'s conceptual prose to drop its path tokens instead of
    adding a linter allowlist entry. Every allowlist entry is a place the guardrail is
    off; rewording removes the exception entirely.
- Verified: 36 pages, **0 WARN**, 0 ERROR. Commit `8adc164`.

### 22:50 — Phase 2: path-scope the reference section
- What I'm doing: mark the Cloud Shell page Kubernetes-only, rebuild `09Reference/_index.md`
  as a per-path index.
- Why: the reference section was the one place a reader could still not tell which
  troubleshooting steps were theirs.
- Notes: the `docker compose command not found` and Web Preview `Unauthorized` entries were
  merged into one `### Path-specific issues` `pathtabs` block, so the two paths sit side by
  side instead of interleaved. The OpenAI-endpoint comparison table row became
  `http://<ollama-host>:11434/v1` — it was describing the API shape, not instructing, so a
  placeholder host is more accurate anyway and needs no allowlist entry.
- Verified: 36 pages, 0 WARN, 0 ERROR. Commit `80baf28`.

### 23:05 — Phase 3: handouts + PDF
- What I'm doing: `scripts/gen_handouts.py`, generated handouts, `handout-pdf.yml`.
- Why: print CSS renders only the active tab, so a printed lab page silently omits the
  other path — the exact bug being fixed, reintroduced on paper.
- Findings:
  - Cross-contamination bug of my own making: the fence branch routed fenced code inside a
    *non-kept* `pathtab` to the output buffer, so both paths' commands landed in both
    handouts. Only caught by grepping the output for the other path's tokens — the page
    looked plausible. Worth noting that "it renders" proves nothing here.
  - `hidden: true` is the documented relearn menu-exclusion flag
    (`frontmatter.toml:228`, consumed by `menu.html` and `_relearn/pageIsHidden.gotmpl`).
    Confirmed in the built site rather than trusting the docs: `grep -rl handout` over
    every rendered HTML file matches only the handout pages themselves.
  - **`repoConfig.json` shortcuts cannot link an internal page.** `hugo.jinja` emits only
    `url =`, never `pageRef`; relearn's `menuPermalink.gotmpl` runs the value through
    `relLangURL`, which strips the baseURL off a fully-qualified self-URL, so the result is
    classified "local" and warns on *every* page. Measured: adding the two handout
    shortcuts took the build from 0 to 2 WARNs. Reverted; the handouts are linked from each
    path's reference table instead. Accepting 2 permanent benign WARNs would have wrecked
    the "0 WARN means clean" rule the rest of this work depends on. Filed as a follow-up to
    add `pageRef` support upstream in `hugo.jinja`.
  - Handout PDFs need `--disable-dev-shm-usage`. The Docker handout (22 pages) rendered
    fine; the Kubernetes one (26 pages) failed with `Printing failed.` until the flag was
    added. Default `/dev/shm` is 64 MB, and only the bigger input exceeds it — a bug that
    would have shipped green if only one handout had been tested.
  - `chromedp/headless-shell` ignores `--print-to-pdf` and hangs (it expects to be driven
    over the DevTools protocol); a full Chromium image works. Verified with
    `zenika/alpine-chrome`.
  - The print HTML roots every asset at `/ai-101/...`, so `file://` rendering silently
    loses the print stylesheet. The workflow serves the site under that prefix over HTTP.
- Decisions:
  - `OUT_DIR` is fully generator-owned: `--check` reports orphans and a normal run deletes
    them, so a renamed page cannot leave a stale handout behind that still builds.
  - Bundle images are copied into the handout bundle under a `<dir-slug>-<name>.png` prefix
    rather than referenced across bundles — genuine page resources, no WARN, and they
    survive into the PDF.
  - Excluded the gate page from the handouts: its `pathtabs` block *is* the interactive
    chooser, so on paper it has nothing to say.
- Verified: 42 pages, 0 WARN, 0 ERROR; `--check` clean; both `index.print.html` render
  (120 KB / 151 KB); both PDFs render (22 pages / 991 KB, 26 pages / 1.49 MB); the only
  cross-path token hits left are three prose lines that explicitly tell the reader the
  other path does not apply. Commit `ece618c`.

### 23:20 — Phase 4: enforcement + docs
- What I'm doing: `scripts/lint_paths.py`, `path-lint.yml`, `CLAUDE.md`, `README.md`.
- Why: `pathtabs` prevents the malformed *block*, but nothing stopped someone from writing
  a `kubectl` command in plain prose — which is how the original bug got in.
- Findings: the linter passed on the first run, which is exactly when a linter is most
  likely to be silently no-oping. Proved each of the five checks by breaking a page,
  confirming exit 1 with the right check name, and restoring. The first attempt at that
  proof was itself wrong — the injected `kubectl` line landed *inside* the preflight
  `pathtabs` block, so the linter correctly said nothing. Re-ran with the line appended
  outside any block.
- Decisions: the `cd "~` check deliberately runs *before* the fenced-code skip, since that
  is the only place the pattern ever appears. Everything repo-specific sits in a CONFIG
  block at the top; emptying `PATH_TITLE_RE`, `PATH_TOKENS` and `ALLOWLIST` leaves a script
  another workshop repo can adopt as-is, with three of the five checks still live.
- Verified: `lint_paths: clean (14 pages, handouts up to date)` on `HEAD`; 42 pages,
  0 WARN, 0 ERROR. Commit `1242cbf`.

### 23:30 — Close-out
- Not completed: **TodoWrite was unavailable in this session** (`ToolSearch` for it returned
  no match), so the per-checkbox task list the prompt asked for could not be created.
  Phases were tracked inline and against the plan file instead.
- Not completed: the `repoConfig.json` shortcut link (Phase 3) — see 23:05.
- Still open from Phase 0: Jeff's browser sign-off on the UX. Nothing pushed, no PR opened.

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
- Option: handout links as `menu.shortcuts` entries in `scripts/repoConfig.json` (Phase 3).
  - Why rejected: costs 2 permanent Hugo WARNs on every page. `hugo.jinja` emits only
    `url =` for shortcuts and relearn runs it through `relLangURL`, which strips the
    baseURL off a self-URL, so no form of the link avoids the "is a local URL" warning.
  - Lesson learned: a benign warning is not free in a repo where `errorLevel = warning` is
    the only line of defence — it raises the noise floor that real breakage hides in.
- Option: `chromedp/headless-shell` for the PDF step.
  - Why rejected: it does not honour `--print-to-pdf` and hangs indefinitely; it expects to
    be driven over the DevTools protocol. A full Chromium build works directly.

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

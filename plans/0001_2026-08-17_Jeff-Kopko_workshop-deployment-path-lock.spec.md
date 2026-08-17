# Spec: Deployment-Path Lock for Workshop Guides
Date: 2026-08-17
Owner: Jeff Kopko
Slug: workshop-deployment-path-lock
Spec File: plans/0001_2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.spec.md
Plan File: plans/0001_2026-08-17_Jeff-Kopko_workshop-deployment-path-lock.md

## Problem

Both `ai-101` and `k8s-101-workshop` open with a deployment choice, then expect the
participant to carry that choice through every later technical step by hand.
Participants lose the thread and follow steps that belong to the other path.

Measured state of `ai-101` (verified 2026-08-17 on `jkopkoEdits`):

1. **Six path-branch tab groups, none synchronized.** `Docker Compose` / `Kubernetes / Helm`
   tab pairs exist at `content/03Agents/1_lab/index.md:15`, `content/04MCP/1_lab/index.md:15,118`,
   `content/05Security/1_lab/index.md:15,124,201`. None sets `groupid`, so the theme
   assigns each a random group id: every group independently defaults to its first tab
   (`Docker Compose`) and resets on every page load. A Kubernetes participant must
   re-click the correct tab six times, and again after every navigation.
2. **Path-specific instructions outside tabs.** These are unbranched prose the
   participant must filter mentally:
   - `content/03Agents/1_lab/index.md:59`, `content/04MCP/1_lab/index.md:52`,
     `content/05Security/1_lab/index.md:42` — "Open the UI at `http://localhost:8080`
     (Docker) or `http://localhost:8100` / Web Preview URL (Kubernetes)".
   - `content/05Security/1_lab/index.md:142-145` — a Kubernetes-only port-forward
     recovery step in plain prose.
   - `content/02Inference/1_lab/index.md:11-17` — Lab 1 has **no tabs at all**; its
     Kubernetes branch is a single `notice` and the lab scripts assume `localhost:11434`.
3. **No indication of which path you are on.** Nothing on any page states the chosen
   path, so a participant who drifted has no signal until a command fails.
4. **No state check between labs.** Labs 2-4 each depend on the previous lab's teardown
   plus, on Kubernetes, background `kubectl port-forward` jobs surviving across pages.
   Nothing verifies that before the next lab's steps begin.

`k8s-101-workshop` has **no live deployment branch today** — AKS is commented out at
`content/01_introduction/_index.md:41` and its overview pages exist only as disabled
`*.md.txt`. Its exposure is prospective: a future second path would be built with the
same defects.

## Users & Stakeholders

- **Workshop participant** (primary) — follows the published site during a timed,
  instructor-led session or self-paced. Loses time and confidence when a command
  from the wrong path fails.
- **Instructor / presenter** — fields "my command failed" interruptions; needs to
  deep-link a specific path's setup page and to hand out printable material.
- **Workshop authors** (Fortinet CSE team, multiple contributors across ~7 workshop
  repos) — must be able to add a branch point without knowing theme internals.

## User Journeys

1. **Choose once, stay on path** — participant starts `ai-101`
   - Trigger: opens Setup & Prerequisites
   - Steps: sees one explicit path chooser; clicks `Kubernetes / Helm`; follows the
     linked setup page; proceeds through Labs 1-4
   - Outcome: every branch point on every later page is already showing the
     Kubernetes variant, on every page load, without further clicks

2. **Confirm which path I am on** — participant returns after a break
   - Trigger: reopens Lab 3 in a new tab
   - Steps: top of the page states the current path and gives one command to verify
     the environment is in the expected state, with the expected output
   - Outcome: participant either confirms state and continues, or sees immediately
     that they are on the wrong path and switches in place

3. **Switch path deliberately** — participant's laptop can't run the lab
   - Trigger: Docker Compose path fails on their machine mid-Lab-2
   - Steps: selects the other path at the top of the page
   - Outcome: that click re-points every branch point on the whole site; no page is
     left showing a mix of the two

4. **Print a single-path handout** — instructor prepares for a room with poor Wi-Fi
   - Trigger: before the session
   - Steps: opens the handout page for one path, or downloads the generated PDF
   - Outcome: a linear document containing only that path's steps — the other path's
     commands are absent, not merely collapsed

5. **Author adds a branch point** — contributor documents a new lab step
   - Trigger: opens a PR adding a `kubectl` command
   - Steps: uses the documented convention; CI checks it
   - Outcome: PR fails if the branch is unsynchronized, mistitled, or if a
     path-specific command sits outside a path tab

## Success Criteria

- [ ] Selecting a path once causes **every** path-branch block in the workshop to show
      that path, persisting across page loads and navigation.
- [ ] Every page containing path-specific steps states the current path at the top.
- [ ] Each lab opens with a path-correct preflight command plus expected output.
- [ ] Zero path-specific commands (`docker compose`, `docker exec`, `kubectl`, `helm`,
      `localhost:8080|8100|11434`, `port-forward`, NodePort/Web Preview URLs) remain
      outside a path-scoped block in `content/`.
- [ ] Every path-branch tab group uses the identical group id and identical tab title
      strings, verified mechanically — a mismatch cannot ship silently.
- [ ] A generated, linear, single-path handout page exists per path, printable, and a
      PDF per path is produced by CI.
- [ ] Handouts are derived from the lab pages, and CI fails if they are stale.
- [ ] A first-time visitor with no stored choice, and a visitor with JavaScript
      disabled, both still see a coherent, followable page.
- [ ] `k8s-101-workshop` carries the same documented convention and the same CI check,
      so a future second path is built correctly from the start.

## Out of Scope

- **AKS as a third `ai-101` path.** Discussed and explicitly dropped from this effort;
  no AKS content exists to convert.
- **Reviving AKS in `k8s-101-workshop`.** Remains single-path (self-managed kubeadm).
- **Removing the dead AKS references in `k8s-101-workshop`** (`01_introduction/_index.md:41`,
  the commented block in `02_quickstart_overview_faq/_index.md`) and **fixing its
  beginner/experienced routing text**. Both are real confusion sources; deferred by
  decision, tracked as follow-ups.
- **Preflight blocks for `k8s-101-workshop` hands-on pages.** Deferred.
- **Upstreaming to CentralRepo.** Prove the pattern in `ai-101` first; the CentralRepo
  PR is a follow-up.
- Rewriting lab content, changing the lab app, or altering Helm/Compose behaviour.

## Open Questions

- Should the generated handout pages appear in the site sidebar, or be reachable only
  from `scripts/repoConfig.json` shortcuts and the reference section?
- `k8s-101-workshop` already ships `content/k8s-101.pdf` linked from `repoConfig.json`.
  If handout PDFs become the pattern, does that file get regenerated or retired?

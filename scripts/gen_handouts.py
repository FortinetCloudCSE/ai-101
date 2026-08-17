#!/usr/bin/env python3
"""Generate one linear, single-path handout page per deployment path.

The lab pages are the single source of truth. This script walks ``content/`` in
site order and, for each deployment path, emits one page with every ``pathtabs``
block flattened down to that path's body. The other path is dropped entirely --
not collapsed behind a tab -- because print output renders only the active tab
(``format-print.css``), so a printed tabbed page silently omits the other path.

For the same reason, the *non*-path tab groups (the command-vs-"Expected Output"
axis) are flattened as well, into labelled subsections. Leaving them as tabs cost
12 hidden panels in the Docker handout and 17 in the Kubernetes one.

Usage
-----
    python3 scripts/gen_handouts.py            # write the handout pages
    python3 scripts/gen_handouts.py --check    # exit 1 if regenerating would change anything

Run from the repo root (or anywhere -- paths are resolved relative to this file).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT = REPO_ROOT / "content"
OUT_DIR = CONTENT / "09Reference" / "handouts"

GENERATOR = "scripts/gen_handouts.py"

# Deployment paths. Keys must match the ``path=`` values accepted by the
# ``pathtab`` shortcode (layouts/shortcodes/pathtab.html) and the vocabulary in
# scripts/lint_paths.py.
PATHS = [
    {
        "key": "docker",
        "title": "Docker Compose",
        "slug": "handout-docker",
        "weight": 20,
    },
    {
        "key": "k8s",
        "title": "Kubernetes / Helm",
        "slug": "handout-k8s",
        "weight": 30,
    },
]

# A source page is included in the handouts when it either contains a pathtabs
# block or declares a whole-page ``deploymentPath``. That is exactly the set of
# pages carrying path-specific instructions; pure-theory pages are left out so
# the handout stays a followable command sheet.
#
# Directories never walked (the generated output itself).
EXCLUDE_DIRS = {OUT_DIR}

# Pages skipped even though they contain a pathtabs block, keyed by path relative
# to content/. The gate page's pathtabs block *is* the interactive path chooser --
# on paper the path is already chosen, so it has nothing to say.
EXCLUDE_PAGES = {Path("01Intro/_index.md")}

# Paragraphs that only make sense on the interactive site: they tell the reader to
# click the other path's tab, which is impossible on paper. Matched against the
# whole paragraph (these sentences wrap across lines), outside fenced code.
STRIP_PARAGRAPH_PATTERNS = [
    re.compile(r"Click the \*\*(Docker Compose|Kubernetes / Helm)\*\* tab"),
]

# Individual lines dropped from the handout, outside fenced code. Used for table
# rows -- a whole table is one "paragraph" to the stripper above, so a row must be
# removed line-by-line. The reference index links the handouts; inside a handout
# that row would link to the page you are already reading.
STRIP_LINE_PATTERNS = [
    re.compile(r"^\|\s*\[Printable handout\]"),
]

# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------

FRONT_MATTER_DELIM = "---"
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
PATHTABS_OPEN_RE = re.compile(r"^\s*\{\{<\s*pathtabs\b.*?>\}\}\s*$")
PATHTABS_CLOSE_RE = re.compile(r"^\s*\{\{<\s*/\s*pathtabs\s*>\}\}\s*$")
PATHTAB_OPEN_RE = re.compile(r"^\s*\{\{%\s*pathtab\s+path=\"([^\"]+)\"\s*%\}\}\s*$")
PATHTAB_CLOSE_RE = re.compile(r"^\s*\{\{%\s*/\s*pathtab\s*%\}\}\s*$")
HEADING_RE = re.compile(r"^(#{1,5})(\s+)(.*)$")

# Plain (non-path) tab groups -- the command-vs-"Expected Output" axis. ``\b`` and
# the mandatory whitespace before ``title=`` keep these from matching ``pathtabs``
# / ``pathtab``, which are flattened separately and first.
TABS_OPEN_RE = re.compile(r"^\s*\{\{<\s*tabs\b.*?>\}\}\s*$")
TABS_CLOSE_RE = re.compile(r"^\s*\{\{<\s*/\s*tabs\s*>\}\}\s*$")
TAB_OPEN_RE = re.compile(r"^\s*\{\{%\s*tab\s+.*?title=\"([^\"]*)\".*?%\}\}\s*$")
TAB_CLOSE_RE = re.compile(r"^\s*\{\{%\s*/\s*tab\s*%\}\}\s*$")

SIMPLE_FM_RE = re.compile(r"^(\w+)\s*:\s*(.*)$")


def split_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Return (front matter as a flat str->str dict, body)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONT_MATTER_DELIM:
        return {}, text
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONT_MATTER_DELIM:
            fm: dict[str, str] = {}
            for raw in lines[1:i]:
                m = SIMPLE_FM_RE.match(raw.strip())
                if m:
                    fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
            return fm, "\n".join(lines[i + 1 :])
    return {}, text


def iter_lines_with_fence_state(lines: list[str]):
    """Yield (line, in_fence) so transforms never touch fenced code blocks."""
    fence: str | None = None
    for line in lines:
        m = FENCE_RE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)[0] * 3
                yield line, True
                continue
            yield line, False
        else:
            yield line, True
            if m and line.strip().startswith(fence):
                fence = None


# --------------------------------------------------------------------------
# Page model
# --------------------------------------------------------------------------


class Page:
    def __init__(self, md_path: Path):
        self.md_path = md_path
        self.rel_md = md_path.relative_to(CONTENT)
        self.rel_dir = md_path.parent.relative_to(CONTENT)
        text = md_path.read_text(encoding="utf-8")
        self.front_matter, self.body = split_front_matter(text)
        self.title = self.front_matter.get("title", md_path.parent.name)
        self.deployment_path = self.front_matter.get("deploymentPath") or None

    @property
    def weight(self) -> int:
        try:
            return int(self.front_matter.get("weight", "0"))
        except ValueError:
            return 0

    @property
    def has_pathtabs(self) -> bool:
        return bool(PATHTABS_OPEN_RE.search(self.body) or "{{< pathtabs" in self.body)

    def relevant_to(self, path_key: str) -> bool:
        if self.rel_md in EXCLUDE_PAGES:
            return False
        if self.deployment_path and self.deployment_path != path_key:
            return False
        return self.has_pathtabs or self.deployment_path is not None


def collect_pages() -> list[Page]:
    pages: list[Page] = []
    for md in sorted(CONTENT.rglob("*.md")):
        if md.name not in ("index.md", "_index.md"):
            continue
        if any(str(md).startswith(str(d)) for d in EXCLUDE_DIRS):
            continue
        pages.append(Page(md))
    return pages


def dir_weight(rel_dir: Path, by_dir: dict[Path, Page]) -> int:
    page = by_dir.get(rel_dir)
    return page.weight if page else 0


def site_order(pages: list[Page]) -> list[Page]:
    """Sort pages the way the site presents them: section weight, then page weight.

    The key is one (weight, name) pair per path component. A section's own
    ``_index.md`` has a shorter key than its children, and Python orders a
    shorter tuple-prefix first, so a section index sorts ahead of its pages.
    """
    by_dir = {p.rel_dir: p for p in pages}

    def key(page: Page):
        parts = page.rel_dir.parts
        return [
            (dir_weight(Path(*parts[: i + 1]), by_dir), parts[i])
            for i in range(len(parts))
        ]

    return sorted(pages, key=key)


# --------------------------------------------------------------------------
# Body transform
# --------------------------------------------------------------------------


def flatten_pathtabs(body: str, path_key: str, source: str) -> str:
    """Replace every pathtabs block with just ``path_key``'s body."""
    out: list[str] = []
    # None = outside any pathtabs block. Otherwise a dict of block state.
    block: dict | None = None

    for line, in_fence in iter_lines_with_fence_state(body.splitlines()):
        if in_fence:
            if block is None:
                out.append(line)
            elif block["keep"]:
                block["buf"].append(line)
            # else: fenced code inside the other path's tab -- dropped
            continue

        if block is None:
            if PATHTABS_OPEN_RE.match(line):
                block = {"buf": [], "keep": False, "seen": set()}
                continue
            out.append(line)
            continue

        m = PATHTAB_OPEN_RE.match(line)
        if m:
            key = m.group(1)
            if key in block["seen"]:
                raise SystemExit(f"{source}: pathtabs block defines {key!r} twice")
            block["seen"].add(key)
            block["keep"] = key == path_key
            continue
        if PATHTAB_CLOSE_RE.match(line):
            block["keep"] = False
            continue
        if PATHTABS_CLOSE_RE.match(line):
            missing = {p["key"] for p in PATHS} - block["seen"]
            if missing:
                raise SystemExit(
                    f"{source}: pathtabs block is missing path(s) {sorted(missing)}"
                )
            body_lines = block["buf"]
            while body_lines and not body_lines[0].strip():
                body_lines.pop(0)
            while body_lines and not body_lines[-1].strip():
                body_lines.pop()
            out.extend(body_lines)
            block = None
            continue
        if block["keep"]:
            block["buf"].append(line)

    if block is not None:
        raise SystemExit(f"{source}: unclosed pathtabs block")
    return "\n".join(out)


def flatten_plain_tabs(body: str, source: str) -> str:
    """Turn every non-path tab group into labelled subsections.

    Path tabs are resolved by ``flatten_pathtabs``; what is left is the
    command-vs-"Expected Output" axis. Those must be flattened too, for the same
    reason the path tabs are: ``format-print.css`` renders only the *active* tab,
    so in a PDF every second and third panel silently disappears. That loses all
    the expected-output panels a reader needs to check their work on paper, and at
    least one real instruction ("Follow the logs").

    Each tab becomes a bold label followed by its body. Deliberately not a
    heading: heading depth here is already four to five levels deep after
    ``demote_headings``, and these labels do not belong in the table of contents.
    """
    out: list[str] = []
    # None = outside any tab group. Otherwise a list of rendered lines.
    block: list[str] | None = None

    def emit_label(title: str) -> None:
        if block and block[-1].strip():
            block.append("")
        if title:
            block.append(f"**{title}**")
            block.append("")

    for line, in_fence in iter_lines_with_fence_state(body.splitlines()):
        if in_fence:
            (out if block is None else block).append(line)
            continue

        if block is None:
            if TABS_OPEN_RE.match(line):
                block = []
                continue
            out.append(line)
            continue

        if TABS_OPEN_RE.match(line):
            raise SystemExit(f"{source}: nested tabs groups are not supported")
        m = TAB_OPEN_RE.match(line)
        if m:
            emit_label(m.group(1).strip())
            continue
        if TAB_CLOSE_RE.match(line):
            continue
        if TABS_CLOSE_RE.match(line):
            while block and not block[0].strip():
                block.pop(0)
            while block and not block[-1].strip():
                block.pop()
            out.extend(block)
            block = None
            continue
        block.append(line)

    if block is not None:
        raise SystemExit(f"{source}: unclosed tabs group")
    return "\n".join(out)


def demote_headings(body: str) -> str:
    """Push every heading down one level so page titles can be the ``##`` spine."""
    out: list[str] = []
    for line, in_fence in iter_lines_with_fence_state(body.splitlines()):
        if in_fence:
            out.append(line)
            continue
        m = HEADING_RE.match(line)
        out.append(f"#{m.group(1)}{m.group(2)}{m.group(3)}" if m else line)
    return "\n".join(out)


def strip_site_only_paragraphs(body: str) -> str:
    out: list[str] = []
    para: list[str] = []
    para_fenced = False

    def flush() -> None:
        nonlocal para, para_fenced
        if para and not para_fenced:
            joined = " ".join(l.strip() for l in para)
            if any(p.search(joined) for p in STRIP_PARAGRAPH_PATTERNS):
                para, para_fenced = [], False
                return
        out.extend(para)
        para, para_fenced = [], False

    for line, in_fence in iter_lines_with_fence_state(body.splitlines()):
        if in_fence:
            para_fenced = True
            para.append(line)
            continue
        if not line.strip():
            flush()
            out.append(line)
            continue
        if any(p.search(line) for p in STRIP_LINE_PATTERNS):
            continue
        para.append(line)
    flush()
    return "\n".join(out)


LINK_RE = re.compile(r"(!?)\[([^\]]*)\]\(\s*([^)\s]+)([^)]*)\)")


def _absolute_page_ref(source_dir: Path, dest: str) -> str:
    """``../../09Reference/`` on a page in 05Security/1_lab -> ``/09Reference``.

    Hugo's link render hook resolves a ``/``-rooted content path to a real page and
    emits the baseURL-prefixed URL, so the link survives being moved into the
    handout bundle. Verified against this image: relative sibling refs warn
    ``is not a page or a resource``, ``/``-rooted refs do not.
    """
    anchor = ""
    if "#" in dest:
        dest, anchor = dest.split("#", 1)
        anchor = "#" + anchor
    if not dest:
        return anchor
    target = (source_dir / dest).as_posix()
    parts: list[str] = []
    for part in target.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    if parts and parts[-1] in ("index.md", "_index.md"):
        parts.pop()
    return "/" + "/".join(parts) + anchor


def rewrite_refs(body: str, page: Page, resources: dict[str, Path]) -> str:
    """Make links and images valid from the handout bundle's location.

    Page links become ``/``-rooted content refs. Bundle-resource images are
    recorded in ``resources`` for copying into the handout bundle under a
    collision-proof name, and rewritten to that bare name so they stay genuine
    page resources (no ``is not a resource`` warning, works in print and PDF).
    """
    prefix = page.rel_dir.as_posix().replace("/", "-").lower()

    def repl(m: re.Match) -> str:
        bang, text, dest, tail = m.groups()
        if dest.startswith(("http://", "https://", "mailto:", "#", "/")):
            return m.group(0)
        if bang:
            src = (page.md_path.parent / dest.lstrip("./")).resolve()
            if not src.is_file():
                return m.group(0)
            name = f"{prefix}-{src.name}"
            resources[name] = src
            return f"{bang}[{text}]({name}{tail})"
        return f"{bang}[{text}]({_absolute_page_ref(page.rel_dir, dest)}{tail})"

    out: list[str] = []
    for line, in_fence in iter_lines_with_fence_state(body.splitlines()):
        out.append(line if in_fence else LINK_RE.sub(repl, line))
    return "\n".join(out)


def collapse_blank_runs(body: str) -> str:
    out: list[str] = []
    blanks = 0
    for line in body.splitlines():
        if line.strip():
            blanks = 0
            out.append(line)
        else:
            blanks += 1
            if blanks < 3:
                out.append("")
    return "\n".join(out).strip("\n")


def render_page(page: Page, path_key: str, resources: dict[str, Path]) -> str:
    source = str(page.md_path.relative_to(REPO_ROOT))
    body = flatten_pathtabs(page.body, path_key, source)
    body = flatten_plain_tabs(body, source)
    body = strip_site_only_paragraphs(body)
    body = rewrite_refs(body, page, resources)
    body = demote_headings(body)
    return collapse_blank_runs(body)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def build_handout(spec: dict, pages: list[Page], resources: dict[str, Path]) -> str:
    included = [p for p in pages if p.relevant_to(spec["key"])]
    parts = [
        "---",
        f'title: "Handout — {spec["title"]}"',
        f'linkTitle: "Handout — {spec["title"]}"',
        f'weight: {spec["weight"]}',
        "hidden: true",
        f'deploymentPath: {spec["key"]}',
        'outputs: ["html", "print"]',
        "---",
        "",
        f'{{{{% notice style="note" title="Generated file — do not edit" %}}}}',
        f"This page is generated by `{GENERATOR}` from the workshop pages. Edit the",
        f"source pages instead and re-run the generator; CI fails if this file is stale.",
        "",
        f"It contains **only the {spec['title']} path**. Print it, or use your browser's",
        "print view for a clean single-path PDF.",
        "{{% /notice %}}",
        "",
    ]
    for page in included:
        rendered = render_page(page, spec["key"], resources)
        if not rendered.strip():
            continue
        parts.append(f"## {page.title}")
        parts.append("")
        parts.append(rendered)
        parts.append("")
        parts.append("---")
        parts.append("")
    while parts and parts[-1] in ("", "---"):
        parts.pop()
    return "\n".join(parts).rstrip("\n") + "\n"


def build_section_index() -> str:
    rows = "\n".join(
        f'| [Handout — {s["title"]}]({s["slug"]}/) | `{s["key"]}` |' for s in PATHS
    )
    return f"""---
title: "Printable handouts"
linkTitle: "Printable handouts"
weight: 20
hidden: true
---

One linear page per deployment path, containing only that path's steps. Generated
from the workshop pages by `{GENERATOR}` — do not edit the handouts by hand.

| Handout | Path |
|---|---|
{rows}

Each handout also renders a print-optimised variant at `index.print.html`, which is
what CI turns into a PDF artifact.
"""


def targets() -> dict[Path, bytes]:
    """Every byte OUT_DIR should contain. OUT_DIR is fully generator-owned."""
    pages = site_order(collect_pages())
    out: dict[Path, bytes] = {
        OUT_DIR / "_index.md": build_section_index().encode("utf-8")
    }
    for spec in PATHS:
        resources: dict[str, Path] = {}
        bundle = OUT_DIR / spec["slug"]
        out[bundle / "index.md"] = build_handout(spec, pages, resources).encode("utf-8")
        for name, src in resources.items():
            out[bundle / name] = src.read_bytes()
    return out


def existing() -> set[Path]:
    if not OUT_DIR.exists():
        return set()
    return {p for p in OUT_DIR.rglob("*") if p.is_file()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if regenerating would change anything (CI freshness gate)",
    )
    args = ap.parse_args()

    wanted = targets()
    orphans = sorted(existing() - set(wanted))

    if args.check:
        stale = [
            path
            for path, content in wanted.items()
            if not path.exists() or path.read_bytes() != content
        ]
        if stale or orphans:
            print("Handouts are stale. Re-run:  python3 " + GENERATOR, file=sys.stderr)
            for path in stale:
                print(f"  changed: {path.relative_to(REPO_ROOT)}", file=sys.stderr)
            for path in orphans:
                print(f"  orphan:  {path.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        print(f"Handouts up to date ({len(wanted)} files).")
        return 0

    for path, content in sorted(wanted.items()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    for path in orphans:
        path.unlink()
        print(f"removed {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Evaluation adapter for the output of the site's existing checks (seo-check.mjs, a11y-check.mjs).

It adds no criteria. It reads the text those scripts print, verifies that the output has the
known shape and agrees with the real exit code, and maps each message to a stable criterion.
Anything it does not recognise stays visible: an unknown output shape makes the check
'unparsed' (the run is incomplete, never clean); an unknown message becomes '<family>.unclassified'.

Identity of a finding = site + criterion + location (+ a stable detail) - never the message text
and never a line number, so counts inside messages may change without creating a new finding.
"""
import re
from pathlib import Path

ERROR, WARNING, EDITORIAL = "technical-error", "warning", "editorial-suggestion"
CLASS_LABEL = {ERROR: "technical error", WARNING: "warning", EDITORIAL: "editorial suggestion"}
FAMILY_PREFIX = {"seo": "SEO", "a11y": "A11Y", "editorial": "ED"}
FAMILY_SCRIPT = {"seo": "seo-check.mjs (npm run seo:check)", "a11y": "a11y-check.mjs (npm run a11y:check)"}
FAMILY_RULES = {"seo": "rules/seo.md", "a11y": "rules/accessibility.md"}
GLOBAL = "(site)"

# criterion -> (short title, why it can matter, rule reference, priority level, priority reason, generic proposal)
CATALOG = {
    "seo.title-missing": ("page has no <title>", "Search results and browser tabs have nothing to show.", "seo.md section 2", "high", "check error: the audit fails", "Pass a unique title (30-60 characters) to BaseLayout."),
    "seo.title-too-long": ("title is long", "Long titles are often cut off in results (editorial judgement; no ranking claim).", "seo.md section 2 (30-60 characters)", "low", "warning only; the script threshold is 65", "Shorten the title to 60 characters or less, main topic first, without dropping meaning."),
    "seo.title-too-short": ("title is very short", "A very short title says little about the page.", "seo.md section 2 (30-60 characters)", "low", "warning only", "Extend the title to a descriptive 30-60 characters using words that are already true for the page."),
    "seo.description-missing": ("page has no meta description", "Result snippets then fall back to arbitrary page text.", "seo.md section 2", "high", "check error: the audit fails", "Pass a unique description of 120-160 characters to BaseLayout."),
    "seo.description-too-long": ("meta description is too long", "Long descriptions are cut off in snippets (editorial judgement).", "seo.md section 2 (max 160)", "low", "warning only", "Shorten the description to 160 characters or less."),
    "seo.description-too-short": ("meta description is short", "seo.md asks for 120-160 characters; a very short description gives people little reason to open the page. The length is a guideline, not a reason to pad.", "seo.md section 2 (120-160)", "medium", "warning; the page is indexable and the description is the snippet candidate", "Rewrite the description as one concrete sentence of 120-160 characters from facts already on the page; do not add keywords."),
    "seo.canonical-missing": ("missing canonical link", "Duplicate URLs cannot be resolved to the intended one.", "seo.md section 2", "high", "check error", "Restore the canonical link in BaseLayout."),
    "seo.canonical-offsite": ("canonical points off-site", "The canonical must name this site.", "seo.md section 2", "high", "check error", "Fix the canonical URL to the site address."),
    "seo.h1-count": ("page does not have exactly one <h1>", "One h1 states the page topic.", "seo.md section 2", "high", "check error", "Keep exactly one h1 that matches the title's topic."),
    "seo.lang-missing": ("missing lang on <html>", "Language is needed by search engines and assistive technology.", "seo.md section 2", "high", "check error", "Set <html lang=\"en\">."),
    "seo.viewport-missing": ("missing viewport meta", "Mobile rendering depends on it.", "seo.md section 6", "high", "check error", "Restore the viewport meta tag in BaseLayout."),
    "seo.open-graph-missing": ("missing Open Graph property", "Shared links lack a proper card.", "seo.md section 5", "high", "check error", "Restore the Open Graph tags in BaseLayout."),
    "seo.twitter-card-missing": ("missing twitter:card", "Shared links lack a proper card.", "seo.md section 5", "high", "check error", "Restore the twitter:card tag in BaseLayout."),
    "seo.image-alt-missing": ("image without alt", "Images need alt text (empty alt for decoration).", "seo.md section 2, accessibility.md", "high", "check error", "Add a descriptive alt, or alt=\"\" for decorative images."),
    "seo.image-size-missing": ("image without width/height", "Missing dimensions can cause layout shift.", "seo.md section 6", "low", "warning only", "Set width and height on the image."),
    "seo.json-ld-invalid": ("invalid JSON-LD", "Broken structured data is ignored. The check tests JSON syntax only, not schema.org validity.", "seo.md section 1", "high", "check error", "Fix the JSON-LD syntax of the page."),
    "seo.duplicate-title-description": ("duplicate title or description", "Pages should be distinguishable in results.", "seo.md section 2 (unique)", "high", "check error", "Give each listed page its own title and description."),
    "seo.site-file-missing": ("required site file missing", "robots.txt and the sitemap are expected in the build.", "seo.md section 1", "high", "check error", "Restore the page that generates the missing file."),
    "seo.sitemap-url-without-page": ("sitemap URL has no page", "The sitemap lists a URL that is not built.", "seo.md section 3", "high", "check error", "Remove the entry or build the page."),
    "seo.page-not-in-sitemap": ("indexable page is not in the sitemap", "New pages should be listed.", "seo.md section 3", "medium", "warning", "Add the page to src/pages/sitemap.xml.ts."),
    "a11y.main-count": ("page does not have exactly one <main>", "Landmark navigation depends on it.", "accessibility.md", "high", "check error", "Use exactly one <main>."),
    "a11y.header-missing": ("missing <header>", "Landmark navigation.", "accessibility.md", "high", "check error", "Restore the header landmark."),
    "a11y.footer-missing": ("missing <footer>", "Landmark navigation.", "accessibility.md", "high", "check error", "Restore the footer landmark."),
    "a11y.nav-label-missing": ("<nav> without aria-label", "Several navigations must be distinguishable.", "accessibility.md", "high", "check error", "Add an aria-label to the nav."),
    "a11y.skip-link-missing": ("missing skip link", "Keyboard users need to bypass the header.", "accessibility.md", "high", "check error", "Restore the skip link to #main."),
    "a11y.main-id-missing": ("<main> without id=\"main\"", "The skip link needs its target.", "accessibility.md", "high", "check error", "Set id=\"main\" on <main>."),
    "a11y.heading-jump": ("heading level jumps", "Skipped levels confuse screen reader navigation.", "accessibility.md", "high", "check error", "Use the next lower heading level."),
    "a11y.link-name-missing": ("link without accessible name", "Screen readers announce nothing useful.", "accessibility.md", "high", "check error", "Give the link visible text or an aria-label."),
    "a11y.link-text-vague": ("vague link text", "Links must make sense out of context.", "accessibility.md", "high", "check error", "Use descriptive link text."),
    "a11y.link-text-ambiguous": ("same link text, different targets", "Identical labels for different targets mislead.", "accessibility.md", "high", "check error", "Make the link texts distinct."),
    "a11y.button-name-missing": ("button without accessible name", "Screen readers announce nothing useful.", "accessibility.md", "high", "check error", "Add text or an aria-label."),
    "a11y.symbol-read-aloud": ("symbol is read aloud", "Decorative glyphs are announced.", "accessibility.md", "high", "check error", "Wrap the symbol in aria-hidden=\"true\"."),
    "a11y.image-alt-missing": ("image without alt", "Images need alt text (empty alt for decoration).", "accessibility.md", "high", "check error", "Add alt text, or alt=\"\" for decorative images."),
    "a11y.image-size-missing": ("image without width/height", "Required by the accessibility rules of this site.", "accessibility.md", "high", "check error", "Set width and height."),
    "a11y.table-header-missing": ("table without <th>", "Header cells give data cells meaning.", "accessibility.md", "high", "check error", "Add <th> header cells."),
    "a11y.form-label-missing": ("form control without label", "Controls need a name.", "accessibility.md", "high", "check error", "Associate a label with the control."),
    "a11y.status-region-missing": ("filterable list without role=\"status\"", "Result changes must be announced.", "accessibility.md", "high", "check error", "Add the status region."),
    "a11y.font-size-absolute": ("font-size in absolute units", "Relative units respect the reader's text size.", "accessibility.md rule 24", "high", "check error", "Use rem."),
    "a11y.root-font-size": ("root font-size overrides the browser setting", "Relative units respect the reader's text size.", "accessibility.md rule 24", "high", "check error", "Remove the absolute root font size."),
}
UNCLASSIFIED = ("message is not known to the adapter", "The adapter does not recognise this message; it is kept verbatim so nothing is lost.", "unknown", "medium", "unknown message shape; review by hand", "Read the evidence and decide by hand.")

# family, regex over the message (location prefix removed), criterion, detail group (int|None)
PATTERNS = [
    ("seo", r"missing <title>$", "seo.title-missing", None),
    ("seo", r"title is \d+ chars", "seo.title-too-long", None),
    ("seo", r"title is very short", "seo.title-too-short", None),
    ("seo", r"missing meta description$", "seo.description-missing", None),
    ("seo", r"description is \d+ chars \(max 160\)", "seo.description-too-long", None),
    ("seo", r"description is short", "seo.description-too-short", None),
    ("seo", r"missing canonical link$", "seo.canonical-missing", None),
    ("seo", r"canonical is not on ", "seo.canonical-offsite", None),
    ("seo", r"expected exactly one <h1>", "seo.h1-count", None),
    ("seo", r"missing lang on <html>$", "seo.lang-missing", None),
    ("seo", r"missing viewport meta$", "seo.viewport-missing", None),
    ("seo", r"missing (og:[A-Za-z:_]+)$", "seo.open-graph-missing", 1),
    ("seo", r"missing twitter:card$", "seo.twitter-card-missing", None),
    ("seo", r"image without alt: (.*)$", "seo.image-alt-missing", 1),
    ("seo", r"image without width/height \(layout shift\): (.*)$", "seo.image-size-missing", 1),
    ("seo", r"invalid JSON-LD$", "seo.json-ld-invalid", None),
    ("seo", r"missing (/[^ ]+)$", "seo.site-file-missing", 1),
    ("seo", r"sitemap URL has no page: (.*)$", "seo.sitemap-url-without-page", 1),
    ("seo", r"indexable page is not in the sitemap$", "seo.page-not-in-sitemap", None),
    ("a11y", r"expected exactly one <main>$", "a11y.main-count", None),
    ("a11y", r"missing <header>$", "a11y.header-missing", None),
    ("a11y", r"missing <footer>$", "a11y.footer-missing", None),
    ("a11y", r"<nav> without aria-label$", "a11y.nav-label-missing", None),
    ("a11y", r"missing skip link$", "a11y.skip-link-missing", None),
    ("a11y", r'<main> without id="main"$', "a11y.main-id-missing", None),
    ("a11y", r"heading level jumps from (h\d to h\d)$", "a11y.heading-jump", 1),
    ("a11y", r"link without accessible name \(href=(.*)\)$", "a11y.link-name-missing", 1),
    ("a11y", r'vague link text "(.*)" \(href=(.*)\)$', "a11y.link-text-vague", 0),
    ("a11y", r'same link text "(.*)" leads to different targets', "a11y.link-text-ambiguous", 1),
    ("a11y", r"button without accessible name$", "a11y.button-name-missing", None),
    ("a11y", r'symbol "(.*)" is read aloud', "a11y.symbol-read-aloud", 1),
    ("a11y", r"image without alt: (.*)$", "a11y.image-alt-missing", 1),
    ("a11y", r"image without width/height: (.*)$", "a11y.image-size-missing", 1),
    ("a11y", r"table without <th> header cells$", "a11y.table-header-missing", None),
    ("a11y", r"form control without label: (.*)$", "a11y.form-label-missing", 1),
    ("a11y", r'filterable list without role="status" region$', "a11y.status-region-missing", None),
    ("a11y", r"font-size in ([0-9.]+(?:px|pt)) \(use rem\)$", "a11y.font-size-absolute", 1),
    ("a11y", r"root font-size ([0-9.]+(?:px|pt)) overrides", "a11y.root-font-size", 1),
]
COMPILED = [(f, re.compile(p), c, d) for f, p, c, d in PATTERNS]
DUPLICATE_RE = re.compile(r'^duplicate title/description "(.*)" on: (.*)$')
LOC_RE = re.compile(r"^(/[^\s:]*): (.*)$", re.S)
SECTION_RE = re.compile(r"^(Warnings|Errors) \((\d+)\):\s*$")
CHECKED_RE = re.compile(r"^Checked (\d+) pages?\b")


def unparsed(reason: str) -> dict:
    return {"status": "unparsed", "reason": reason, "pages": None, "errors": [], "warnings": []}


def parse_output(text: str, exit_code) -> dict:
    """Split a check's stdout into error/warning items and verify shape and consistency with the exit code."""
    if exit_code not in (0, 1):
        return unparsed(f"exit code {exit_code} is not a defined result of the check (0 = no errors, 1 = errors)")
    lines = text.splitlines()
    pages = None
    sections = {"Warnings": [], "Errors": []}
    declared = {}
    current = None
    saw_clean_line = False
    for line in lines:
        m = CHECKED_RE.match(line)
        if m and pages is None:
            pages = int(m.group(1))
            continue
        m = SECTION_RE.match(line)
        if m:
            current = m.group(1)
            declared[current] = int(m.group(2))
            continue
        if line.startswith("No errors"):
            saw_clean_line = True
            current = None
            continue
        if current and line.startswith("- "):
            sections[current].append(line[2:])
        elif current and line.strip() and sections[current]:
            sections[current][-1] += "\n" + line   # continuation of a multi-line message
        elif not line.strip():
            current = None   # a blank line ends a section (the checks print one between sections)
    if pages is None:
        return unparsed("output has no 'Checked N pages' line")
    for name, items in sections.items():
        if name in declared and declared[name] != len(items):
            return unparsed(f"'{name} ({declared[name]})' announces {declared[name]} items but {len(items)} were read")
    errors, warnings = sections["Errors"], sections["Warnings"]
    if exit_code == 0 and (errors or "Errors" in declared):
        return unparsed("exit code 0 but the output lists errors")
    if exit_code == 1 and not errors:
        return unparsed("exit code 1 but the output lists no errors")
    if exit_code == 0 and not saw_clean_line:
        return unparsed("exit code 0 but the output lacks the 'No errors.' line")
    return {"status": "ok", "reason": "", "pages": pages, "errors": errors, "warnings": warnings}


def classify(family: str, cls: str, item: str) -> dict:
    """Turn one output item into a raw finding {family, class, criterion, location, detail, message}."""
    location, message = GLOBAL, item
    m = LOC_RE.match(item)
    if m:
        location, message = m.group(1), m.group(2)
    dup = DUPLICATE_RE.match(item) if family == "seo" else None
    if dup:
        pages = sorted(p.strip() for p in dup.group(2).split(","))
        return {"family": family, "class": cls, "criterion": "seo.duplicate-title-description",
                "location": ", ".join(pages), "detail": "", "message": item}
    for fam, regex, criterion, group in COMPILED:
        if fam != family:
            continue
        hit = regex.search(message)
        if hit:
            if group is None:
                detail = ""
            elif group == 0:
                detail = "|".join(hit.groups())
            else:
                detail = hit.group(group)
            return {"family": family, "class": cls, "criterion": criterion, "location": location,
                    "detail": detail[:160], "message": message}
    return {"family": family, "class": cls, "criterion": f"{family}.unclassified", "location": location,
            "detail": re.sub(r"\d+", "#", message)[:120], "message": message}


def collect(family: str, parsed: dict) -> list:
    """Raw findings of one parsed check; identical identities are merged with an occurrence count."""
    merged = {}
    for cls, items in ((ERROR, parsed["errors"]), (WARNING, parsed["warnings"])):
        for item in items:
            raw = classify(family, cls, item)
            key = identity_key(raw)
            if key in merged:
                merged[key]["occurrences"] += 1
            else:
                merged[key] = {**raw, "occurrences": 1}
    return list(merged.values())


def identity_key(raw: dict) -> str:
    return "|".join([raw["criterion"], raw["location"], raw.get("detail", "")])


def catalog_entry(criterion: str):
    return CATALOG.get(criterion, UNCLASSIFIED)


def source_files(root: Path, site_path: str, url: str) -> list:
    """Repo-relative source files that produce a built URL; only files that exist, never guessed."""
    if not url.startswith("/") or url == GLOBAL:
        return []
    site = Path(site_path)
    pages = root / site / "src" / "pages"
    stem = url.removesuffix(".html").strip("/") or "index"
    found = []
    direct = pages / f"{stem}.astro"
    if direct.is_file():
        found.append(direct)
    else:
        parent = pages / Path(stem).parent
        dynamic = sorted(parent.glob("[[]*[]].astro")) if parent.is_dir() else []
        if len(dynamic) == 1:
            found.append(dynamic[0])
            data = root / site / "src" / "data" / f"{Path(stem).parent.name}.json"
            slug = Path(stem).name
            if data.is_file() and f'"slug": "{slug}"' in data.read_text(encoding="utf-8"):
                found.append(data)
        content = root / site / "src" / "content"
        if content.is_dir():
            found += [p for p in sorted(content.rglob(f"{Path(stem).name}.md*")) if Path(stem).parent.name in p.parts]
    return [p.relative_to(root).as_posix() for p in found]

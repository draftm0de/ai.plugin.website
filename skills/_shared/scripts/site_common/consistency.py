"""Version-2 consistency between the manifest `domain` and the domain-dependent site configuration.

Supported configuration contract (text only; JavaScript/TypeScript is never executed, nothing is repaired):

* ``astro.config.mjs`` in the site folder: after removing comments, the object that is really the default export
  (``export default defineConfig({...})``, ``export default {...}`` or one plain ``const NAME = ...; export default NAME;``) with only
  plain top-level properties (no spread, no computed key). ``site`` is either absent or one plain string literal. A ``defineConfig``
  call that is not that export, several defaults, re-exports and reassignment make it unverifiable.
* ``src/lib/site.ts``: after removing comments, exactly one ``export const SITE`` declaration with an optional type annotation,
  assigned one plain string literal or ``null``.

Anything else (variables, template expressions, spreads, a second declaration, an unreadable or missing file, a symlink in the path,
a file that is not regular or is larger than 1 MiB) is *not reliably checkable*. That is reported as such; it is never read as
"no domain" and never as a match. A conflict is a reliably read value that differs from the manifest.
Comments never count as configuration. Consumers of the URL (layout canonical, social metadata, sitemap, robots.txt, SEO check)
read ``SITE`` / ``site`` and are covered by checking those two values.
"""
import os
import re
from pathlib import Path

MAX_BYTES = 1024 * 1024
CONFIG = "astro.config.mjs"
LIB = "src/lib/site.ts"


def strip_comments(text: str) -> str:
    """Remove // and /* */ comments outside of string/template literals; literals are kept verbatim."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "'\"`":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            out.append(" ")
        else:
            out.append(c)
            i += 1
    return "".join(out)


_STRING = re.compile(r"""^\s*(?:'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)")\s*""")


def _plain_string(text: str):
    """(value, rest) for a leading plain string literal, else None. Escapes make it non-plain."""
    m = _STRING.match(text)
    if not m:
        return None
    value = m.group(1) if m.group(1) is not None else m.group(2)
    if "\\" in value:
        return None
    return value, text[m.end():]


def _read(root: Path, rel: str):
    """(text, None) or (None, reason). Refuses symlinks anywhere between the project root and the file, itself included."""
    current = root
    for part in rel.split("/"):
        current = current / part
        try:
            if current.is_symlink():
                return None, f"{rel}: a symlink is in the path ({current.name}); not read"
        except OSError as error:
            return None, f"{rel}: not readable ({error.strerror})"
    return _read_regular(current, rel)


def _read_regular(path: Path, rel: str):
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None, f"{rel}: missing"
    except OSError as error:
        return None, f"{rel}: not readable ({error.strerror})"
    import stat
    if not stat.S_ISREG(info.st_mode):
        return None, f"{rel}: not a regular file"
    if info.st_size > MAX_BYTES:
        return None, f"{rel}: larger than 1 MiB, not read"
    try:
        return path.read_text(encoding="utf-8"), None
    except (OSError, UnicodeDecodeError):
        return None, f"{rel}: not readable as UTF-8 text"


def _close_index(literal: str):
    """Index of the `}` that closes the object literal starting at literal[0], or None."""
    depth, i, n = 0, 0, len(literal)
    while i < n:
        ch = literal[i]
        if ch in "'\"`":
            j = i + 1
            while j < n and literal[j] != ch:
                j += 2 if literal[j] == "\\" else 1
            i = j + 1
            continue
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _statement_ends(tail: str, closing_paren: bool) -> bool:
    """After the literal (and the `)` of defineConfig) nothing may continue the expression: only `;`, a line break or the end."""
    m = re.match(r"\s*\)" if closing_paren else r"\s*", tail)
    if not m:
        return False
    tail = tail[m.end():]
    if not tail.strip():
        return True
    if tail.lstrip().startswith(";"):
        return True
    lead = re.match(r"[ \t]*\n", tail) or re.match(r"[ \t]*(\r\n)", tail)
    return bool(lead) and tail.lstrip()[:1] not in tuple(".[(`+-*/,?:=|&<>%") and not tail.lstrip().startswith("in ")


def _literal_site(literal: str):
    """('site', value|None) for the text of an object literal starting with `{`, else ('unchecked', reason)."""
    depth, i, n = 0, 0, len(literal)
    entries, entry_start = [], 1
    while i < n:
        c = literal[i]
        if c in "'\"`":
            j = i + 1
            while j < n and literal[j] != c:
                j += 2 if literal[j] == "\\" else 1
            i = j + 1
            continue
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
            if depth == 0:
                entries.append(literal[entry_start:i])
                break
        elif c == "," and depth == 1:
            entries.append(literal[entry_start:i])
            entry_start = i + 1
        i += 1
    else:
        return "unchecked", "the exported config object is not closed"
    site = []
    for entry in entries:
        e = entry.strip()
        if not e:
            continue
        if e.startswith("..."):
            return "unchecked", "the exported config object contains a spread"
        m = re.match(r"""^(?:([A-Za-z_$][\w$]*)|'([^']*)'|"([^"]*)")\s*:\s*(.*)$""", e, re.S)
        if not m:
            return "unchecked", "the exported config object has a property that is not `key: value`"
        key = next(g for g in m.groups()[:3] if g is not None)
        if key == "site":
            site.append(m.group(4))
    if not site:
        return "site", None
    if len(site) > 1:
        return "unchecked", "`site` is set more than once"
    value = _plain_string(site[0])
    if value is None or value[1].strip():
        return "unchecked", "`site` is not one plain string literal"
    return "site", value[0]


def astro_site(text: str):
    """The `site` of the config object that is actually the default export, or ('unchecked', reason).
    Supported exported forms: `export default defineConfig({...})`, `export default {...}`, and `export default NAME;` where NAME is
    declared exactly once as `const|let|var NAME = defineConfig({...})` or `= {...}`. Everything else (a defineConfig call that is not
    exported, several default exports, re-exports, function calls, reassignment) is unchecked."""
    code = strip_comments(text)
    exports = list(re.finditer(r"\bexport\s+default\b", code))
    if len(exports) != 1 or re.search(r"\bexport\s*\{[^}]*\bdefault\b", code) or re.search(r"\bmodule\.exports\b|\bexports\.default\b", code):
        return "unchecked", "expected exactly one `export default`"
    rest = code[exports[0].end():].lstrip()
    stray = "a defineConfig call exists that is not the default export; the exported object is not judged"
    calls = len(re.findall(r"\bdefineConfig\s*\(", code))

    def literal(text, closing_paren):
        end = _close_index(text)
        if end is None:
            return "unchecked", "the exported config object is not closed"
        if not _statement_ends(text[end + 1:], closing_paren):
            return "unchecked", "the config object is followed by more of the expression (a call, member access or operator)"
        return _literal_site(text[:end + 1])
    call = re.match(r"defineConfig\s*\(\s*", rest)
    if call:
        rest = rest[call.end():]
        if not rest.startswith("{"):
            return "unchecked", "defineConfig does not receive an object literal"
        if calls != 1:
            return "unchecked", "defineConfig is called more than once; the exported one cannot be told apart reliably"
        return literal(rest, True)
    if rest.startswith("{"):
        return ("unchecked", stray) if calls else literal(rest, False)
    ident = re.match(r"([A-Za-z_$][\w$]*)\s*;?\s*$", rest)
    if not ident:
        return "unchecked", "the default export is neither an object literal, defineConfig({...}) nor a plain name"
    name = ident.group(1)
    declarations = list(re.finditer(rf"\b(?:const|let|var)\s+{re.escape(name)}\s*=\s*", code))
    uses = 0
    for hit in re.finditer(rf"(?<![\w$]){re.escape(name)}(?![\w$])", code):
        before = code[:hit.start()].rstrip()
        if not before.endswith(".") or before.endswith("..."):      # `x.name` is a member of something else; `...name` is a use
            uses += 1
    if len(declarations) != 1 or uses != 2:
        return "unchecked", (f"`{name}` is not declared exactly once or is used elsewhere (property or bracket assignment, Object.assign, "
                             "passing it to a function ...): the final exported object cannot be read reliably")
    after = code[declarations[0].end():].lstrip()
    call = re.match(r"defineConfig\s*\(\s*", after)
    if call:
        after = after[call.end():]
        if calls != 1:
            return "unchecked", "defineConfig is called more than once; the exported one cannot be told apart reliably"
    if not after.startswith("{"):
        return "unchecked", f"`{name}` is not initialised with an object literal"
    if not call and calls:
        return "unchecked", stray
    return literal(after, bool(call))


def lib_site(text: str):
    code = strip_comments(text)
    decls = list(re.finditer(r"\bexport\s+(?:const|let|var)\s+SITE\b", code))
    if len(decls) != 1 or len(re.findall(r"\bSITE\b\s*(?::[^=;]*)?=(?!=)", code)) != 1:
        return "unchecked", "expected exactly one `export const SITE = ...` and no other assignment"
    m = re.match(r"\s*(?::\s*[A-Za-z |]+?)?\s*=\s*(.*?);", code[decls[0].end():], re.S)
    if not m:
        return "unchecked", "SITE is not assigned a single plain value"
    raw = m.group(1).strip()
    if raw == "null":
        return "site", None
    value = _plain_string(raw)
    if value is None or value[1].strip():
        return "unchecked", "SITE is not a plain string literal or null"
    return "site", value[0]


def check_texts(domain, config_text, lib_text) -> dict:
    """Core comparison on already read texts (None = not available). Returns {"conflicts": [...], "unverifiable": [...]}."""
    expected = f"https://{domain}" if domain else None
    conflicts, unverifiable = [], []
    for label, text, reader in ((CONFIG + " `site`", config_text, astro_site), (LIB + " `SITE`", lib_text, lib_site)):
        if text is None:
            continue
        kind, value = reader(text)
        if kind == "unchecked":
            unverifiable.append(f"{label} is not reliably checkable: {value}")
        elif value != expected:
            want = f"'{expected}'" if expected else "no site URL (the manifest has no `domain`)"
            have = f"'{value}'" if value else "no site URL"
            conflicts.append(f"{label} is {have} but the manifest requires {want}")
    return {"conflicts": conflicts, "unverifiable": unverifiable}


def check(root: Path, component: dict) -> dict:
    """Read both files below ``root / component['path']`` without following symlinks and compare them to the manifest."""
    base = component["path"].rstrip("/")
    texts, notes = {}, []
    for rel in (CONFIG, LIB):
        text, reason = _read(Path(root), f"{base}/{rel}")
        texts[rel] = text
        if reason:
            notes.append(f"{reason}: not reliably checkable")
    result = check_texts(component.get("domain"), texts[CONFIG], texts[LIB])
    result["unverifiable"] = notes + result["unverifiable"]
    return result

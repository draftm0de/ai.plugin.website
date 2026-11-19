"""Template placeholders: render and detect unresolved ones (standard library only)."""
import re

TPL = ".tpl"
PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


def render(text: str, values: dict) -> str:
    return PLACEHOLDER_RE.sub(lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), text)


def unresolved(text: str) -> list:
    return sorted(set(PLACEHOLDER_RE.findall(text)))

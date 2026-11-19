"""The repository's scratch folder (.tmp): working data that is never committed. Created and git-ignored on demand."""
from pathlib import Path

COMMENT = "# temporary working data (import workspaces, scratch files), never committed"


def ignored(gitignore_text: str, name: str) -> bool:
    wanted = {name, name + "/", "/" + name, "/" + name + "/"}
    return any(line.strip() in wanted for line in gitignore_text.splitlines())


def ensure(root: Path, name: str, dry_run: bool = False) -> list:
    """Create <root>/<name>/ and make sure .gitignore lists it. Returns notes. Never removes or rewrites anything."""
    notes = []
    folder = root / name
    if not folder.is_dir():
        notes.append(f"{'would create' if dry_run else 'created'} {name}/ (scratch folder, git-ignored)")
        if not dry_run:
            folder.mkdir(parents=True)
    gitignore = root / ".gitignore"
    text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    if not ignored(text, name):
        notes.append(f"{'would add' if dry_run else 'added'} {name}/ to .gitignore")
        if not dry_run:
            prefix = "" if not text or text.endswith("\n") else "\n"
            gitignore.write_text(text + prefix + ("\n" if text else "") + f"{COMMENT}\n{name}/\n", encoding="utf-8")
    return notes


def gitignore_after(text: str, name: str):
    """New .gitignore content that lists <name>/, or None when it already does (same formula as ensure)."""
    if ignored(text, name):
        return None
    prefix = "" if not text or text.endswith("\n") else "\n"
    return text + prefix + ("\n" if text else "") + f"{COMMENT}\n{name}/\n"

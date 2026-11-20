"""Git-independent project ignore rules and source snapshots. Never follow links.

Only project-local .gitignore files participate; global Git configuration is not
part of the website contract. Ignored/private data is never opened by snapshots.
"""
import fnmatch
import hashlib
import os
from pathlib import Path
import re
import stat

from .errors import Stop

PRIVATE = {'.git', '.aws', '.ssh', '.local', '.tmp', '.idea', '__pycache__'}


def private(parts):
    return any(p in PRIVATE or p.startswith('.env') or p.endswith(('.pem', '.key')) for p in parts)


def read_regular(path, *, root=None):
    """Open each parent through a directory descriptor; no symlink race traversal."""
    path = Path(path)
    root = Path(root) if root is not None else path.parent
    directory = None
    try:
        parts = path.relative_to(root).parts
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0), dir_fd=directory)
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise Stop(f"not a regular project file: {path}")
            return stream.read()
    except OSError as error:
        raise Stop(f"cannot safely read project file {path}: {error}") from error
    finally:
        if directory is not None:
            os.close(directory)


def pattern_regex(pattern):
    """Local wildmatch: * and ? stay within a component, ** spans components."""
    if any(token in pattern for token in ('[[:', '[[=', '[[.')):
        raise Stop(f"unsupported locale-dependent character class in .gitignore: {pattern}")
    result = ''
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == '\\' and i + 1 < len(pattern):
            i += 1
            result += re.escape(pattern[i])
        elif c == '*':
            if pattern[i:i+2] == '**' and (i == 0 or pattern[i-1] == '/') and (i+2 == len(pattern) or pattern[i+2] == '/'):
                i += 1
                if i+1 < len(pattern) and pattern[i+1] == '/':
                    result += '(?:.*/)?'
                    i += 1
                else:
                    result += '.*'
            else:
                result += '[^/]*'
        elif c == '?':
            result += '[^/]'
        elif c == '[':
            start = i + 1
            if start < len(pattern) and pattern[start] == '!':
                start += 1
            if start < len(pattern) and pattern[start] == ']':
                start += 1
            end = pattern.find(']', start)
            if end < 0:
                result += r'\['
            else:
                result += '(?!/)' + fnmatch.translate(pattern[i:end+1])[4:-3]
                i = end
        else:
            result += re.escape(c)
        i += 1
    try:
        return re.compile('^' + result + '$')
    except re.error as error:
        raise Stop(f"unsupported .gitignore pattern {pattern!r}: {error}") from error


class IgnoreRules:
    def __init__(self, root):
        self.root = Path(root)
        self.cache = {}

    def rules(self, directory):
        if directory not in self.cache:
            path = self.root / directory / '.gitignore'
            rules = []
            if path.is_symlink():
                raise Stop(f"ignore rules must not be a symbolic link: {path}")
            if path.exists():
                try:
                    text = read_regular(path, root=self.root).decode('utf-8')
                except UnicodeError as error:
                    raise Stop(f"ignore rules are not UTF-8: {path}") from error
                for line in text.splitlines():
                    # Unescaped trailing spaces have no meaning in gitignore.
                    line = re.sub(r'(?<!\\) +$', '', line)
                    if not line or line.startswith('#'):
                        continue
                    negate = line.startswith('!')
                    if negate:
                        line = line[1:]
                    directory_only = line.endswith('/')
                    line = line.rstrip('/')
                    anchored = '/' in line
                    line = line.lstrip('/')
                    if line:
                        rules.append((pattern_regex(line), negate, directory_only, anchored))
            self.cache[directory] = rules
        return self.cache[directory]

    def ignored(self, relative, is_dir=False):
        parts = Path(relative).parts
        if Path(relative).is_absolute() or '..' in parts:
            raise Stop('ignore check requires a project-relative path')
        # A negated child cannot re-include a path inside an excluded parent.
        for depth in range(1, len(parts)+1):
            directory = depth < len(parts) or is_dir
            ignored = False
            for parent in range(depth):
                base = '/'.join(parts[:parent])
                rel = '/'.join(parts[parent:depth])
                for regex, negate, only_dir, anchored in self.rules(base):
                    if only_dir and not directory:
                        continue
                    if regex.fullmatch(rel if anchored else parts[depth-1]):
                        ignored = not negate
            if ignored:
                return True
        return False


def is_ignored(root, relative):
    return IgnoreRules(root).ignored(relative)


def snapshot(root, exclude=()):
    """Hash non-ignored project files; record links themselves, never their targets."""
    root = Path(root)
    rules = IgnoreRules(root)
    result = {}
    excluded = tuple(p.rstrip('/') for p in exclude)

    def visit(directory, prefix=''):
        with os.scandir(directory) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                rel = prefix + entry.name
                if private(Path(rel).parts) or any(rel == p or rel.startswith(p + '/') for p in excluded):
                    continue
                is_dir = entry.is_dir(follow_symlinks=False)
                if rules.ignored(rel, is_dir):
                    continue
                if entry.is_symlink():
                    result[rel] = 'LINK:' + os.readlink(entry.name, dir_fd=directory)
                elif is_dir:
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    try:
                        visit(child, rel + '/')
                    finally:
                        os.close(child)
                elif entry.is_file(follow_symlinks=False):
                    mode = stat.S_IMODE(entry.stat(follow_symlinks=False).st_mode)
                    result[rel] = f'FILE:{mode:o}:' + hashlib.sha256(read_regular(root / rel, root=root)).hexdigest()
                else:
                    raise Stop(f"unsupported source file type: {rel}")
    try:
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            visit(directory)
        finally:
            os.close(directory)
    except OSError as error:
        raise Stop(f"cannot snapshot project sources: {error}") from error
    return result


def changed(before, after):
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))

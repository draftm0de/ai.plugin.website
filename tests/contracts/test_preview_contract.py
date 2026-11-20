"""Contracts of the migrated `preview` skill: identity against the source inventory (hash or explicit change list), skill text,
call patterns and pre-approvals derived from each other, communication block, shipped-runtime hygiene. Structural/text checks
only: they prove no product behaviour and no host acceptance."""
import ast
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "preview"
TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")
INVENTORY = json.loads((ROOT / "docs/migration/source-inventory.json").read_text())
PREFIX = INVENTORY["plugin_root"] + "/"
SOURCE = {e["path"][len(PREFIX):]: e["sha256"] for e in INVENTORY["files"] if e["path"].startswith(PREFIX)}


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


# Adapted code: target -> (source path, [(new text, old text)]). Reversing the listed replacements must give back the recorded
# source bytes: the diff is exactly this list (docs/migration/changes.md).
ADAPTED = {
    "scripts/control.py": ("scripts/preview/control.py", [
        ('"""Website plugin, skill `preview`: runtime control: start | status | stop | inspect of the dev server of one site.',
         '"""zyris-website-preview runtime control: start | status | stop of the dev server of one site.'),
        ("Exit codes: 0 running-new | running-reused | not-running | stopped | page-confirmed, 1 every failure state,",
         "Exit codes: 0 running-new | running-reused | not-running | stopped, 1 every failure state,"),
        ('HERE = Path(__file__).resolve().parent\nsys.path.insert(0, str(HERE))\n'
         'sys.path.insert(0, str(HERE.parents[1] / "_shared" / "scripts"))   # shared package `site_common` (resolver, manifest validator, errors)\n',
         "sys.path.insert(0, str(Path(__file__).resolve().parent))\n"),
        ("from site_common import sites  # noqa: E402\nfrom site_common.errors import", "import sites  # noqa: E402\nfrom errors import"),
        ("import preview  # noqa: E402\nimport sites  # noqa: E402", "import preview  # noqa: E402\nimport sites  # noqa: E402"),
    ]),
    "scripts/preview.py": ("scripts/preview/preview.py", [
        ('"""Website plugin, skill `preview`: pick the site, write its dev-server entry into `.claude/launch.json`, print a JSON result.\n\n'
         "`.claude/launch.json` is a Claude-desktop-specific artifact (see references/preview.md); it is not a Codex integration.\n",
         '"""zyris-website-preview: pick the site, prepare its dev-server entry, print a JSON result.\n\n'),
        ("The caller starts the server with the returned launch name and opens the url. The skill's own start path is `control.py`.",
         "The caller starts the server with the returned launch name and opens the url."),
        ('HERE = Path(__file__).resolve().parent\nsys.path.insert(0, str(HERE))\n'
         'sys.path.insert(0, str(HERE.parents[1] / "_shared" / "scripts"))   # shared package `site_common` (resolver, manifest validator, errors)\n',
         "sys.path.insert(0, str(Path(__file__).resolve().parent))\n"),
        ("from site_common import sites  # noqa: E402\nfrom site_common.errors import", "import sites  # noqa: E402\nfrom errors import"),
        ('SKILL_DIR = HERE.parent\nRES = SKILL_DIR / "templates"   # templates of this skill, inside the plugin (never a developer path, never written to)',
         'PLUGIN_ROOT = Path(__file__).resolve().parents[2]\nRES = PLUGIN_ROOT / "templates" / "preview"   # templates and data of this function (never a developer path)'),
    ]),
}

# Protection corrections (review of stage 3): hunks that make control.py/preview.py differ from the source beyond the stage-3 migration.
# Applied after ADAPTED, in order; reversing them too must give the source bytes. Generated from the files, see changes.md BD-5/BD-6.
PROTECTION = {
    "scripts/preview.py": [('import argparse\nimport json\nimport os\nimport stat\nimport sys\n', 'import argparse\nimport json\nimport sys\n'), ('def _checked_launch_file(root: Path) -> Path:\n    """`.claude/launch.json` of the project, after a metadata-only check (lstat, no content access): `.claude` must be absent or a real\n    directory (not a symlink, not a broken one either), `launch.json` absent or a regular file (not a symlink, not a broken one,\n    not a directory or special file). Nothing behind a link is ever read, overwritten or removed."""\n    directory = root / ".claude"\n    file = directory / "launch.json"\n    for path, what, ok in ((directory, "directory", stat.S_ISDIR), (file, "regular file", stat.S_ISREG)):\n        try:\n            mode = os.lstat(path).st_mode\n        except FileNotFoundError:\n            continue\n        except OSError as error:\n            raise Stop(f"{path} cannot be inspected ({error}); left untouched.")\n        if stat.S_ISLNK(mode):\n            raise Stop(f"{path} is a symbolic link (also a broken one counts); the launch configuration is neither read nor written through "\n                       "links and nothing was started. Replace it by a real file or directory yourself.")\n        if not ok(mode):\n            raise Stop(f"{path} is not a {what}; left untouched and nothing was started. Remove or repair it yourself.")\n    return file\n\n\ndef write_launch(root: Path, component: dict) -> str:\n    entry = launch_entry(component)\n    name = entry["name"]\n    file = _checked_launch_file(root)\n    if os.path.lexists(file):\n        try:\n            fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW)\n            with os.fdopen(fd, "r", encoding="utf-8") as handle:\n                data = json.loads(handle.read())\n            configs = data["configurations"]\n            if not isinstance(configs, list):\n                raise TypeError\n        except (ValueError, KeyError, TypeError):\n            raise Stop(f"{file} is not valid launch JSON (object with a \'configurations\' list); left untouched. Repair or remove it.")\n        except OSError as error:\n            raise Stop(f"{file} cannot be read safely ({error}); left untouched.")\n    else:\n        data, configs = {"version": "0.0.1", "configurations": []}, []\n    if entry in configs:      # identical own entry present: write nothing (contract D2)\n        return name\n    data["configurations"] = [c for c in configs if c.get("name") != name] + [entry]\n    file.parent.mkdir(parents=True, exist_ok=True)\n    _checked_launch_file(root)                      # again right before the write (the directory may just have been created)\n    try:\n        fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o666)\n    except OSError as error:\n        raise Stop(f"{file} cannot be written safely ({error}); left untouched.")\n    with os.fdopen(fd, "w", encoding="utf-8") as handle:\n        handle.write(json.dumps(data, indent=2) + "\\n")\n    return name\n\n\n', 'def write_launch(root: Path, component: dict) -> str:\n    entry = launch_entry(component)\n    name = entry["name"]\n    file = root / ".claude" / "launch.json"\n    if file.is_file():\n        try:\n            data = json.loads(file.read_text(encoding="utf-8"))\n            configs = data["configurations"]\n            if not isinstance(configs, list):\n                raise TypeError\n        except (ValueError, KeyError, TypeError):\n            raise Stop(f"{file} is not valid launch JSON (object with a \'configurations\' list); left untouched. Repair or remove it.")\n    else:\n        data, configs = {"version": "0.0.1", "configurations": []}, []\n    if entry in configs:      # identical own entry present: write nothing (contract D2)\n        return name\n    data["configurations"] = [c for c in configs if c.get("name") != name] + [entry]\n    file.parent.mkdir(parents=True, exist_ok=True)\n    file.write_text(json.dumps(data, indent=2) + "\\n", encoding="utf-8")\n    return name\n\n\n')],
    "scripts/control.py": [('def check_state_area(path: Path) -> None:\n    """Read-only check (lstat only, creates nothing) of the state area a state file lives in, before ANY access to the file:\n    the base directory (`<TMPDIR>/zyris-website` or the override) and the project directory below it must each be absent\n    (a normal case: nothing is known yet) or a real directory (no symlink) owned by us and not writable by group/others.\n    The base is checked first, because a link there would make the lstat of the project directory follow it. Ancestors of the\n    base (the system temp folder, which may legitimately sit behind a system link such as /var -> /private/var) are not examined.\n    Raises UnsafeState; an unsafe area is never evidence of ownership."""\n    project = path.parent\n    for directory in (project.parent, project):\n        st = _lstat(directory)\n        if st is None:\n            return\n        if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or not _is_mine(st) or st.st_mode & 0o022:\n            raise UnsafeState(f"state directory {directory} is a symlink, not a directory, not owned by this user or writable by others; "\n                              "nothing in it was read, changed, removed or used as evidence")\n\n\n', ''), ('    """The target of a record write must be absent or a regular file of ours, in a safe state area."""\n    check_state_area(path)\n', '    """The target of a record write must be absent or a regular file of ours."""\n'), ('def read_record(path: Path):\n    check_state_area(path)\n', 'def read_record(path: Path):\n'), ('def _unlink_if_same(path: Path, fd_stat) -> None:\n    try:\n        check_state_area(path)\n    except UnsafeState:\n        return\n', 'def _unlink_if_same(path: Path, fd_stat) -> None:\n'), ('    """Unlink a regular file of ours; never a symlink, a foreign file or anything in an unsafe state area."""\n    try:\n        check_state_area(path)\n    except UnsafeState:\n        return False\n', '    """Unlink a regular file of ours; never a symlink or a foreign file."""\n'), ('        return None\n    try:\n        check_state_area(path)\n    except UnsafeState:\n        return None\n    st = _lstat(path)\n    return path if', '        return None\n    st = _lstat(path)\n    return path if'), ('        check_state_area(Path(path))\n', ''), ('    except (OSError, UnsafeState):\n', '    except OSError:\n')],
}
# Manifest version 2 (docs/development/manifest-v2-divergence.md): hunks applied after PROTECTION, undone first. Not a recomputed hash:
# reversing ADAPTED + PROTECTION + V2 still has to give the recorded source bytes.
_CONSIST = "    notes = manifest.require_consistent(root, component)   # contradictions stop here, before anything is written or started\n"
V2 = {
    "scripts/preview.py": [
        ("from site_common import manifest, sites  # noqa: E402\nfrom site_common.errors import", "from site_common import sites  # noqa: E402\nfrom site_common.errors import"),
        (_CONSIST, ""),
    ],
    "scripts/control.py": [
        ("from site_common import manifest, sites  # noqa: E402\nfrom site_common.errors import", "from site_common import sites  # noqa: E402\nfrom site_common.errors import"),
        ('    if args.verb == "start":     # stopping or inspecting never needs a consistent configuration; starting does\n        manifest.require_consistent(root, component)\n', ""),
        ('"""(SITE url, SITE_NAME) read from src/lib/site.ts; None for a value that cannot be read, "" for SITE = null (no domain yet)."""',
         '"""(SITE url, SITE_NAME) read from src/lib/site.ts; None for a value that cannot be read."""'),
        ("'[^']*'|null)\", text)", "'[^']*')\", text)"),
        ('        if raw == "null":\n            return ""            # explicitly no value (version 2: domain not decided yet), different from None = unreadable\n', ""),
        ('    domainless = site_url == ""\n    if site_url is None or not site_name or served_name is None or (canonical is None and not domainless):',
         "    if not site_url or not site_name or not canonical or served_name is None:"),
        ("    if (domainless and canonical) or (not domainless and not same_site_url(canonical, site_url)) or served_name != site_name:",
         "    if not same_site_url(canonical, site_url) or served_name != site_name:"),
        ('    if domainless:\n        base["identity_basis"] = "site name only (the site has no domain, so the page has no canonical address to compare)"\n', ""),
    ],
}
NOT_MIGRATED = {   # source files of the preview area that are deliberately not in the skill (shared module or ZIP-era / contract material)
    "scripts/preview/errors.py": "shared: skills/_shared/scripts/site_common/errors.py",
    "scripts/preview/manifest.py": "shared: skills/_shared/scripts/site_common/manifest.py",
    "scripts/preview/schema.py": "shared: skills/_shared/scripts/site_common/schema.py",
    "scripts/preview/sites.py": "shared: skills/_shared/scripts/site_common/sites.py",
}


class IdentityTests(unittest.TestCase):
    def test_launch_template_is_byte_identical_to_the_source(self):
        self.assertEqual(sha_bytes((SKILL / "templates/launch/astro-static.json.tpl").read_bytes()),
                         SOURCE["templates/preview/launch/astro-static.json.tpl"])

    def test_no_template_exists_that_the_source_did_not_have(self):
        found = {p.relative_to(SKILL / "templates").as_posix() for p in (SKILL / "templates").rglob("*") if p.is_file()}
        self.assertEqual(found, {"launch/astro-static.json.tpl"})

    def test_adapted_scripts_differ_only_by_the_listed_replacements(self):
        for rel, (source, replacements) in ADAPTED.items():
            text = (SKILL / rel).read_text(encoding="utf-8")
            for new, old in reversed(V2.get(rel, [])):
                self.assertIn(new, text, (rel, "v2", new[:60]))
                text = text.replace(new, old)
            for new, old in reversed(PROTECTION[rel]):          # the protection corrections were applied last: undo them first
                self.assertIn(new, text, (rel, "protection", new[:60]))
                text = text.replace(new, old)
            for new, old in replacements:
                self.assertIn(new, text, (rel, new[:60]))
                text = text.replace(new, old)
            self.assertEqual(sha_bytes(text.encode()), SOURCE[source], f"{rel}: diff exceeds the change list")

    def test_every_inventoried_preview_script_is_migrated_or_recorded_as_shared(self):
        names = {p.name for p in (SKILL / "scripts").glob("*.py")}
        for src in SOURCE:
            if src.startswith("scripts/preview/") and src.endswith(".py"):
                name = src.rsplit("/", 1)[1]
                if src in NOT_MIGRATED:
                    self.assertNotIn(name, names, f"{name} must not be duplicated next to the shared module")
                    self.assertTrue((ROOT / "skills/_shared/scripts/site_common" / name).is_file(), name)
                else:
                    self.assertIn(name, names, name)
        self.assertEqual(names, {"control.py", "preview.py"})

    def test_adapted_files_are_in_the_change_list(self):
        changes = (ROOT / "docs/migration/changes.md").read_text()
        for target in ADAPTED:
            self.assertIn(f"skills/preview/{target}", changes, target)


class RuntimeHygieneTests(unittest.TestCase):
    def test_scripts_import_only_standard_library_and_the_shared_package(self):
        local = {"preview", "site_common"}
        for path in (SKILL / "scripts").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
                for name in names:
                    top = name.split(".")[0]
                    self.assertTrue(top in sys.stdlib_module_names or top in local, (path.name, name))
                    self.assertNotIn(top, {"errors", "sites", "manifest", "schema"}, (path.name, "flat shared import"))

    def test_no_developer_paths_source_checkout_or_old_names_in_the_skill_payload(self):
        bad = ("www.draftmode", "ai.plugins", "interview-coach", "/Users/", "CLAUDE_PLUGIN_ROOT", "/zyris-website:", "templates/setup",
               "zyris-website.schema", "contracts/")
        for path in SKILL.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                for word in bad:
                    self.assertNotIn(word, text, (path.relative_to(ROOT), word))

    def test_no_state_or_bytecode_in_the_installed_skill(self):
        self.assertEqual(list(SKILL.rglob("__pycache__")), [])
        self.assertEqual(list(SKILL.rglob("*.pyc")), [])


class SkillTextTests(unittest.TestCase):
    def front(self):
        head = TEXT.split("---")[1]
        return head

    def test_frontmatter_name_matches_the_folder_and_has_a_description(self):
        self.assertRegex(self.front(), r"(?m)^name: preview$")
        self.assertRegex(self.front(), r"(?m)^description: \S")

    def test_allowed_tools_are_exactly_the_narrow_patterns_of_the_call_forms(self):
        tools = re.findall(r"(?m)^  - '(.+)'$", self.front())
        self.assertEqual(tools, ['Bash(python3 -B "${CLAUDE_SKILL_DIR}/scripts/control.py" *)',
                                 'Bash(test -f "${CLAUDE_SKILL_DIR}/scripts/control.py")'])
        for tool in tools:
            self.assertNotRegex(tool, r"python3 \*|python3:\*|Bash\(\*\)|Bash\(sh|Bash\(bash")
        calls = re.findall(r'(?m)^python3 -B "\$\{CLAUDE_SKILL_DIR\}/scripts/(\w+\.py)" (\S+)', TEXT)
        self.assertTrue(calls)
        self.assertEqual({c[0] for c in calls}, {"control.py"})         # every call is covered by exactly the one python pattern
        self.assertIn('test -f "${CLAUDE_SKILL_DIR}/scripts/control.py"', TEXT)
        self.assertEqual(len(re.findall(r"python3 -B", self.front())), 1)

    def test_every_call_form_writes_the_script_path_as_one_quoted_argument_with_python3_dash_B(self):
        for line in TEXT.splitlines():
            if "scripts/control.py" in line and line.startswith("python3"):
                self.assertTrue(line.startswith('python3 -B "${CLAUDE_SKILL_DIR}/scripts/control.py" '), line)
        self.assertNotIn("PYTHONPATH=", TEXT)

    def test_claude_and_codex_path_handling_are_separated(self):
        self.assertIn("Claude:", TEXT)
        self.assertIn("Codex:", TEXT)
        self.assertIn("Do **not** run `${CLAUDE_SKILL_DIR}` as a shell variable", TEXT)
        self.assertIn("No path, no run", TEXT)
        self.assertIn("never copy scripts into the website project", TEXT)

    def test_communication_block_is_identical_to_the_other_skills_and_present_once(self):
        pat = r"<!-- user-communication -->.*?<!-- /user-communication -->"
        mine = re.findall(pat, TEXT, re.S)
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0], re.search(pat, (ROOT / "skills/setup/SKILL.md").read_text(), re.S).group(0))

    def test_read_first_links_resolve(self):
        self.assertIn("`references/preview.md`", TEXT)
        self.assertIn("`../_shared/references/interfaces.md`", TEXT)
        self.assertTrue((SKILL / "references/preview.md").is_file())
        self.assertTrue((SKILL / ".." / "_shared/references/interfaces.md").resolve().is_file())

    def test_skill_never_installs_and_keeps_the_three_facts_apart(self):
        self.assertIn("never installs dependencies", TEXT)
        self.assertIn("needs-install", TEXT)
        self.assertIn("Only `page-confirmed` is evidence", TEXT)
        self.assertIn("do not claim a visual result", TEXT)
        self.assertIn("Claude-desktop artifact", TEXT)
        self.assertNotIn("preview_start", TEXT.replace("no host preview/start tool", ""))

    def test_reference_states_the_process_page_visual_separation_and_the_launch_artifact_status(self):
        ref = (SKILL / "references/preview.md").read_text()
        for needle in ("Claude-desktop-specific artifact", "not a Codex integration", "page-identity-only", "visibility_checked",
                       "at most 600", "insufficient-evidence", "never by name, port or guessed pid"):
            self.assertIn(needle.lower(), ref.lower(), needle)
        self.assertNotIn("PLANNED", ref)
        self.assertNotIn("passed", ref.lower().replace("passed to", ""))


if __name__ == "__main__":
    unittest.main()

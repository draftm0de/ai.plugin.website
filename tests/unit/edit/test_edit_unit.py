"""Unit tests of the pure guards in edit.py (in-process, temporary directories only)."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.support import edit_helpers as t  # noqa: F401  (puts skills/edit/scripts on sys.path)

import edit  # noqa: E402


class Dirs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)


class AtomicReplace(Dirs):
    def test_replaces_content_and_keeps_the_mode(self):
        f = self.tmp / "a.txt"
        f.write_bytes(b"old")
        os.chmod(f, 0o640)
        edit.atomic_replace(f, b"new\r\n")
        self.assertEqual((f.read_bytes(), f.stat().st_mode & 0o777), (b"new\r\n", 0o640))
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["a.txt"])

    def test_a_failing_replace_leaves_the_original_and_no_temp_file(self):
        f = self.tmp / "a.txt"
        f.write_bytes(b"old")
        with mock.patch.object(edit.os, "replace", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                edit.atomic_replace(f, b"new")
        self.assertEqual(f.read_bytes(), b"old")
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["a.txt"])

    def test_a_failing_write_leaves_the_original_and_no_temp_file(self):
        f = self.tmp / "a.txt"
        f.write_bytes(b"old")
        with mock.patch.object(edit.os, "fsync", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                edit.atomic_replace(f, b"new")
        self.assertEqual((f.read_bytes(), sorted(p.name for p in self.tmp.iterdir())), (b"old", ["a.txt"]))


class ReadRegular(Dirs):
    def test_regular_absent_symlink_and_directory(self):
        f = self.tmp / "a.txt"
        f.write_bytes(b"x")
        self.assertEqual(edit.read_regular(f), b"x")
        self.assertIsNone(edit.read_regular(self.tmp / "absent"))
        os.symlink(f, self.tmp / "link")
        with self.assertRaises(edit.Refused):
            edit.read_regular(self.tmp / "link")
        with self.assertRaises(edit.Refused):
            edit.read_regular(self.tmp)


class RemoveOwnFolder(Dirs):
    ORIGINAL = b"original bytes"

    def session(self):
        folder = self.tmp / "edit-x"
        (folder / "original" / "src" / "pages").mkdir(parents=True)
        (folder / "original" / "src" / "pages" / "index.astro").write_bytes(self.ORIGINAL)
        for name in (".owner", "index.json"):
            (folder / name).write_text("x")
        st = {"file": "src/pages/index.astro", "original_sha": edit.sha(self.ORIGINAL)}
        return folder, st

    def listing(self, folder):
        return sorted(str(p.relative_to(folder)) for p in folder.rglob("*"))

    def test_removes_exactly_the_objects_the_run_created(self):
        folder, st = self.session()
        edit.remove_own_folder(folder, st)
        self.assertFalse(folder.exists())

    def test_every_unexpected_object_stops_the_whole_cleanup_before_the_first_deletion(self):
        for label, tamper in (
                ("file in the folder", lambda f: (f / "notes.txt").write_text("k")),
                ("file directly under original", lambda f: (f / "original" / "notes.txt").write_text("k")),
                ("file next to the backup", lambda f: (f / "original/src/pages/notes.txt").write_text("k")),
                ("foreign directory", lambda f: (f / "original/extra").mkdir()),
                ("foreign directory in src", lambda f: (f / "original/src/other").mkdir()),
                ("empty foreign file", lambda f: (f / "original/src/x").write_text("")),
                ("legacy fixed temp name", lambda f: (f / "index.json.tmp").write_text("k")),
                ("changed backup", lambda f: (f / "original/src/pages/index.astro").write_bytes(b"changed")),
                ("backup is a link", lambda f: ((f / "original/src/pages/index.astro").unlink(), os.symlink(f / "index.json", f / "original/src/pages/index.astro"))),
                ("directory is a link", lambda f: (shutil.rmtree(f / "original/src/pages"), os.symlink(f / "original/src", f / "original/src/pages"))),
                ("backup is a directory", lambda f: ((f / "original/src/pages/index.astro").unlink(), (f / "original/src/pages/index.astro").mkdir())),
                ("owner is a directory", lambda f: ((f / ".owner").unlink(), (f / ".owner").mkdir())),
                ("missing owner", lambda f: (f / ".owner").unlink())):
            with self.subTest(label):
                folder, st = self.session()
                tamper(folder)
                before = self.listing(folder)
                with self.assertRaises(edit.CleanupRefused):
                    edit.remove_own_folder(folder, st)
                self.assertEqual(self.listing(folder), before)
                shutil.rmtree(folder)

    def test_a_link_to_outside_is_never_followed(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep").write_text("k")
        folder, st = self.session()
        shutil.rmtree(folder / "original")
        os.symlink(outside, folder / "original")
        with self.assertRaises(edit.CleanupRefused):
            edit.remove_own_folder(folder, st)
        self.assertEqual((outside / "keep").read_text(), "k")


class Redaction(unittest.TestCase):
    # (line, every fragment of the fictional secret that must be gone)
    CASES = [("TOKEN=abc123", ["abc123"]), ("NPM_TOKEN: abc123", ["abc123"]), ("api_key=abc123", ["abc123"]),
             ("Authorization: Bearer fake-token-123", ["Bearer", "fake-token-123", "fake", "token-123"]),
             ("authorization: Basic ZmFrZTpmYWtl", ["Basic", "ZmFrZTpmYWtl"]),
             ("Proxy-Authorization: Bearer fake proxy tok", ["Bearer", "fake", "proxy", "tok"]),
             ('PASSWORD="first second"', ["first", "second"]), ("PASSWORD='first second third'", ["first", "second", "third"]),
             ('password = "alpha  beta"', ["alpha", "beta"]), ("PASSWORD=first second", ["first", "second"]),
             (r'PASSWORD="first \"second\" third"', ["first", "second", "third"]), (r"SECRET='it\'s one two'", ["one", "two"]),
             ('{"client_secret": "alpha beta", "x": 1}', ["alpha", "beta"]), ('{"password": "a\\"b c"}', ["b c"]),
             ('PASSWORD="unclosed one two', ["unclosed", "one", "two"]), ("SECRET='unclosed one two", ["unclosed", "one", "two"]),
             ('"auth_token": "alpha beta', ["alpha", "beta"]), ("export MY_AUTH_HEADER=abc123", ["abc123"]), ("DB_PASSWD:abc123", ["abc123"])]

    def test_known_secret_fields_lose_every_part_of_their_value(self):
        for line, fragments in self.CASES:
            out = edit.redact(f"before\n{line}\nafter")
            for fragment in fragments:
                self.assertNotIn(fragment, out, (line, fragment))
            self.assertIn("<redacted>", out, line)
            self.assertTrue(out.startswith("before\n") and out.endswith("\nafter"), line)      # neighbouring lines stay

    def test_two_fields_on_one_line_and_in_json_are_both_redacted(self):
        out = edit.redact('{"token": "one two", "next_password": "three four", "keep": "ok"}')
        for fragment in ("one", "two", "three", "four"):
            self.assertNotIn(fragment, out)
        self.assertIn('"keep": "ok"', out)

    def test_ordinary_diagnostics_stay(self):
        text = "build exploded: Cannot find module './x' (src/pages/index.astro:12)\nlast line: nobody"
        self.assertEqual(edit.redact(text), text)

    def test_the_rest_of_a_line_after_an_unquoted_value_is_dropped_on_purpose(self):
        self.assertEqual(edit.redact("TOKEN=abc then more text"), "TOKEN=<redacted>")


class StateArea(Dirs):
    def test_an_area_below_project_or_plugin_is_refused(self):
        root = self.tmp / "project"
        root.mkdir()
        with mock.patch.object(edit.tempfile, "tempdir", str(root)):
            with self.assertRaises(edit.Refused):
                edit.check_state_area(root)
        outside = self.tmp / "tmp"
        outside.mkdir()
        with mock.patch.object(edit.tempfile, "tempdir", str(outside)):
            edit.check_state_area(root)                       # fine: neither inside the project nor the plugin
            with mock.patch.object(edit, "PLUGIN_ROOT", outside):
                with self.assertRaises(edit.Refused):
                    edit.check_state_area(root)


class ArgumentSurface(unittest.TestCase):
    def test_no_command_takes_a_path_to_write_to(self):
        text = (t.PY / "edit.py").read_text()
        for flag in ('"--file"', '"--path"', '"--target"', '"--site-path"'):
            self.assertNotIn(flag, text)
        self.assertEqual(edit.ALLOWED, ("src/pages/index.astro",))
        self.assertEqual(edit.REPAIR_LIMIT, 2)


if __name__ == "__main__":
    unittest.main()

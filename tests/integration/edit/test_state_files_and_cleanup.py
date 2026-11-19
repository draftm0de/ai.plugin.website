"""edit: state files and the backup tree are never read or written through links or foreign objects (access spy, fictional external
files), the cleanup verifies the whole backup tree before the first deletion, and tool output is redacted before it is cut.
Unchanged hashes alone prove nothing about reading: every case also asserts that the spy saw no access to the external folder."""
import json
import os
import shutil
from pathlib import Path

from tests.integration.edit.test_symlink_reads import SpiedCase
from tests.support import edit_helpers as t
from tests.support.edit_helpers import EditCase, GOOD, delta, git, tree

NEW = GOOD.replace("Training twice a week.", "Training three times a week.")
SECRET = "EXTERNAL SECRET\n"


class StateFilesAndLinks(SpiedCase):
    def prepare(self):
        (self.external / "victim.txt").write_text(SECRET)
        self.st = self.begin()
        self.session = Path(self.st)

    def attack_all_commands(self, label, expect=None):
        before_project, before_ext = self.snap(), tree(self.external)
        for name, argv in self.commands(self.st):
            code, d, records = self.spy(*argv)
            self.assertEqual(code, 1, (label, name, d))
            self.assertIn(d.get("state") or ("conflict" if str(d.get("outcome", "")).startswith("conflict") else None), ("refused", "stop", "conflict"), (label, name, d))
            self.assertNotIn("raw", d, (label, name))
            self.assertNotIn("Traceback", json.dumps(d))
            self.assertEqual(self.reads_of(records, self.external), [], f"{label}/{name}: external access")
            if expect:
                self.assertIn(expect, d.get("message", ""), (label, name))
        self.assertEqual(self.snap(), before_project, label)
        self.assertEqual(tree(self.external), before_ext, label)
        self.assertEqual(self.npm_calls(), [], label)

    def test_a_fixed_temp_name_as_symlink_is_neither_written_through_nor_removed(self):
        self.prepare()
        link = self.session / "index.json.tmp"
        os.symlink(self.external / "victim.txt", link)
        before_ext = tree(self.external)
        for argv in (("write", "--state", self.st, "--content-file", str(self.tmpdir / "c.astro")), ("check", "--state", self.st, "--npm", str(self.npm))):
            (self.tmpdir / "c.astro").write_text(NEW)
            code, d, records = self.spy(*argv)
            self.assertEqual(code, 0, d)
            self.assertEqual(self.reads_of(records, self.external), [], argv[0])
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), str(self.external / "victim.txt"))
        self.assertEqual(tree(self.external), before_ext)
        self.assertEqual((self.external / "victim.txt").read_text(), SECRET)
        code, f, records = self.spy("finish", "--state", self.st, "--visual-done")                  # the link is foreign: nothing is removed
        self.assertEqual(code, 0, f)
        self.assertTrue(f["backup"].startswith("kept (nothing removed); cleanup refused"), f["backup"])
        self.assertTrue(link.is_symlink())
        self.assertEqual(self.reads_of(records, self.external), [])
        self.assertEqual(tree(self.external), before_ext)

    def test_temp_files_of_the_state_writer_are_exclusive_and_leave_nothing_behind(self):
        self.prepare()
        self.write(self.st, NEW)
        self.assertEqual(sorted(p.name for p in self.session.iterdir()), [".owner", "index.json", "original"])

    def test_index_json_as_symlink(self):
        self.prepare()
        shutil.copy2(self.session / "index.json", self.external / "index.json")
        (self.session / "index.json").unlink()
        os.symlink(self.external / "index.json", self.session / "index.json")
        self.attack_all_commands("index.json")

    def test_owner_as_symlink(self):
        self.prepare()
        shutil.copy2(self.session / ".owner", self.external / "owner")
        (self.session / ".owner").unlink()
        os.symlink(self.external / "owner", self.session / ".owner")
        self.attack_all_commands(".owner")

    def test_original_backup_file_as_symlink(self):
        self.prepare()
        (self.external / "index.astro").write_text(SECRET)
        backup = self.session / "original/src/pages/index.astro"
        backup.unlink()
        os.symlink(self.external / "index.astro", backup)
        self.write(self.st, NEW)                                         # writing does not need the backup
        for name, argv in (("diff", ("diff", "--state", self.st)), ("finish", ("finish", "--state", self.st, "--visual-done"))):
            code, d, records = self.spy(*argv)
            self.assertEqual(code, 1, (name, d))
            self.assertEqual(d["state"] if "state" in d else "refused", "refused", d)
            self.assertEqual(self.reads_of(records, self.external), [], name)
            self.assertNotIn(SECRET.strip(), json.dumps(d))
        self.assertEqual((self.external / "index.astro").read_text(), SECRET)
        self.assertTrue(self.session.is_dir())

    def test_parent_directory_of_the_backup_as_symlink(self):
        self.prepare()
        (self.external / "pages").mkdir()
        (self.external / "pages" / "index.astro").write_text(SECRET)
        shutil.rmtree(self.session / "original/src/pages")
        os.symlink(self.external / "pages", self.session / "original/src/pages")
        before_ext = tree(self.external)
        for name, argv in (("diff", ("diff", "--state", self.st)), ("finish", ("finish", "--state", self.st, "--visual-done"))):
            code, d, records = self.spy(*argv)
            self.assertEqual(code, 1, (name, d))
            self.assertEqual(self.reads_of(records, self.external), [], name)
            self.assertNotIn(SECRET.strip(), json.dumps(d))
        self.assertEqual(tree(self.external), before_ext)

    def test_session_folder_replaced_by_a_symlink(self):
        self.prepare()
        shutil.copytree(self.session, self.external / "session")
        moved = self.session.parent / "moved-away"
        self.session.rename(moved)
        os.symlink(self.external / "session", self.session)
        self.attack_all_commands("session folder link")
        self.assertTrue(moved.is_dir())

    def test_session_folder_replaced_by_a_forged_copy_for_another_project_root(self):
        self.prepare()
        forged = self.session.parent / "edit-forged"
        shutil.copytree(self.session, forged)
        idx = json.loads((forged / "index.json").read_text())
        idx["root"] = str(self.external)
        (forged / "index.json").write_text(json.dumps(idx))
        before = tree(forged)
        for name, argv in self.commands(str(forged)):
            code, d, records = self.spy(*argv)
            self.assertEqual((code, d["state"]), (1, "refused"), (name, d))
            self.assertEqual(self.reads_of(records, self.external), [], name)
        self.assertEqual(tree(forged), before)
        self.assertEqual(self.index.read_text(), GOOD)

    def test_a_state_folder_outside_the_backup_area_is_refused_before_anything_in_it_is_read(self):
        self.prepare()
        outside = self.external / "edit-copy"
        shutil.copytree(self.session, outside)
        for name, argv in self.commands(str(outside)):
            code, d, records = self.spy(*argv)
            self.assertEqual((code, d["state"]), (1, "refused"), (name, d))
            self.assertEqual(self.reads_of(records, self.external), [], name)

    def test_the_parent_of_the_session_folder_as_symlink(self):
        self.prepare()
        area = self.session.parent
        shutil.copytree(area, self.external / "area", symlinks=True)
        moved = area.with_name("moved-area")
        area.rename(moved)
        os.symlink(self.external / "area", area)
        self.attack_all_commands("area link")


class CleanupVerifiesTheWholeTree(EditCase):
    def checked_session(self):
        st = self.begin()
        self.write(st, NEW)
        self.check(st)
        return st, Path(st)

    def assert_refused_and_intact(self, st, session, before, code, f):
        self.assertEqual(code, 0, f)
        self.assertEqual(f["outcome"], "complete")                          # the work itself is complete; only the cleanup was refused
        self.assertTrue(f["backup"].startswith("kept (nothing removed); cleanup refused"), f["backup"])
        self.assertEqual(f["backup_folder"], st)
        self.assertEqual(tree(session), before)

    def test_foreign_objects_anywhere_in_the_tree_keep_the_whole_backup(self):
        for label, rel, make in (("directly under original", "original/notes.txt", "file"),
                                 ("under original/src/pages", "original/src/pages/notes.txt", "file"),
                                 ("under original/src", "original/src/notes.txt", "file"),
                                 ("foreign subdirectory", "original/src/pages/sub", "dir"),
                                 ("foreign subdirectory with content", "original/extra/inner.txt", "nested")):
            with self.subTest(label):
                self.index.write_text(GOOD)
                st, session = self.checked_session()
                target = session / rel
                if make == "dir":
                    target.mkdir()
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("someone else's note")
                before = tree(session)
                code, f = self.finish(st, visual=True)
                self.assert_refused_and_intact(st, session, before, code, f)
                self.assertTrue((session / "original/src/pages/index.astro").is_file())
                self.assertEqual((session / ".owner").is_file() and (session / "index.json").is_file(), True)
                shutil.rmtree(session)

    def test_a_replaced_backup_file_or_link_keeps_everything_and_is_reported(self):
        for label, tamper in (("changed content", lambda b: b.write_bytes(b"not the original")),
                              ("replaced by symlink", lambda b: (b.unlink(), os.symlink(self.site / "package.json", b))),
                              ("replaced by directory", lambda b: (b.unlink(), b.mkdir()))):
            with self.subTest(label):
                self.index.write_text(GOOD)
                st, session = self.checked_session()
                tamper(session / "original/src/pages/index.astro")
                before = tree(session)
                pkg = t.sha(self.site / "package.json")
                code, f = self.finish(st, visual=True)
                self.assertEqual(code, 1, f)                                  # the original is not trustworthy: controlled stop, nothing complete
                self.assertEqual(f["state"], "refused")
                self.assertEqual(tree(session), before)
                self.assertEqual(t.sha(self.site / "package.json"), pkg)
                shutil.rmtree(session)

    def test_an_unchanged_regular_backup_is_removed_after_complete(self):
        st, session = self.checked_session()
        code, f = self.finish(st, visual=True)
        self.assertEqual((code, f["outcome"], f["backup"]), (0, "complete", "removed (own folder only)"))
        self.assertFalse(session.exists())
        self.assertTrue(session.parent.is_dir())

    def test_a_cleanup_failure_part_way_reports_what_remains(self):
        st, session = self.checked_session()
        os.chmod(session / "original/src/pages", 0o555)                       # the backup file cannot be removed
        self.addCleanup(os.chmod, session / "original/src/pages", 0o755)
        if os.access(session / "original/src/pages", os.W_OK):
            self.skipTest("directory stays writable")
        code, f = self.finish(st, visual=True)
        os.chmod(session / "original/src/pages", 0o755)
        self.assertEqual(code, 0, f)
        self.assertTrue(f["backup"].startswith("kept;"), f["backup"])
        self.assertIn("original/src/pages/index.astro", f["backup"])          # the actual state is named
        self.assertEqual(f["backup_folder"], st)


def _sh(text):
    """Single-quoted shell literal."""
    return "'" + text.replace("'", "'\\''") + "'"


class Redaction(EditCase):
    FAKE = {"TOKEN=tok-AAAA1111": "stdout", "NPM_PASSWORD: pw-BBBB2222": "stderr", '"api_key": "key-CCCC3333"': "stderr", "AUTH_SECRET=sec-DDDD4444": "stdout"}

    def noisy_npm(self, lines, fail=False, pad=0):
        script = self.tmpdir / "bin" / "npm-noisy"
        body = ["#!/bin/sh", 'echo "$*" >> "$FAKE_NPM_LOG"', 'if [ "$2" = build ]; then']
        for text, stream in lines:
            body.append(f"  echo '{text}'" + (" >&2" if stream == "stderr" else ""))
        if pad:
            body.append(f"  i=0; while [ $i -lt {pad} ]; do echo 'padding line to push the key out of the tail window, nothing secret here'; i=$((i+1)); done")
        body.append(f"  exit {3 if fail else 0}")
        body.append("fi")
        body.append('echo "No errors."')
        script.write_text("\n".join(body) + "\n")
        script.chmod(0o755)
        return script

    def assert_clean(self, d):
        text = json.dumps(d)
        for secret in ("tok-AAAA1111", "pw-BBBB2222", "key-CCCC3333", "sec-DDDD4444"):
            self.assertNotIn(secret, text, secret)

    def test_values_in_stdout_and_stderr_are_redacted_and_the_diagnosis_stays_useful(self):
        st = self.begin()
        self.write(st, NEW)
        npm = self.noisy_npm([(k, v) for k, v in self.FAKE.items()] + [("build exploded: Cannot find module x", "stderr")], fail=True)
        code, d = self.check(st, npm=npm)
        self.assertEqual((code, d["state"], d["build"]["exit"]), (1, "failed", 3))      # the real exit code and status are kept
        self.assertFalse(d["check"]["ran"])
        self.assert_clean(d)
        self.assertIn("build exploded: Cannot find module x", d["build"]["tail"])
        self.assertIn("TOKEN=<redacted>", d["build"]["tail"])
        _, f = self.finish(st)
        self.assert_clean(f)

    def test_output_over_the_cut_limit_is_redacted_before_it_is_cut(self):
        """The secret line is the LAST one before the cut point's key: cutting first could leave only the value; redacting first cannot."""
        st = self.begin()
        self.write(st, NEW)
        long_line = "x" * 1982          # 23 + 1982 + newline = 2006 characters: the cut would start inside the key ("OKEN=tok-...")
        script = self.tmpdir / "bin" / "npm-long"
        script.write_text('#!/bin/sh\necho "$*" >> "$FAKE_NPM_LOG"\nif [ "$2" = build ]; then\n'
                          f"  printf 'NPM_TOKEN=tok-AAAA1111 %s\\n' {long_line!r}\n  exit 3\nfi\necho ok\n")
        script.chmod(0o755)
        code, d = self.check(st, npm=script)
        self.assertEqual((code, d["state"], d["build"]["exit"]), (1, "failed", 3))
        self.assert_clean(d)
        self.assertLessEqual(len(d["build"]["tail"]), 2000)
        self.assertEqual(d["build"]["tail"].strip(), "NPM_TOKEN=<redacted>")          # the unquoted value runs to the end of its line: the whole line goes

    FRAGMENTS = ("fake-token-123", "Bearer", "ZmFrZTpmYWtl", "first", "second", "third", "alpha", "beta", "gamma")
    LINES_OUT = ["Authorization: Bearer fake-token-123", 'PASSWORD="first second third"', "{\"client_secret\": \"alpha beta\", \"x\": 1}"]
    LINES_ERR = ["Proxy-Authorization: Basic ZmFrZTpmYWtl", "PASSWORD='first \\'second\\' third'", 'API_KEY="gamma alpha unclosed', "ordinary stderr diagnosis"]

    def script(self, name, exit_code, pad=0):
        lines = []
        for text in self.LINES_OUT:
            lines.append("printf '%s\\n' " + _sh(text))
        for text in self.LINES_ERR:
            lines.append("printf '%s\\n' " + _sh(text) + " >&2")
        if pad:
            lines.append(f"i=0; while [ $i -lt {pad} ]; do echo 'padding diagnosis line'; i=$((i+1)); done")
        path = self.tmpdir / "bin" / name
        path.write_text('#!/bin/sh\necho "$*" >> "$FAKE_NPM_LOG"\nif [ "$2" = build ]; then\n' + "\n".join("  " + l for l in lines) + f"\n  exit {exit_code}\nfi\necho fine\n")
        path.chmod(0o755)
        return path

    def assert_no_fragment(self, d):
        text = json.dumps(d)
        for fragment in self.FRAGMENTS:
            self.assertNotIn(fragment, text, fragment)

    def test_authorization_and_multi_word_values_leave_no_fragment_on_failure_and_success(self):
        for exit_code, state in ((3, "failed"), (0, "checked")):
            with self.subTest(exit_code):
                self.index.write_text(GOOD)
                st = self.begin()
                self.write(st, NEW)
                code, d = self.check(st, npm=self.script(f"npm-{exit_code}", exit_code))
                self.assertEqual((d["state"], d["build"]["exit"]), (state, exit_code))
                self.assertEqual(code, 0 if exit_code == 0 else 1)
                self.assert_no_fragment(d)
                tail = d["build"]["tail"]
                self.assertIn("ordinary stderr diagnosis", tail)                  # unaffected diagnosis lines stay
                self.assertIn("Authorization=<redacted>", tail)
                self.assertIn("Proxy-Authorization=<redacted>", tail)
                self.assert_no_fragment(self.finish(st)[1])

    def test_a_long_output_is_redacted_before_it_is_cut_and_keeps_its_diagnosis(self):
        st = self.begin()
        self.write(st, NEW)
        code, d = self.check(st, npm=self.script("npm-long", 3, pad=200))
        self.assertEqual((code, d["state"], d["build"]["exit"]), (1, "failed", 3))
        self.assertLessEqual(len(d["build"]["tail"]), 2000)
        self.assert_no_fragment(d)
        self.assertIn("padding diagnosis line", d["build"]["tail"])
        st = self.begin()                                                    # secret lines inside the window AND at its edge
        pad_first = self.tmpdir / "bin" / "npm-edge"
        pad_first.write_text('#!/bin/sh\necho "$*" >> "$FAKE_NPM_LOG"\nif [ "$2" = build ]; then\n'
                             "  printf 'Authorization: Bearer fake-token-123 %s\\n' " + _sh("x" * 1960) + "\n  exit 3\nfi\n")
        pad_first.chmod(0o755)
        self.write(st, NEW + "<!-- edge -->\n")
        code, d = self.check(st, npm=pad_first)
        self.assert_no_fragment(d)

    def test_a_passing_check_with_secret_output_is_redacted_too(self):
        st = self.begin()
        self.write(st, NEW)
        script = self.tmpdir / "bin" / "npm-ok"
        script.write_text('#!/bin/sh\necho "$*" >> "$FAKE_NPM_LOG"\necho "TOKEN=tok-AAAA1111"\necho "PASSWORD: pw-BBBB2222" >&2\nexit 0\n')
        script.chmod(0o755)
        code, d = self.check(st, npm=script)
        self.assertEqual((code, d["state"]), (0, "checked"))
        self.assert_clean(d)
        self.assertIn("<redacted>", d["build"]["tail"])
        self.assertIn("<redacted>", d["check"]["tail"])


if __name__ == "__main__":
    import unittest
    unittest.main()

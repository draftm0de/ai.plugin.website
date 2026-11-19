"""edit: begin, write and replace. Only the start page changes; hash-guarded atomic writes; conflicts never overwrite; foreign
work survives; line endings are not normalised. Temporary projects, throw-away git repositories."""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from unittest import mock

from tests.support import edit_helpers as t
from tests.support.edit_helpers import EditCase, GOOD, delta, git, sha, tree

import edit as edit_mod  # noqa: E402

NEW = GOOD.replace("Training twice a week.", "Training three times a week.")


class AllowedChange(EditCase):
    def test_e1_shape_and_only_the_target_changes(self):
        before = self.snap()
        st = self.begin()
        self.assertEqual(self.write(st, NEW)[1]["state"], "written")
        code, d = self.check(st)
        self.assertEqual((code, d["state"], d["build"]["exit"], d["check"]["exit"]), (0, "checked", 0, 0))
        self.assertEqual(delta(before, self.snap()), {f"{self.rel}/src/pages/index.astro"})
        self.assertEqual(self.npm_calls(), ["run build", "run check"])
        for forbidden in ("package.json", "package-lock.json", "src/styles/foundation/tokens.css", "rules/seo.md", "scripts/seo-check.mjs"):
            self.assertEqual(sha(self.site / forbidden), before[f"{self.rel}/{forbidden}"])

    def test_e2_replace_only_named_text(self):
        st = self.begin()
        code, d = self.replace(st, "We play on Sundays.", "We play on Saturdays.")
        self.assertEqual(d["state"], "written")
        self.assertEqual(self.index.read_text(), GOOD.replace("Sundays", "Saturdays"))
        # ambiguous, absent or empty find text writes nothing
        before = self.snap()
        for find in ("<section", "no such text", ""):
            code, d = self.replace(st, find, "x")
            self.assertEqual((code, d["state"]), (1, "stop"), find)
        self.assertEqual(delta(before, self.snap()), set())

    def test_e3_repeat_is_unchanged(self):
        st = self.begin()
        self.write(st, NEW)
        h1 = sha(self.index)
        mtime = self.index.stat().st_mtime_ns
        code, d = self.write(st, NEW)
        self.assertEqual((code, d["state"]), (0, "unchanged"))
        self.assertEqual((sha(self.index), self.index.stat().st_mtime_ns), (h1, mtime))
        st2 = self.begin()                                       # a second session on the already changed page: still unchanged
        self.assertEqual(self.write(st2, NEW)[1]["state"], "unchanged")
        self.assertEqual(self.index.read_text().count("Training three times a week."), 1)

    def test_other_targets_are_not_reachable_through_the_cli(self):
        st = self.begin()
        for flag in ("--file", "--path", "--target", "--site-path"):
            self.assertEqual(self.edit("write", "--state", st, "--content-file", str(self.index), flag, "src/pages/other.astro")[0], 2)
        self.assertEqual(self.edit("create", "--root", str(self.root))[0], 2)                  # there is no command that creates files
        self.assertFalse((self.site / "src" / "pages" / "other.astro").exists())

    def test_the_allow_list_is_exactly_the_start_page(self):
        self.assertEqual(edit_mod.ALLOWED, ("src/pages/index.astro",))
        for rel in ("src/pages/about.astro", "src/pages/index.astro/../404.astro", "../x", "/etc/passwd", "package.json", "rules/seo.md",
                    ".project/specs/zyris-website.json", "src/pages/", "src/pages/blog/index.astro", "src/pages/Index.astro"):
            with self.subTest(rel), self.assertRaises(edit_mod.Refused):
                edit_mod.safe_target(self.root, self.rel, rel)
        for site in ("", "/abs", "../outside", "sites/../../outside"):
            with self.subTest(site), self.assertRaises(edit_mod.Refused):
                edit_mod.safe_target(self.root, site, "src/pages/index.astro")
        self.assertEqual(edit_mod.safe_target(self.root, self.rel, "src/pages/index.astro"), self.index)


class ForeignWork(EditCase):
    def test_e4_dirty_tree_and_untracked_files_survive(self):
        other = self.site / "src" / "styles" / "site.css"
        other.write_text(other.read_text() + "\n/* someone else's work */\n")
        (self.site / "notes.txt").write_text("untracked\n")
        (self.root / "draft.md").write_text("untracked at root\n")
        self.index.write_text(GOOD.replace("Ask at the front desk.", "Ask at the front desk (earlier uncommitted edit)."))
        before, status = self.snap(), git(self.root, "status", "--porcelain=v1", "--untracked-files=all")
        st = self.begin()
        start_text = self.index.read_text()
        self.write(st, start_text.replace("Training twice a week.", "Training three times a week."))
        self.assertEqual(delta(before, self.snap()), {f"{self.rel}/src/pages/index.astro"})
        self.assertIn("earlier uncommitted edit", self.index.read_text())
        self.assertEqual(git(self.root, "stash", "list"), "")
        self.assertEqual(status, git(self.root, "status", "--porcelain=v1", "--untracked-files=all"))   # nothing cleaned, nothing staged
        _, d = self.edit("diff", "--state", st)
        self.assertIn("three times", d["diff"])
        changed = [l for l in d["diff"].splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        self.assertFalse([l for l in changed if "earlier uncommitted edit" in l])     # earlier foreign work is part of the original
        _, f = self.finish(st)
        self.assertEqual(f["git_status_delta_since_begin"], [])

    def test_begin_records_head_and_the_start_status_including_untracked_files(self):
        (self.root / "draft.md").write_text("untracked at root\n")
        code, d = self.edit("begin", "--root", str(self.root), "--site", self.DOMAIN, check=True)
        self.assertEqual(d["head"], git(self.root, "rev-parse", "HEAD").strip())
        self.assertIn("?? draft.md", d["uncommitted_at_start"])
        saved = json.loads((Path(d["state_folder"]) / "index.json").read_text())
        self.assertEqual((saved["head"], saved["porcelain_start"]), (d["head"], d["uncommitted_at_start"]))

    def test_e5_foreign_change_is_a_conflict(self):
        st = self.begin()
        foreign = GOOD + "<!-- foreign -->\n"
        self.index.write_text(foreign)
        before = self.snap()
        code, d = self.write(st, NEW)
        self.assertEqual((code, d["state"]), (1, "conflict"))
        self.assertEqual(self.index.read_text(), foreign)
        self.assertEqual(delta(before, self.snap()), set())
        self.assertEqual(d["backup_kept"], st)
        self.assertTrue(Path(st).is_dir())
        self.index.unlink()                                      # removal meanwhile is a conflict as well
        self.assertEqual(self.write(st, NEW)[1]["state"], "conflict")
        self.assertFalse(self.index.exists())

    def test_e5_foreign_change_between_two_own_writes(self):
        st = self.begin()
        self.write(st, NEW)
        theirs = NEW + "<!-- foreign second -->\n"
        self.index.write_text(theirs)
        code, d = self.write(st, NEW.replace("Sundays", "Mondays"))
        self.assertEqual((code, d["state"]), (1, "conflict"))
        self.assertEqual(self.index.read_text(), theirs)
        _, f = self.finish(st, visual=True)
        self.assertEqual(f["backup"], "kept")
        self.assertTrue(Path(st).is_dir())

    def test_replace_conflicts_too_and_never_overwrites(self):
        st = self.begin()
        foreign = GOOD.replace("Sundays", "Foreign days")
        self.index.write_text(foreign)
        code, d = self.replace(st, "Training twice a week.", "Training daily.")
        self.assertEqual((code, d["state"]), (1, "conflict"))
        self.assertEqual(self.index.read_text(), foreign)


class SymlinksAndPaths(EditCase):
    def begin_raw(self):
        return self.edit("begin", "--root", str(self.root), "--site", self.DOMAIN)

    def test_e7_symlinks_and_missing_target_are_refused_at_begin(self):
        victim = self.tmpdir / "victim.txt"
        victim.write_text("precious")
        self.index.unlink()                                                     # symlink at the target
        os.symlink(victim, self.index)
        self.assertEqual(self.begin_raw()[0], 1)
        self.assertEqual(victim.read_text(), "precious")
        self.assertTrue(self.index.is_symlink())
        self.index.unlink()                                                     # absent target: nothing is created
        self.assertEqual(self.begin_raw()[0], 1)
        self.assertFalse(self.index.exists())
        self.index.write_text(GOOD)                                             # symlinked parent component
        pages = self.site / "src" / "pages"
        pages.rename(self.site / "src" / "pages_real")
        os.symlink(self.site / "src" / "pages_real", pages)
        self.assertEqual(self.begin_raw()[0], 1)
        pages.unlink()
        (self.site / "src" / "pages_real").rename(pages)
        moved = self.tmpdir / "moved-site"                                      # symlinked site folder
        self.site.rename(moved)
        os.symlink(moved, self.site)
        self.assertEqual(self.begin_raw()[0], 1)
        self.assertEqual(victim.read_text(), "precious")
        self.assertEqual(self.state_files(), {})                                # no session was opened by any of these

    def test_symlink_inserted_after_begin_is_a_conflict_without_touching_the_target(self):
        victim = self.tmpdir / "victim.txt"
        victim.write_text("precious")
        st = self.begin()
        self.index.unlink()
        os.symlink(victim, self.index)
        code, d = self.write(st, NEW)
        self.assertEqual((code, d["state"]), (1, "conflict"))
        self.assertEqual(victim.read_text(), "precious")
        self.assertTrue(self.index.is_symlink())
        self.assertEqual(self.edit("diff", "--state", st)[0], 1)
        code, f = self.finish(st, visual=True)
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", json.dumps(f))
        self.assertEqual(victim.read_text(), "precious")
        self.assertTrue(Path(st).is_dir())

    def test_parent_directory_symlink_inserted_after_begin_is_a_conflict(self):
        outside = self.tmpdir / "outside"
        (outside / "pages").mkdir(parents=True)
        (outside / "pages" / "index.astro").write_text(GOOD)
        before = tree(outside)
        st = self.begin()
        pages = self.site / "src" / "pages"
        pages.rename(self.site / "src" / "pages_real")
        os.symlink(outside / "pages", pages)
        for code, d in (self.write(st, NEW), self.replace(st, "Sundays", "Mondays"), self.check(st), self.edit("diff", "--state", st)):
            self.assertEqual((code, d["state"]), (1, "conflict"))
        self.assertEqual(tree(outside), before)
        self.assertEqual(self.npm_calls(), [])

    def test_site_is_bound_to_the_resolver_not_to_the_caller(self):
        outside = self.tmpdir / "outside"
        (outside / "src" / "pages").mkdir(parents=True)
        (outside / "src" / "pages" / "index.astro").write_text("EXTERNAL\n")
        before = tree(outside)
        self.assertEqual(self.edit("begin", "--root", str(self.root), "--site", self.DOMAIN, "--site-path", str(outside))[0], 2)   # no free path
        self.make_site("other.test")                                            # a partial or other name does not authorise this site
        self.assertEqual(self.edit("begin", "--root", str(self.root), "--site", "club")[0], 1)
        self.assertEqual(self.edit("begin", "--root", str(self.root), "--site", "nope.test")[0], 1)
        mf = self.root / ".project/specs/zyris-website.json"                      # absolute, traversing or outside manifest paths
        orig = mf.read_text()
        for bad in (str(outside), "../outside", "sites/../../outside"):
            data = json.loads(orig)
            data["components"][0]["path"] = bad
            mf.write_text(json.dumps(data))
            self.assertEqual(self.edit("begin", "--root", str(self.root), "--site", self.DOMAIN)[0], 1, bad)
        mf.write_text(orig)
        self.assertEqual(tree(outside), before)
        self.assertEqual(self.index.read_text(), GOOD)

    def test_tampered_state_cannot_redirect_a_write(self):
        outside = self.tmpdir / "outside"
        (outside / "src" / "pages").mkdir(parents=True)
        (outside / "src" / "pages" / "index.astro").write_text("EXTERNAL\n")
        st = self.begin()
        idx = json.loads((Path(st) / "index.json").read_text())
        for key, value in (("site_path", str(outside)), ("file", "package.json"), ("file", "../x")):
            tampered = {**idx, key: value}
            (Path(st) / "index.json").write_text(json.dumps(tampered))
            self.assertEqual(self.write(st, NEW)[0], 1, (key, value))
        self.assertEqual((outside / "src" / "pages" / "index.astro").read_text(), "EXTERNAL\n")
        self.assertEqual(self.index.read_text(), GOOD)
        self.assertEqual(sha(self.site / "package.json"), t.tree(self.site)["package.json"])

    def test_state_folder_is_not_trusted_blindly(self):
        fake = self.tmpdir / "fake"
        fake.mkdir()
        (fake / "index.json").write_text(json.dumps({"token": "x"}))
        (fake / ".owner").write_text("y")
        c = self.tmpdir / "c"
        c.write_text("x")
        self.assertEqual(self.edit("write", "--state", str(fake), "--content-file", str(c))[0], 1)
        st = self.begin()                                                       # a state folder copied out of the backup area
        copied = self.tmpdir / "copied"
        shutil.copytree(st, copied)
        for command in (("write", "--content-file", str(c)), ("check",), ("diff",), ("finish", "--visual-done")):
            self.assertEqual(self.edit(command[0], "--state", str(copied), *command[1:])[0], 1, command)
        self.assertTrue(copied.is_dir())
        self.assertEqual(self.index.read_text(), GOOD)


class LineEndingsAndBytes(EditCase):
    def test_crlf_file_with_a_single_line_replacement_changes_only_those_bytes(self):
        crlf = GOOD.replace("\n", "\r\n").encode()
        self.index.write_bytes(crlf)
        git(self.root, "commit", "-qam", "crlf")
        st = self.begin()
        code, d = self.replace(st, "Training twice a week.", "Training three times a week.")
        self.assertEqual(d["state"], "written")
        self.assertEqual(self.index.read_bytes(), crlf.replace(b"Training twice a week.", b"Training three times a week."))
        self.assertEqual(self.index.read_bytes().count(b"\r\n"), crlf.count(b"\r\n"))
        self.assertNotIn(b"\n", self.index.read_bytes().replace(b"\r\n", b""))             # no bare LF was introduced

    def test_multiline_replacement_in_a_crlf_file_uses_the_requested_bytes_only(self):
        crlf = GOOD.replace("\n", "\r\n").encode()
        self.index.write_bytes(crlf)
        git(self.root, "commit", "-qam", "crlf")
        st = self.begin()
        find = '<section class="prose" id="about"><h2>About</h2><p>We play on Sundays.</p></section>\r\n    <section class="prose" id="contact">'
        new = '<section class="prose" id="about"><h2>About us</h2></section>\r\n    <section class="prose" id="contact">'
        code, d = self.replace(st, find, new)
        self.assertEqual((code, d["state"]), (0, "written"))
        self.assertEqual(self.index.read_bytes(), crlf.replace(find.encode(), new.encode()))
        # LF text against a CRLF file does not match and is never "normalised" into a match
        before = self.snap()
        code, d = self.replace(st, "</section>\n    <section", "</section>\n\n    <section")
        self.assertEqual((code, d["state"]), (1, "stop"))
        self.assertEqual(delta(before, self.snap()), set())

    def test_lf_multiline_replacement_and_mixed_endings_are_kept(self):
        mixed = (GOOD.replace("</header>\n", "</header>\r\n")).encode()
        self.index.write_bytes(mixed)
        git(self.root, "commit", "-qam", "mixed")
        st = self.begin()
        self.replace(st, "<h2>About</h2><p>We play on Sundays.</p>", "<h2>About</h2>\n      <p>We play on Sundays.</p>")
        self.assertEqual(self.index.read_bytes(), mixed.replace(b"<h2>About</h2><p>We play on Sundays.</p>",
                                                               b"<h2>About</h2>\n      <p>We play on Sundays.</p>"))

    def test_the_backup_is_the_original_bytes_even_when_they_are_not_utf8(self):
        raw = GOOD.encode() + b"<!-- \xff\xfe -->\r\n"
        self.index.write_bytes(raw)
        git(self.root, "commit", "-qam", "raw")
        st = self.begin()
        self.assertEqual((Path(st) / "original" / "src/pages/index.astro").read_bytes(), raw)
        code, d = self.replace(st, "Training twice a week.", "Training daily.")        # bytes-level replace works on a non-UTF-8 file
        self.assertEqual((code, d["state"]), (0, "written"))
        self.assertEqual(self.index.read_bytes(), raw.replace(b"Training twice a week.", b"Training daily."))
        code, d = self.edit("diff", "--state", st)                                      # no traceback for the report either
        self.assertEqual(code, 0, d)

    def test_the_total_diff_of_a_crlf_file_shows_only_the_changed_lines(self):
        self.index.write_bytes(GOOD.replace("\n", "\r\n").encode())
        git(self.root, "commit", "-qam", "crlf")
        st = self.begin()
        self.replace(st, "Training twice a week.", "Training daily.")
        code, d = self.edit("diff", "--state", st)
        changed = [l for l in d["diff"].splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        self.assertEqual(len(changed), 2, changed)

    def test_a_line_ending_only_change_is_visible_in_the_total_diff(self):
        st = self.begin()
        self.write(st, GOOD.replace("\n", "\r\n"))
        code, d = self.edit("diff", "--state", st)
        self.assertEqual(code, 0)
        self.assertIn("\r\n", d["diff"])
        self.assertIn("+", d["diff"])

    def test_non_utf8_find_text_is_rejected_without_a_traceback(self):
        st = self.begin()
        p = self.run_edit("replace", "--state", st, "--find", "\udcff", "--replace", "x")
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertNotIn("Traceback", p.stdout + p.stderr)
        self.assertEqual(self.index.read_text(), GOOD)

    def test_write_keeps_permissions_and_leaves_no_temp_file(self):
        os.chmod(self.index, 0o640)
        st = self.begin()
        self.write(st, NEW)
        self.assertEqual(self.index.stat().st_mode & 0o777, 0o640)
        self.assertEqual([p.name for p in self.index.parent.iterdir() if p.name.startswith(".edit-")], [])


class WriteFailures(EditCase):
    def test_unreadable_content_file_is_a_stop_and_writes_nothing(self):
        st = self.begin()
        before = self.snap()
        code, d = self.edit("write", "--state", st, "--content-file", str(self.tmpdir / "missing.astro"))
        self.assertEqual((code, d["state"]), (1, "stop"))
        self.assertEqual(delta(before, self.snap()), set())

    def test_a_directory_that_cannot_be_written_is_reported_and_leaves_the_file_unchanged(self):
        st = self.begin()
        pages = self.index.parent
        os.chmod(pages, stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(os.chmod, pages, 0o755)
        if os.access(pages, os.W_OK):
            self.skipTest("the directory stays writable for this user")
        before = self.snap()
        code, d = self.write(st, NEW)
        os.chmod(pages, 0o755)
        self.assertEqual((code, d["state"]), (1, "stop"), d)
        self.assertIn("unchanged", d["message"])
        self.assertEqual(delta(before, self.snap()), set())
        self.assertEqual(json.loads((Path(st) / "index.json").read_text())["writes"], [])     # no false success recorded
        self.assertEqual(self.write(st, NEW)[1]["state"], "written")                          # and the session still works

    def test_a_failing_replace_removes_the_temp_file_and_reports_no_success(self):
        """In-process: os.replace fails after the temp file was written."""
        st = self.begin()
        argv = ["write", "--state", st, "--content-file", str(self.tmpdir / "c.astro")]
        (self.tmpdir / "c.astro").write_text(NEW)
        before = self.snap()
        with mock.patch.object(edit_mod.tempfile, "tempdir", str(self.tmpdir)), \
                mock.patch.object(edit_mod.os, "replace", side_effect=OSError(28, "No space left on device")):
            with mock.patch("builtins.print") as printed:
                code = edit_mod.main(argv)
        report = json.loads(printed.call_args[0][0])
        self.assertEqual((code, report["state"]), (1, "stop"))
        self.assertIn("No space left", report["message"])
        self.assertEqual(delta(before, self.snap()), set())
        self.assertEqual([p.name for p in self.index.parent.iterdir() if p.name.startswith(".edit-")], [])
        saved = json.loads((Path(st) / "index.json").read_text())
        self.assertEqual((saved["writes"], saved["expected_sha"]), ([], sha(self.index)))


if __name__ == "__main__":
    import unittest
    unittest.main()

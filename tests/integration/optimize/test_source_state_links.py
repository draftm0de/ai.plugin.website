"""The read-only guard (`source_state`) records a versioned symbolic link as the link object and never opens, stats or follows
its target; a tracked path below a directory that became a symbolic link is an unsafe state and stops the run.

Evidence is an access spy on every way the guard could reach the external file (os.open, builtins.open, io.open, os.stat) AND an
access lock (mode 000) on the external file/folder: an unchanged hash of the external file would only prove write protection.
Fictional temporary files only."""
import builtins
import contextlib
import io
import os
import stat
from unittest import mock

from tests.support import optimize_helpers as h
from site_common.errors import Stop
import audit


@contextlib.contextmanager
def access_spy(external):
    """Record every open/stat whose real path lies below `external`; lstat/readlink are deliberately not wrapped."""
    ext = os.path.realpath(external)
    touched = []

    def wrap(original, name):
        def spy(path, *args, **kwargs):
            try:
                real = os.path.realpath(os.fspath(path))
            except TypeError:                                  # file descriptors
                real = None
            if real and (real == ext or real.startswith(ext + os.sep)):
                touched.append((name, os.fspath(path)))
            return original(path, *args, **kwargs)
        return spy

    with mock.patch("os.open", wrap(os.open, "os.open")), mock.patch.object(builtins, "open", wrap(builtins.open, "open")), \
            mock.patch.object(io, "open", wrap(io.open, "io.open")), mock.patch("os.stat", wrap(os.stat, "os.stat")):
        yield touched


class LinkCase(h.AuditCase):
    def setUp(self):
        super().setUp()
        self.outside = self.tmp / "outside"
        self.outside.mkdir()
        self.secret = self.outside / "secret.txt"
        self.secret.write_text("external content that must never be read\n")
        self.copy = self.outside / "secret-copy.txt"
        self.copy.write_text(self.secret.read_text())          # identical content, other link target
        self.rel = "sites/fx.test/src/link.txt"
        os.symlink(self.secret, self.site / "src" / "link.txt")
        (self.site / "fx" / "build.sh").write_text(
            (self.site / "fx" / "build.sh").read_text()
            + f'if [ -f src/RELINK ]; then ln -sf "{self.copy}" src/link.txt; fi\n'
            + 'if [ -f src/SWAP ]; then mv src/dirx src/dirx.moved && ln -s "$SWAP_TARGET" src/dirx; fi\n')
        (self.site / "src" / "dirx").mkdir()
        (self.site / "src" / "dirx" / "file.txt").write_text("tracked inside\n")
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "links")

    def lock(self, *paths):
        for path in paths:
            os.chmod(path, 0)
            self.addCleanup(os.chmod, path, 0o755 if path.is_dir() else 0o644)

    def state(self):
        return audit.source_state(self.root, ".project/reports/")


class VersionedLinks(LinkCase):
    def test_a_link_to_an_external_file_is_recorded_as_the_link_and_the_target_is_not_touched(self):
        self.lock(self.secret)
        with access_spy(self.outside) as touched:
            state = self.state()
            result = self.audit()
        self.assertEqual(touched, [], "the external file must not be opened or stat'ed")
        self.assertEqual(state["hashes"][self.rel], "LINK:" + str(self.secret))
        self.assertEqual(result["status"], "clean-with-warnings", result)
        self.assertEqual(result["readonly_violations"], [])

    def test_a_dangling_link_is_recorded_without_error(self):
        os.unlink(self.site / "src" / "link.txt")
        os.symlink(self.tmp / "does-not-exist", self.site / "src" / "link.txt")
        h.sh(self.root, "git", "commit", "-qam", "dangling")
        self.assertEqual(self.state()["hashes"][self.rel], "LINK:" + str(self.tmp / "does-not-exist"))
        self.assertEqual(self.audit()["status"], "clean-with-warnings")

    def test_a_changed_link_text_with_identical_target_content_is_a_visible_difference(self):
        before = self.state()
        os.unlink(self.site / "src" / "link.txt")
        os.symlink(self.copy, self.site / "src" / "link.txt")
        after = self.state()
        self.assertEqual(self.secret.read_bytes(), self.copy.read_bytes())
        self.assertIn(self.rel, audit.state_diff(before, after))
        self.assertNotEqual(before["digest"], after["digest"])

    def test_a_link_exchanged_during_the_run_ends_as_readonly_violated_without_opening_either_target(self):
        (self.site / "src" / "RELINK").write_text("")
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "marker")
        self.lock(self.secret, self.copy)
        with access_spy(self.outside) as touched:
            result = self.audit()
        self.assertEqual(touched, [])
        self.assertEqual(result["status"], "readonly-violated", result)
        self.assertIn(self.rel, result["readonly_violations"])
        self.assertEqual(os.readlink(self.site / "src" / "link.txt"), str(self.copy), "the link is neither resolved nor repaired")

    def test_a_link_to_a_folder_and_other_file_types_are_handled_without_following(self):
        os.symlink(self.outside, self.site / "src" / "folder-link")
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "folder link")
        self.lock(self.outside)
        with access_spy(self.outside) as touched:
            state = self.state()
        self.assertEqual(touched, [])
        self.assertEqual(state["hashes"]["sites/fx.test/src/folder-link"], "LINK:" + str(self.outside))

    def test_apply_still_refuses_a_link_as_target(self):
        proposal = {"summary": "edit", "kind": "draft", "proposed": "x", "edit": {"file": self.rel, "find": "external", "replace": "changed"}}
        self.audit(proposals={"seo.description-too-short|/a.html|": proposal})
        self.decide(["SEO-001"], "approved")
        with self.assertRaises(Stop) as ctx:
            self.apply(["SEO-001"], minutes=1)
        self.assertIn("symlink", str(ctx.exception))
        self.assertIn("never be read", self.secret.read_text())


class LinkedParents(LinkCase):
    def swap_parent(self):
        os.rename(self.site / "src" / "dirx", self.tmp / "dirx.moved")
        ext = self.tmp / "ext-dir"
        ext.mkdir()
        (ext / "file.txt").write_text("external folder content\n")
        os.symlink(ext, self.site / "src" / "dirx")
        return ext

    def test_a_tracked_path_below_a_swapped_parent_link_stops_with_a_diagnosis_and_nothing_is_opened(self):
        ext = self.swap_parent()
        self.lock(ext / "file.txt", ext)
        with access_spy(ext) as touched:
            with self.assertRaises(Stop) as ctx:
                self.state()
        self.assertEqual(touched, [])
        message = str(ctx.exception)
        self.assertIn("sites/fx.test/src/dirx/file.txt", message)
        self.assertIn("symbolic link", message)
        self.assertIn("nothing behind the link was read", message)

    def test_the_audit_stops_before_building_and_writes_no_report(self):
        ext = self.swap_parent()
        self.lock(ext / "file.txt", ext)
        calls = len(self.npm_calls())
        with access_spy(ext) as touched:
            with self.assertRaises(Stop):
                self.audit()
        self.assertEqual(touched, [])
        self.assertEqual(len(self.npm_calls()), calls, "no build in an unsafe state")
        self.assertEqual(self.reports(), [])
        self.assertFalse((self.root / ".project" / "reports" / "fx.test" / "optimize.md").exists())
        self.assertTrue(os.path.islink(self.site / "src" / "dirx"), "the link is not resolved, removed or repaired")

    def test_a_parent_swapped_during_the_run_stops_after_the_build_with_nothing_reported(self):
        ext = self.tmp / "ext-dir"
        ext.mkdir()
        (ext / "file.txt").write_text("external folder content\n")
        (self.site / "src" / "SWAP").write_text("")
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "swap marker")
        self.lock(ext / "file.txt", ext)
        with mock.patch.dict(os.environ, {"SWAP_TARGET": str(ext)}):
            with access_spy(ext) as touched:
                with self.assertRaises(Stop) as ctx:
                    self.audit()
        self.assertEqual(touched, [])
        self.assertIn("symbolic link", str(ctx.exception))
        self.assertEqual(self.reports(), [], "an unsafe run reports nothing as clean or done")

    def test_the_cli_reports_the_unsafe_state_as_a_stop_message(self):
        ext = self.swap_parent()
        code, out = self.cli("audit", "--npm", str(self.npm))
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP:"), out)
        self.assertIn("symbolic link", out)
        self.assertNotIn("Traceback", out)

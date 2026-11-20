"""`.claude/launch.json` is never read, written or removed through a symbolic link (also a broken one) or when it is of an unsupported
file type; the generator refuses with a concrete diagnosis instead of a traceback. Fictional data only. A controlled access spy shows
that the content behind the link is never touched (an unchanged hash alone would not show that nothing was read)."""
import io
import json
import os
import signal
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tests.support import preview_helpers as helpers
from tests.support.preview_process import AccessSpy
import preview


def call(root, *argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = preview.main(["--root", str(root), *argv])
    return code, out.getvalue()


def tree(root):
    import hashlib
    result = {}
    for current, dirs, files in os.walk(root):
        for name in dirs + files:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                result[rel] = "link->" + os.readlink(path)
            elif path.is_dir():
                result[rel] = "dir"
            elif path.is_file():
                result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                result[rel] = "special"        # e.g. a FIFO: never opened by the test helper
    return result


EXTERNAL_LAUNCH = {"version": "0.0.1", "configurations": [{"name": "external-entry", "port": 1}]}


class LaunchLinkCases:
    """Builds the project and the external area for one case; subclasses of the tests use these names."""

    @staticmethod
    def project_and_external():
        root = helpers.make_repo(helpers.ONE_SITE, ("alpha.example",))
        external = Path(tempfile.mkdtemp()).resolve() / "outside"
        external.mkdir()
        return root, external

    @classmethod
    def claude_dir_symlink(cls):
        root, external = cls.project_and_external()
        (external / "launch.json").write_text(json.dumps(EXTERNAL_LAUNCH))
        (root / ".claude").symlink_to(external, target_is_directory=True)
        return root, external

    @classmethod
    def launch_file_symlink(cls):
        root, external = cls.project_and_external()
        target = external / "elsewhere.json"
        target.write_text(json.dumps(EXTERNAL_LAUNCH))
        (root / ".claude").mkdir()
        (root / ".claude" / "launch.json").symlink_to(target)
        return root, external

    @classmethod
    def launch_file_broken_symlink(cls):
        root, external = cls.project_and_external()
        (root / ".claude").mkdir()
        (root / ".claude" / "launch.json").symlink_to(external / "does-not-exist.json")
        return root, external

    @classmethod
    def claude_dir_broken_symlink(cls):
        root, external = cls.project_and_external()
        (root / ".claude").symlink_to(external / "missing-dir", target_is_directory=True)
        return root, external

    @classmethod
    def launch_file_is_directory(cls):
        root, external = cls.project_and_external()
        (root / ".claude" / "launch.json").mkdir(parents=True)
        return root, external

    @classmethod
    def launch_file_is_fifo(cls):
        root, external = cls.project_and_external()
        (root / ".claude").mkdir()
        os.mkfifo(root / ".claude" / "launch.json")
        return root, external


CASES = ("claude_dir_symlink", "launch_file_symlink", "launch_file_broken_symlink", "claude_dir_broken_symlink",
         "launch_file_is_directory", "launch_file_is_fifo")


class LaunchLinkProtectionTests(unittest.TestCase):
    def setUp(self):
        signal.alarm(30)                      # a regression that opens the FIFO would block; fail instead of hanging
        self.addCleanup(signal.alarm, 0)

    def test_the_generator_refuses_every_unsafe_launch_location_without_reading_or_writing_behind_it(self):
        for name in CASES:
            with self.subTest(case=name):
                root, external = getattr(LaunchLinkCases, name)()
                before_project, before_external = tree(root), tree(external)
                with AccessSpy(external) as spy:
                    code, out = call(root, "alpha.example")
                self.assertEqual(code, 1, out)
                self.assertTrue(out.startswith("STOP:"), out)
                self.assertNotIn("Traceback", out)
                self.assertTrue("symbolic link" in out or "is not a" in out, out)
                self.assertEqual(spy.hits, [], "content behind the link was accessed")
                self.assertEqual(tree(external), before_external)          # external files unchanged, nothing created (also not for a broken link)
                self.assertEqual(tree(root), before_project)

    def test_write_launch_itself_raises_a_controlled_stop(self):
        from site_common.errors import Stop
        for name in CASES:
            with self.subTest(case=name):
                root, external = getattr(LaunchLinkCases, name)()
                with AccessSpy(external) as spy, self.assertRaises(Stop):
                    preview.write_launch(root, helpers.ONE_SITE["components"][0])
                self.assertEqual(spy.hits, [])

    def test_a_link_to_a_file_inside_the_project_is_refused_too(self):
        root, external = LaunchLinkCases.project_and_external()
        (root / ".claude").mkdir()
        (root / "real.json").write_text(json.dumps(EXTERNAL_LAUNCH))
        (root / ".claude" / "launch.json").symlink_to(root / "real.json")
        before = tree(root)
        code, out = call(root, "alpha.example")
        self.assertEqual((code, out.startswith("STOP:")), (1, True), out)
        self.assertEqual(tree(root), before)

    def test_a_normal_launch_file_keeps_independent_entries_and_replaces_only_the_own_one(self):
        root, external = LaunchLinkCases.project_and_external()
        launch = root / ".claude" / "launch.json"
        launch.parent.mkdir()
        other = {"name": "other", "port": 1}
        launch.write_text(json.dumps({"version": "0.0.1", "configurations": [other, {"name": "website-manager-alpha.example", "port": 9}]}))
        with AccessSpy(external) as spy:
            self.assertEqual(call(root, "alpha.example")[0], 0)
        self.assertEqual(spy.hits, [])
        names = [c["name"] for c in json.loads(launch.read_text())["configurations"]]
        self.assertEqual(names, ["other", "website-manager-alpha.example"])
        self.assertEqual(json.loads(launch.read_text())["configurations"][1]["port"], 4321)

    def test_an_identical_own_entry_is_not_written_again(self):
        root, external = LaunchLinkCases.project_and_external()
        self.assertEqual(call(root, "alpha.example")[0], 0)
        launch = root / ".claude" / "launch.json"
        launch.write_text(launch.read_text().replace('"version": "0.0.1"', '"version":    "0.0.1"'))
        before = (launch.read_bytes(), os.lstat(launch).st_mtime_ns, os.lstat(launch).st_ino)
        writes = []
        real_open = os.open

        def watch(path, flags, *a, **k):
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC) and os.fspath(path) == str(launch):
                writes.append(path)
            return real_open(path, flags, *a, **k)
        os.open = watch
        try:
            self.assertEqual(call(root, "alpha.example")[0], 0)
        finally:
            os.open = real_open
        self.assertEqual(writes, [])
        self.assertEqual((launch.read_bytes(), os.lstat(launch).st_mtime_ns, os.lstat(launch).st_ino), before)

    def test_a_missing_claude_folder_is_a_normal_case_and_gets_created(self):
        root, external = LaunchLinkCases.project_and_external()
        self.assertEqual(call(root, "alpha.example")[0], 0)
        self.assertTrue((root / ".claude" / "launch.json").is_file())
        self.assertFalse((root / ".claude").is_symlink())

    def test_invalid_launch_json_still_stops_untouched(self):
        root, external = LaunchLinkCases.project_and_external()
        launch = root / ".claude" / "launch.json"
        launch.parent.mkdir()
        launch.write_text("{ not json")
        code, out = call(root, "alpha.example")
        self.assertEqual((code, launch.read_text()), (1, "{ not json"))
        self.assertIn("not valid launch JSON", out)


if __name__ == "__main__":
    unittest.main()

"""Review findings 1-3: exclusive staging files, adopt repetition re-checks, ownership record validation."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from tests.support import setup_paths as helpers  # noqa: F401  (sets up sys.path first)
from tests.support import setup_helpers as h
import static_setup

SCRIPT = helpers.SITE_SCRIPT
MANAGED = ".project/specs/website.managed.json"


def create(root, domain="b.example", **kw):
    return static_setup.execute(h.opts("create", domain, root, **kw), h.FakeRunner())


def adopt(root, domain="adopted.example", **kw):
    return static_setup.execute(h.opts("adopt", domain, root, **kw), h.FakeRunner())


def file_writes(root, domain="b.example"):
    return len([w for w in static_setup.make_plan(h.opts("create", domain, root)).writes if w.kind == "file"])


def tmp_leftovers(root):
    return [k for k in h.snapshot(root) if k.endswith(".zw-tmp") and "foreign" not in k]


class StagingFileTests(unittest.TestCase):
    def setUp(self):
        self.root = h.repo()
        self.outside = Path(self.root.parent) / f"outside-{self.root.name}.txt"
        self.outside.write_text("outside\n")
        self.addCleanup(lambda: self.outside.unlink(missing_ok=True))

    def fail_nth_replace(self, n):
        real, calls = os.replace, []

        def failing(src, dst):
            calls.append(dst)
            if len(calls) == n:
                raise OSError("injected rename failure")
            return real(src, dst)
        return mock.patch.object(static_setup, "_replace", failing)

    def test_foreign_predictable_tmp_file_is_kept_byte_identical(self):
        (self.root / ".gitignore").write_text("keep\n")
        foreign = self.root / "..gitignore.zw-tmp"
        old_names = [self.root / ".gitignore.zw-tmp", foreign, self.root / ".project" / "specs" / ".website.json.zw-tmp"]
        (self.root / ".project" / "specs").mkdir(parents=True)
        for f in old_names:
            f.write_bytes(b"foreign\x00bytes\n")
        before = {f: f.read_bytes() for f in old_names}
        result = create(self.root)
        self.assertEqual(result["state"], "created", result)
        for f, data in before.items():
            self.assertEqual(f.read_bytes(), data, f)
        with self.fail_nth_replace(3):
            self.assertEqual(create(self.root, "c.example")["state"], "failed-rolled-back")
        for f, data in before.items():
            self.assertEqual(f.read_bytes(), data, f)

    def test_symlink_at_the_old_predictable_name_is_neither_followed_nor_removed(self):
        for name in ("..gitignore.zw-tmp", ".gitignore.zw-tmp"):
            (self.root / name).symlink_to(self.outside)
        result = create(self.root)
        self.assertEqual(result["state"], "created", result)
        self.assertEqual(self.outside.read_text(), "outside\n")
        for name in ("..gitignore.zw-tmp", ".gitignore.zw-tmp"):
            self.assertTrue((self.root / name).is_symlink())
            self.assertEqual(os.readlink(self.root / name), str(self.outside))
        with self.fail_nth_replace(2):
            create(self.root, "c.example")
        self.assertEqual(self.outside.read_text(), "outside\n")
        self.assertTrue((self.root / "..gitignore.zw-tmp").is_symlink())

    def test_symlink_in_the_site_folder_target_is_not_written_through(self):
        # the staging file of a rollback restore must not follow a link either
        (self.root / ".gitignore").write_text("keep\n")
        (self.root / ".gitignore.zw-tmp").symlink_to(self.outside)
        with self.fail_nth_replace(file_writes(self.root) - 1):
            result = create(self.root)
        self.assertEqual(result["state"], "failed-rolled-back", result)
        self.assertEqual((self.root / ".gitignore").read_text(), "keep\n")
        self.assertEqual(self.outside.read_text(), "outside\n")
        self.assertEqual(tmp_leftovers(self.root), [".gitignore.zw-tmp"])

    def test_staging_files_are_created_exclusively_with_unpredictable_names(self):
        seen = []
        real = static_setup.tempfile.mkstemp

        def spy(*a, **kw):
            fd, name = real(*a, **kw)
            seen.append((name, os.fstat(fd).st_mode & 0o777))
            return fd, name
        with mock.patch.object(static_setup.tempfile, "mkstemp", spy):
            create(self.root)
        self.assertGreater(len(seen), 40)
        self.assertEqual(len({n for n, _ in seen}), len(seen))
        self.assertTrue(all(n.endswith(".zw-tmp") for n, _ in seen))
        self.assertFalse(tmp_leftovers(self.root))
        mode = (self.root / ".project" / "specs" / "website.json").stat().st_mode & 0o777
        mask = os.umask(0)
        os.umask(mask)
        self.assertEqual(mode, 0o666 & ~mask)

    def test_existing_file_keeps_its_mode(self):
        (self.root / ".gitignore").write_text("keep\n")
        os.chmod(self.root / ".gitignore", 0o640)
        create(self.root)
        self.assertEqual((self.root / ".gitignore").stat().st_mode & 0o777, 0o640)

    def test_write_and_rename_failures_leave_no_own_tmp_file_and_restore_state(self):
        (self.root / ".gitignore").write_text("keep\n")
        foreign = self.root / ".gitignore.zw-tmp"
        foreign.write_bytes(b"foreign\n")
        before = h.snapshot(self.root)
        total = file_writes(self.root)
        for n in (1, 5, 30, total - 1, total):
            with self.fail_nth_replace(n):
                result = create(self.root)
            self.assertEqual(result["state"], "failed-rolled-back", (n, result))
            self.assertEqual(h.snapshot(self.root), before, n)
        real, count = static_setup._write_all, []

        def failing_write(fd, data):
            count.append(1)
            if len(count) == 10:
                raise OSError("injected write failure")
            return real(fd, data)
        with mock.patch.object(static_setup, "_write", failing_write):
            result = create(self.root)
        self.assertEqual(result["state"], "failed-rolled-back", result)
        self.assertEqual(h.snapshot(self.root), before)

    def test_failing_restore_cleans_its_own_tmp_file_and_reports_partial(self):
        (self.root / ".gitignore").write_text("keep\n")
        with self.fail_nth_replace(file_writes(self.root) - 1), mock.patch.object(static_setup, "_restore", side_effect=OSError("injected: restore")):
            result = create(self.root)
        self.assertEqual(result["state"], "failed-partial", result)
        self.assertFalse(tmp_leftovers(self.root))
        self.assertTrue(any(".gitignore" in r for r in result["remaining"]), result["remaining"])


class AdoptRepetitionTests(unittest.TestCase):
    def setUp(self):
        self.root = h.repo()
        self.site = h.make_static_site(self.root)
        self.assertEqual(adopt(self.root)["state"], "adopted")

    def refused(self, *needles, via_plan=False):
        before = h.snapshot(self.root)
        results = [static_setup.plan_only(h.opts("adopt", "adopted.example", self.root)), adopt(self.root)]
        for result in results:
            self.assertEqual((result["state"], result["exit"]), ("invalid", 1), result)
            text = "\n".join(result["problems"])
            for needle in needles:
                self.assertIn(needle, text)
        self.assertEqual(h.snapshot(self.root), before)
        return results

    def test_valid_identical_repetition_stays_unchanged(self):
        before = h.snapshot(self.root)
        for result in (adopt(self.root), static_setup.plan_only(h.opts("adopt", "adopted.example", self.root))):
            self.assertEqual((result["state"], result["exit"]), ("unchanged", 0), result)
        self.assertEqual(h.snapshot(self.root), before)

    def test_deleted_site_folder(self):
        import shutil
        shutil.rmtree(self.site)
        self.refused("sites/adopted.example", "folder is missing")

    def test_site_path_replaced_by_a_file(self):
        import shutil
        shutil.rmtree(self.site)
        self.site.write_text("not a folder\n")
        self.refused("folder is missing")

    def test_package_json_removed(self):
        (self.site / "package.json").unlink()
        self.refused("package.json is missing")

    def test_build_script_removed(self):
        (self.site / "package.json").write_text(json.dumps({"name": "x", "scripts": {"check": "echo"}}))
        self.refused("no 'build' script")

    def test_package_json_corrupted(self):
        (self.site / "package.json").write_text("{nope")
        self.refused("not valid JSON")

    def test_gitignore_of_build_output_removed(self):
        (self.site / ".gitignore").write_text("# nothing\n")
        self.refused("not git-ignored")

    def test_build_flag_never_runs_after_a_refused_repetition(self):
        (self.site / "package.json").unlink()
        runner = h.NoRun()
        result = static_setup.execute(h.opts("adopt", "adopted.example", self.root, build=True), runner)
        self.assertEqual(result["state"], "invalid", result)

    def test_created_site_with_deleted_folder_is_refused_too(self):
        import shutil
        create(self.root, "c.example")
        shutil.rmtree(self.root / "sites" / "c.example")
        before = h.snapshot(self.root)
        for result in (static_setup.plan_only(h.opts("create", "c.example", self.root, site_type="astro-static")), create(self.root, "c.example")):
            self.assertEqual((result["state"], result["exit"]), ("invalid", 1), result)
        self.assertEqual(h.snapshot(self.root), before)


def cli(root, *argv):
    result = subprocess.run([sys.executable, str(SCRIPT), *argv, "--root", str(root)], capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


GOOD_HASH = "a" * 64


class OwnershipRecordTests(unittest.TestCase):
    def setUp(self):
        self.root = h.repo()
        h.make_static_site(self.root)
        self.assertEqual(adopt(self.root)["state"], "adopted")
        create(self.root, "c.example")
        self.record = h.record_of(self.root)
        self.file = self.root / MANAGED

    def corrupt(self, mutate):
        data = json.loads(json.dumps(self.record))
        mutate(data)
        self.file.write_text(json.dumps(data))
        return self.file.read_bytes()

    def assert_refused(self, raw, label, *needles):
        before = h.snapshot(self.root)
        commands = [("create", "c.example", "--type", "astro-static"), ("adopt", "adopted.example"),
                    ("plan", "create", "d.example", "--type", "astro-static"), ("plan", "adopt", "adopted.example"),
                    ("verify", "c.example")]
        for command in commands:
            for as_json in (False, True):
                argv = list(command) + (["--json"] if as_json else [])
                code, out, err = cli(self.root, *argv)
                where = f"{label}: {' '.join(argv)}"
                self.assertEqual(code, 1, (where, out, err))
                self.assertNotIn("Traceback", out + err, where)
                self.assertEqual(err, "", where)
                if as_json:
                    data = json.loads(out)
                    self.assertEqual((data["state"], data["exit"]), ("invalid", 1), where)
                    text = "\n".join(data["problems"])
                else:
                    text = out
                self.assertIn("ownership record", text, where)
                for needle in needles:
                    self.assertIn(needle, text, where)
        self.assertEqual(h.snapshot(self.root), before, label)
        self.assertEqual(self.file.read_bytes(), raw, label)

    def test_missing_type(self):
        self.assert_refused(self.corrupt(lambda d: d["sites"]["c.example"].pop("type")), "type", "sites['c.example'].type")

    def test_missing_mode_and_template_version(self):
        self.assert_refused(self.corrupt(lambda d: d["sites"]["c.example"].pop("mode")), "mode", ".mode")
        self.record = h.record_of(self.root)
        self.assert_refused(self.corrupt(lambda d: d["sites"]["c.example"].pop("template_version")), "tv", "template_version")

    def test_wrong_field_types(self):
        for label, mutate, needle in [
            ("type int", lambda d: d["sites"]["c.example"].update(type=5), ".type"),
            ("files list", lambda d: d["sites"]["c.example"].update(files=[]), ".files must be an object"),
            ("sites list", lambda d: d.update(sites=[]), "sites must be an object"),
            ("project_files str", lambda d: d.update(project_files="x"), "project_files must be an object"),
            ("version str", lambda d: d.update(version="1"), "version must be 1"),
            ("version bool", lambda d: d.update(version=True), "version must be 1"),
            ("entry null", lambda d: d["sites"].update({"c.example": None}), "must be an object"),
            ("sha int", lambda d: d["project_files"][".project/specs/website.schema.json"].update(sha256=1), "sha256"),
        ]:
            self.record = h.record_of(self.root)
            self.assert_refused(self.corrupt(mutate), label, needle)
            self.file.write_text(json.dumps(self.record))

    def test_root_not_an_object(self):
        self.file.write_text("[]")
        self.assert_refused(b"[]", "array", "must be a JSON object")

    def test_invalid_hashes(self):
        for label, bad in [("short", "abc"), ("upper", "A" * 64), ("non-hex", "z" * 64), ("long", "a" * 65), ("empty", "")]:
            self.record = h.record_of(self.root)
            raw = self.corrupt(lambda d, b=bad: d["sites"]["c.example"]["files"].update({"package.json": b}))
            self.assert_refused(raw, label, "sha256")

    def test_absolute_and_parent_paths(self):
        for label, rel, needle in [("absolute", "/etc/passwd", "relative"), ("dotdot", "../../x", "'..'"),
                                   ("inner dotdot", "src/../../x", "'..'"), ("backslash", "src\\x", "relative"),
                                   ("empty segment", "src//x", "empty segment"), ("empty", "", "non-empty"),
                                   ("drive", "C:/x", "relative")]:
            self.record = h.record_of(self.root)
            raw = self.corrupt(lambda d, r=rel: d["sites"]["c.example"]["files"].update({r: GOOD_HASH}))
            self.assert_refused(raw, label, needle)

    def test_bad_project_file_path_and_site_key(self):
        raw = self.corrupt(lambda d: d["project_files"].update({"../escape": {"sha256": GOOD_HASH, "template_version": "static-1"}}))
        self.assert_refused(raw, "project path", "'..'")
        self.record = h.record_of(self.root)
        raw = self.corrupt(lambda d: d["sites"].update({"../x": d["sites"]["c.example"]}))
        self.assert_refused(raw, "site key", "not a site ID")

    def test_adopted_site_must_not_own_files(self):
        raw = self.corrupt(lambda d: d["sites"]["adopted.example"]["files"].update({"package.json": GOOD_HASH}))
        self.assert_refused(raw, "adopted", "owns no files")

    def test_unusable_json_and_non_utf8(self):
        self.file.write_text("{broken")
        self.assert_refused(b"{broken", "json", "not valid JSON")
        self.file.write_bytes(b"\xff\xfe\x00")
        self.assert_refused(b"\xff\xfe\x00", "utf8", "not valid JSON")

    def test_the_valid_record_is_accepted_and_paths_never_leave_the_site(self):
        code, out, err = cli(self.root, "plan", "create", "c.example", "--type", "astro-static")   # no npm involved
        self.assertEqual((code, "ownership record" in out), (0, False), out)
        # a hostile path is refused before it is joined to the site folder
        outside = self.root.parent / f"victim-{self.root.name}"
        outside.write_text("untouched\n")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        raw = self.corrupt(lambda d: d["sites"]["c.example"]["files"].update({f"../../{outside.name}": GOOD_HASH}))
        self.assert_refused(raw, "escape", "'..'")
        self.assertEqual(outside.read_text(), "untouched\n")


if __name__ == "__main__":
    unittest.main()

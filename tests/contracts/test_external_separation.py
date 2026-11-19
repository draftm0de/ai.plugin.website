"""Real-npm tests must never run in a default run, even with an inherited ZW_REAL_NPM=1 (or similar) in the environment."""
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run_tests.py"
POISONED = {**os.environ, "ZW_REAL_NPM": "1", "ZW_EXTERNAL": "1", "AI_PLUGIN_TEST_EXTERNAL": "1"}


class DefaultRunExcludesRealNpm(unittest.TestCase):
    def collected(self, kind):
        proc = subprocess.run([sys.executable, "-B", str(RUNNER), "--kind", kind, "--list"], cwd=ROOT, env=POISONED,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        return proc.stdout.splitlines()

    def test_no_default_layer_collects_the_external_tests_even_with_inherited_variables(self):
        for kind in ("deterministic", "integration", "unit", "contracts"):
            ids = self.collected(kind)
            self.assertGreater(len(ids), 1, kind)
            self.assertFalse([i for i in ids if "tests.external" in i or "real_npm" in i.lower()], kind)

    def test_external_tests_are_skipped_without_starting_anything_even_with_inherited_variables(self):
        import tests.external as external
        self.assertFalse(external.ENABLED)
        started = []
        marker = lambda *a, **k: started.append(a) or (_ for _ in ()).throw(AssertionError("real process started"))   # noqa: E731
        with mock.patch.dict(os.environ, {"ZW_REAL_NPM": "1"}), mock.patch("subprocess.run", marker), \
                mock.patch("subprocess.Popen", marker):
            suite = unittest.TestLoader().discover(str(ROOT / "tests" / "external"), pattern="test_*.py", top_level_dir=str(ROOT))
            result = unittest.TestResult()
            suite.run(result)
        self.assertEqual(started, [])
        self.assertGreaterEqual(len(result.skipped), 3)
        self.assertEqual((result.errors, result.failures, result.testsRun - len(result.skipped)), ([], [], 0))

    def test_explicit_runner_refuses_without_approval_and_starts_nothing(self):
        proc = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "run_external_tests.py")], env=POISONED,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("NOT RUN", proc.stdout)


if __name__ == "__main__":
    unittest.main()

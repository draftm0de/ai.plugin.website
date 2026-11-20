"""REAL npm tests (network, downloads, starts the real tool). NOT part of any default layer; NOT RUN in development stages.

Run only through `python3 -B scripts/run_external_tests.py --approved` after a separate release. Enablement is a module flag set by
that runner (`tests.external.ENABLED`), never an environment variable. Skipped tests are never counted as passed.
S1 and S16 with the real template, real `npm install`, real build and `npm run check`; plus real npm exit codes on a
dependency-free package. Everything happens in temporary repositories.
"""
import unittest

import tests.external as external

from tests.support import setup_helpers as h
import static_setup



@unittest.skipUnless(external.ENABLED, "external real-npm tests: only via scripts/run_external_tests.py --approved")
class RealNpmTests(unittest.TestCase):
    def steps(self, result):
        return {n: (s["ran"], s["exit"]) for n, s in result["verification"].items()}

    def test_s1_new_site_installs_builds_and_passes_check(self):
        root = h.repo()
        result = static_setup.execute(h.opts("create", "real.example", root, build=True))
        self.assertEqual((result["state"], result["exit"]), ("created", 0), result)
        self.assertEqual(self.steps(result), {"install": (True, 0), "build": (True, 0), "check": (True, 0)})
        site = root / "sites" / "real.example"
        self.assertTrue((site / "dist" / "index.html").is_file())
        self.assertTrue((site / "package-lock.json").is_file())
        self.assertEqual(result["lockfile"], "created")
        for legacy in ("Dockerfile", ".dockerignore", "docker-compose.yml", "Caddyfile", "site.caddy"):
            self.assertFalse((site / legacy).exists())
        again = static_setup.execute(h.opts("create", "real.example", root, build=True))
        self.assertEqual((again["state"], self.steps(again)), ("unchanged", {"install": (True, 0), "build": (True, 0), "check": (True, 0)}))

    def test_s16_broken_generated_file_then_repair_then_verify(self):
        root = h.repo()
        real_runner = static_setup.default_runner
        page = root / "sites" / "real.example" / "src" / "pages" / "index.astro"

        def breaking(argv, cwd):
            if argv[-1] == "build":                       # the person's mistake lands before the build runs
                page.write_text("---\nthrow new Error('broken page');\n---\n<h1>x</h1>\n")
            return real_runner(argv, cwd)
        failed = static_setup.execute(h.opts("create", "real.example", root, build=True), breaking)
        self.assertEqual((failed["state"], failed["exit"]), ("failed-build", 1), failed)
        steps = self.steps(failed)
        self.assertEqual((steps["install"], steps["check"]), ((True, 0), (False, None)))
        self.assertTrue(steps["build"][0] and steps["build"][1] not in (0, None))
        self.assertIn("real.example", [c["name"] for c in h.manifest_of(root)["components"]])
        page.write_text("---\nimport BaseLayout from '../layouts/BaseLayout.astro';\n---\n"
                        "<BaseLayout title=\"Repaired page by a person\" description=\"A repaired page with a description long enough for the audit.\">"
                        "<h1>Repaired</h1></BaseLayout>\n")
        repaired = page.read_bytes()
        record = (root / ".project/specs/website.manage.json").read_bytes()
        result = static_setup.verify(h.opts("verify", "real.example", root))
        self.assertEqual((result["state"], result["exit"]), ("verified", 0), result)
        self.assertEqual(self.steps(result), {"install": (True, 0), "build": (True, 0), "check": (True, 0)})
        self.assertEqual(page.read_bytes(), repaired)
        self.assertEqual((root / ".project/specs/website.manage.json").read_bytes(), record)
        conflict = static_setup.execute(h.opts("create", "real.example", root))
        self.assertEqual(conflict["state"], "conflict")
        self.assertIn("setup verify", " ".join(conflict["problems"]))


@unittest.skipUnless(external.ENABLED, "external real-npm tests: only via scripts/run_external_tests.py --approved")
class RealNpmProcessTests(unittest.TestCase):
    """Moved from the adopt tests: real npm on a package without dependencies. Not part of the default run."""

    def setUp(self):
        self.root = h.repo()

    def test_real_npm_exit_codes_without_network(self):
        """Real npm on a package without dependencies (works offline): exit codes come from real processes."""
        h.make_static_site(self.root, scripts={"build": "node -e \"require('fs').mkdirSync('dist',{recursive:true})\"",
                                               "check": "node -e \"process.exit(4)\""})
        result = static_setup.execute(h.opts("adopt", "adopted.example", self.root, build=True))
        self.assertEqual(result["state"], "failed-check", result)
        self.assertEqual({n: (s["ran"], s["exit"]) for n, s in result["verification"].items()},
                         {"install": (True, 0), "build": (True, 0), "check": (True, 4)})
        self.assertEqual(result["lockfile"], "created")
        failing = h.repo()
        h.make_static_site(failing, scripts={"build": "node -e \"process.exit(3)\""})
        result = static_setup.execute(h.opts("adopt", "adopted.example", failing, build=True))
        self.assertEqual({n: (s["ran"], s["exit"]) for n, s in result["verification"].items()},
                         {"install": (True, 0), "build": (True, 3), "check": (False, None)})
        self.assertEqual(result["state"], "failed-build")


if __name__ == "__main__":
    unittest.main()

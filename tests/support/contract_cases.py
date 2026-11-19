"""Test-case mixin shared by the three suites: every consumer must refuse the same inputs, before any follow-up step."""
import json

from tests.support import manifest_contract as mc

NEEDLE = {                     # a word the message must contain so the cause is traceable
    "old manifest + old project schema": "type",
    "old manifest + current schema": "type",
    "type astro + loosened schema": "type",
    "type hugo + loosened schema": "type",
    "removed field serve + loosened schema": "serve",
    "removed field dockerfile + loosened schema": "dockerfile",
    "removed field registry + loosened schema": "registry",
    "removed field retention + loosened schema": "retention",
}
BROKEN_SCHEMAS = (("project schema missing", None), ("project schema not JSON", "{not json"), ("project schema not an object", "[]\n"))


class ContractMixin:
    FORBIDDEN = ()             # paths that must not exist after a refusal (follow-up artefacts of the consumer)
    START = "STOP"             # how a refusal message of this consumer begins

    def setUp(self):
        self.sb = mc.Sandbox()

    def assert_refused(self, root, before, code, out, needle, label):
        self.assertEqual(code, 1, (label, out))
        self.assertTrue(out.lstrip().startswith(self.START), (label, out))
        self.assertNotIn("Traceback", out, label)
        self.assertIn(needle, out, (label, out))
        self.assertEqual(mc.snapshot(root), before, f"{label}: files changed")           # manifest, schema, site: byte for byte
        self.assertEqual(self.sb.npm_calls(), [], f"{label}: npm was called")                # no install, build or check
        self.assertEqual(self.sb.state_files(), [], f"{label}: a process record was written")
        for rel in self.FORBIDDEN:
            self.assertFalse((root / rel).exists(), f"{label}: {rel} exists")

    def refusal_matrix(self, entries):
        """entries: [(script, argv-builder(root))]; every entry must refuse every case."""
        for label, manifest, schema_text in mc.refusal_cases():
            root = mc.make_project(manifest, schema_text)
            before = mc.snapshot(root)
            for script, build in entries:
                code, out = self.sb.run(script, *build(root))
                self.assert_refused(root, before, code, out, NEEDLE[label], f"{script} / {label}")

    def broken_schema_matrix(self, entries, needle="website.schema.json"):
        for label, schema_text in BROKEN_SCHEMAS:
            root = mc.make_project(mc.good_manifest(), schema_text)
            before = mc.snapshot(root)
            for script, build in entries:
                code, out = self.sb.run(script, *build(root))
                self.assert_refused(root, before, code, out, needle, f"{script} / {label}")

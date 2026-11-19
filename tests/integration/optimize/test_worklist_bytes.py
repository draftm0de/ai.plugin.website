"""BD-17: the work list is read and written byte-exactly (UTF-8, no newline translation). Carriage returns inside a proposal's
search/replacement text are part of the rendered, checksummed text; reading must give back exactly what was rendered.
Real hand edits, damaged checksums and non-UTF-8 files still stop without touching the file. Fictional fixtures, fake npm."""
import json
import os
import unittest

from tests.support import optimize_helpers as h
from site_common.errors import Stop
import store
import worklist as wl

ORIGINAL = b"one\r\ntwo\r\nthree\r\nkeep\r\n"


class Base(h.AuditCase):
    def setUp(self):
        super().setUp()
        (self.site / "src" / "crlf.txt").write_bytes(ORIGINAL)
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "crlf file")
        self.path = self.root / ".project" / "reports" / "fx.test" / "optimize.md"
        self.proposal = {"summary": "multi-line", "kind": "draft", "current": "one\r\ntwo", "proposed": "uno\r\ndos",
                         "edit": {"file": "sites/fx.test/src/crlf.txt", "find": "one\r\ntwo", "replace": "uno\r\ndos"}}

    def audit_with_proposal(self, minutes=0):
        return self.audit(minutes=minutes, proposals={"seo.description-too-short|/a.html|": self.proposal})


class CrlfProposal(Base):

    def test_full_cycle_with_a_crlf_search_and_replacement_text(self):
        self.audit_with_proposal()
        raw = self.path.read_bytes()
        self.assertIn(b"\r", raw, "the rendered work list carries the carriage returns")
        self.assertEqual(self.state()["findings"][0]["proposal"]["edits"][0]["find"], "one\r\ntwo")
        code, out = self.cli("show")                                   # re-read through the real entry point
        self.assertEqual(code, 0, out)
        code, out = self.cli("decide", "SEO-001", "--status", "approved")
        self.assertEqual(code, 0, out)
        before = self.tracked_hashes()
        self.apply(["SEO-001"], minutes=1)
        self.assertEqual((self.site / "src" / "crlf.txt").read_bytes(), b"uno\r\ndos\r\nthree\r\nkeep\r\n")     # exactly the released bytes
        changed = {k for k, v in self.tracked_hashes().items() if v != before[k]}
        self.assertEqual(changed, {"sites/fx.test/src/crlf.txt"})
        self.assertIsNotNone(self.finding("SEO-001")["applied"])
        again = self.audit(minutes=2)                                  # a later audit still reads the list
        self.assertEqual(again["readonly_violations"], [])
        self.assertEqual(self.cli("show")[0], 0)

    def test_repeated_reading_is_stable_and_the_stored_bytes_are_the_rendered_text(self):
        self.audit_with_proposal()
        raw = self.path.read_bytes()
        for _ in range(3):
            text, sha = store.read_worklist(self.root, "fx.test")
            self.assertEqual(text.encode("utf-8"), raw)
            self.assertEqual(wl.render(wl.parse(text, "fx.test")).encode("utf-8"), raw)
        self.assertEqual(self.path.read_bytes(), raw, "reading never rewrites")

    def test_a_list_rendered_by_the_former_code_is_read_unchanged(self):
        """The renderer is unchanged, so bytes it produced earlier (text-mode write on POSIX: identical bytes) must parse as they are."""
        self.audit_with_proposal()
        state = self.state()
        legacy = wl.render(state).encode("utf-8")
        self.assertIn(b"\r", legacy)
        self.path.write_bytes(legacy)
        text, _ = store.read_worklist(self.root, "fx.test")
        self.assertEqual(wl.parse(text, "fx.test")["findings"][0]["id"], "SEO-001")
        self.assertEqual(self.path.read_bytes(), legacy)

    def test_a_plain_lf_work_list_still_works(self):
        self.audit()
        self.assertNotIn(b"\r", self.path.read_bytes())
        self.decide(["SEO-001"], "approved")
        self.assertEqual(self.finding("SEO-001")["status"], "approved")

    def test_write_is_byte_exact(self):
        text = "line one\r\nline two\rthree\n"
        tmp = store._private_tmp(self.tmp, ".t-", text)
        self.assertEqual(tmp.read_bytes(), text.encode("utf-8"))


class StillStopsOnRealDamage(Base):
    def setUp(self):
        super().setUp()
        self.audit_with_proposal()
        self.good = self.path.read_bytes()

    def assert_refused_untouched(self, damaged):
        self.path.write_bytes(damaged)
        calls = len(self.npm_calls())
        for args in (("audit", "--npm", str(self.npm)), ("show",), ("decide", "SEO-001", "--status", "approved"), ("apply", "SEO-001", "--npm", str(self.npm))):
            code, out = self.cli(*args)
            self.assertEqual(code, 1, (args, out))
            self.assertTrue(out.startswith("STOP:"), (args, out))
            self.assertNotIn("Traceback", out)
        self.assertEqual(self.path.read_bytes(), damaged, "the damaged list is never overwritten")
        self.assertEqual(len(self.npm_calls()), calls)

    def test_a_real_hand_edit_is_refused(self):
        self.assert_refused_untouched(self.good.replace(b"- proposed", b"- approved", 1))

    def test_a_hand_edit_that_only_touches_a_carriage_return_is_refused(self):
        self.assertIn(b"one\r two", self.good)                         # the renderer shows a newline as a space, the CR stays
        self.assert_refused_untouched(self.good.replace(b"one\r two", b"one two", 1))

    def test_a_damaged_checksum_is_refused(self):
        marker = b"sha256="
        i = self.good.index(marker) + len(marker)
        flipped = b"0" if self.good[i:i + 1] != b"0" else b"1"
        self.assert_refused_untouched(self.good[:i] + flipped + self.good[i + 1:])

    def test_a_list_converted_wholesale_to_other_line_endings_is_a_change_and_is_not_normalised(self):
        self.assert_refused_untouched(self.good.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))

    def test_a_file_that_is_not_utf8_is_refused(self):
        self.assert_refused_untouched(b"\xff\xfe\x00 not text")

    def test_truncated_list_is_refused(self):
        self.assert_refused_untouched(self.good[: len(self.good) // 2])


if __name__ == "__main__":
    unittest.main()

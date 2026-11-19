import unittest

from tests.support import setup_paths as helpers  # noqa: F401  (sets up sys.path first)
import clone


class PlaceholderTests(unittest.TestCase):
    def test_render_replaces_known_placeholders_and_leaves_unknown_ones(self):
        self.assertEqual(clone.render("hi {{x}} {{y}}", {"x": "1"}), "hi 1 {{y}}")

    def test_unresolved_lists_the_remaining_names_once(self):
        self.assertEqual(clone.unresolved("{{a}} {{b}} {{a}}"), ["a", "b"])
        self.assertEqual(clone.unresolved("plain"), [])

    def test_github_expressions_are_not_placeholders(self):
        self.assertEqual(clone.unresolved("${{ github.sha }} {{name}}"), ["name"])

    def test_template_suffix(self):
        self.assertEqual(clone.TPL, ".tpl")


if __name__ == "__main__":
    unittest.main()

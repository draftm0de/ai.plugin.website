import unittest

from tests.support import setup_paths as helpers  # noqa: F401  (sets up sys.path first)
import validate
from errors import Ask, Stop

CONFIG = {"types": {"astro-static": {}}}


class DomainTests(unittest.TestCase):
    def test_valid(self):
        for d in ["alpha-shop.example", "beta.example", "www.gamma.example"]:
            self.assertEqual(validate.check_domain(d), d)

    def test_missing_asks(self):
        with self.assertRaises(Ask):
            validate.check_domain(None)

    def test_invalid_stops(self):
        for d in ["Alpha.example", "nodot", "a b.example", "../x.example", "-a.example", "a..example"]:
            with self.assertRaises(Stop, msg=d):
                validate.check_domain(d)


class TypeTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate.check_type("astro-static", CONFIG), "astro-static")

    def test_missing_asks(self):
        with self.assertRaises(Ask):
            validate.check_type(None, CONFIG)

    def test_unsupported_stops(self):
        for name in ("hugo", "astro"):          # "astro" is the removed Docker/Caddy type: rejected, not translated
            with self.assertRaises(Stop, msg=name):
                validate.check_type(name, CONFIG)


if __name__ == "__main__":
    unittest.main()

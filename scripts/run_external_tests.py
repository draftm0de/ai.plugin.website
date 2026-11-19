#!/usr/bin/env python3
"""Explicit, separate entry for tests that start the REAL npm tool (network). Never part of `make test` or run_tests.py.

Requires --approved (the owner's separate release). Enables the tests by a module flag, not by an environment variable.
"""
import argparse
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved", action="store_true", help="the real npm/network tests were released separately")
    args = parser.parse_args()
    if not args.approved:
        print("NOT RUN: real npm tests need --approved (separate release).")
        return 2
    import tests.external as external
    external.ENABLED = True
    suite = unittest.TestLoader().discover(str(ROOT / "tests" / "external"), pattern="test_*.py", top_level_dir=str(ROOT))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    sys.exit(main())

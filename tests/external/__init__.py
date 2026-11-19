"""Tests that start the REAL npm tool (network, downloads). Not a test layer of the default run.

They are only enabled when the dedicated runner `scripts/run_external_tests.py` sets ENABLED programmatically after an explicit
`--approved` flag. An inherited environment variable can never enable them. Needs a separate release by the owner.
"""
ENABLED = False

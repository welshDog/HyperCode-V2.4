"""Tests for scripts/mint_agent_keys.py.

    python -m unittest discover -s scripts -p "test_mint_agent_keys.py" -v

Pins: (1) no arguments must NOT rotate anything (it used to rotate every agent), (2) the agents that run but had no
key row/file (governor, throttle-agent, tips-tricks-writer) can be minted, (3) the SQL carries only a hash.
"""

import contextlib
import hashlib
import importlib.util
import io
import os
import re
import tempfile
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("mint", Path(__file__).with_name("mint_agent_keys.py"))
mint = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mint)


class MintAgentKeys(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        mint.SECRETS_DIR = Path(self.tmp.name)

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        import sys
        old = sys.argv
        sys.argv = ["mint_agent_keys.py"] + argv
        code = 0
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    mint.main()
                except SystemExit as e:
                    code = e.code if isinstance(e.code, int) else 1
        finally:
            sys.argv = old
        return code, out.getvalue(), err.getvalue()

    def test_no_arguments_rotates_nothing(self):
        code, out, _ = self._run([])
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_missing_agents_are_mintable(self):
        for name in ("governor", "throttle-agent", "tips-tricks-writer"):
            self.assertIn(name, mint.AGENTS)

    def test_minting_one_agent_touches_only_that_agent(self):
        code, out, _ = self._run(["governor"])
        self.assertEqual(code, 0)
        self.assertEqual(os.listdir(self.tmp.name), ["agent_api_key_governor.txt"])
        self.assertEqual(len(re.findall("INSERT INTO agent_api_keys", out)), 1)

    def test_sql_has_the_hash_but_never_the_raw_key(self):
        _, out, _ = self._run(["governor"])
        raw = (Path(self.tmp.name) / "agent_api_key_governor.txt").read_text(encoding="ascii")
        self.assertTrue(raw.startswith("hc_"))
        self.assertIn(hashlib.sha256(raw.encode()).hexdigest(), out)
        self.assertNotIn(raw, out)

    def test_all_flag_mints_every_agent(self):
        code, out, _ = self._run(["--all"])
        self.assertEqual(code, 0)
        self.assertEqual(len(os.listdir(self.tmp.name)), len(mint.AGENTS))

    def test_unknown_agent_is_rejected_before_writing(self):
        code, out, _ = self._run(["not-an-agent"])
        self.assertNotEqual(code, 0)
        self.assertEqual(os.listdir(self.tmp.name), [])


if __name__ == "__main__":
    unittest.main()

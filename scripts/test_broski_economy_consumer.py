"""Tests for scripts/broski_economy_consumer.py - the postgres sink key handling and failure reporting.

    python -m unittest discover -s scripts -p "test_broski_economy_consumer.py" -v

Background: after the 2026-10-15 master-key rotation the consumer kept the OLD key, core answered 401 for every
award, and the log only said "->pg FAILED (HTTPError)" (no status, no alert). These tests pin the fixes:
the key can come from a Compose secret file, failures name the HTTP status, and repeated auth rejections are loud.
"""

import http.server
import os
import sys
import tempfile
import threading
import unittest
import unittest.mock
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import broski_economy_consumer as c  # noqa: E402


class ReadSecret(unittest.TestCase):
    def setUp(self):
        self._env = unittest.mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        for k in ("DEMO_KEY", "DEMO_KEY_FILE"):
            os.environ.pop(k, None)

    def tearDown(self):
        self._env.stop()

    def _file(self, text):
        f = tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8")
        f.write(text)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_file_wins_and_is_stripped(self):
        os.environ["DEMO_KEY_FILE"] = self._file("from-file\n")
        os.environ["DEMO_KEY"] = "from-env"
        self.assertEqual(c._read_secret("DEMO_KEY"), "from-file")

    def test_env_fallback_when_no_file_var(self):
        os.environ["DEMO_KEY"] = "from-env"
        self.assertEqual(c._read_secret("DEMO_KEY"), "from-env")

    def test_env_fallback_when_file_missing_or_empty(self):
        os.environ["DEMO_KEY"] = "from-env"
        os.environ["DEMO_KEY_FILE"] = os.path.join(tempfile.gettempdir(), "definitely-not-here-xyz")
        self.assertEqual(c._read_secret("DEMO_KEY"), "from-env")
        os.environ["DEMO_KEY_FILE"] = self._file("  \n")
        self.assertEqual(c._read_secret("DEMO_KEY"), "from-env")

    def test_empty_when_nothing_set(self):
        self.assertEqual(c._read_secret("DEMO_KEY"), "")

    def test_key_source_never_returns_the_value(self):
        os.environ["DEMO_KEY_FILE"] = self._file("secret-value")
        self.assertEqual(c._key_source("DEMO_KEY"), "file")
        os.environ.pop("DEMO_KEY_FILE")
        os.environ["DEMO_KEY"] = "secret-value"
        self.assertEqual(c._key_source("DEMO_KEY"), "env")
        os.environ.pop("DEMO_KEY")
        self.assertEqual(c._key_source("DEMO_KEY"), "none")


class FailureReporting(unittest.TestCase):
    def test_describe_includes_http_status(self):
        err = urllib.error.HTTPError("http://x", 401, "Unauthorized", {}, None)
        self.assertEqual(c._describe_failure(err), "HTTP 401")

    def test_describe_non_http_uses_class_name(self):
        self.assertEqual(c._describe_failure(urllib.error.URLError("boom")), "URLError")

    def test_alert_on_first_then_every_tenth_consecutive_auth_failure(self):
        err = urllib.error.HTTPError("http://x", 401, "Unauthorized", {}, None)
        self.assertIn("stale or wrong", c._auth_alert(err, 1))
        for n in range(2, 10):
            self.assertIsNone(c._auth_alert(err, n), n)
        self.assertIn("x10", c._auth_alert(err, 10))
        self.assertIsNone(c._auth_alert(err, 11))

    def test_403_also_counts_but_other_errors_do_not(self):
        self.assertIsNotNone(c._auth_alert(urllib.error.HTTPError("u", 403, "F", {}, None), 1))
        self.assertIsNone(c._auth_alert(urllib.error.HTTPError("u", 500, "E", {}, None), 1))
        self.assertIsNone(c._auth_alert(urllib.error.URLError("down"), 1))


class _Handler(http.server.BaseHTTPRequestHandler):
    status = 200
    seen_key = None

    def do_POST(self):
        type(self).seen_key = self.headers.get("X-API-Key")
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(type(self).status)
        self.end_headers()

    def log_message(self, *a):
        pass


class PostToCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def _patched(self, key="k-test", discord="123"):
        return unittest.mock.patch.multiple(c, _CORE_URL=self.url, _CORE_API_KEY=key, _DEV_XP_DISCORD_ID=discord)

    def test_success_returns_true_and_sends_the_key_header(self):
        _Handler.status = 200
        with self._patched():
            self.assertIs(c._post_to_core(10, "git:x", "commit", "git:x:1"), True)
        self.assertEqual(_Handler.seen_key, "k-test")

    def test_401_returns_the_error_with_its_status(self):
        _Handler.status = 401
        with self._patched():
            res = c._post_to_core(10, "git:x", "commit", "git:x:1")
        self.assertIsInstance(res, urllib.error.HTTPError)
        self.assertEqual(c._describe_failure(res), "HTTP 401")

    def test_unconfigured_sink_returns_none(self):
        with self._patched(key=""):
            self.assertIsNone(c._post_to_core(10, "git:x", "commit"))


if __name__ == "__main__":
    unittest.main()

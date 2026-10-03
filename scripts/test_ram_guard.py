"""Tests for scripts/ram_guard.py (stdlib unittest: no pytest needed on the host).

    python -m unittest discover -s scripts -p "test_ram_guard.py" -v

The numbers are REAL readings from 2026-10-03, so a threshold change that would have missed the thrash fails here.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ram_guard as rg  # noqa: E402

# Windows host out of RAM; WSL still looked "fine" to `wsl -e free -m` alone (the incident)
THRASH = rg.Metrics(host_free_mb=1, host_total_mb=7974, compression_mb=4511, wsl_avail_mb=1317, wsl_total_mb=3917,
                    swap_used_mb=1085, swap_total_mb=2048, docker_ok=True, unhealthy=["hypercode-core", "postgres"])
# the same machine once memory was freed
GOOD = rg.Metrics(host_free_mb=767, host_total_mb=7974, compression_mb=1935, wsl_avail_mb=1782, wsl_total_mb=3917,
                  swap_used_mb=1076, swap_total_mb=2048, docker_ok=True, unhealthy=[])

FREE_M = """               total        used        free      shared  buff/cache   available
Mem:            3917        2151         292          36        1471        1551
Swap:           2048        1074         973
"""


def levels(findings):
    return {f.name: f.level for f in findings}


class Evaluate(unittest.TestCase):
    def test_the_real_thrash_is_RED_even_though_WSL_alone_looked_ok(self):
        overall, f = rg.evaluate(THRASH)
        self.assertEqual(overall, rg.RED)
        lv = levels(f)
        self.assertEqual((lv["host free"], lv["host compression"]), (rg.RED, rg.RED))
        self.assertEqual(lv["WSL available"], rg.AMBER)  # 1317 MB: the old single check would not have called this RED

    def test_the_real_good_state_is_GREEN(self):
        overall, f = rg.evaluate(GOOD)
        self.assertEqual(overall, rg.GREEN, [(x.name, x.level, x.value) for x in f])

    def test_swap_alone_does_not_change_the_verdict(self):  # ~1.08 GB in BOTH the good and the bad state
        self.assertEqual(levels(rg.evaluate(GOOD)[1])["WSL swap used"], rg.GREEN)

    def test_build_floor_is_AMBER_below_1500_and_RED_below_1200(self):
        near = rg.Metrics(**{**GOOD.__dict__, "wsl_avail_mb": 1407})
        low = rg.Metrics(**{**GOOD.__dict__, "wsl_avail_mb": 1150})
        self.assertEqual(rg.evaluate(near)[0], rg.AMBER)
        self.assertEqual(rg.evaluate(low)[0], rg.RED)

    def test_an_unreadable_number_is_AMBER_never_silently_GREEN(self):
        m = rg.Metrics(**{**GOOD.__dict__, "host_free_mb": None})
        overall, f = rg.evaluate(m)
        self.assertEqual(overall, rg.AMBER)
        self.assertEqual(levels(f)["host free"], rg.AMBER)

    def test_docker_unresponsive_is_RED_and_unhealthy_containers_are_AMBER(self):
        self.assertEqual(rg.evaluate(rg.Metrics(**{**GOOD.__dict__, "docker_ok": False}))[0], rg.RED)
        amber = rg.evaluate(rg.Metrics(**{**GOOD.__dict__, "unhealthy": ["grafana"]}))
        self.assertEqual(amber[0], rg.AMBER)
        self.assertIn("grafana", [x for x in amber[1] if x.name == "docker"][0].detail)

    def test_thresholds_can_be_overridden(self):
        m = rg.Metrics(**{**GOOD.__dict__, "wsl_avail_mb": 1407})
        self.assertEqual(rg.evaluate(m, {"wsl_avail_amber": 1300})[0], rg.GREEN)


class ExitCodes(unittest.TestCase):
    def test_a_build_needs_GREEN_the_others_only_need_not_RED(self):
        self.assertEqual([rg.exit_code("build", x) for x in (rg.GREEN, rg.AMBER, rg.RED)], [0, 1, 2])
        for purpose in ("check", "restart", "start"):
            self.assertEqual([rg.exit_code(purpose, x) for x in (rg.GREEN, rg.AMBER, rg.RED)], [0, 0, 2])


class Parsing(unittest.TestCase):
    def test_free_m_real_sample(self):
        self.assertEqual(rg.parse_free_m(FREE_M), {"total": 3917, "avail": 1551, "swap_used": 1074, "swap_total": 2048})

    def test_free_m_garbage_gives_Nones_not_a_crash(self):
        self.assertEqual(rg.parse_free_m("nonsense\nMem: a b c"), {"total": None, "avail": None, "swap_used": None, "swap_total": None})
        self.assertEqual(rg.parse_free_m(""), {"total": None, "avail": None, "swap_used": None, "swap_total": None})

    def test_host_json(self):
        self.assertEqual(rg.parse_host_json('noise\n{"free":810,"total":7974,"compression":1546}')["free"], 810)
        self.assertEqual(rg.parse_host_json("not json"), {})
        self.assertEqual(rg.parse_host_json(""), {})


class Output(unittest.TestCase):
    def test_report_is_ascii_only_for_the_cp1252_console(self):
        for m in (GOOD, THRASH):
            overall, f = rg.evaluate(m)
            m2 = rg.Metrics(**{**m.__dict__, "top_host_procs": ["chrome 900MB"]})
            rg.render("build", overall, f, m2, rg.exit_code("build", overall)).encode("ascii")

    def test_red_report_tells_you_what_to_do_green_does_not(self):
        r_overall, r_f = rg.evaluate(THRASH)
        red = rg.render("build", r_overall, r_f, THRASH, 2)
        self.assertIn("NOT OK", red)
        self.assertIn("never `compose down`", red)
        g_overall, g_f = rg.evaluate(GOOD)
        self.assertNotIn("  * ", rg.render("build", g_overall, g_f, GOOD, 0))


class Main(unittest.TestCase):
    def run_main(self, argv, metrics_seq):
        seq = list(metrics_seq)
        with mock.patch.object(rg, "measure", side_effect=lambda skip=False: seq.pop(0) if len(seq) > 1 else seq[0]), \
             mock.patch.object(rg.time, "sleep"), contextlib.redirect_stdout(io.StringIO()) as out:
            code = rg.main(argv)
        return code, out.getvalue()

    def test_exit_codes_through_main(self):
        self.assertEqual(self.run_main(["--for", "build"], [GOOD])[0], 0)
        self.assertEqual(self.run_main(["--for", "build"], [THRASH])[0], 2)
        near = rg.Metrics(**{**GOOD.__dict__, "wsl_avail_mb": 1407})
        self.assertEqual(self.run_main(["--for", "build"], [near])[0], 1)
        self.assertEqual(self.run_main(["--for", "restart"], [near])[0], 0)

    def test_wait_polls_until_it_is_ok(self):
        code, _ = self.run_main(["--for", "build", "--wait", "60"], [THRASH, THRASH, GOOD])
        self.assertEqual(code, 0)

    def test_wait_gives_up_when_the_time_is_up(self):
        with mock.patch.object(rg.time, "time", side_effect=[0, 0, 100, 100, 100]):
            code, _ = self.run_main(["--for", "build", "--wait", "30"], [THRASH])
        self.assertEqual(code, 2)

    def test_json_and_out_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ram.json")
            code, out = self.run_main(["--json", "--out", path, "--for", "build"], [THRASH])
            data = json.loads(out)
            self.assertEqual((code, data["overall"], data["exit_code"]), (2, "RED", 2))
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["metrics"]["host_free_mb"], 1)
            self.assertFalse(os.path.exists(path + ".tmp"))


if __name__ == "__main__":
    unittest.main()

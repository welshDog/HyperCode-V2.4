"""Tests for pressure.py (stdlib unittest, no Docker).

    python -m unittest discover -s agents/throttle-agent -p "test_pressure.py" -v
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pressure as p  # noqa: E402

TIERS = {1: ["postgres"], 2: ["crew-orchestrator"], 3: ["celery-worker"], 4: ["skillweaver"],
         5: ["prometheus", "grafana"], 6: ["cadvisor"]}
PROTECT = {1, 2, 3}
HOLD = 300.0


class SignalFile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "ram.json")

    def tearDown(self):
        self.dir.cleanup()

    def write(self, obj, age=0.0, raw=None):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(raw if raw is not None else json.dumps(obj))
        t = 1_000_000.0
        os.utime(self.path, (t - age, t - age))
        return t  # "now"

    def test_missing_file_is_UNKNOWN(self):
        s = p.read_signal(os.path.join(self.dir.name, "nope.json"), now=1.0)
        self.assertEqual((s.level, s.reason), (p.UNKNOWN, "signal file missing"))

    def test_fresh_valid_signal_carries_the_level_and_metrics(self):
        now = self.write({"overall": "RED", "metrics": {"host_free_mb": 1, "wsl_avail_mb": 1317, "compression_mb": 4511}}, age=10)
        s = p.read_signal(self.path, now=now, max_age_s=120)
        self.assertEqual((s.level, s.host_free_mb, s.wsl_avail_mb, s.compression_mb), (p.RED, 1, 1317, 4511))
        self.assertAlmostEqual(s.age_s, 10, places=1)

    def test_a_stale_signal_is_UNKNOWN_even_if_it_says_GREEN(self):
        now = self.write({"overall": "GREEN"}, age=500)
        s = p.read_signal(self.path, now=now, max_age_s=120)
        self.assertEqual(s.level, p.UNKNOWN)
        self.assertIn("stale", s.reason)

    def test_corrupt_or_wrong_shape_is_UNKNOWN(self):
        for raw in ("{not json", "[]", '"RED"', '{"overall": "PURPLE"}', '{"x": 1}', ""):
            now = self.write(None, raw=raw)
            self.assertEqual(p.read_signal(self.path, now=now).level, p.UNKNOWN, raw)

    def test_metrics_that_are_not_ints_are_ignored(self):
        now = self.write({"overall": "AMBER", "metrics": {"host_free_mb": True, "wsl_avail_mb": "1400", "compression_mb": None}})
        s = p.read_signal(self.path, now=now)
        self.assertEqual((s.level, s.host_free_mb, s.wsl_avail_mb, s.compression_mb), (p.AMBER, None, None, None))


class ParseTiers(unittest.TestCase):
    def test_valid_override(self):
        self.assertEqual(p.parse_tiers('{"6": ["cadvisor"], "5": ["grafana", " loki "]}', TIERS),
                         {6: ["cadvisor"], 5: ["grafana", "loki"]})

    def test_anything_invalid_falls_back_to_the_defaults_entirely(self):
        for raw in (None, "", "  ", "{bad", "[]", "{}", '{"x": ["a"]}', '{"0": ["a"]}', '{"6": "cadvisor"}',
                    '{"6": [1]}', '{"6": [""]}', '{"6": ["ok"], "5": "bad"}'):
            self.assertIs(p.parse_tiers(raw, TIERS), TIERS, raw)


def run(level, paused=(), protect=PROTECT, tiers=TIERS, green_since=None, now=1000.0, hold=HOLD):
    return p.step(level, set(paused), set(protect), tiers, green_since, now, hold)


class Step(unittest.TestCase):
    def test_UNKNOWN_never_acts(self):
        s = run(p.UNKNOWN)
        self.assertEqual((s.to_pause, s.to_resume, s.green_since), ((), (), None))

    def test_UNKNOWN_does_not_resume_what_is_paused_and_restarts_the_hold(self):
        s = run(p.UNKNOWN, paused={6, 5}, green_since=100.0, now=9999.0)
        self.assertEqual((s.to_pause, s.to_resume, s.green_since), ((), (), None))

    def test_GREEN_with_nothing_paused_does_nothing(self):
        s = run(p.GREEN)
        self.assertEqual((s.to_pause, s.to_resume), ((), ()))

    def test_AMBER_pauses_only_tier_6(self):
        self.assertEqual(run(p.AMBER).to_pause, (6,))

    def test_RED_pauses_6_5_4_in_that_order(self):
        self.assertEqual(run(p.RED).to_pause, (6, 5, 4))

    def test_protected_tiers_are_never_paused_and_are_reported(self):
        s = run(p.RED, protect={1, 2, 3, 4})
        self.assertEqual((s.to_pause, s.protected_skipped), ((6, 5), (4,)))

    def test_already_paused_tiers_are_not_paused_again(self):
        self.assertEqual(run(p.RED, paused={6}).to_pause, (5, 4))

    def test_a_tier_that_is_not_configured_is_skipped(self):
        self.assertEqual(run(p.RED, tiers={5: ["grafana"]}).to_pause, (5,))

    def test_hysteresis_first_green_starts_the_clock_but_does_not_resume(self):
        s = run(p.GREEN, paused={6}, green_since=None, now=1000.0)
        self.assertEqual((s.to_resume, s.green_since), ((), 1000.0))

    def test_resume_only_after_the_hold_time_of_continuous_green(self):
        self.assertEqual(run(p.GREEN, paused={6, 5}, green_since=1000.0, now=1000.0 + HOLD - 1).to_resume, ())
        self.assertEqual(run(p.GREEN, paused={6, 5}, green_since=1000.0, now=1000.0 + HOLD).to_resume, (5, 6))

    def test_amber_or_red_after_green_restarts_the_clock(self):
        for level in (p.AMBER, p.RED):
            s = run(level, paused={6}, green_since=1000.0, now=1000.0 + 10 * HOLD)
            self.assertEqual((s.to_resume, s.green_since), ((), None), level)

    def test_nothing_to_resume_when_nothing_is_paused(self):
        self.assertEqual(run(p.GREEN, paused=set(), green_since=0.0, now=99999.0).to_resume, ())

    def test_full_sequence_red_then_calm(self):
        paused, gs, log = set(), None, []
        for t, level in [(0, p.RED), (30, p.RED), (60, p.AMBER), (90, p.GREEN), (200, p.GREEN), (390, p.GREEN), (400, p.GREEN)]:
            s = p.step(level, paused, PROTECT, TIERS, gs, float(t), HOLD)
            paused |= set(s.to_pause)
            paused -= set(s.to_resume)
            gs = s.green_since
            log.append((t, level, s.to_pause, s.to_resume))
        by_t = {t: (pause, resume) for t, _level, pause, resume in log}
        self.assertEqual(by_t[0], ((6, 5, 4), ()))   # RED pauses everything pausable
        self.assertEqual(by_t[30], ((), ()))         # still RED: nothing new
        self.assertEqual(by_t[60], ((), ()))         # AMBER: everything stays paused
        self.assertEqual(by_t[90], ((), ()))         # GREEN starts: the hold clock starts, no resume yet
        self.assertEqual(by_t[200], ((), ()))        # 110 s of GREEN: not enough
        self.assertEqual(by_t[390], ((), (4, 5, 6)))  # 90 + 300 s = 300 s of continuous GREEN: resume all
        self.assertEqual(by_t[400], ((), ()))        # nothing left to do
        self.assertEqual(paused, set())


if __name__ == "__main__":
    unittest.main()

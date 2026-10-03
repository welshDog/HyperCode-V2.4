"""Integration tests: the REAL main.py with Docker faked. Run inside the throttle image (needs fastapi/docker/prometheus):

    docker run --rm -v "<this dir>:/w" -w /w --entrypoint python hypercode-throttle-agent:latest -m unittest test_main_signal -v

Properties: observe mode NEVER touches Docker; an UNKNOWN signal NEVER acts; protected tiers are never paused;
resume needs continuous GREEN for the hold time; a typo in THROTTLE_MODE can never arm enforcement.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.pop("THROTTLE_MODE", None)
import main  # noqa: E402

NOW = 2_000_000.0


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "ram.json")
        main._sim_paused_tiers.clear()
        main._autopilot_paused_tiers.clear()
        main._autopilot_below_since = None
        main._decision_log.clear()
        main._last_logged_level = None
        main._last_signal = None
        self.client = mock.Mock(name="docker_client_factory")
        self.pause = mock.Mock(name="pause_tier")
        self.resume = mock.Mock(name="resume_tier")
        self.now = NOW
        patches = [
            mock.patch.object(main, "THROTTLE_SIGNAL_FILE", self.path),
            mock.patch.object(main, "_docker_client", self.client),
            mock.patch.object(main, "_pause_tier_sync", self.pause),
            mock.patch.object(main, "_resume_tier_sync", self.resume),
            mock.patch.object(main.time, "time", lambda: self.now),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def signal(self, level, age=1.0):
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"overall": level, "metrics": {"host_free_mb": 1, "wsl_avail_mb": 1300, "compression_mb": 4500}}, fh)
        os.utime(self.path, (self.now - age, self.now - age))

    def cycle(self, mode):
        with mock.patch.object(main, "THROTTLE_MODE", mode):
            main._signal_cycle_sync()


class Observe(Base):
    def test_RED_logs_what_it_would_pause_and_never_touches_docker(self):
        self.signal("RED")
        self.cycle("observe")
        self.client.assert_not_called()
        self.pause.assert_not_called()
        self.resume.assert_not_called()
        self.assertEqual(main._sim_paused_tiers, {6, 5, 4})
        d = main._decision_log[-1]
        self.assertEqual((d["mode"], d["signal"]), ("observe", "RED"))
        self.assertIn("cadvisor", d["would_pause"]["6"])
        self.assertIn("prometheus", d["would_pause"]["5"])
        self.assertIn("evolve-relay", d["would_pause"]["4"])
        self.assertNotIn("postgres", json.dumps(d))

    def test_missing_or_stale_signal_is_UNKNOWN_and_pauses_nothing(self):
        self.cycle("observe")  # no file
        self.assertEqual(main._last_signal["level"], "UNKNOWN")
        self.signal("RED", age=9999)  # stale
        self.cycle("observe")
        self.assertEqual(main._last_signal["level"], "UNKNOWN")
        self.assertEqual(main._sim_paused_tiers, set())
        self.client.assert_not_called()

    def test_observe_timeline_would_resume_after_the_hold(self):
        self.signal("RED")
        self.cycle("observe")
        self.now += 30
        self.signal("GREEN")
        self.cycle("observe")
        self.assertEqual(main._sim_paused_tiers, {6, 5, 4})  # hold just started
        self.now += main.THROTTLE_RESUME_HOLD_MINUTES * 60
        self.signal("GREEN")
        self.cycle("observe")
        self.assertEqual(main._sim_paused_tiers, set())
        self.assertIn("4", main._decision_log[-1]["would_resume"])
        self.pause.assert_not_called()
        self.resume.assert_not_called()

    def test_signal_endpoint_reports_state_and_says_it_is_simulated(self):
        self.signal("AMBER")
        with mock.patch.object(main, "THROTTLE_MODE", "observe"):
            self.cycle("observe")
            s = main.signal_status()
        self.assertEqual((s["mode"], s["paused_tiers"], s["paused_tiers_are_simulated"]), ("observe", [6], True))
        self.assertEqual(s["signal"]["level"], "AMBER")
        self.assertEqual(s["protect_tiers"], [1, 2, 3])


class Enforce(Base):
    def test_RED_pauses_6_5_4_in_order_and_remembers_them(self):
        self.signal("RED")
        self.cycle("enforce")
        self.assertEqual([c.args[1] for c in self.pause.call_args_list], [6, 5, 4])
        self.assertEqual(main._autopilot_paused_tiers, {6, 5, 4})

    def test_UNKNOWN_never_acts_not_even_to_connect_to_docker(self):
        self.cycle("enforce")  # missing file
        self.signal("RED", age=9999)
        self.cycle("enforce")  # stale file
        self.client.assert_not_called()
        self.pause.assert_not_called()

    def test_protected_tiers_are_never_paused(self):
        self.signal("RED")
        with mock.patch.object(main, "THROTTLE_PROTECT_TIERS", {1, 2, 3, 4}):
            self.cycle("enforce")
        self.assertEqual([c.args[1] for c in self.pause.call_args_list], [6, 5])

    def test_resume_needs_continuous_green_for_the_hold_time(self):
        self.signal("RED")
        self.cycle("enforce")
        hold = main.THROTTLE_RESUME_HOLD_MINUTES * 60
        self.now += 10
        self.signal("GREEN")
        self.cycle("enforce")
        self.now += hold - 20
        self.signal("GREEN")
        self.cycle("enforce")
        self.resume.assert_not_called()
        self.now += 10
        self.signal("AMBER")  # a blip restarts the clock
        self.cycle("enforce")
        self.now += hold
        self.signal("GREEN")
        self.cycle("enforce")
        self.resume.assert_not_called()  # clock only just restarted
        self.now += hold
        self.signal("GREEN")
        self.cycle("enforce")
        self.assertEqual(sorted(c.args[1] for c in self.resume.call_args_list), [4, 5, 6])
        self.assertEqual(main._autopilot_paused_tiers, set())


class Config(unittest.TestCase):
    def mode(self, **env):
        e = {k: v for k, v in os.environ.items() if not k.startswith("THROTTLE_") and k != "AUTO_THROTTLE_ENABLED"}
        e.update(env)
        r = subprocess.run([sys.executable, "-c", "import main; print(main.THROTTLE_MODE)"], cwd=HERE, env=e,
                           capture_output=True, text=True, timeout=120)
        return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]

    def test_default_is_off_and_the_old_flag_still_means_enforce(self):
        self.assertEqual(self.mode(), "off")
        self.assertEqual(self.mode(AUTO_THROTTLE_ENABLED="true"), "enforce")

    def test_explicit_modes(self):
        for m in ("off", "observe", "enforce"):
            self.assertEqual(self.mode(THROTTLE_MODE=m), m)

    def test_a_typo_can_never_arm_enforcement(self):
        for typo in ("enfroce", "ENFORCE_NOW", "yes", "1"):
            self.assertEqual(self.mode(THROTTLE_MODE=typo, AUTO_THROTTLE_ENABLED="true"), "observe", typo)

    def test_tiers_override_and_bad_override_falls_back(self):
        def tiers(raw):
            e = {k: v for k, v in os.environ.items() if not k.startswith("THROTTLE_")}
            e["THROTTLE_TIERS_JSON"] = raw
            r = subprocess.run([sys.executable, "-c", "import main, json; print(json.dumps(main._get_tiers()))"], cwd=HERE,
                               env=e, capture_output=True, text=True, timeout=120)
            return json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(tiers('{"6": ["cadvisor"]}'), {"6": ["cadvisor"]})
        self.assertIn("1", tiers("{broken"))  # fell back to the defaults


class Tiers(unittest.TestCase):
    def test_no_container_is_in_two_tiers(self):
        names = [n for v in main.DEFAULT_TIERS.values() for n in v]
        self.assertEqual(len(names), len(set(names)), sorted(n for n in set(names) if names.count(n) > 1))

    def test_the_crew_and_infrastructure_are_in_protected_tiers(self):
        protected = {n for t in main.THROTTLE_PROTECT_TIERS for n in main.DEFAULT_TIERS.get(t, [])}
        for must in ("postgres", "redis", "hypercode-core", "safety-shepherd", "healer-agent", "crew-orchestrator",
                     "coder-agent", "qa-engineer", "docker-socket-proxy-healer", "memstream"):
            self.assertIn(must, protected, must)

    def test_protect_container_defaults_cover_what_must_never_be_paused(self):
        for must in ("throttle-agent", "healer-agent", "postgres", "redis", "hypercode-core", "safety-shepherd",
                     "docker-socket-proxy-healer"):
            self.assertIn(must, main.THROTTLE_PROTECT_CONTAINERS, must)


if __name__ == "__main__":
    unittest.main()

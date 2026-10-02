"""HyperCrew Day 3 — the RAM-aware slot gate."""

import asyncio

import pytest

from app.crew import slots
from app.crew.slots import HARD_MAX_AWAKE, SlotGate, SlotUnavailable, read_available_mb


def run(coro):
    return asyncio.run(coro)


def gate(cap=3, floor=0, reader=lambda: 4000, poll=0.005):
    return SlotGate(cap=cap, min_available_mb=floor, ram_reader=reader, poll_s=poll)


def test_cap_is_clamped_to_the_hard_max_and_at_least_one():
    assert SlotGate(cap=10).cap == HARD_MAX_AWAKE == 3
    assert SlotGate(cap=0).cap == 1 and SlotGate(cap=-5).cap == 1


def test_fourth_agent_waits_and_then_times_out_instead_of_starting():
    async def scenario():
        g = gate(cap=3)
        for _ in range(3):
            await g.acquire(1)
        assert g.active == 3
        with pytest.raises(SlotUnavailable, match="slots are busy"):
            await g.acquire(0.05)
        assert g.active == 3  # the waiter never took a slot

    run(scenario())


def test_a_released_slot_lets_the_waiter_in():
    async def scenario():
        g = gate(cap=1)
        await g.acquire(1)
        waiter = asyncio.create_task(g.acquire(2))
        await asyncio.sleep(0.03)
        assert not waiter.done()
        g.release()
        ticket = await waiter
        assert ticket.wait_ms >= 20 and g.active == 1

    run(scenario())


def test_never_more_than_cap_run_at_once():
    async def scenario():
        g, running, peak = gate(cap=3), 0, 0

        async def worker():
            nonlocal running, peak
            async with g.slot(5):
                running += 1
                peak = max(peak, running)
                await asyncio.sleep(0.02)
                running -= 1

        await asyncio.gather(*(worker() for _ in range(9)))
        return peak, g.active

    peak, active = run(scenario())
    assert peak == 3 and active == 0


def test_slot_is_released_when_the_work_raises():
    async def scenario():
        g = gate(cap=1)
        with pytest.raises(ValueError):
            async with g.slot(1):
                raise ValueError("boom")
        assert g.active == 0

    run(scenario())


def test_slot_is_released_when_the_work_is_cancelled():
    async def scenario():
        g = gate(cap=1)

        async def held():
            async with g.slot(1):
                await asyncio.sleep(10)

        task = asyncio.create_task(held())
        await asyncio.sleep(0.02)
        assert g.active == 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert g.active == 0

    run(scenario())


def test_release_never_goes_negative():
    g = gate()
    g.release()
    g.release()
    assert g.active == 0


def test_low_ram_blocks_even_with_free_slots():
    async def scenario():
        g = gate(cap=3, floor=1200, reader=lambda: 500)
        with pytest.raises(SlotUnavailable, match="RAM"):
            await g.acquire(0.05)
        assert g.active == 0

    run(scenario())


def test_enough_ram_lets_the_agent_in_and_reports_it():
    async def scenario():
        ticket = await gate(floor=1200, reader=lambda: 2048).acquire(1)
        assert ticket.available_mb == 2048

    run(scenario())


def test_ram_recovering_while_waiting_lets_the_agent_in():
    readings = iter([500, 500, 500, 2000, 2000, 2000])

    async def scenario():
        ticket = await gate(floor=1200, reader=lambda: next(readings)).acquire(2)
        assert ticket.available_mb == 2000

    run(scenario())


def test_unreadable_ram_falls_back_to_the_cap_alone():
    async def scenario():
        ticket = await gate(floor=1200, reader=lambda: None).acquire(1)
        assert ticket.available_mb is None

    run(scenario())


def test_floor_zero_disables_the_ram_check_entirely():
    def boom():
        raise AssertionError("reader must not be called")

    run(gate(floor=0, reader=boom).acquire(1))


def test_read_available_mb_parses_meminfo(tmp_path):
    f = tmp_path / "meminfo"
    f.write_text("MemTotal:  8000000 kB\nMemAvailable:  2097152 kB\n")
    assert read_available_mb(str(f)) == 2048


def test_read_available_mb_is_none_when_missing_or_malformed(tmp_path):
    assert read_available_mb(str(tmp_path / "nope")) is None
    bad = tmp_path / "bad"
    bad.write_text("MemAvailable: lots kB\n")
    assert read_available_mb(str(bad)) is None
    none = tmp_path / "none"
    none.write_text("MemTotal: 1 kB\n")
    assert read_available_mb(str(none)) is None


def test_gate_from_env(monkeypatch):
    monkeypatch.setenv("CREW_MAX_AWAKE", "2")
    monkeypatch.setenv("CREW_MIN_AVAILABLE_MB", "900")
    g = slots.gate_from_env()
    assert g.cap == 2 and g.min_available_mb == 900


def test_gate_from_env_ignores_garbage_and_clamps(monkeypatch):
    monkeypatch.setenv("CREW_MAX_AWAKE", "lots")
    monkeypatch.setenv("CREW_MIN_AVAILABLE_MB", "-4")
    g = slots.gate_from_env()
    assert g.cap == 3 and g.min_available_mb == 0
    monkeypatch.setenv("CREW_MAX_AWAKE", "99")
    assert slots.gate_from_env().cap == 3


def test_timeout_env(monkeypatch):
    monkeypatch.setenv("CREW_SLOT_TIMEOUT_S", "7")
    assert slots.slot_timeout_s() == 7.0
    monkeypatch.setenv("CREW_SLOT_TIMEOUT_S", "0")
    assert slots.slot_timeout_s() == 1.0


def test_singleton_can_be_replaced_and_reset():
    mine = gate()
    slots.set_slot_gate(mine)
    try:
        assert slots.get_slot_gate() is mine
    finally:
        slots.set_slot_gate(None)
    assert slots.get_slot_gate() is not mine
    slots.set_slot_gate(None)

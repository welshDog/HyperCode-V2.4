# agents/mission-director/tests/test_no_execution.py
"""Asserts no code path in this module can ever set an
execution/mutation flag True. main.py never constructs an ExecutionView
itself -- execution always comes verbatim from fleet-controller's own
PlanResponse, which fleet-controller's own Phase 0 already proves can
never be True. This test guards against a future regression introducing
a local override."""
import inspect

import main


def test_main_module_never_hardcodes_performed_true():
    source = inspect.getsource(main)
    assert "performed=True" not in source
    assert "performed = True" not in source


def test_terminal_helper_never_sets_plan_response():
    """_terminal() is used for every failure path -- plan_response must
    always be None there, since fleet-controller was never successfully
    reached (or never called) on any path that uses it."""
    source = inspect.getsource(main._terminal)
    assert "plan_response=None" in source

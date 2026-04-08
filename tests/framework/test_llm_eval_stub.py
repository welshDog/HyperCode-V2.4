"""T10 — Deterministic LLM_EVAL stub tests.

Verifies that Evaluator._check_llm_eval (and the full evaluate() pipeline via
EvaluationMethod.LLM_EVAL) is:

  1. Deterministic — same input always returns same output
  2. Never makes a network call
  3. Handles all documented spec formats correctly
  4. Integrates cleanly through evaluate()
  5. Emits a UserWarning (stub notice) on every call
"""
from __future__ import annotations

import json
import warnings
from types import SimpleNamespace
from typing import Any

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from framework.evaluator import Evaluator
from framework.models import EvaluationCriteria, EvaluationMethod


# ── Helpers ───────────────────────────────────────────────────────────────────

def _response(text: str = "", status: int = 200):
    """Minimal response double accepted by Evaluator._get_content."""
    return SimpleNamespace(text=text, status_code=status)


def _json_response(obj: Any, status: int = 200):
    return _response(json.dumps(obj), status)


evaluator = Evaluator()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Determinism
# ─────────────────────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_string_spec_same_input_same_output(self):
        resp = _response("status: completed, task_id: 123")
        r1 = evaluator._check_llm_eval(resp, "status, completed")
        r2 = evaluator._check_llm_eval(resp, "status, completed")
        assert r1 == r2

    def test_dict_spec_same_input_same_output(self):
        resp = _json_response({"status": "ok", "task_id": "t-1"})
        spec = {"required_keys": ["status", "task_id"], "status_ok": True}
        r1 = evaluator._check_llm_eval(resp, spec)
        r2 = evaluator._check_llm_eval(resp, spec)
        assert r1 == r2

    def test_failing_spec_is_also_deterministic(self):
        resp = _response("nothing useful")
        spec = {"contains_all": ["status", "task_id"]}
        r1 = evaluator._check_llm_eval(resp, spec)
        r2 = evaluator._check_llm_eval(resp, spec)
        assert r1 == r2 is False

    def test_hundred_calls_all_identical(self):
        resp = _response("hello world")
        results = [evaluator._check_llm_eval(resp, "hello") for _ in range(100)]
        assert all(r == results[0] for r in results)


# ─────────────────────────────────────────────────────────────────────────────
# 2. No network calls
# ─────────────────────────────────────────────────────────────────────────────

class TestNoNetworkCalls:
    def test_does_not_call_socket(self, monkeypatch):
        """Patch socket.socket to raise if touched — stub must not use network."""
        import socket

        original = socket.socket

        def no_socket(*args, **kwargs):
            raise AssertionError("LLM_EVAL stub must NOT open a socket")

        monkeypatch.setattr(socket, "socket", no_socket)
        resp = _response("some content")
        # Must not raise AssertionError
        result = evaluator._check_llm_eval(resp, "some")
        assert isinstance(result, bool)

    def test_does_not_import_openai(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name in ("openai", "anthropic", "httpx", "requests"):
                raise AssertionError(f"LLM_EVAL stub must NOT import {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", guarded_import)
        resp = _response("test response")
        result = evaluator._check_llm_eval(resp, "test")
        assert isinstance(result, bool)


# ─────────────────────────────────────────────────────────────────────────────
# 3. String shorthand spec
# ─────────────────────────────────────────────────────────────────────────────

class TestStringSpec:
    def test_single_keyword_found(self):
        assert evaluator._check_llm_eval(_response("status ok"), "status") is True

    def test_single_keyword_not_found(self):
        assert evaluator._check_llm_eval(_response("all good"), "status") is False

    def test_multiple_keywords_all_found(self):
        assert evaluator._check_llm_eval(_response("status completed task_id"), "status, completed, task_id") is True

    def test_multiple_keywords_one_missing(self):
        assert evaluator._check_llm_eval(_response("status completed"), "status, completed, task_id") is False

    def test_case_insensitive_matching(self):
        assert evaluator._check_llm_eval(_response("STATUS COMPLETED"), "status, completed") is True

    def test_empty_keyword_list_passes(self):
        # No keywords → trivially True
        assert evaluator._check_llm_eval(_response("anything"), "") is True

    def test_whitespace_keywords_ignored(self):
        assert evaluator._check_llm_eval(_response("status ok"), "status, , ok") is True


# ─────────────────────────────────────────────────────────────────────────────
# 4. Dict spec — required_keys
# ─────────────────────────────────────────────────────────────────────────────

class TestDictSpecRequiredKeys:
    def test_all_required_keys_present(self):
        resp = _json_response({"status": "ok", "task_id": "t-1", "result": {}})
        assert evaluator._check_llm_eval(resp, {"required_keys": ["status", "task_id"]}) is True

    def test_missing_required_key_fails(self):
        resp = _json_response({"status": "ok"})
        assert evaluator._check_llm_eval(resp, {"required_keys": ["status", "task_id"]}) is False

    def test_empty_required_keys_passes(self):
        resp = _json_response({"anything": 1})
        assert evaluator._check_llm_eval(resp, {"required_keys": []}) is True

    def test_non_json_response_fails_required_keys(self):
        resp = _response("not json")
        assert evaluator._check_llm_eval(resp, {"required_keys": ["status"]}) is False


# ─────────────────────────────────────────────────────────────────────────────
# 5. Dict spec — forbidden_keys
# ─────────────────────────────────────────────────────────────────────────────

class TestDictSpecForbiddenKeys:
    def test_forbidden_key_absent_passes(self):
        resp = _json_response({"status": "ok"})
        assert evaluator._check_llm_eval(resp, {"forbidden_keys": ["error"]}) is True

    def test_forbidden_key_present_fails(self):
        resp = _json_response({"status": "ok", "error": "something went wrong"})
        assert evaluator._check_llm_eval(resp, {"forbidden_keys": ["error"]}) is False

    def test_multiple_forbidden_first_present_fails(self):
        resp = _json_response({"traceback": "...", "status": "ok"})
        assert evaluator._check_llm_eval(resp, {"forbidden_keys": ["traceback", "exception"]}) is False

    def test_multiple_forbidden_none_present_passes(self):
        resp = _json_response({"status": "ok"})
        assert evaluator._check_llm_eval(resp, {"forbidden_keys": ["error", "traceback"]}) is True


# ─────────────────────────────────────────────────────────────────────────────
# 6. Dict spec — contains_all / contains_any
# ─────────────────────────────────────────────────────────────────────────────

class TestDictSpecContains:
    def test_contains_all_satisfied(self):
        resp = _response("Task started successfully")
        assert evaluator._check_llm_eval(resp, {"contains_all": ["Task", "successfully"]}) is True

    def test_contains_all_one_missing_fails(self):
        resp = _response("Task started")
        assert evaluator._check_llm_eval(resp, {"contains_all": ["Task", "successfully"]}) is False

    def test_contains_any_one_present_passes(self):
        resp = _response("workflow completed")
        assert evaluator._check_llm_eval(resp, {"contains_any": ["completed", "finished", "done"]}) is True

    def test_contains_any_none_present_fails(self):
        resp = _response("workflow started")
        assert evaluator._check_llm_eval(resp, {"contains_any": ["completed", "finished", "done"]}) is False

    def test_contains_any_empty_list_passes(self):
        resp = _response("anything")
        assert evaluator._check_llm_eval(resp, {"contains_any": []}) is True

    def test_contains_all_case_insensitive(self):
        resp = _response("TASK COMPLETED")
        assert evaluator._check_llm_eval(resp, {"contains_all": ["task", "completed"]}) is True


# ─────────────────────────────────────────────────────────────────────────────
# 7. Dict spec — min_length / max_length
# ─────────────────────────────────────────────────────────────────────────────

class TestDictSpecLength:
    def test_min_length_satisfied(self):
        resp = _response("a" * 50)
        assert evaluator._check_llm_eval(resp, {"min_length": 10}) is True

    def test_min_length_not_satisfied(self):
        resp = _response("short")
        assert evaluator._check_llm_eval(resp, {"min_length": 100}) is False

    def test_max_length_satisfied(self):
        resp = _response("short text")
        assert evaluator._check_llm_eval(resp, {"max_length": 100}) is True

    def test_max_length_exceeded(self):
        resp = _response("a" * 500)
        assert evaluator._check_llm_eval(resp, {"max_length": 100}) is False

    def test_exact_min_max_boundary_passes(self):
        resp = _response("a" * 50)
        assert evaluator._check_llm_eval(resp, {"min_length": 50, "max_length": 50}) is True

    def test_off_by_one_min_fails(self):
        resp = _response("a" * 49)
        assert evaluator._check_llm_eval(resp, {"min_length": 50}) is False


# ─────────────────────────────────────────────────────────────────────────────
# 8. Dict spec — status_ok
# ─────────────────────────────────────────────────────────────────────────────

class TestDictSpecStatusOk:
    def test_status_ok_with_200_passes(self):
        resp = _response("ok", status=200)
        assert evaluator._check_llm_eval(resp, {"status_ok": True}) is True

    def test_status_ok_with_201_passes(self):
        resp = _response("created", status=201)
        assert evaluator._check_llm_eval(resp, {"status_ok": True}) is True

    def test_status_ok_with_400_fails(self):
        resp = _response("bad request", status=400)
        assert evaluator._check_llm_eval(resp, {"status_ok": True}) is False

    def test_status_ok_with_500_fails(self):
        resp = _response("server error", status=500)
        assert evaluator._check_llm_eval(resp, {"status_ok": True}) is False

    def test_status_ok_false_ignores_status(self):
        resp = _response("error", status=500)
        assert evaluator._check_llm_eval(resp, {"status_ok": False}) is True

    def test_no_status_code_attribute_ignored(self):
        """If response has no status_code, status_ok check is skipped."""
        resp = SimpleNamespace(text="hello")
        assert evaluator._check_llm_eval(resp, {"status_ok": True}) is True


# ─────────────────────────────────────────────────────────────────────────────
# 9. Non-standard spec types
# ─────────────────────────────────────────────────────────────────────────────

class TestNonStandardSpec:
    def test_none_spec_truthy_content_passes(self):
        resp = _response("non-empty")
        assert evaluator._check_llm_eval(resp, None) is True

    def test_none_spec_empty_content_fails(self):
        resp = _response("")
        assert evaluator._check_llm_eval(resp, None) is False

    def test_integer_spec_treated_as_truthy(self):
        resp = _response("hello")
        assert evaluator._check_llm_eval(resp, 42) is True

    def test_list_spec_treated_as_truthy(self):
        resp = _response("hello")
        assert evaluator._check_llm_eval(resp, ["a", "b"]) is True


# ─────────────────────────────────────────────────────────────────────────────
# 10. UserWarning emitted
# ─────────────────────────────────────────────────────────────────────────────

class TestStubWarning:
    def test_warning_emitted_on_string_spec(self):
        resp = _response("hello")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            evaluator._check_llm_eval(resp, "hello")
        assert any("deterministic stub" in str(warning.message).lower() for warning in w)

    def test_warning_emitted_on_dict_spec(self):
        resp = _json_response({"status": "ok"})
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            evaluator._check_llm_eval(resp, {"required_keys": ["status"]})
        assert len(w) >= 1

    def test_warning_category_is_user_warning(self):
        resp = _response("test")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            evaluator._check_llm_eval(resp, "test")
        assert any(issubclass(warning.category, UserWarning) for warning in w)


# ─────────────────────────────────────────────────────────────────────────────
# 11. Integration via evaluate() pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluatePipeline:
    def test_llm_eval_criterion_passes_through_evaluate(self):
        resp = _json_response({"status": "completed", "task_id": "t-99"})
        criteria = [
            EvaluationCriteria(
                method=EvaluationMethod.LLM_EVAL,
                value={"required_keys": ["status", "task_id"], "contains_all": ["completed"]},
                weight=1.0,
            )
        ]
        success, score, errors = evaluator.evaluate(resp, criteria)
        assert success is True
        assert score == 100.0
        assert errors == []

    def test_llm_eval_criterion_fails_through_evaluate(self):
        resp = _json_response({"result": "partial"})
        criteria = [
            EvaluationCriteria(
                method=EvaluationMethod.LLM_EVAL,
                value={"required_keys": ["status", "task_id"]},
                weight=2.0,
            )
        ]
        success, score, errors = evaluator.evaluate(resp, criteria)
        assert success is False
        assert score == 0.0
        assert len(errors) == 1

    def test_llm_eval_mixed_with_status_code(self):
        resp = _json_response({"status": "ok"}, status=200)
        criteria = [
            EvaluationCriteria(method=EvaluationMethod.STATUS_CODE, value=200, weight=1.0),
            EvaluationCriteria(
                method=EvaluationMethod.LLM_EVAL,
                value={"required_keys": ["status"]},
                weight=1.0,
            ),
        ]
        success, score, errors = evaluator.evaluate(resp, criteria)
        assert success is True
        assert score == 100.0

    def test_partial_score_when_one_criterion_fails(self):
        resp = _response("hello world")
        criteria = [
            EvaluationCriteria(
                method=EvaluationMethod.LLM_EVAL,
                value="hello",
                weight=1.0,
                description="Must contain hello",
            ),
            EvaluationCriteria(
                method=EvaluationMethod.LLM_EVAL,
                value="missing_keyword",
                weight=1.0,
                description="Must contain missing",
            ),
        ]
        success, score, errors = evaluator.evaluate(resp, criteria)
        assert success is False
        assert score == pytest.approx(50.0)
        assert len(errors) == 1

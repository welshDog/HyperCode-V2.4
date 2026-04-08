import re
import json
from typing import Any, Dict, List, Tuple
from .models import EvaluationCriteria, EvaluationMethod

class Evaluator:
    def evaluate(self, response: Any, criteria: List[EvaluationCriteria]) -> Tuple[bool, float, List[str]]:
        """
        Evaluate a response against a list of criteria.
        Returns: (success, score, error_messages)
        """
        total_score = 0.0
        max_score = 0.0
        errors = []
        all_passed = True

        for criterion in criteria:
            passed = False
            max_score += criterion.weight
            
            try:
                if criterion.method == EvaluationMethod.STATUS_CODE:
                    passed = self._check_status_code(response, criterion.value)
                elif criterion.method == EvaluationMethod.CONTAINS:
                    passed = self._check_contains(response, criterion.value)
                elif criterion.method == EvaluationMethod.EXACT_MATCH:
                    passed = self._check_exact_match(response, criterion.value)
                elif criterion.method == EvaluationMethod.REGEX:
                    passed = self._check_regex(response, criterion.value)
                elif criterion.method == EvaluationMethod.JSON_SCHEMA:
                    passed = self._check_json_schema(response, criterion.value)
                elif criterion.method == EvaluationMethod.LLM_EVAL:
                    passed = self._check_llm_eval(response, criterion.value)
                
                if passed:
                    total_score += criterion.weight
                else:
                    all_passed = False
                    errors.append(f"Failed criterion: {criterion.description or criterion.method} - Expected {criterion.value}")

            except Exception as e:
                all_passed = False
                errors.append(f"Evaluation error for {criterion.method}: {str(e)}")

        normalized_score = (total_score / max_score) * 100 if max_score > 0 else 0
        return all_passed, normalized_score, errors

    def _check_status_code(self, response: Any, expected: int) -> bool:
        # Assumes response object has status_code attribute (like httpx response)
        if hasattr(response, "status_code"):
            return response.status_code == expected
        return False

    def _check_contains(self, response: Any, expected: str) -> bool:
        content = self._get_content(response)
        return expected in content

    def _check_exact_match(self, response: Any, expected: Any) -> bool:
        content = self._get_content(response)
        # Try to parse content as JSON if expected is not string
        if not isinstance(expected, str) and isinstance(content, str):
            try:
                content = json.loads(content)
            except:
                pass
        return content == expected

    def _check_regex(self, response: Any, pattern: str) -> bool:
        content = self._get_content(response)
        return bool(re.search(pattern, content))

    def _check_json_schema(self, response: Any, schema: Dict) -> bool:
        try:
            import jsonschema
            content = self._get_content(response)
            if isinstance(content, str):
                content = json.loads(content)
            
            jsonschema.validate(instance=content, schema=schema)
            return True
        except ImportError:
            # Fallback for simple dict check if jsonschema not installed
            content = self._get_content(response)
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except:
                    return False
            
            if not isinstance(content, dict):
                # If content is a list, we can't validate "required" keys on the list itself
                # unless we have logic for it. For now, fail if not dict.
                return False
                
            if "required" in schema:
                for key in schema["required"]:
                    if key not in content:
                        return False
            return True
        except Exception:
            return False

    def _check_llm_eval(self, response: Any, prompt_or_spec: Any) -> bool:
        """Deterministic LLM_EVAL stub.

        Instead of calling a real LLM (which is non-deterministic and
        requires network access), this stub evaluates responses using a
        structured rule set derived from the prompt/spec value.

        Spec formats accepted
        ─────────────────────
        str  — keyword list (comma-separated) that must ALL appear in content:
                ``"status, completed, task_id"``

        dict — structured spec with optional keys:
                ``required_keys``   : list[str]  — JSON keys that must exist
                ``forbidden_keys``  : list[str]  — JSON keys that must NOT exist
                ``contains_any``    : list[str]  — at least one must appear in content
                ``contains_all``    : list[str]  — all must appear in content
                ``min_length``      : int        — minimum content character length
                ``max_length``      : int        — maximum content character length
                ``status_ok``       : bool       — if True, response.status_code must be 2xx

        Behaviour
        ─────────
        - Never calls an external service
        - Always returns True/False deterministically for the same input
        - Logs a warning so developers know this is the stub path
        """
        import warnings
        warnings.warn(
            "LLM_EVAL is using the deterministic stub — no real LLM call made.",
            stacklevel=3,
        )

        content = self._get_content(response)

        # String shorthand: comma-separated keywords
        if isinstance(prompt_or_spec, str):
            keywords = [k.strip() for k in prompt_or_spec.split(",") if k.strip()]
            return all(kw.lower() in content.lower() for kw in keywords)

        if not isinstance(prompt_or_spec, dict):
            return bool(content)

        spec = prompt_or_spec

        # status_ok check
        if spec.get("status_ok", False):
            if hasattr(response, "status_code") and not (200 <= response.status_code < 300):
                return False

        # Parse JSON content for key checks
        parsed: Any = None
        try:
            parsed = json.loads(content) if isinstance(content, str) else content
        except Exception:
            parsed = None

        # required_keys
        for key in spec.get("required_keys", []):
            if parsed is None or not isinstance(parsed, dict) or key not in parsed:
                return False

        # forbidden_keys
        for key in spec.get("forbidden_keys", []):
            if parsed is not None and isinstance(parsed, dict) and key in parsed:
                return False

        # contains_all — all strings must appear
        for phrase in spec.get("contains_all", []):
            if phrase.lower() not in content.lower():
                return False

        # contains_any — at least one must appear
        contains_any = spec.get("contains_any", [])
        if contains_any and not any(p.lower() in content.lower() for p in contains_any):
            return False

        # length bounds
        if "min_length" in spec and len(content) < spec["min_length"]:
            return False
        if "max_length" in spec and len(content) > spec["max_length"]:
            return False

        return True

    def _get_content(self, response: Any) -> str:
        if hasattr(response, "text"):
            return response.text
        if hasattr(response, "content"):
            return response.content.decode()
        if isinstance(response, (dict, list)):
            return json.dumps(response)
        return str(response)

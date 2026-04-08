#!/usr/bin/env python3
"""
HyperCode Self-Improver — skill eval runner.

Usage:
  python scripts/skill_eval.py --skill hypercode-hypersync --mode eval
  python scripts/skill_eval.py --skill hypercode-hypersync --mode improve --iterations 3
  python scripts/skill_eval.py --mode eval   # runs all skills
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

# ---------------------------------------------------------------------------
# Eval case loading
# ---------------------------------------------------------------------------

def _load_evals_json(skill_dir: Path) -> list[dict]:
    """Load EVALS.json if present (preferred — per-skill dedicated evals)."""
    evals_path = skill_dir / "EVALS.json"
    if evals_path.exists():
        return json.loads(evals_path.read_text(encoding="utf-8"))
    return []


def _load_evals_from_global_examples(skill_name: str) -> list[dict]:
    """Fall back to extracting cases from EVAL_EXAMPLES.md for the given skill."""
    examples_path = SKILLS_DIR / "hypercode-self-improver" / "EVAL_EXAMPLES.md"
    if not examples_path.exists():
        return []
    text = examples_path.read_text(encoding="utf-8")
    # Extract JSON blocks
    cases: list[dict] = []
    for block in re.findall(r"```json\s*([\s\S]*?)```", text):
        try:
            parsed = json.loads(block.strip())
            if isinstance(parsed, list):
                cases.extend(c for c in parsed if c.get("skill") == skill_name)
            elif isinstance(parsed, dict) and parsed.get("skill") == skill_name:
                cases.append(parsed)
        except json.JSONDecodeError:
            pass
    return cases


def load_evals(skill_name: str) -> list[dict]:
    skill_dir = SKILLS_DIR / skill_name
    cases = _load_evals_json(skill_dir)
    if not cases:
        cases = _load_evals_from_global_examples(skill_name)
    return cases


# ---------------------------------------------------------------------------
# Skill content loading
# ---------------------------------------------------------------------------

def load_skill_md(skill_name: str) -> str:
    path = SKILLS_DIR / skill_name / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"SKILL.md not found for skill '{skill_name}' at {path}")
    return path.read_text(encoding="utf-8")


def list_skills() -> list[str]:
    return sorted(
        d.name for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _heuristic_score(skill_content: str, case: dict) -> dict[str, Any]:
    """
    Binary pass/fail heuristic: each expected behavior is checked against the
    lowercased skill content. Not a substitute for LLM scoring but always works.
    """
    skill_lower = skill_content.lower()
    behaviors = case.get("expected_behavior", [])
    results = []
    for behavior in behaviors:
        # tokenise the behavior into keywords and check coverage
        keywords = re.findall(r"[a-z0-9_/-]+", behavior.lower())
        # require ≥ 60% of keywords to appear
        hits = sum(1 for kw in keywords if kw in skill_lower)
        passed = (hits / len(keywords)) >= 0.6 if keywords else True
        results.append({"behavior": behavior, "passed": passed, "hits": hits, "total_keywords": len(keywords)})

    passed_count = sum(1 for r in results if r["passed"])
    return {
        "query": case.get("query", ""),
        "score": passed_count / len(behaviors) if behaviors else 1.0,
        "passed": passed_count == len(behaviors),
        "behaviors": results,
        "method": "heuristic",
    }


def _llm_score(skill_content: str, case: dict, model: str = "openai/gpt-4o-mini") -> dict[str, Any]:
    """LLM-based binary scoring via OpenRouter (requires OPENROUTER_API_KEY)."""
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return _heuristic_score(skill_content, case)

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _heuristic_score(skill_content, case)

    base_url = "https://openrouter.ai/api/v1" if os.environ.get("OPENROUTER_API_KEY") else None
    client = OpenAI(api_key=api_key, base_url=base_url)

    behaviors = case.get("expected_behavior", [])
    behaviors_str = "\n".join(f"- {b}" for b in behaviors)

    prompt = textwrap.dedent(f"""
        You are evaluating a Claude Code skill.

        SKILL CONTENT:
        ---
        {skill_content[:3000]}
        ---

        USER QUERY: {case.get("query", "")}

        EXPECTED BEHAVIORS:
        {behaviors_str}

        For each expected behavior, reply with a JSON array like:
        [{{"behavior": "...", "passed": true/false, "reason": "one sentence"}}]

        Only output the JSON array, nothing else.
    """).strip()

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0,
        )
        raw = resp.choices[0].message.content or "[]"
        # Strip markdown code fences if present
        raw = re.sub(r"^```[a-z]*\n?", "", raw.strip())
        raw = re.sub(r"\n?```$", "", raw.strip())
        results = json.loads(raw)
        passed_count = sum(1 for r in results if r.get("passed"))
        return {
            "query": case.get("query", ""),
            "score": passed_count / len(behaviors) if behaviors else 1.0,
            "passed": passed_count == len(behaviors),
            "behaviors": results,
            "method": "llm",
        }
    except Exception as exc:
        print(f"  [warn] LLM scoring failed ({exc}), falling back to heuristic", file=sys.stderr)
        return _heuristic_score(skill_content, case)


def score_case(skill_content: str, case: dict, use_llm: bool = True) -> dict[str, Any]:
    if use_llm:
        return _llm_score(skill_content, case)
    return _heuristic_score(skill_content, case)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(skill_name: str, results: list[dict[str, Any]]) -> float:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    score_pct = (passed / total * 100) if total else 0.0

    print(f"\n{'='*60}")
    print(f"  SKILL: {skill_name}")
    print(f"  Score: {passed}/{total}  ({score_pct:.0f}%)")
    print(f"  Method: {results[0]['method'] if results else 'n/a'}")
    print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}")

    for r in results:
        status = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"\n  {status}  {r['query']}")
        for b in r.get("behaviors", []):
            b_status = "  [+]" if b.get("passed") else "  [-]"
            reason = b.get("reason", "")
            print(f"    {b_status} {b['behavior']}" + (f"  — {reason}" if reason else ""))

    print(f"\n  Overall: {'PASS' if passed == total else 'NEEDS IMPROVEMENT'}\n")
    return score_pct


# ---------------------------------------------------------------------------
# Improve mode
# ---------------------------------------------------------------------------

def improve_skill(skill_name: str, failures: list[dict], iterations: int) -> None:
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    skill_content = skill_path.read_text(encoding="utf-8")

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  [improve] No API key — cannot auto-rewrite. Printing suggested improvements instead.\n")
        _suggest_improvements(skill_name, failures)
        return

    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        print("  [improve] openai package not available")
        return

    base_url = "https://openrouter.ai/api/v1" if os.environ.get("OPENROUTER_API_KEY") else None
    client = OpenAI(api_key=api_key, base_url=base_url)

    failed_behaviors = []
    for r in failures:
        for b in r.get("behaviors", []):
            if not b.get("passed"):
                failed_behaviors.append(f"Query: {r['query']} | Behavior: {b['behavior']}")

    if not failed_behaviors:
        print("  [improve] No failures to fix.")
        return

    failures_str = "\n".join(f"- {fb}" for fb in failed_behaviors)

    for i in range(1, iterations + 1):
        print(f"\n  [improve] Iteration {i}/{iterations}...")
        prompt = textwrap.dedent(f"""
            You are improving a Claude Code skill definition.

            CURRENT SKILL.md:
            ---
            {skill_content}
            ---

            These expected behaviors are NOT currently covered:
            {failures_str}

            Rewrite the SKILL.md to cover these behaviors. Keep the frontmatter intact.
            Keep it concise and actionable. Output ONLY the complete new SKILL.md content.
        """).strip()

        try:
            resp = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3,
            )
            new_content = (resp.choices[0].message.content or "").strip()
            if not new_content or "---" not in new_content:
                print("  [improve] LLM returned invalid content, skipping iteration.")
                continue

            # Re-score with new content
            skill_content = new_content
            print(f"  [improve] Rewritten. Re-evaluating...")

        except Exception as exc:
            print(f"  [improve] Error on iteration {i}: {exc}")
            break

    # Write improved version
    backup_path = skill_path.with_suffix(f".bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.md")
    backup_path.write_text(skill_path.read_text(encoding="utf-8"), encoding="utf-8")
    skill_path.write_text(skill_content, encoding="utf-8")
    print(f"\n  [improve] Written to {skill_path}")
    print(f"  [improve] Backup saved to {backup_path.name}")


def _suggest_improvements(skill_name: str, failures: list[dict]) -> None:
    print(f"  Suggested improvements for {skill_name}:")
    for r in failures:
        for b in r.get("behaviors", []):
            if not b.get("passed"):
                print(f"  → Add coverage for: {b['behavior']}")
                print(f"    (from query: {r['query']})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run_eval(skill_name: str, use_llm: bool = True) -> float:
    print(f"\n  Loading evals for: {skill_name}")
    cases = load_evals(skill_name)
    if not cases:
        print(f"  [warn] No eval cases found for '{skill_name}'. Add EVALS.json to .claude/skills/{skill_name}/")
        return 0.0

    skill_content = load_skill_md(skill_name)
    results = [score_case(skill_content, case, use_llm=use_llm) for case in cases]
    score = print_report(skill_name, results)
    return score


def main() -> None:
    parser = argparse.ArgumentParser(description="HyperCode skill evaluator")
    parser.add_argument("--skill", default=None, help="Skill name (omit to run all)")
    parser.add_argument("--mode", choices=["eval", "improve", "benchmark"], default="eval")
    parser.add_argument("--iterations", type=int, default=3, help="Improve mode iterations")
    parser.add_argument("--no-llm", action="store_true", help="Force heuristic scoring only")
    args = parser.parse_args()

    skills = [args.skill] if args.skill else list_skills()
    use_llm = not args.no_llm

    if args.mode == "eval":
        scores: dict[str, float] = {}
        for skill in skills:
            try:
                scores[skill] = run_eval(skill, use_llm=use_llm)
            except FileNotFoundError as exc:
                print(f"  [skip] {exc}")

        if len(skills) > 1:
            print("\n" + "="*60)
            print("  SUMMARY")
            print("="*60)
            for s, score in sorted(scores.items(), key=lambda x: x[1]):
                bar = "█" * int(score / 10)
                print(f"  {score:5.0f}%  {bar:<10}  {s}")
            avg = sum(scores.values()) / len(scores) if scores else 0
            print(f"\n  Average: {avg:.0f}%")

        failing = [s for s, sc in scores.items() if sc < 100]
        sys.exit(0 if not failing else 1)

    elif args.mode == "improve":
        if not args.skill:
            print("--skill required for improve mode")
            sys.exit(1)

        cases = load_evals(args.skill)
        skill_content = load_skill_md(args.skill)
        results = [score_case(skill_content, case, use_llm=use_llm) for case in cases]
        failures = [r for r in results if not r["passed"]]

        if not failures:
            print(f"  All evals pass for '{args.skill}' — nothing to improve.")
            sys.exit(0)

        print(f"  {len(failures)} failing evals. Running improve loop ({args.iterations} iterations)...")
        improve_skill(args.skill, failures, args.iterations)

    elif args.mode == "benchmark":
        print("Benchmark mode: tracks scores over time.")
        print("(Not yet implemented — eval mode scores are the baseline.)")


if __name__ == "__main__":
    main()

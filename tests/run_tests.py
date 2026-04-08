#!/usr/bin/env python3
"""
HyperCode Observability & Resilience Test Runner
Executes full test suite: unit, chaos, stress, longevity
"""

import subprocess
import sys
import argparse

def run_command(cmd, description, timeout=None):
    """Run a shell command and report results"""
    print(f"\n{'='*70}")
    print(f"▶ {description}")
    print(f"{'='*70}")
    print(f"$ {cmd}\n")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            timeout=timeout,
            cwd=".",
        )
        if result.returncode == 0:
            print(f"✓ {description} passed")
            return True
        else:
            print(f"✗ {description} failed (exit code {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ {description} timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"✗ {description} error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Run HyperCode observability tests"
    )
    parser.add_argument(
        "--suite",
        choices=["unit", "chaos", "stress", "soak", "redteam", "all"],
        default="unit",
        help="Test suite to run"
    )
    parser.add_argument(
        "--soak-hours",
        type=int,
        default=1,  # Default to 1 hour for testing (set to 72 for production)
        help="Duration of soak test in hours"
    )
    
    args = parser.parse_args()
    
    results = {}
    
    # ========================================================================
    # UNIT TESTS: Health checks, basic contracts
    # ========================================================================
    if args.suite in ["unit", "all"]:
        print("\n" + "="*70)
        print("UNIT TESTS: Health, Prometheus, Loki")
        print("="*70)
        
        tests = [
            ("pytest tests/test_agent_observability.py::test_services_health -v -s", "Services Health Checks"),
            ("pytest tests/test_agent_observability.py::test_prometheus_scrape_targets -v -s", "Prometheus Scrape Targets"),
            ("pytest tests/test_agent_observability.py::test_loki_log_ingestion -v -s", "Loki Log Ingestion"),
            ("pytest tests/test_agent_observability.py::test_latency_slo_hypercode_core -v -s", "Latency SLO Check"),
            ("pytest tests/test_agent_observability.py::test_error_rate_slo -v -s", "Error Rate SLO Check"),
        ]
        
        results["unit"] = []
        for cmd, desc in tests:
            results["unit"].append(run_command(cmd, desc, timeout=60))
    
    # ========================================================================
    # CHAOS TESTS: Failure injection
    # ========================================================================
    if args.suite in ["chaos", "all"]:
        print("\n" + "="*70)
        print("CHAOS TESTS: Failure Injection & Recovery")
        print("="*70)
        
        tests = [
            ("pytest tests/test_agent_observability.py::test_redis_failure_recovery -v -s", "Redis Failure & Recovery"),
            ("pytest tests/test_agent_observability.py::test_postgres_failure_recovery -v -s", "PostgreSQL Failure & Recovery"),
            ("pytest tests/test_agent_observability.py::test_core_service_restart -v -s", "Core Service Restart"),
            ("pytest tests/test_agent_observability.py::test_cascading_failure_agent_interdependency -v -s", "Cascading Failure"),
        ]
        
        results["chaos"] = []
        for cmd, desc in tests:
            results["chaos"].append(run_command(cmd, desc, timeout=120))
    
    # ========================================================================
    # STRESS TESTS: Load & resource limits
    # ========================================================================
    if args.suite in ["stress", "all"]:
        print("\n" + "="*70)
        print("STRESS TESTS: High Load & Memory Leaks")
        print("="*70)
        
        tests = [
            ("pytest tests/test_agent_observability.py::test_concurrent_load_100_req_sec -v -s", "100 req/sec Load Test"),
            ("pytest tests/test_agent_observability.py::test_memory_leak_detection -v -s", "Memory Leak Detection"),
        ]
        
        results["stress"] = []
        for cmd, desc in tests:
            results["stress"].append(run_command(cmd, desc, timeout=600))
    
    # ========================================================================
    # SOAK TEST: 72-hour (or specified duration) uptime
    # ========================================================================
    if args.suite in ["soak", "all"]:
        print("\n" + "="*70)
        print(f"SOAK TEST: {args.soak_hours}-hour Endurance (THIS MAY TAKE A WHILE)")
        print("="*70)
        
        timeout_seconds = args.soak_hours * 3600 + 300  # +5min buffer
        cmd = "pytest tests/test_agent_observability.py::test_72h_uptime_soak -v -s -m slow"
        results["soak"] = [run_command(cmd, "Endurance Soak", timeout=timeout_seconds)]
    
    # ========================================================================
    # RED-TEAM TESTS: Security & adversarial
    # ========================================================================
    if args.suite in ["redteam", "all"]:
        print("\n" + "="*70)
        print("RED-TEAM TESTS: Security & Adversarial")
        print("="*70)
        
        tests = [
            ("pytest tests/test_agent_observability.py::test_prompt_injection_defense -v -s", "Prompt Injection Defense"),
            ("pytest tests/test_agent_observability.py::test_resource_exhaustion_protection -v -s", "Resource Exhaustion Protection"),
        ]
        
        results["redteam"] = []
        for cmd, desc in tests:
            results["redteam"].append(run_command(cmd, desc, timeout=120))
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total_tests = sum(len(v) for v in results.values() if isinstance(v, list))
    total_passed = sum(sum(1 for t in v if t) for v in results.values() if isinstance(v, list))
    
    for suite_name, suite_results in results.items():
        if isinstance(suite_results, list):
            passed = sum(1 for t in suite_results if t)
            print(f"{suite_name.upper():12} {passed}/{len(suite_results)} passed")
    
    print(f"\nTOTAL: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total_tests - total_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

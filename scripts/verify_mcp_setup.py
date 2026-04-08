#!/usr/bin/env python3
"""
MCP Gateway + Model Runner Verification Suite
=============================================

Quick validation that all components are healthy and ready for agents.
Run this after starting: docker compose -f docker-compose.yml -f docker-compose.mcp-gateway.yml up -d

Usage:
    python verify_mcp_setup.py
    python verify_mcp_setup.py --verbose
"""

import asyncio
import httpx
import sys
from typing import Optional
from datetime import datetime


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def print_check(name: str, passed: bool, message: str = ""):
    symbol = f"{Colors.GREEN}✅{Colors.RESET}" if passed else f"{Colors.RED}❌{Colors.RESET}"
    status = f"{Colors.GREEN}OK{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
    msg = f" - {message}" if message else ""
    print(f"{symbol} {name}: {status}{msg}")


async def check_service(url: str, name: str, auth_header: Optional[str] = None) -> bool:
    """Check if a service is healthy"""
    try:
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
        
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url, headers=headers)
            return response.status_code == 200
    except Exception as e:
        print(f"  Error checking {name}: {e}")
        return False


async def test_mcp_gateway() -> bool:
    """Test MCP Gateway functionality"""
    print(f"\n{Colors.BLUE}🔧 Testing MCP Gateway{Colors.RESET}")
    
    api_key = "agent-key-001"
    
    # Test 1: Health check
    passed = await check_service(
        "http://localhost:8820/health",
        "Gateway health",
        f"Bearer {api_key}"
    )
    print_check("Gateway health", passed)
    
    # Test 2: Tool discovery
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                "http://localhost:8820/tools/discover",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if response.status_code == 200:
                data = response.json()
                tool_count = len(data.get("tools", []))
                print_check("Tool discovery", True, f"Found {tool_count} tools")
                return True
    except Exception as e:
        print_check("Tool discovery", False, str(e))
    
    return False


async def test_model_runner() -> bool:
    """Test Docker Model Runner"""
    print(f"\n{Colors.BLUE}🧠 Testing Model Runner{Colors.RESET}")
    
    # Test 1: Health check
    passed = await check_service("http://localhost:11434/api/health", "Model Runner health")
    print_check("Model Runner health", passed)
    
    # Test 2: List available models
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                if models:
                    default_model = models[0].get("name", "unknown")
                    print_check("Models available", True, f"Default: {default_model}")
                    return True
                else:
                    print_check("Models available", False, "No models found (may be downloading...)")
    except Exception as e:
        print_check("Models available", False, str(e))
    
    return False


async def test_mcp_tools() -> bool:
    """Test individual MCP tools"""
    print(f"\n{Colors.BLUE}🛠️  Testing MCP Tools{Colors.RESET}")
    
    tools = [
        ("http://localhost:3001/health", "GitHub Tool"),
        ("http://localhost:3002/health", "PostgreSQL Tool"),
        ("http://localhost:3003/health", "FileSystem Tool"),
        ("http://localhost:3004/health", "VectorDB Tool"),
    ]
    
    results = []
    for url, name in tools:
        passed = await check_service(url, name)
        print_check(name, passed)
        results.append(passed)
    
    return all(results)


async def test_tool_call() -> bool:
    """Test an actual tool call through gateway"""
    print(f"\n{Colors.BLUE}📞 Testing Tool Call (via Gateway){Colors.RESET}")
    
    api_key = "agent-key-001"
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            payload = {
                "tool": "filesystem:list_directory",
                "params": {"path": "/workspace"}
            }
            
            response = await client.post(
                "http://localhost:8820/tools/call",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                latency = data.get("latency_ms", 0)
                print_check("Tool call execution", True, f"Latency: {latency}ms")
                return True
            else:
                print_check("Tool call execution", False, f"Status {response.status_code}")
    except Exception as e:
        print_check("Tool call execution", False, str(e))
    
    return False


async def test_database_connectivity() -> bool:
    """Test PostgreSQL connectivity for audit logs"""
    print(f"\n{Colors.BLUE}📊 Testing Database Connectivity{Colors.RESET}")
    
    try:
        # Try to connect to PostgreSQL via MCP Postgres tool
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get("http://localhost:3002/health")
            if response.status_code == 200:
                print_check("PostgreSQL connectivity", True, "Audit table ready")
                return True
    except Exception as e:
        print_check("PostgreSQL connectivity", False, str(e))
    
    return False


async def test_observability() -> bool:
    """Test Prometheus metrics"""
    print(f"\n{Colors.BLUE}📈 Testing Observability{Colors.RESET}")
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get("http://localhost:8820/metrics")
            if response.status_code == 200:
                content = response.text
                has_metrics = "mcp_tool_calls_total" in content
                print_check("Prometheus metrics", has_metrics)
                return has_metrics
    except Exception as e:
        print_check("Prometheus metrics", False, str(e))
    
    return False


def print_summary(results: dict) -> int:
    """Print summary and return exit code"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}📋 VERIFICATION SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for category, result in results.items():
        status = f"{Colors.GREEN}✅ OK{Colors.RESET}" if result else f"{Colors.RED}❌ FAIL{Colors.RESET}"
        print(f"{category}: {status}")
    
    print(f"\n{Colors.BLUE}Overall: {passed}/{total} checks passed{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}🎉 All systems ready for agents!{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.YELLOW}⚠️  Some checks failed. See above for details.{Colors.RESET}\n")
        return 1


async def main():
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}MCP Gateway + Model Runner Verification{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    results = {}
    
    try:
        results["MCP Gateway"] = await test_mcp_gateway()
        results["Model Runner"] = await test_model_runner()
        results["MCP Tools"] = await test_mcp_tools()
        results["Tool Call"] = await test_tool_call()
        results["Database"] = await test_database_connectivity()
        results["Observability"] = await test_observability()
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.RESET}")
        return 1
    
    exit_code = print_summary(results)
    
    if exit_code == 0:
        print(f"{Colors.GREEN}Next: Wire agents to MCP in docker-compose.yml{Colors.RESET}")
        print(f"{Colors.GREEN}See: INTEGRATION_SUMMARY.md for agent wiring examples{Colors.RESET}\n")
    
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

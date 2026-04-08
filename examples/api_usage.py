"""
Example: Using HyperCode Agent Crew API
"""
import httpx
import json
import time

ORCHESTRATOR_URL = "http://localhost:8080"

def check_health():
    """Check if orchestrator is healthy"""
    response = httpx.get(f"{ORCHESTRATOR_URL}/health")
    print(f"Health Check: {response.json()}")

def get_agent_status():
    """Get status of all agents"""
    response = httpx.get(f"{ORCHESTRATOR_URL}/agents/status")
    agents = response.json()
    
    print("\n🤖 Agent Status:")
    print("-" * 50)
    for agent in agents:
        status_emoji = "✅" if agent["status"] == "online" else "❌"
        print(f"{status_emoji} {agent['agent']}: {agent['status']}")

def plan_shopping_cart_feature():
    """Example: Plan a shopping cart feature"""
    print("\n📋 Planning Shopping Cart Feature...")
    print("-" * 50)
    
    response = httpx.post(
        f"{ORCHESTRATOR_URL}/plan",
        json={
            "task": "Create a shopping cart feature with add/remove items, quantity adjustment, and checkout button",
            "context": {
                "tech_stack": "Next.js, FastAPI, PostgreSQL",
                "requirements": [
                    "User can add items to cart",
                    "User can adjust quantities",
                    "Show total price",
                    "Persist cart in database",
                    "Responsive design"
                ]
            },
            "priority": "high"
        },
        timeout=60.0
    )
    
    result = response.json()
    print(f"\n✅ Task Created: {result['task_id']}")
    print(f"Status: {result['status']}")
    print(f"Assigned Agents: {', '.join(result['assigned_agents'])}")
    
    return result['task_id']

def check_task_status(task_id):
    """Check status of a task"""
    response = httpx.get(f"{ORCHESTRATOR_URL}/task/{task_id}")
    result = response.json()
    
    print(f"\n📊 Task Status: {task_id}")
    print("-" * 50)
    print(f"Status: {result.get('status')}")
    if 'plan' in result:
        try:
            plan = json.loads(result['plan'])
            print(f"Tasks: {len(plan.get('tasks', []))}")
        except:
            pass

def start_security_audit():
    """Example: Start a security audit workflow"""
    print("\n🔒 Starting Security Audit...")
    print("-" * 50)
    
    response = httpx.post(
        f"{ORCHESTRATOR_URL}/workflow/security_audit",
        json={
            "workflow_type": "security_audit",
            "description": "Comprehensive security audit of authentication system",
            "requirements": {
                "scope": ["authentication", "authorization", "data_encryption"],
                "compliance": ["OWASP", "GDPR"]
            }
        }
    )
    
    result = response.json()
    print(f"✅ Workflow Started: {result['workflow_id']}")
    print(f"Agents Involved: {', '.join(result['agents'])}")

def execute_frontend_task():
    """Example: Direct frontend task execution"""
    print("\n🎨 Executing Frontend Task...")
    print("-" * 50)
    
    response = httpx.post(
        f"{ORCHESTRATOR_URL}/agent/frontend-specialist/execute",
        json={
            "agent": "frontend-specialist",
            "message": "Create a reusable ProductCard component with image, title, price, and add-to-cart button. Use Tailwind CSS for styling.",
            "context": {
                "framework": "React",
                "styling": "Tailwind CSS"
            }
        },
        timeout=60.0
    )
    
    result = response.json()
    print(f"Status: {result['status']}")
    if result['status'] == 'completed':
        print(f"\n📝 Result:\n{result['result'][:500]}...")  # First 500 chars

def main():
    print("=" * 60)
    print("  HyperCode Agent Crew - API Examples")
    print("=" * 60)
    
    try:
        # 1. Health check
        check_health()
        
        # 2. Get agent status
        get_agent_status()
        
        # 3. Plan a feature
        task_id = plan_shopping_cart_feature()
        
        # Wait a bit for processing
        time.sleep(3)
        
        # 4. Check task status
        check_task_status(task_id)
        
        # 5. Start a security audit
        start_security_audit()
        
        # 6. Execute a frontend task
        execute_frontend_task()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed!")
        print("=" * 60)
        
    except httpx.ConnectError:
        print("\n❌ Error: Cannot connect to orchestrator")
        print("Make sure agents are running: make up")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()

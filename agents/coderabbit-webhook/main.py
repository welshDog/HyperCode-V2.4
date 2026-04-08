"""
CodeRabbit Webhook Agent - PR Code Review Automation

Receives CodeRabbit review webhooks and coordinates agent execution.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import httpx

logger = logging.getLogger(__name__)

# Configuration
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://crew-orchestrator:8080")
CODERABBIT_WEBHOOK_SECRET = os.getenv("CODERABBIT_WEBHOOK_SECRET", "")
CORE_URL = os.getenv("CORE_URL", "http://hypercode-core:8000")

app = FastAPI(
    title="CodeRabbit Webhook Agent",
    version="0.1.0",
    description="Receives CodeRabbit PR reviews and coordinates auto-fix execution"
)


class CodeRabbitReview(BaseModel):
    """CodeRabbit review webhook payload"""
    pr_number: int
    repo: str
    branch: str
    review_comments: List[str]
    critical_issues: int
    suggestions: List[Dict[str, Any]]


class AutoFixTask(BaseModel):
    """Task to execute for auto-fixing"""
    agent_type: str  # "backend-specialist", "frontend-specialist", etc.
    task_description: str
    pr_number: int
    repo: str
    priority: str = "medium"  # low, medium, high, critical


@app.on_event("startup")
async def startup():
    logger.info("CodeRabbit Webhook Agent started on port 8000")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "coderabbit-webhook-agent",
        "version": "0.1.0"
    }


@app.get("/capabilities")
async def capabilities():
    return {
        "name": "coderabbit-webhook-agent",
        "version": "0.1.0",
        "capabilities": [
            "Receive CodeRabbit PR reviews",
            "Extract action items",
            "Coordinate agent auto-fixes",
            "Update PR with results",
        ],
        "integrations": [
            "CodeRabbit",
            "crew-orchestrator",
            "GitHub"
        ]
    }


@app.post("/webhook/coderabbit")
async def receive_coderabbit_webhook(request: Request):
    """
    Receive CodeRabbit review webhook.
    
    Expected format:
    {
        "event": "review_completed",
        "pr": {
            "number": 123,
            "repo": "owner/repo",
            "branch": "feature/xyz",
            "html_url": "https://github.com/..."
        },
        "review": {
            "summary": "...",
            "critical_issues": [...],
            "suggestions": [...],
            "comments": [...]
        }
    }
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Validate secret (optional)
    if CODERABBIT_WEBHOOK_SECRET:
        header_secret = request.headers.get("X-CodeRabbit-Secret")
        if header_secret != CODERABBIT_WEBHOOK_SECRET:
            logger.warning("Invalid CodeRabbit webhook secret")
            raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Extract relevant info
    event_type = payload.get("event")
    if event_type != "review_completed":
        return {"status": "ignored", "reason": f"Event type: {event_type}"}
    
    pr_data = payload.get("pr", {})
    review_data = payload.get("review", {})
    
    pr_number = pr_data.get("number")
    repo = pr_data.get("repo")
    branch = pr_data.get("branch")
    
    if not all([pr_number, repo, branch]):
        raise HTTPException(status_code=400, detail="Missing PR data")
    
    logger.info(f"CodeRabbit review received for {repo}#{pr_number}")
    
    # Parse review and generate tasks
    critical_issues = review_data.get("critical_issues", [])
    suggestions = review_data.get("suggestions", [])
    comments = review_data.get("comments", [])
    
    tasks = await parse_review_and_generate_tasks(
        pr_number=pr_number,
        repo=repo,
        branch=branch,
        critical_issues=critical_issues,
        suggestions=suggestions,
        comments=comments
    )
    
    logger.info(f"Generated {len(tasks)} auto-fix tasks from review")
    
    # Submit tasks to orchestrator
    results = await submit_tasks_to_orchestrator(tasks)
    
    return {
        "status": "accepted",
        "pr": pr_number,
        "repo": repo,
        "tasks_generated": len(tasks),
        "tasks_submitted": len(results),
        "results": results
    }


@app.post("/webhook/github")
async def receive_github_webhook(request: Request):
    """
    Receive GitHub webhook for PR events.
    Triggers CodeRabbit review request.
    """
    try:
        payload = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    action = payload.get("action")
    if action == "opened":
        pr = payload.get("pull_request", {})
        pr_number = pr.get("number")
        repo = payload.get("repository", {}).get("full_name")
        
        logger.info(f"GitHub PR opened: {repo}#{pr_number}")
        
        # Trigger CodeRabbit review (external API call)
        # await trigger_coderabbit_review(repo, pr_number)
        
        return {
            "status": "acknowledged",
            "pr": pr_number,
            "repo": repo
        }
    
    return {"status": "ignored"}


@app.post("/execute-fix")
async def execute_fix(task: AutoFixTask):
    """
    Execute a single auto-fix task.
    
    Called by orchestrator after coordinating agents.
    """
    logger.info(f"Executing fix task: {task.task_description}")
    
    # This would be called by crew-orchestrator
    # to execute the actual fix in the codebase
    
    return {
        "status": "executing",
        "task": task.task_description,
        "pr": task.pr_number
    }


@app.get("/status/{pr_number}")
async def get_fix_status(pr_number: int):
    """
    Get status of fixes for a specific PR.
    """
    # Query orchestrator for task status
    return {
        "pr_number": pr_number,
        "tasks": [],
        "completed": 0,
        "in_progress": 0,
        "failed": 0
    }


async def parse_review_and_generate_tasks(
    pr_number: int,
    repo: str,
    branch: str,
    critical_issues: List[Dict[str, Any]],
    suggestions: List[Dict[str, Any]],
    comments: List[str],
) -> List[AutoFixTask]:
    """
    Parse CodeRabbit review and generate auto-fix tasks.
    
    Returns list of tasks to execute.
    """
    tasks = []
    
    # Categorize by agent type
    backend_issues = []
    frontend_issues = []
    database_issues = []
    security_issues = []
    
    # Analyze critical issues
    for issue in critical_issues:
        issue_type = issue.get("type", "").lower()
        # CodeRabbit may send either "description" or "message" — normalise both
        description = (issue.get("description") or issue.get("message") or "").lower()

        if "database" in issue_type or "schema" in description:
            database_issues.append(issue)
        elif "security" in issue_type or "vulnerability" in description or "injection" in description:
            security_issues.append(issue)
        elif "api" in issue_type or "backend" in description:
            backend_issues.append(issue)
        elif "ui" in issue_type or "frontend" in description:
            frontend_issues.append(issue)
        else:
            # Default unclassified critical issues to backend
            backend_issues.append(issue)
    
    # Analyze suggestions
    for suggestion in suggestions:
        category = suggestion.get("category", "").lower()
        if "performance" in category:
            backend_issues.append(suggestion)
        elif "style" in category:
            frontend_issues.append(suggestion)
    
    # Generate tasks
    if backend_issues:
        tasks.append(AutoFixTask(
            agent_type="backend-specialist",
            task_description=f"Fix {len(backend_issues)} backend issues in PR#{pr_number}",
            pr_number=pr_number,
            repo=repo,
            priority="critical" if len(backend_issues) > 3 else "high"
        ))
    
    if frontend_issues:
        tasks.append(AutoFixTask(
            agent_type="frontend-specialist",
            task_description=f"Fix {len(frontend_issues)} frontend issues in PR#{pr_number}",
            pr_number=pr_number,
            repo=repo,
            priority="high"
        ))
    
    if database_issues:
        tasks.append(AutoFixTask(
            agent_type="database-architect",
            task_description=f"Review {len(database_issues)} database changes in PR#{pr_number}",
            pr_number=pr_number,
            repo=repo,
            priority="critical"
        ))
    
    if security_issues:
        tasks.append(AutoFixTask(
            agent_type="security-engineer",
            task_description=f"Audit {len(security_issues)} security findings in PR#{pr_number}",
            pr_number=pr_number,
            repo=repo,
            priority="critical"
        ))
    
    logger.info(f"Generated {len(tasks)} tasks from {len(critical_issues)} issues")
    return tasks


async def submit_tasks_to_orchestrator(tasks: List[AutoFixTask]) -> List[Dict[str, Any]]:
    """
    Submit tasks to crew-orchestrator for execution.
    """
    results = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for task in tasks:
                try:
                    response = await client.post(
                        f"{ORCHESTRATOR_URL}/workflow/execute",
                        json={
                            "agent_type": task.agent_type,
                            "task": task.task_description,
                            "priority": task.priority,
                            "metadata": {
                                "pr_number": task.pr_number,
                                "repo": task.repo,
                                "source": "coderabbit-webhook"
                            }
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        results.append({
                            "task": task.task_description,
                            "status": "submitted",
                            "workflow_id": result.get("workflow_id")
                        })
                        logger.info(f"Task submitted: {task.task_description}")
                    else:
                        logger.error(f"Failed to submit task: {response.status_code}")
                        results.append({
                            "task": task.task_description,
                            "status": "failed",
                            "error": f"HTTP {response.status_code}"
                        })
                
                except Exception as e:
                    logger.error(f"Error submitting task: {e}")
                    results.append({
                        "task": task.task_description,
                        "status": "error",
                        "error": str(e)
                    })
    
    except Exception as e:
        logger.error(f"Failed to connect to orchestrator: {e}")
    
    return results


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting CodeRabbit Webhook Agent on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

"""
Mission Ledger Client — HyperCode V3

Persistent, auditable record of all agent work.
Every mission has: goal, builder, branch, PR, proof, approval state, rollback route, next action.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from supabase import create_client, Client


class MissionLedger:
    """Client for interacting with the Mission Ledger in Supabase."""
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """
        Initialize the Mission Ledger client.
        
        Args:
            supabase_url: Supabase project URL (default: SUPABASE_URL env var)
            supabase_key: Supabase anon/service key (default: SUPABASE_KEY env var)
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
    
    # ==================== MISSIONS ====================
    
    def create_mission(
        self,
        goal: str,
        builder: str = "claude-code",
        context_pack: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new mission.
        
        Args:
            goal: Clear description of what needs to be done
            builder: Who/what will execute (default: claude-code)
            context_pack: Related issues, acceptance criteria, etc.
            metadata: Additional metadata
            
        Returns:
            Mission record with mission_id
        """
        mission_data = {
            "goal": goal,
            "builder": builder,
            "context_pack": context_pack or {},
            "metadata": metadata or {},
            "status": "pending",
            "next_action": "Review mission plan and approve start"
        }
        
        result = self.client.table("missions").insert(mission_data).execute()
        mission = result.data[0]
        
        # Record event
        self.record_event(mission["mission_id"], "created", {"goal": goal})
        
        return mission
    
    def get_mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Get a mission by ID."""
        result = self.client.table("missions").select("*").eq("mission_id", mission_id).execute()
        return result.data[0] if result.data else None
    
    def update_mission(
        self,
        mission_id: str,
        status: Optional[str] = None,
        branch: Optional[str] = None,
        pr_url: Optional[str] = None,
        pr_number: Optional[int] = None,
        preview_url: Optional[str] = None,
        next_action: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update a mission.
        
        Args:
            mission_id: Mission to update
            status: New status
            branch: Git branch name
            pr_url: Pull request URL
            pr_number: Pull request number
            preview_url: Deployment preview URL
            next_action: Recommended next action
            metadata: Additional metadata to merge
            
        Returns:
            Updated mission record
        """
        update_data = {}
        if status:
            update_data["status"] = status
        if branch:
            update_data["branch"] = branch
        if pr_url:
            update_data["pr_url"] = pr_url
        if pr_number:
            update_data["pr_number"] = pr_number
        if preview_url:
            update_data["preview_url"] = preview_url
        if next_action:
            update_data["next_action"] = next_action
        if metadata:
            # Merge with existing metadata
            existing = self.get_mission(mission_id)
            if existing:
                merged = existing.get("metadata", {})
                merged.update(metadata)
                update_data["metadata"] = merged
        
        result = self.client.table("missions").update(update_data).eq("mission_id", mission_id).execute()
        return result.data[0]
    
    def list_missions(
        self,
        status: Optional[str] = None,
        builder: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List missions with optional filters.
        
        Args:
            status: Filter by status
            builder: Filter by builder
            limit: Max results (default: 50)
            
        Returns:
            List of mission records
        """
        query = self.client.table("missions").select("*").order("created_at", desc=True).limit(limit)
        
        if status:
            query = query.eq("status", status)
        if builder:
            query = query.eq("builder", builder)
        
        result = query.execute()
        return result.data
    
    # ==================== MISSION EVENTS ====================
    
    def record_event(
        self,
        mission_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record a mission event (audit trail).
        
        Args:
            mission_id: Mission this event belongs to
            event_type: Type of event (created, started, task_completed, etc.)
            event_data: Additional event data
            
        Returns:
            Event record
        """
        event = {
            "mission_id": mission_id,
            "event_type": event_type,
            "event_data": event_data or {}
        }
        
        result = self.client.table("mission_events").insert(event).execute()
        return result.data[0]
    
    def get_mission_events(self, mission_id: str) -> List[Dict[str, Any]]:
        """Get all events for a mission."""
        result = self.client.table("mission_events").select("*").eq("mission_id", mission_id).order("created_at", asc=True).execute()
        return result.data
    
    # ==================== MISSION PROOF ====================
    
    def attach_proof(
        self,
        mission_id: str,
        proof_type: str,
        status: str,
        result_json: Optional[Dict[str, Any]] = None,
        artifact_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Attach proof of work to a mission.
        
        Args:
            mission_id: Mission this proof belongs to
            proof_type: Type of proof (lint, tests, security_scan, playwright, deployment, rollback)
            status: Result status (pending, passed, failed, skipped)
            result_json: Detailed results
            artifact_url: URL to artifact (log file, report, etc.)
            
        Returns:
            Proof record
        """
        proof = {
            "mission_id": mission_id,
            "proof_type": proof_type,
            "status": status,
            "result_json": result_json or {},
            "artifact_url": artifact_url
        }
        
        result = self.client.table("mission_proof").insert(proof).execute()
        return result.data[0]
    
    def get_mission_proof(self, mission_id: str) -> List[Dict[str, Any]]:
        """Get all proof for a mission."""
        result = self.client.table("mission_proof").select("*").eq("mission_id", mission_id).order("created_at", asc=True).execute()
        return result.data
    
    def get_mission_with_proof(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a mission with all its proof attached.
        
        Returns:
            Mission record with 'proof' field containing dict of proof_type -> status
        """
        mission = self.get_mission(mission_id)
        if not mission:
            return None
        
        proof_records = self.get_mission_proof(mission_id)
        proof_summary = {p["proof_type"]: p["status"] for p in proof_records}
        
        mission["proof"] = proof_summary
        return mission
    
    # ==================== UTILITY ====================
    
    def start_mission(self, mission_id: str, branch: str) -> Dict[str, Any]:
        """Mark a mission as in_progress and record start event."""
        self.update_mission(mission_id, status="in_progress", branch=branch)
        self.record_event(mission_id, "started", {"branch": branch})
        return self.get_mission(mission_id)
    
    def complete_mission(
        self,
        mission_id: str,
        pr_url: str,
        pr_number: int,
        preview_url: Optional[str] = None,
        next_action: str = "Review PR and approve deployment"
    ) -> Dict[str, Any]:
        """Mark a mission as awaiting_review with PR details."""
        self.update_mission(
            mission_id,
            status="awaiting_review",
            pr_url=pr_url,
            pr_number=pr_number,
            preview_url=preview_url,
            next_action=next_action
        )
        self.record_event(mission_id, "review_requested", {
            "pr_url": pr_url,
            "pr_number": pr_number,
            "preview_url": preview_url
        })
        return self.get_mission(mission_id)
    
    def fail_mission(self, mission_id: str, error: str) -> Dict[str, Any]:
        """Mark a mission as failed with error details."""
        self.update_mission(mission_id, status="failed", next_action="Review failure and decide: retry or rollback")
        self.record_event(mission_id, "failed", {"error": error})
        return self.get_mission(mission_id)


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    # Example: Create and track a mission
    ledger = MissionLedger()
    
    # Create mission
    mission = ledger.create_mission(
        goal="Add secure Vercel preview deployment flow",
        builder="claude-code",
        context_pack={
            "related_issues": ["#123"],
            "acceptance_criteria": [
                "Preview deploys on PR creation",
                "Secure token handling via environment variables",
                "Automatic cleanup on PR close"
            ]
        }
    )
    
    print(f"Created mission: {mission['mission_id']}")
    print(f"Goal: {mission['goal']}")
    print(f"Status: {mission['status']}")
    print(f"Next action: {mission['next_action']}")
    
    # Start mission
    mission = ledger.start_mission(mission['mission_id'], "feat/vercel-preview-flow")
    print(f"\nMission started: {mission['status']}")
    
    # Attach proof (simulated)
    ledger.attach_proof(
        mission['mission_id'],
        proof_type="lint",
        status="passed",
        result_json={"errors": 0, "warnings": 2}
    )
    
    ledger.attach_proof(
        mission['mission_id'],
        proof_type="tests",
        status="passed",
        result_json={"total": 42, "passed": 42, "failed": 0}
    )
    
    # Complete mission
    mission = ledger.complete_mission(
        mission['mission_id'],
        pr_url="https://github.com/welshDog/HyperCode-V2.4/pull/453",
        pr_number=453,
        preview_url="https://hypercode-v2-4-git-feat-vercel-preview-flow.vercel.app"
    )
    
    print(f"\nMission completed: {mission['status']}")
    print(f"PR: #{mission['pr_number']}")
    print(f"Preview: {mission['preview_url']}")
    
    # Get full mission with proof
    full_mission = ledger.get_mission_with_proof(mission['mission_id'])
    print(f"\nProof: {full_mission['proof']}")
    print(f"Next action: {full_mission['next_action']}")

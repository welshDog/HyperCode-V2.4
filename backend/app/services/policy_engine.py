"""
Policy Engine for Track 2: Policy-Aware Crew Orchestrator.

Evaluates agent actions against policy rules and writes tamper-evident audit logs.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

from asyncpg import Pool


class PolicyAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyResult(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    PENDING_APPROVAL = "pending_approval"


@dataclass
class PolicyCheck:
    agent_id: Optional[str]
    task_id: Optional[str]
    action: str
    data_domain: Optional[str]
    details: Optional[Dict[str, Any]] = None


@dataclass
class PolicyDecision:
    result: PolicyResult
    matched_rule_name: Optional[str]
    reason: str


class PolicyEngine:
    """
    Simple policy engine:
      - Loads enabled rules from policy_rules, ordered by priority DESC.
      - Evaluates conditions against the incoming check.
      - Returns the first matching rule's action as the decision.
      - Writes an audit log entry with chained hash.
    """

    def __init__(self, db_pool: Pool):
        self.db_pool = db_pool

    async def evaluate(self, check: PolicyCheck) -> PolicyDecision:
        """
        Evaluate a policy check against all enabled rules.
        Returns the decision from the highest-priority matching rule.
        """
        async with self.db_pool.acquire() as conn:
            # Load rules
            rows = await conn.fetch(
                """
                SELECT id, name, condition, action, priority
                FROM policy_rules
                WHERE enabled = true
                ORDER BY priority DESC;
                """
            )

            # Evaluate conditions
            for row in rows:
                condition: dict = row["condition"]
                if self._matches(condition, check):
                    action = PolicyAction(row["action"])
                    result = self._action_to_result(action)
                    return PolicyDecision(
                        result=result,
                        matched_rule_name=row["name"],
                        reason=f"Matched rule {row['name']} (priority {row['priority']})",
                    )

            # Default: allow if no rule matches
            return PolicyDecision(
                result=PolicyResult.ALLOWED,
                matched_rule_name=None,
                reason="No matching policy rule; default allow",
            )

    def _matches(self, condition: dict, check: PolicyCheck) -> bool:
        """
        Simple condition evaluator.
        Supported ops: eq, ne, in, not_in, exists.
        Condition shape examples:
          {"field": "data_domain", "op": "in", "value": ["users", "token_transactions"]}
          {"field": "action", "op": "eq", "value": "award_tokens"}
          {"field": "agent_id", "op": "exists"}
        """
        field = condition.get("field")
        op = condition.get("op")
        value = condition.get("value")

        # Extract field value from check
        if field == "data_domain":
            field_value = check.data_domain
        elif field == "action":
            field_value = check.action
        elif field == "agent_id":
            field_value = check.agent_id
        elif field == "task_id":
            field_value = check.task_id
        else:
            field_value = None

        if op == "eq":
            return field_value == value
        elif op == "ne":
            return field_value != value
        elif op == "in":
            return field_value in value
        elif op == "not_in":
            return field_value not in value
        elif op == "exists":
            return field_value is not None
        else:
            # Unknown op = no match
            return False

    def _action_to_result(self, action: PolicyAction) -> PolicyResult:
        if action == PolicyAction.ALLOW:
            return PolicyResult.ALLOWED
        elif action == PolicyAction.DENY:
            return PolicyResult.DENIED
        elif action == PolicyAction.REQUIRE_APPROVAL:
            return PolicyResult.PENDING_APPROVAL
        else:
            return PolicyResult.ALLOWED

    async def log_decision(
        self,
        check: PolicyCheck,
        decision: PolicyDecision,
    ) -> None:
        """
        Write a tamper-evident audit log entry.
        hash_prev = hash of the most recent row.
        hash_self = sha256 of (timestamp, agent_id, task_id, action, data_domain, policy_result, hash_prev).
        """
        async with self.db_pool.acquire() as conn:
            # Get last hash
            last_row = await conn.fetchrow(
                """
                SELECT hash_self
                FROM audit_log
                ORDER BY timestamp DESC
                LIMIT 1;
                """
            )
            hash_prev = last_row["hash_self"] if last_row else None

            # Build hash_self
            payload = {
                "timestamp": None,  # will be set by DB
                "agent_id": check.agent_id,
                "task_id": check.task_id,
                "action": check.action,
                "data_domain": check.data_domain,
                "policy_result": decision.result.value,
                "hash_prev": hash_prev,
            }
            payload_json = json.dumps(payload, sort_keys=True)
            hash_self = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

            await conn.execute(
                """
                INSERT INTO audit_log (
                    agent_id, task_id, action, data_domain, policy_result, details, hash_prev, hash_self
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
                """,
                check.agent_id,
                check.task_id,
                check.action,
                check.data_domain,
                decision.result.value,
                json.dumps(check.details) if check.details else None,
                hash_prev,
                hash_self,
            )


async def create_policy_engine(db_pool: Pool) -> PolicyEngine:
    return PolicyEngine(db_pool)

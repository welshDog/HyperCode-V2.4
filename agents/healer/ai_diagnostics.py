"""
AI-Powered Diagnostics for Healer Agent

Uses Claude/Perplexity to analyze symptoms and recommend fixes.
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
import httpx

logger = logging.getLogger(__name__)


class AIDiagnostics:
    """AI-powered root cause analysis and fix recommendations"""
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        perplexity_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self.perplexity_key = perplexity_api_key or os.getenv("PERPLEXITY_API_KEY", "")
        self.anthropic_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
    
    async def diagnose(
        self,
        agent_name: str,
        symptoms: List[str],
        logs: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze symptoms and provide root cause analysis + fix recommendations.
        
        Args:
            agent_name: Name of failing agent
            symptoms: List of observed symptoms
            logs: Optional error logs
            context: Optional additional context
        
        Returns:
            {
                "root_cause": "...",
                "confidence": 0.85,
                "recommended_fix": "...",
                "steps": [...],
                "estimated_resolution_time_minutes": 10,
                "escalate_to_human": False
            }
        """
        
        # Try Claude first (best results)
        if self.anthropic_key:
            return await self._diagnose_with_claude(
                agent_name, symptoms, logs, context
            )
        
        # Fallback to Perplexity
        if self.perplexity_key:
            return await self._diagnose_with_perplexity(
                agent_name, symptoms, logs, context
            )
        
        # Fallback to OpenAI
        if self.openai_key:
            return await self._diagnose_with_openai(
                agent_name, symptoms, logs, context
            )
        
        # No API keys available
        logger.warning("No AI API keys configured for diagnostics")
        return {
            "root_cause": "Unknown (AI diagnostics unavailable)",
            "confidence": 0.0,
            "recommended_fix": "Manual investigation required",
            "steps": ["Check logs manually", "Contact on-call engineer"],
            "estimated_resolution_time_minutes": 30,
            "escalate_to_human": True,
        }
    
    async def _diagnose_with_claude(
        self,
        agent_name: str,
        symptoms: List[str],
        logs: Optional[str],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Diagnose using Claude API"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.anthropic_key)
            
            prompt = self._build_diagnostic_prompt(
                agent_name, symptoms, logs, context
            )
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            response_text = message.content[0].text
            return self._parse_diagnostic_response(response_text)
            
        except Exception as e:
            logger.error(f"Claude diagnostics failed: {e}")
            return self._fallback_diagnosis(agent_name, symptoms)
    
    async def _diagnose_with_perplexity(
        self,
        agent_name: str,
        symptoms: List[str],
        logs: Optional[str],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Diagnose using Perplexity API"""
        try:
            prompt = self._build_diagnostic_prompt(
                agent_name, symptoms, logs, context
            )
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.perplexity_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "pplx-70b-online",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1024,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    logger.error(f"Perplexity API error: {response.status_code}")
                    return self._fallback_diagnosis(agent_name, symptoms)
                
                data = response.json()
                response_text = data["choices"][0]["message"]["content"]
                return self._parse_diagnostic_response(response_text)
                
        except Exception as e:
            logger.error(f"Perplexity diagnostics failed: {e}")
            return self._fallback_diagnosis(agent_name, symptoms)
    
    async def _diagnose_with_openai(
        self,
        agent_name: str,
        symptoms: List[str],
        logs: Optional[str],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Diagnose using OpenAI API"""
        try:
            import openai
            openai.api_key = self.openai_key
            
            prompt = self._build_diagnostic_prompt(
                agent_name, symptoms, logs, context
            )
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            
            response_text = response["choices"][0]["message"]["content"]
            return self._parse_diagnostic_response(response_text)
            
        except Exception as e:
            logger.error(f"OpenAI diagnostics failed: {e}")
            return self._fallback_diagnosis(agent_name, symptoms)
    
    def _build_diagnostic_prompt(
        self,
        agent_name: str,
        symptoms: List[str],
        logs: Optional[str],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Build diagnostic prompt for AI model"""
        prompt = f"""You are a DevOps diagnostic expert. Analyze the following system failure and provide a root cause analysis.

Agent: {agent_name}
Symptoms:
{json.dumps(symptoms, indent=2)}

{f"Logs:{json.dumps(logs, indent=2)}" if logs else ""}

{f"Context:{json.dumps(context, indent=2)}" if context else ""}

Provide a structured diagnosis with:
1. ROOT_CAUSE: Most likely root cause (be specific)
2. CONFIDENCE: Your confidence level (0-1)
3. RECOMMENDED_FIX: Specific action to resolve
4. STEPS: Numbered list of implementation steps
5. ESTIMATED_TIME: Minutes to resolution
6. ESCALATE: Whether to escalate to human (true/false)

Format your response as JSON for parsing.
"""
        return prompt
    
    def _parse_diagnostic_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response into structured format"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "root_cause": parsed.get("ROOT_CAUSE", "Unknown"),
                    "confidence": float(parsed.get("CONFIDENCE", 0.5)),
                    "recommended_fix": parsed.get("RECOMMENDED_FIX", "Manual fix required"),
                    "steps": parsed.get("STEPS", []),
                    "estimated_resolution_time_minutes": int(parsed.get("ESTIMATED_TIME", 15)),
                    "escalate_to_human": parsed.get("ESCALATE", False),
                }
        except Exception as e:
            logger.error(f"Failed to parse diagnostic response: {e}")
        
        # Fallback: extract key info from text
        return {
            "root_cause": response_text[:200],
            "confidence": 0.5,
            "recommended_fix": response_text,
            "steps": response_text.split("\n"),
            "estimated_resolution_time_minutes": 15,
            "escalate_to_human": True,
        }
    
    def _fallback_diagnosis(
        self,
        agent_name: str,
        symptoms: List[str],
    ) -> Dict[str, Any]:
        """Fallback diagnosis when AI is unavailable"""
        return {
            "root_cause": f"Unknown failure in {agent_name}",
            "confidence": 0.0,
            "recommended_fix": "Manual investigation required - AI diagnostics unavailable",
            "steps": [
                "Check application logs",
                "Review recent deployments",
                "Verify resource availability (CPU, memory, disk)",
                "Check network connectivity",
                "Contact on-call engineer",
            ],
            "estimated_resolution_time_minutes": 30,
            "escalate_to_human": True,
        }

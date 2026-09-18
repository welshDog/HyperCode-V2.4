"""
Skill Registration & Discovery Examples
Shows how agents register and discover skills
"""

import asyncio
import json
from typing import Dict, Any, List
from skills_library import SkillLibrary


class SkillRegistrationExample:
    """Examples of how to register skills from the library"""

    @staticmethod
    def example_1_register_single_skill():
        """Example 1: Register a single skill"""
        print("\n" + "=" * 80)
        print("EXAMPLE 1: Register a Single Skill")
        print("=" * 80)
        
        skill = SkillLibrary.code_review_skill()
        
        print(f"\n📝 Registering Skill:")
        print(f"   Name: {skill['name']}")
        print(f"   ID: {skill['skill_id']}")
        print(f"   Category: {skill['category']}")
        
        print(f"\n📥 Input Schema:")
        for input_name, input_desc in skill['inputs'].items():
            print(f"   - {input_name}: {input_desc}")
        
        print(f"\n📤 Output Schema:")
        for output_name, output_desc in skill['outputs'].items():
            print(f"   - {output_name}: {output_desc}")
        
        print(f"\n⏱️  Performance:")
        print(f"   Execution Time: {skill['execution_time_ms']}ms")
        print(f"   Token Cost: {skill['cost_tokens']} tokens")
        
        print(f"\n🔗 Dependencies:")
        for dep in skill['dependencies']:
            print(f"   - {dep}")
        
        # Simulate registration
        print(f"\n✅ Would POST to: http://localhost:8051/api/v1/skills/register")
        print(f"   Payload: {json.dumps(skill, indent=2)[:200]}...")

    @staticmethod
    def example_2_bulk_register_by_category():
        """Example 2: Register all skills in a category"""
        print("\n" + "=" * 80)
        print("EXAMPLE 2: Bulk Register Skills by Category")
        print("=" * 80)
        
        categories = ["development", "architecture", "devops"]
        
        for category in categories:
            skills = SkillLibrary.get_skills_by_category(category)
            print(f"\n📦 Category: {category.upper()}")
            print(f"   Skills to register: {len(skills)}")
            
            for skill in skills:
                print(f"   ✓ {skill['name']} ({skill['skill_id']})")
            
            print(f"   📍 Registration Endpoint:")
            print(f"      POST http://localhost:8051/api/v1/skills/register-batch")
            print(f"      Payload: {len(skills)} skill definitions")

    @staticmethod
    def example_3_discover_skills():
        """Example 3: Discover skills by tag"""
        print("\n" + "=" * 80)
        print("EXAMPLE 3: Discover Skills")
        print("=" * 80)
        
        search_tags = ["security", "performance", "testing"]
        
        print(f"\n🔍 Discovering Skills by Tags:")
        for tag in search_tags:
            skills = SkillLibrary.get_skills_by_tag(tag)
            print(f"\n   Tag: #{tag}")
            print(f"   Found: {len(skills)} skills")
            
            for skill in skills:
                print(f"      • {skill['name']} ({skill['category']})")
            
            print(f"   🔗 Discovery Query:")
            print(f"      GET http://localhost:8051/api/v1/skills/search?tag={tag}")

    @staticmethod
    def example_4_compose_skills():
        """Example 4: Compose multiple skills into a workflow"""
        print("\n" + "=" * 80)
        print("EXAMPLE 4: Compose Skills into Workflow")
        print("=" * 80)
        
        # Create a code quality workflow
        workflow = {
            "workflow_id": "code_quality_pipeline_v1",
            "name": "Code Quality Pipeline",
            "description": "Complete code quality check workflow",
            "steps": [
                {
                    "step": 1,
                    "skill_id": "code_review_v1",
                    "name": "Code Review",
                    "inputs": {
                        "code": "${input.code}",
                        "language": "${input.language}",
                        "focus_areas": ["security", "performance"]
                    }
                },
                {
                    "step": 2,
                    "skill_id": "bug_detection_v1",
                    "name": "Bug Detection",
                    "inputs": {
                        "code": "${step_1.outputs.refactored_code}",
                        "language": "${input.language}",
                        "severity": "high"
                    }
                },
                {
                    "step": 3,
                    "skill_id": "test_generation_v1",
                    "name": "Test Generation",
                    "inputs": {
                        "code": "${step_2.outputs}",
                        "language": "${input.language}",
                        "coverage_target": 85
                    }
                },
                {
                    "step": 4,
                    "skill_id": "security_audit_v1",
                    "name": "Security Audit",
                    "inputs": {
                        "code": "${input.code}",
                        "language": "${input.language}",
                        "audit_depth": "standard"
                    }
                }
            ],
            "outputs": {
                "quality_score": "${step_1.outputs.quality_score}",
                "bugs_found": "${step_2.outputs.bugs_found}",
                "tests_generated": "${step_3.outputs.test_cases}",
                "security_issues": "${step_4.outputs.vulnerabilities}",
                "final_status": "pass|fail|review_needed"
            }
        }
        
        print(f"\n🔗 Workflow Composition:")
        print(f"   Name: {workflow['name']}")
        print(f"   Steps: {len(workflow['steps'])}")
        
        for step in workflow['steps']:
            print(f"\n   Step {step['step']}: {step['name']}")
            print(f"      Skill: {step['skill_id']}")
            print(f"      Input Source: {list(step['inputs'].values())[0]}")
        
        print(f"\n   📍 Composition Endpoint:")
        print(f"      POST http://localhost:8051/api/v1/skills/compose")
        print(f"      Payload:")
        print(f"      {json.dumps(workflow, indent=8)[:300]}...")

    @staticmethod
    def example_5_get_stats():
        """Example 5: Get skills usage statistics"""
        print("\n" + "=" * 80)
        print("EXAMPLE 5: Skills Statistics")
        print("=" * 80)
        
        summary = SkillLibrary.get_skills_summary()
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Skills Available: {summary['total_skills']}")
        print(f"   Average Token Cost: {summary['average_cost_tokens']} tokens")
        print(f"   Total Dependencies: {summary['total_dependencies']}")
        
        print(f"\n📂 Distribution by Category:")
        for category, count in sorted(summary['categories'].items()):
            percentage = (count / summary['total_skills']) * 100
            bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
            print(f"   {category.upper():20} [{bar}] {percentage:.1f}%")
        
        print(f"\n🏷️  Most Used Tags:")
        for tag, count in summary['popular_tags'][:5]:
            print(f"   #{tag}: {count} skills")
        
        print(f"\n   📍 Stats Endpoint:")
        print(f"      GET http://localhost:8051/api/v1/stats")

    @staticmethod
    def example_6_skill_dependencies():
        """Example 6: Understand skill dependencies"""
        print("\n" + "=" * 80)
        print("EXAMPLE 6: Skill Dependencies & Performance")
        print("=" * 80)
        
        all_skills = SkillLibrary.get_all_skills()
        
        # Group by execution time
        fast = [s for s in all_skills if s['execution_time_ms'] < 2000]
        medium = [s for s in all_skills if 2000 <= s['execution_time_ms'] < 4000]
        slow = [s for s in all_skills if s['execution_time_ms'] >= 4000]
        
        print(f"\n⚡ Performance Tiers:")
        print(f"   Fast (<2s): {len(fast)} skills")
        for skill in fast[:3]:
            print(f"      • {skill['name']} ({skill['execution_time_ms']}ms)")
        
        print(f"\n   Medium (2-4s): {len(medium)} skills")
        for skill in medium[:3]:
            print(f"      • {skill['name']} ({skill['execution_time_ms']}ms)")
        
        print(f"\n   Slow (>4s): {len(slow)} skills")
        for skill in slow[:3]:
            print(f"      • {skill['name']} ({skill['execution_time_ms']}ms)")
        
        # Show dependencies
        print(f"\n🔗 Common Dependencies:")
        all_deps = {}
        for skill in all_skills:
            for dep in skill.get('dependencies', []):
                all_deps[dep] = all_deps.get(dep, 0) + 1
        
        for dep, count in sorted(all_deps.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   • {dep}: required by {count} skills")

    @staticmethod
    def example_7_agent_skill_matrix():
        """Example 7: Skill matrix for different agent types"""
        print("\n" + "=" * 80)
        print("EXAMPLE 7: Agent Skill Matrix")
        print("=" * 80)
        
        # Map agent types to relevant skills
        agent_skills = {
            "code_reviewer": [
                "code_review_v1",
                "bug_detection_v1",
                "test_generation_v1",
                "security_audit_v1"
            ],
            "architect": [
                "architecture_design_v1",
                "design_pattern_v1",
                "api_design_v1",
                "performance_profiling_v1"
            ],
            "devops_engineer": [
                "docker_optimization_v1",
                "kubernetes_deployment_v1",
                "ci_cd_setup_v1",
                "monitoring_setup_v1"
            ],
            "data_scientist": [
                "data_analysis_v1",
                "trend_prediction_v1",
                "data_cleaning_v1",
                "performance_profiling_v1"
            ]
        }
        
        print(f"\n👥 Agent Types & Their Skills:")
        for agent_type, skill_ids in agent_skills.items():
            print(f"\n   {agent_type.upper()}")
            total_tokens = 0
            for skill_id in skill_ids:
                skill = SkillLibrary.get_skill_by_id(skill_id)
                if skill:
                    total_tokens += skill['cost_tokens']
                    print(f"      ✓ {skill['name']} ({skill['cost_tokens']} tokens)")
            print(f"      💰 Total Cost: {total_tokens} tokens")


class SkillCURLExamples:
    """cURL examples for registering and discovering skills"""

    @staticmethod
    def get_curl_examples():
        """Generate cURL command examples"""
        examples = {}
        
        # Register a skill
        skill = SkillLibrary.code_review_skill()
        examples['register_skill'] = f"""
curl -X POST http://localhost:8051/api/v1/skills/register \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(skill, indent=2)}'
        """.strip()
        
        # Search for skills
        examples['search_skills'] = """
curl -X GET "http://localhost:8051/api/v1/skills/search?tag=security" \\
  -H "Content-Type: application/json"
        """.strip()
        
        # Compose skills
        examples['compose'] = """
curl -X POST http://localhost:8051/api/v1/skills/compose \\
  -H "Content-Type: application/json" \\
  -d '{
    "workflow_id": "code_quality_v1",
    "steps": [
      {"skill_id": "code_review_v1", "inputs": {...}},
      {"skill_id": "bug_detection_v1", "inputs": {...}}
    ]
  }'
        """.strip()
        
        # Get stats
        examples['stats'] = """
curl -X GET http://localhost:8051/api/v1/stats \\
  -H "Content-Type: application/json"
        """.strip()
        
        return examples


def main():
    """Run all examples"""
    print("\n\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  🎯 SkillWeaver - Skill Registration & Discovery Examples".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Run examples
    SkillRegistrationExample.example_1_register_single_skill()
    SkillRegistrationExample.example_2_bulk_register_by_category()
    SkillRegistrationExample.example_3_discover_skills()
    SkillRegistrationExample.example_4_compose_skills()
    SkillRegistrationExample.example_5_get_stats()
    SkillRegistrationExample.example_6_skill_dependencies()
    SkillRegistrationExample.example_7_agent_skill_matrix()
    
    # Show cURL examples
    print("\n" + "=" * 80)
    print("CURL COMMAND EXAMPLES")
    print("=" * 80)
    
    examples = SkillCURLExamples.get_curl_examples()
    for name, cmd in examples.items():
        print(f"\n\n📋 {name.upper().replace('_', ' ')}")
        print("-" * 80)
        print(cmd)
    
    print("\n\n" + "=" * 80)
    print("✅ All examples shown. Use the cURL commands to test the API!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

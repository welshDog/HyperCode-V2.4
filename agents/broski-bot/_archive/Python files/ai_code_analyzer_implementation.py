"""
AI-Powered Code Analysis System
Automatically reviews code, detects patterns, and reorganizes project structure.
"""
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CodeMetrics:
    """Metrics for code analysis."""
    file_path: str
    lines_of_code: int
    functions: int
    classes: int
    imports: int
    complexity: int
    test_coverage: float
    documentation_score: float
    issues: List[str]
    recommendations: List[str]


@dataclass
class FeatureDetection:
    """Detected feature in codebase."""
    feature_name: str
    feature_type: str  # "community", "economy", "focus", "ai", etc.
    file_paths: List[str]
    description: str
    is_new: bool
    priority: str  # "high", "medium", "low"


class AICodeAnalyzer:
    """
    AI-powered code analysis and reorganization system.
    
    Scans codebase, detects patterns, identifies features, and suggests
    optimal file organization for community management workflows.
    """
    
    COMMUNITY_KEYWORDS = {
        "contribution", "community", "leaderboard", "reputation",
        "member", "user", "engagement", "support", "help",
    }
    
    ECONOMY_KEYWORDS = {
        "token", "balance", "reward", "earn", "spend", "transfer",
        "daily", "streak", "currency", "economy",
    }
    
    FOCUS_KEYWORDS = {
        "focus", "session", "productivity", "pomodoro", "hyperfocus",
        "timer", "break", "concentration",
    }
    
    AI_KEYWORDS = {
        "classify", "analyze", "predict", "model", "nlp", "sentiment",
        "pattern", "machine learning", "neural", "ai",
    }
    
    def __init__(self, project_root: str) -> None:
        """
        Initialize code analyzer.
        
        Args:
            project_root: Path to project root directory
        """
        self.project_root = Path(project_root)
        self.analyzed_files: List[CodeMetrics] = []
        self.detected_features: List[FeatureDetection] = []
    
    def scan_codebase(self) -> Dict[str, any]:
        """
        Scan entire codebase and generate comprehensive report.
        
        Returns:
            Analysis report dictionary
        """
        logger.info("Starting comprehensive codebase scan", root=str(self.project_root))
        
        # Scan all Python files
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            if self._should_analyze(file_path):
                metrics = self._analyze_file(file_path)
                if metrics:
                    self.analyzed_files.append(metrics)
        
        # Detect features
        self.detected_features = self._detect_features()
        
        # Generate recommendations
        recommendations = self._generate_reorganization_plan()
        
        # Compile report
        report = {
            "total_files": len(self.analyzed_files),
            "total_loc": sum(m.lines_of_code for m in self.analyzed_files),
            "total_functions": sum(m.functions for m in self.analyzed_files),
            "total_classes": sum(m.classes for m in self.analyzed_files),
            "avg_complexity": sum(m.complexity for m in self.analyzed_files) / max(len(self.analyzed_files), 1),
            "avg_documentation": sum(m.documentation_score for m in self.analyzed_files) / max(len(self.analyzed_files), 1),
            "detected_features": len(self.detected_features),
            "new_features": sum(1 for f in self.detected_features if f.is_new),
            "high_priority_features": sum(1 for f in self.detected_features if f.priority == "high"),
            "reorganization_recommendations": recommendations,
            "file_metrics": [
                {
                    "path": m.file_path,
                    "loc": m.lines_of_code,
                    "complexity": m.complexity,
                    "issues": m.issues,
                }
                for m in sorted(self.analyzed_files, key=lambda x: x.complexity, reverse=True)[:10]
            ],
        }
        
        logger.info("Codebase scan complete", **report)
        return report
    
    def _should_analyze(self, file_path: Path) -> bool:
        """Check if file should be analyzed."""
        # Skip test files, migrations, virtual environments
        skip_patterns = [
            "test_", "__pycache__", ".venv", "venv", "env",
            "migrations", ".git", "node_modules",
        ]
        
        return not any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _analyze_file(self, file_path: Path) -> Optional[CodeMetrics]:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Count elements
            functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
            classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
            imports = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))
            
            # Calculate metrics
            lines_of_code = len([line for line in content.split('\n') if line.strip() and not line.strip().startswith('#')])
            complexity = self._calculate_complexity(tree)
            documentation_score = self._calculate_documentation_score(tree, content)
            
            # Detect issues
            issues = self._detect_issues(tree, content)
            recommendations = self._generate_file_recommendations(tree, content)
            
            return CodeMetrics(
                file_path=str(file_path.relative_to(self.project_root)),
                lines_of_code=lines_of_code,
                functions=functions,
                classes=classes,
                imports=imports,
                complexity=complexity,
                test_coverage=0.0,  # Would integrate with coverage.py
                documentation_score=documentation_score,
                issues=issues,
                recommendations=recommendations,
            )
        
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}", error=str(e))
            return None
    
    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 0
        
        for node in ast.walk(tree):
            # Count decision points
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        return complexity
    
    def _calculate_documentation_score(self, tree: ast.AST, content: str) -> float:
        """Calculate documentation quality score (0-1)."""
        total_definitions = 0
        documented_definitions = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                total_definitions += 1
                if ast.get_docstring(node):
                    documented_definitions += 1
        
        if total_definitions == 0:
            return 1.0
        
        return documented_definitions / total_definitions
    
    def _detect_issues(self, tree: ast.AST, content: str) -> List[str]:
        """Detect code issues."""
        issues = []
        
        # Check for missing docstrings
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not ast.get_docstring(node) and not node.name.startswith('_'):
                    issues.append(f"Missing docstring: {node.name}")
        
        # Check for long functions (>50 lines)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                    func_length = node.end_lineno - node.lineno
                    if func_length > 50:
                        issues.append(f"Long function: {node.name} ({func_length} lines)")
        
        # Check for too many imports
        imports = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))
        if imports > 20:
            issues.append(f"Too many imports: {imports}")
        
        return issues
    
    def _generate_file_recommendations(self, tree: ast.AST, content: str) -> List[str]:
        """Generate recommendations for file improvements."""
        recommendations = []
        
        # Suggest breaking up large files
        loc = len([line for line in content.split('\n') if line.strip()])
        if loc > 500:
            recommendations.append("Consider breaking this file into smaller modules")
        
        # Suggest adding type hints
        has_annotations = any(
            hasattr(node, 'returns') and node.returns
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        )
        if not has_annotations:
            recommendations.append("Add type hints for better code clarity")
        
        return recommendations
    
    def _detect_features(self) -> List[FeatureDetection]:
        """Detect features in codebase."""
        features = []
        
        # Group files by feature type
        community_files = []
        economy_files = []
        focus_files = []
        ai_files = []
        
        for metrics in self.analyzed_files:
            metrics.file_path.lower()
            
            # Read file content for keyword analysis
            try:
                with open(self.project_root / metrics.file_path, 'r') as f:
                    content = f.read().lower()
                
                if any(kw in content for kw in self.COMMUNITY_KEYWORDS):
                    community_files.append(metrics.file_path)
                
                if any(kw in content for kw in self.ECONOMY_KEYWORDS):
                    economy_files.append(metrics.file_path)
                
                if any(kw in content for kw in self.FOCUS_KEYWORDS):
                    focus_files.append(metrics.file_path)
                
                if any(kw in content for kw in self.AI_KEYWORDS):
                    ai_files.append(metrics.file_path)
            
            except Exception as e:
                logger.warning(f"Failed to read {metrics.file_path}", error=str(e))
        
        # Create feature detections
        if community_files:
            features.append(FeatureDetection(
                feature_name="Community Management",
                feature_type="community",
                file_paths=community_files,
                description="Files related to community engagement, contributions, and social features",
                is_new=len(community_files) > 0 and "contribution" in str(community_files),
                priority="high",
            ))
        
        if economy_files:
            features.append(FeatureDetection(
                feature_name="Token Economy",
                feature_type="economy",
                file_paths=economy_files,
                description="Files handling token distribution, rewards, and economy",
                is_new=False,
                priority="high",
            ))
        
        if focus_files:
            features.append(FeatureDetection(
                feature_name="Focus & Productivity",
                feature_type="focus",
                file_paths=focus_files,
                description="Files for focus sessions and productivity tracking",
                is_new=False,
                priority="medium",
            ))
        
        if ai_files:
            features.append(FeatureDetection(
                feature_name="AI-Powered Analysis",
                feature_type="ai",
                file_paths=ai_files,
                description="AI and machine learning features for classification and analysis",
                is_new=True,
                priority="high",
            ))
        
        return features
    
    def _generate_reorganization_plan(self) -> Dict[str, List[str]]:
        """Generate file reorganization plan."""
        plan = {
            "create_directories": [
                "src/ai",
                "src/integrations/mintme",
                "src/dashboard",
                "src/services/community",
            ],
            "move_files": [],
            "split_files": [],
            "merge_files": [],
        }
        
        # Identify files that should be moved
        for metrics in self.analyzed_files:
            if "community" in metrics.file_path.lower() and "src/services" not in metrics.file_path:
                plan["move_files"].append({
                    "from": metrics.file_path,
                    "to": f"src/services/community/{Path(metrics.file_path).name}",
                })
            
            # Identify files that should be split
            if metrics.lines_of_code > 500:
                plan["split_files"].append({
                    "file": metrics.file_path,
                    "reason": f"Large file ({metrics.lines_of_code} LOC)",
                })
        
        return plan
    
    def generate_report_markdown(self) -> str:
        """Generate markdown report."""
        report = self.scan_codebase()
        
        md = f"""# 🤖 AI Code Analysis Report
        
## 📊 Overview

- **Total Files Analyzed**: {report['total_files']}
- **Total Lines of Code**: {report['total_loc']:,}
- **Total Functions**: {report['total_functions']:,}
- **Total Classes**: {report['total_classes']:,}
- **Average Complexity**: {report['avg_complexity']:.2f}
- **Average Documentation**: {report['avg_documentation']:.1%}

## 🔍 Detected Features

**Total Features**: {report['detected_features']} ({report['new_features']} new)

"""
        
        for feature in self.detected_features:
            md += f"""
### {feature.feature_name} ({feature.priority.upper()} Priority)
- **Type**: {feature.feature_type}
- **Status**: {"🆕 NEW" if feature.is_new else "✅ Existing"}
- **Files**: {len(feature.file_paths)}
- **Description**: {feature.description}
"""
        
        md += "\n## 📁 Reorganization Recommendations\n\n"
        
        recs = report['reorganization_recommendations']
        
        if recs['create_directories']:
            md += "### Create Directories\n"
            for dir_path in recs['create_directories']:
                md += f"- `{dir_path}`\n"
        
        if recs['move_files']:
            md += "\n### Move Files\n"
            for move in recs['move_files']:
                md += f"- `{move['from']}` → `{move['to']}`\n"
        
        if recs['split_files']:
            md += "\n### Split Large Files\n"
            for split in recs['split_files']:
                md += f"- `{split['file']}` ({split['reason']})\n"
        
        return md


# ============================================================================
# Automated Code Analysis Script
# ============================================================================

def main():
    """Run automated code analysis."""
    import sys
    
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    
    analyzer = AICodeAnalyzer(project_root)
    
    # Generate report
    report_md = analyzer.generate_report_markdown()
    
    # Save to file
    output_path = Path(project_root) / "CODE_ANALYSIS_REPORT.md"
    with open(output_path, 'w') as f:
        f.write(report_md)
    
    print(f"✅ Analysis complete! Report saved to {output_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(report_md[:500])
    print("\n... (see full report in CODE_ANALYSIS_REPORT.md)")


if __name__ == "__main__":
    main()

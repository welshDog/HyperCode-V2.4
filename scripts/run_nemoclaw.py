from pathlib import Path
import sys
sys.path.insert(0, str(Path('agents/broski-nemoclaw-agent')))
from analyzer import BROskiAnalyzer
import ast

SKIP_DIRS = {'_archive', 'new-fix-0.1', 'examples', '.git', '.venv', 'venv', '__pycache__', 'node_modules', 'backups', 'reports', 'htmlcov', 'tests', 'hyperstudio-platform', 'scripts', 'docs'}

def ast_check_fixed(root, files):
    issues = []
    for fp in files:
        if any(d in fp.parts for d in SKIP_DIRS):
            continue
        try:
            tree = ast.parse(fp.read_text(errors='ignore'))
        except SyntaxError as e:
            issues.append({'file': str(fp.relative_to(root)), 'line': e.lineno, 'severity': 'critical', 'message': str(e)})
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({'file': str(fp.relative_to(root)), 'line': node.lineno, 'severity': 'medium', 'message': 'Bare except found'})
    return issues

ROOT = Path('.')
analyzer = BROskiAnalyzer(ROOT)
print('NemoClaw Scanning...')
files = analyzer.py_files()
print('Python files found: ' + str(len(files)))
ruff_issues = analyzer.ruff()
ast_issues = ast_check_fixed(ROOT, files)
total = len(ruff_issues) + len(ast_issues)

issues_per_file = total / max(len(files), 1)
score = max(0, min(100, round(100 - (issues_per_file * 40))))

grade = 'S - LEGENDARY' if score >= 95 else 'A - CLEAN' if score >= 80 else 'B - GOOD' if score >= 65 else 'C - NEEDS WORK' if score >= 50 else 'D - SOS MODE'

print('')
print('==============================')
print('  NemoClaw Health Report')
print('==============================')
print('  Files scanned:  ' + str(len(files)))
print('  Lint issues:    ' + str(len(ruff_issues)))
print('  Secret scan:    SKIPPED')
print('  AST issues:     ' + str(len(ast_issues)))
print('  Total issues:   ' + str(total))
print('  Health Score:   ' + str(score) + '/100')
print('  Grade:          ' + grade)
print('==============================')
print('')
print('TOP LINT ISSUES:')
for i in ruff_issues[:5]:
    short = i.file.replace('H:\\HyperStation zone\\HyperCode\\HyperCode-V2.4\\', '')
    print('  [LINT] ' + short + ':' + str(i.line) + ' - ' + i.message[:55])
print('')
print('AST ISSUES:')
for i in ast_issues[:8]:
    print('  [AST]  ' + i['file'] + ':' + str(i['line']) + ' - ' + i['message'])



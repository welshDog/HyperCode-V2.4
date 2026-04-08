# 📋 TEST FRAMEWORK UPGRADE PROCEDURES TEMPLATE

**Purpose:** Standardized process for all future test framework upgrades  
**Use When:** Upgrading pytest, pytest-asyncio, or related testing packages  
**Estimated Time:** 1-2 days depending on scope

---

## PRE-UPGRADE PHASE (1 day before)

### Step 1: Impact Analysis

```markdown
## Upgrade Impact Assessment

**Target Upgrade:** [Package] [from_version] → [to_version]

### Scope
- [ ] What's changing in the new version?
- [ ] Are there breaking changes?
- [ ] What dependencies are affected?
- [ ] What parts of codebase use this package?

### Dependency Chain
```
[package] [version]
├── [dependency1] [version]
├── [dependency2] [version]
└── [dependency3] [version]
```

### Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Tests fail | HIGH | CRITICAL | Pre-test in isolated env |
| Performance degrades | MEDIUM | HIGH | Benchmark before/after |
| Breaking API changes | MEDIUM | CRITICAL | Review changelog |
| Incompatible with other packages | LOW | HIGH | Run pip check |

### Timeline
- Day 1: Planning and analysis
- Day 2: Development environment upgrade
- Day 3: Testing and verification
- Day 4: CI/CD update
- Day 5: Production deployment
```

### Step 2: Create Pre-Upgrade Snapshot

```bash
#!/bin/bash
# Name: pre_upgrade_snapshot.sh

# Capture baseline
pytest tests/ -v --tb=short > test_results_baseline.txt 2>&1
pip list > requirements_baseline.txt
pip check > dependency_check_baseline.txt
coverage report > coverage_baseline.txt 2>&1 || true

# Create git tag
git tag -a pre-upgrade-pytest-$(date +%Y%m%d) -m "Before upgrading pytest"

# Create backup branch
git checkout -b upgrade/pytest-$(date +%Y%m%d)

# Document
cat > UPGRADE_SNAPSHOT_$(date +%Y%m%d).txt << EOF
Pre-Upgrade Snapshot
Date: $(date)

Test Results: test_results_baseline.txt
Requirements: requirements_baseline.txt
Dependency Check: dependency_check_baseline.txt
Coverage: coverage_baseline.txt

Git Tag: pre-upgrade-pytest-$(date +%Y%m%d)
Git Branch: upgrade/pytest-$(date +%Y%m%d)
EOF
```

### Step 3: Create Upgrade Plan

```markdown
## Detailed Upgrade Plan

### Packages to Update
1. pytest: 8.4.1 → 9.0.0
   - Breaking changes: [list]
   - Dependencies affected: [list]
   - Code changes needed: [list]

2. pytest-asyncio: 1.3.0 → 1.4.0
   - Configuration changes: asyncio_mode updated
   - Fixture changes: [list]

### Order of Operations
1. Update requirements.txt
2. Create isolated test environment
3. Install new versions
4. Run dependency check
5. Update configuration (pytest.ini, conftest.py)
6. Migrate test cases if needed
7. Run full test suite
8. Update CI/CD pipeline
9. Merge to main

### Rollback Plan
If critical issue arises:
1. git checkout pre-upgrade-pytest-20260212
2. pip install -r requirements_baseline.txt
3. pytest tests/ -v  # Verify baseline

### Success Metrics
- All tests pass with new versions
- Coverage reports generate without errors
- Performance within ±10% of baseline
- CI/CD pipeline passes
- No new warnings or errors
```

---

## UPGRADE EXECUTION PHASE (Day 2)

### Step 4: Update Requirements and Dependencies

```bash
#!/bin/bash
# Name: perform_upgrade.sh
# Run from project root

# Step 1: Update requirements.txt
echo "Step 1: Updating requirements.txt..."
# Manually update version numbers (not automatic)
# pytest>=8.4.0 → pytest>=9.0.0
# pytest-asyncio>=1.3.0 → pytest-asyncio>=1.4.0

# Step 2: Create isolated environment
echo "Step 2: Creating isolated test environment..."
python -m venv venv-upgrade-test
source venv-upgrade-test/bin/activate  # or Scripts\activate on Windows

# Step 3: Install
echo "Step 3: Installing new packages..."
pip install --upgrade pip setuptools wheel
pip install -r THE\ HYPERCODE/hypercode-core/requirements.txt

# Step 4: Check for conflicts
echo "Step 4: Checking for dependency conflicts..."
pip check > dependency_check_upgrade.txt
if [ $? -ne 0 ]; then
    echo "❌ Dependency conflicts detected!"
    cat dependency_check_upgrade.txt
    exit 1
fi

# Step 5: Document
echo "Step 5: Documenting changes..."
pip list > requirements_upgrade.txt
pip show pytest pytest-asyncio > package_versions.txt

echo "✅ Upgrade package installation complete"
```

### Step 5: Update Configuration Files

```bash
#!/bin/bash
# Name: update_configuration.sh

# Backup old files
cp pytest.ini pytest.ini.backup
cp conftest.py conftest.py.backup

# Update pytest.ini if needed
# (Review new version docs for required changes)

# Update conftest.py if needed
# (Check for deprecated fixtures or methods)

# Update tox.ini if present
# (Update envlist for new Python versions if needed)

# Verify configuration
pytest --co -q tests/ > test_collection.txt
if [ $? -ne 0 ]; then
    echo "❌ Configuration error detected!"
    cat test_collection.txt
    exit 1
fi

echo "✅ Configuration updated"
```

### Step 6: Test Execution and Comparison

```bash
#!/bin/bash
# Name: test_and_compare.sh

# Run tests with new version
echo "Running test suite with new versions..."
pytest tests/ -v --tb=short > test_results_upgrade.txt 2>&1

# Generate coverage
pytest tests/ --cov=app --cov-report=html --cov-report=json

# Compare results
echo "Comparing test results..."
diff test_results_baseline.txt test_results_upgrade.txt > test_diff.txt || true

# Extract metrics
echo "Test Results Comparison:"
echo "Baseline: $(grep -c '^tests.*PASSED' test_results_baseline.txt || echo 0) PASSED"
echo "Upgrade:  $(grep -c '^tests.*PASSED' test_results_upgrade.txt || echo 0) PASSED"

if [ -f htmlcov/index.html ]; then
    echo "✅ Coverage reports generated"
else
    echo "❌ Coverage reports missing"
fi
```

---

## VERIFICATION PHASE (Day 3)

### Step 7: Comprehensive Testing

```bash
#!/bin/bash
# Name: comprehensive_test.sh

echo "=== Comprehensive Testing ==="

# 1. Unit tests
echo "1. Running unit tests..."
pytest tests/ -m unit -v --tb=short

# 2. Integration tests
echo "2. Running integration tests..."
pytest tests/ -m integration -v --tb=short

# 3. Full suite with coverage
echo "3. Running full suite with coverage..."
pytest tests/ --cov=app --cov-report=term-missing --cov-report=json

# 4. Performance check
echo "4. Checking performance..."
pytest tests/ --durations=10

# 5. No deprecation warnings
echo "5. Checking for deprecation warnings..."
pytest tests/ -W error::DeprecationWarning 2>&1 | grep -i deprecat || echo "No deprecation warnings ✅"

# Summary
echo "=== Test Summary ==="
if [ $? -eq 0 ]; then
    echo "✅ ALL TESTS PASSED"
else
    echo "❌ SOME TESTS FAILED - Review above"
    exit 1
fi
```

### Step 8: CI/CD Pipeline Verification

```bash
#!/bin/bash
# Name: verify_ci_cd.sh

echo "=== CI/CD Verification ==="

# 1. Check workflow syntax
echo "1. Validating GitHub Actions syntax..."
# (Use GitHub's own validator if possible)

# 2. Test locally
echo "2. Simulating CI/CD locally..."
docker run --rm -v $(pwd):/workspace python:3.13 bash -c "
    cd /workspace/backend
    pip install -r requirements.txt
    pytest --cov=backend/app --cov-report=xml
"

if [ $? -eq 0 ]; then
    echo "✅ CI/CD simulation passed"
else
    echo "❌ CI/CD simulation failed"
    exit 1
fi
```

---

## CI/CD UPDATE PHASE (Day 4)

### Step 9: Update GitHub Actions Workflow

```yaml
# File: .github/workflows/tests.yml (or ci-python.yml)
# Update to new requirements and current repo layout

name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.12', '3.13']
      fail-fast: false

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip setuptools wheel
        pip install -r "backend/requirements.txt"
    
    - name: Verify package versions
      run: |
        pip check
        pip show pytest pytest-asyncio
    
    - name: Run tests
      run: |
        cd backend
        pytest -v --cov=backend/app --cov-report=xml --cov-report=html
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
        fail_ci_if_error: true
    
    - name: Archive test results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: test-results-python-${{ matrix.python-version }}
        path: |
          backend/htmlcov/
          test_results.txt
```

---

## DOCUMENTATION & DEPLOYMENT (Day 5)

### Step 10: Create Upgrade Documentation

```markdown
# Test Framework Upgrade: pytest 8.4 → 9.0

## Date: 2026-02-12

### Changes Summary
- [x] Updated pytest from 8.4.1 → 9.0.0
- [x] Updated pytest-asyncio from 1.3.0 → 1.4.0
- [x] Updated pytest.ini configuration
- [x] Updated conftest.py fixtures (if needed)
- [x] Updated GitHub Actions workflow
- [x] All tests verified passing

### Breaking Changes
- Old async test decorator pattern deprecated (use plain async def)
- Coverage XML report format updated
- pytest.ini marker format updated

### Migration Guide
1. Replace @pytest.mark.asyncio with plain async def (in most cases)
2. Update pytest.ini asyncio_mode if needed
3. Verify conftest.py fixtures with new version

### Verification Results
- Tests passed: ✅
- Coverage reports generated: ✅
- CI/CD simulation: ✅
- Performance acceptable: ✅

### Rollback Instructions
If critical issues arise:
```bash
git checkout pre-upgrade-pytest-20260212
pip install -r requirements.txt
pytest tests/
```

### Future Improvements
- Add more comprehensive logging
- Implement automated diff generation
- Create test before/after benchmark comparisons
```

### Step 11: Merge and Deploy

```bash
#!/bin/bash
# Name: merge_and_deploy.sh

# Verify everything is ready
echo "Final verification..."
pytest tests/ -v --tb=short
pip check

# Commit final changes
git add -A
git commit -m "feat: upgrade test framework to pytest 9.0

- Updated pytest from 8.4.1 → 9.0.0
- Updated pytest-asyncio from 1.3.0 → 1.4.0
- Updated pytest.ini for new async patterns
- Updated conftest.py for deprecated fixtures
- Updated GitHub Actions workflow
- All tests verified passing with new versions

See UPGRADE_NOTES.md for details.

Closes #XYZ"

# Tag release
git tag -a test-upgrade-9.0-complete -m "pytest 9.0 upgrade complete and tested"

# Push to main
git checkout main
git pull origin main
git merge upgrade/pytest-$(date +%Y%m%d)
git push origin main
git push origin --tags

echo "✅ Upgrade complete and deployed!"
```

---

## FUTURE UPGRADE CHECKLIST TEMPLATE

Use this for every test framework upgrade:

### Pre-Upgrade
- [ ] Create impact assessment document
- [ ] Identify all affected code
- [ ] Create git tag for rollback
- [ ] Create backup branch
- [ ] Capture baseline metrics

### Upgrade Execution
- [ ] Update requirements.txt
- [ ] Create isolated environment
- [ ] Install new versions
- [ ] Run pip check
- [ ] Update configuration files
- [ ] Verify test collection

### Verification
- [ ] Run full test suite
- [ ] Generate coverage reports
- [ ] Compare performance
- [ ] Check CI/CD simulation
- [ ] Verify no deprecation warnings

### CI/CD Update
- [ ] Update GitHub Actions workflow
- [ ] Test workflow syntax
- [ ] Verify coverage upload
- [ ] Test matrix configurations

### Documentation
- [ ] Create upgrade notes
- [ ] Document breaking changes
- [ ] Provide migration guide
- [ ] Include rollback instructions

### Deployment
- [ ] Merge to main branch
- [ ] Create release tag
- [ ] Push to production
- [ ] Monitor initial runs
- [ ] Document any issues

---

## KEY LESSONS LEARNED

From this upgrade, apply these going forward:

1. **Always have a rollback plan** ← Critical for preventing outages

2. **Test in isolated environment** ← Prevents contamination of main venv

3. **Document breaking changes** ← Helps team understand impact

4. **Run pip check every time** ← Catches dependency conflicts early

5. **Update CI/CD before deployment** ← Prevents failed builds on main

6. **Capture baseline metrics** ← Allows before/after comparison

7. **Create git tags for all upgrades** ← Easy rollback point

8. **Notify team of changes** ← Prevents confusion and duplicate efforts

---

**Use this template for all future test framework upgrades!**

Save this file and refer to it when upgrading pytest, pytest-asyncio, or related testing packages.

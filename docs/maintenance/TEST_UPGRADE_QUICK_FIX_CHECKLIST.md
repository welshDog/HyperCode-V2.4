# ✅ TEST UPGRADE FIXES — QUICK REFERENCE CHECKLIST

**Status:** 🔴 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION  
**Time Required:** 55 minutes (critical fixes) + 3-4 hours (remaining)  
**Priority:** TODAY

---

## 🚨 CRITICAL FIXES (55 Minutes Total)

### ✔️ FIX #1: Install Missing pytest-cov (5 minutes)

**Current Status:** pytest-cov NOT INSTALLED ❌

```bash
# Step 1: Install packages
python -m pip install pytest-cov==4.1.0 coverage==7.4.0 --force-reinstall

# Step 2: Verify
python -c "import pytest_cov; import coverage; print('✅ Both packages installed')"

# Step 3: Test
cd "C:\Users\Lyndz\Downloads\HyperCode-V2.0\HyperCode-V2.0\THE HYPERCODE\hypercode-core"
pytest --version
pytest --help | Select-String cov
```

**Expected Result:** Both packages appear in `pip list` and pytest shows coverage options

---

### ✔️ FIX #2: Resolve Dependency Conflicts (30 minutes)

**Current Status:** Version conflicts detected ⚠️

**Option A: Quick Fix (15 min)**
```bash
# Update requirements.txt
# Change: requests==2.31.0 → requests==2.32.4 (security patches)
# Change: httpx==0.26.0 → httpx==0.27.0 (compatibility)

cd "C:\Users\Lyndz\Downloads\HyperCode-V2.0\HyperCode-V2.0\THE HYPERCODE\hypercode-core"
# Edit requirements.txt, then:

pip install -r requirements.txt --upgrade
pip check  # Should show "No broken requirements found"
```

**Option B: Clean Install (30 min - Recommended)**
```bash
# Move old venv
Rename-Item venv venv.backup

# Create fresh
python -m venv venv
# Activate: venv\Scripts\activate

# Install
pip install --upgrade pip
pip install -r "THE HYPERCODE\hypercode-core\requirements.txt"

# Verify
pip check
pip list > installed-versions.txt
```

**Expected Result:** `pip check` returns "No broken requirements found"

---

### ✔️ FIX #3: Update pytest.ini (20 minutes)

**Current Status:** Configuration incomplete ❌

```bash
# Edit: THE HYPERCODE\hypercode-core\pytest.ini
# Replace entire file with:
```

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py

addopts = 
    -v 
    --tb=short
    --cov=app 
    --cov=main
    --cov-report=term-missing:skip-covered
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-branch

markers =
    experimental: marks tests as experimental/WIP
    flaky: marks tests as flaky/timing-dependent
    slow: marks tests as slow
    unit: unit tests
    integration: integration tests

[coverage:run]
branch = true
parallel = true
omit =
    */tests/*
    */site-packages/*
    */__pycache__/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
precision = 2
```

**Verify:**
```bash
cd "THE HYPERCODE\hypercode-core"
pytest --co -q | head -10  # Should show test list
```

---

## ✅ VERIFICATION (After Critical Fixes)

Run these commands to verify all critical fixes are complete:

```bash
# 1. pytest-cov installed
python -c "import pytest_cov; print('✅ pytest-cov OK')"

# 2. Dependencies resolved
pip check
# Expected: No broken requirements found

# 3. pytest.ini correct
cd "THE HYPERCODE\hypercode-core"
pytest --version
pytest --co -q | wc -l  # Should show count of tests

# 4. Quick test run
pytest tests/test_agents.py -v --tb=short 2>&1 | head -20

# 5. Coverage works
pytest tests/ --cov=app --co -q  # Should not error
```

---

## 🔄 FOLLOW-UP FIXES (3-4 Hours - This Week)

### Fix #4: Optimize Test Performance (1-2 hours)
- [ ] Profile slow tests: `pytest tests/ --durations=20`
- [ ] Add timeouts to fixtures
- [ ] Mark slow tests with @pytest.mark.slow
- [ ] Verify full run < 60 seconds

### Fix #5: Update CI/CD Pipeline (1 hour)
- [ ] Review .github/workflows/test.yml
- [ ] Add pytest-cov to install step
- [ ] Add coverage upload
- [ ] Add matrix testing

### Fix #6: Document Test Data Migration (2 hours)
- [ ] Create TEST_DATA_MIGRATION.md
- [ ] Add versioning to conftest.py
- [ ] Document rollback procedures

### Fix #7: Add Missing Config Files (1 hour)
- [ ] Create tests/.env.test
- [ ] Create tox.ini
- [ ] Create documentation

---

## 📋 COMMIT CHECKLIST

After each fix, commit to git:

```bash
# After Fix #1
git add .
git commit -m "fix: install missing pytest-cov and coverage dependencies"

# After Fix #2
git add requirements.txt installed-versions.txt
git commit -m "fix: resolve dependency conflicts and version mismatches"

# After Fix #3
git add pytest.ini
git commit -m "fix: update pytest.ini with correct coverage configuration"

# After all fixes
git add -A
git commit -m "feat: complete test framework upgrade with all dependencies installed

- Installed missing pytest-cov and coverage packages
- Resolved all dependency conflicts
- Updated pytest.ini with correct configuration
- Verified all tests can run with coverage reporting

Tests now pass with proper coverage reports."

# Tag release
git tag -a test-upgrade-complete-2026-02-12 -m "Test upgrade completion"
```

---

## ❌ COMMON MISTAKES TO AVOID

### ❌ Don't
- ❌ Skip `pip check` verification
- ❌ Use `--force-install` without checking conflicts
- ❌ Leave pytest-cov commented out in requirements
- ❌ Forget to update both pytest.ini AND conftest.py
- ❌ Run tests in old directory with cached pytest.ini

### ✅ Do
- ✅ Run `pip check` after each install
- ✅ Document every version change
- ✅ Test immediately after each fix
- ✅ Commit changes after verification
- ✅ Update CI/CD pipeline along with local config

---

## 📞 VALIDATION TIMELINE

```
10:00 - START: Install pytest-cov (5 min)
        Verify: python -c "import pytest_cov"

10:10 - Resolve dependencies (30 min)
        Verify: pip check

10:45 - Update pytest.ini (20 min)
        Verify: pytest --co -q

11:05 - TEST RUN: Full verification (15 min)
        pytest tests/ -v --tb=short

11:20 - COMMIT & TAG (5 min)
        git commit && git tag

11:25 - STATUS: ✅ CRITICAL FIXES COMPLETE
```

---

## 🎯 SUCCESS CRITERIA

All critical fixes are complete when:

- [x] pytest-cov installed (`import pytest_cov` works)
- [x] coverage installed (`import coverage` works)
- [x] No dependency conflicts (`pip check` passes)
- [x] pytest.ini has coverage options
- [x] Tests can run with `--cov` flag
- [x] Coverage reports generate (htmlcov/index.html exists)
- [x] All changes committed to git

---

**Estimated Time: 55 minutes for critical fixes**  
**Start Now. Be Done by Noon.**

Let me know if you need help with any step!

# 🔄 BROski Bot Migration Report

**Date:** March 4, 2026
**Sprint:** 1
**Task:** 1.1 (Restructure Repository)

## 📋 Summary

The repository has been successfully restructured from a flat file layout to a modular, enterprise-grade architecture. All source code has been migrated to the `src/` directory, organized by layer (Core, Services, Repositories, Cogs).

## 🏗️ New Directory Structure

```
src/
├── agents/         # AI Agents (Classifier, Code Analyzer)
├── cogs/           # Discord Extensions (Economy, Focus, etc.)
├── config/         # Settings & Logging
├── core/           # Core Logic (Database, Exceptions)
├── integrations/   # External APIs (MintMe)
├── models/         # Database Models
├── repositories/   # Data Access Layer
├── services/       # Business Logic Layer
└── utils/          # Utilities
tests/              # Test Suite
docs/               # Documentation
scripts/            # Deployment & Maintenance Scripts
data/               # Local Data & Database
backups/            # Backups of legacy files
```

## 🔄 Migrated Files

| Original File | New Location | Notes |
| :--- | :--- | :--- |
| `broski_main.py` | `src/main.py` & `src/bot.py` | Split into entry point and bot class |
| `broski_database.py` | `src/core/database.py` | |
| `broski_settings.py` | `src/config/settings.py` | |
| `broski_logging.py` | `src/config/logging.py` | |
| `broski_exceptions.py` | `src/core/exceptions.py` | |
| `broski_models.py` | `src/models/__init__.py` | |
| `broski_services.py` | `src/services/economy.py` | |
| `broski_repositories.py` | `src/repositories/economy.py` | |
| `broski_economy_cog.py` | `src/cogs/economy.py` | Enterprise version |
| `bot.py` | `src/bot_legacy.py` | Legacy version preserved |
| `cogs/economy.py` | `src/cogs/economy_legacy.py` | Legacy version preserved |
| `focus_engine.py` | `src/cogs/focus.py` | Legacy version (needs update) |
| `ai_relay.py` | `src/cogs/ai_relay.py` | |
| `community.py` | `src/cogs/community.py` | |
| `broski_tests.py` | `tests/test_enterprise.py` | |
| `ai_code_analyzer...` | `src/agents/code_analyzer.py` | |
| `ai_contribution...` | `src/agents/classifier.py` | |

## 🛠️ Configuration Changes

- **Dependencies:** Migrated from `requirements.txt` to `pyproject.toml` (Poetry).
- **Environment:** `.env` file structure preserved (loaded by `pydantic-settings`).
- **Entry Point:** Changed from `python bot.py` to `python -m src.main run` or `broski run`.

## ⚠️ Known Issues / Next Steps

1.  **Focus Cog:** `src/cogs/focus.py` is the legacy version and may not be compatible with the new SQLAlchemy-based `src/bot.py`. It requires refactoring (Sprint 2).
2.  **Legacy Bot:** `src/bot_legacy.py` will fail to run unless `cogs` path is adjusted or run from root with modifications.
3.  **Database:** The new architecture expects a PostgreSQL connection string in `DATABASE_URL`. Ensure `.env` is updated or use SQLite URL for dev.

## ✅ Validation

- Directory structure verified.
- Import paths updated in new files.
- `pyproject.toml` created with all dependencies.

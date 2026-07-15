# HyperCode Requirements Sync (P0) — Design

## Goal

Eliminate dependency drift between `requirements.txt` and `requirements.lock` by:

1. Making `requirements.lock` the single source of truth for pinned versions.
2. Updating `requirements.txt` to remove duplicates and align versions to the lock.

## Current Problem (Observed)

- `requirements.lock` is generated from `requirements.txt` via `pip-compile`, but the two files are currently out of sync (versions and duplicate entries exist in `requirements.txt`).
- This creates ambiguous installs depending on whether someone uses `pip install -r requirements.txt` or `pip install -r requirements.lock`.

## Non-Goals

- No mass dependency upgrades/downgrades beyond matching the existing lock.
- No changes to `backend/requirements.txt` or service-level requirements in this pass.

## Approach

1. Treat `requirements.lock` as authoritative.
2. Edit `requirements.txt`:
   - Remove duplicate entries.
   - Replace conflicting pins with the version currently in `requirements.lock`.
   - Prefer exact pins where a pin already exists, to keep installs deterministic.
3. Do not regenerate `requirements.lock` in this pass (it already represents the desired solved set).

## Acceptance Criteria

- `requirements.txt` has no duplicate packages.
- Any pinned versions in `requirements.txt` match the corresponding versions in `requirements.lock`.
- The `pip-compile` header in `requirements.lock` remains valid (lock remains the stable solved set).


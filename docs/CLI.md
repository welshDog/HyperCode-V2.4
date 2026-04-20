# HyperCode CLI Manual

**Status:** Experimental  
**Last Updated:** 2026-04-20  
**Applies To:** HyperCode v2.4.2

The CLI lives in `cli/` and is intended for scripted interactions (agent listing, task submission, and Jira ticket helpers).

## Installation

```powershell
python -m pip install -r .\cli\requirements.txt
```

## Configuration

Environment variables:
- `HYPERCODE_API_URL` (default: `http://localhost:8000`)
- `HYPERCODE_API_KEY` (default: `dev-key`)

## Usage

```powershell
python .\cli\main.py --help
```

## Commands (current)

- `agents` — list agents
- `run --task "<text>"` — submit a task (uses `HYPERCODE_API_KEY`)
- `costs` — request cost metrics (if enabled)
- `jira-generate` — generate Jira payloads from templates
- `jira-validate` — validate Jira payloads

## Notes

- Mission Control is the canonical operator UI: `http://127.0.0.1:8088`
- Canonical API reference: [API.md](API.md)

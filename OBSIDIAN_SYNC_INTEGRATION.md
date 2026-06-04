# HyperAgent Loop → Obsidian Vault Integration

## Current State

✅ **Vault sync container is ready** — clones fresh, syncs to PARA folders, pushes to GitHub  
✅ **Result writer module is ready** — `result_writer.py` created in `agents/crew-orchestrator/`  
🔜 **Integration needed** — Wire the post-run hook into `agents/crew-orchestrator/main.py`

---

## How to Wire It Up

### Step 1: Add Import to `main.py`

At the top of `agents/crew-orchestrator/main.py`, after existing imports, add:

```python
# Import result writer for post-execution sync
try:
    from .result_writer import write_and_sync
except ImportError:
    from result_writer import write_and_sync
```

### Step 2: Add Post-Run Hook to `/execute` Endpoint

Find this section in `main.py` (near line 1070):

```python
    # Final update
    if redis_client:
        task_data = json.loads(await redis_client.get(f"task:{task.id}:details"))
        task_data["progress"] = 100
        task_data["status"] = "completed"
        await redis_client.set(f"task:{task.id}:details", json.dumps(task_data))
        await log_event("orchestrator", "success", "Workflow completed")

        # Publish BROski$ reward event — backend Celery / Discord bot listens
        broski_event = {
            "event": "task_completed",
            "task_id": task.id,
            "task_type": task.type,
            "agents": list(results.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await redis_client.publish("broski_events", json.dumps(broski_event))
        logger.info(
            json.dumps({"event": "broski_event_published", "task_id": task.id})
        )

    return {"status": "completed", "message": "Workflow finished", "results": results}
```

Replace the final `return` with this:

```python
    # ── POST-RUN HOOK: Write results and trigger vault sync ──────────────────
    # Serialize execution results to canonical files, then trigger obsidian-sync
    try:
        started_at_str = task_data.get("started_at") if redis_client else datetime.now(timezone.utc).isoformat()
        try:
            started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
        except:
            started_at = datetime.now(timezone.utc)
        
        duration_secs = (datetime.now(timezone.utc) - started_at).total_seconds()
        
        sync_result = await write_and_sync(
            result=results,
            task_id=task.id,
            agents=list(results.keys()),
            duration_seconds=duration_secs,
            auto_sync=True,
            dry_run=False,
        )
        logger.info(
            json.dumps({
                "event": "results_synced_to_vault",
                "task_id": task.id,
                "sync_files": sync_result.get("files_written", {}),
            })
        )
    except Exception as e:
        logger.error(
            json.dumps({
                "event": "result_sync_failed",
                "task_id": task.id,
                "error": str(e),
            })
        )
        # Non-blocking — don't fail the task if sync fails

    return {"status": "completed", "message": "Workflow finished", "results": results}
```

### Step 3: Test the Chain

#### Test 1 — Results files are written

After an execution, check that the files are created:

```bash
# From HyperCode-V2.4 root
ls -la results/latest-*
cat results/latest-summary.md
```

Expected output:
- `latest-summary.md` contains task summary + agent names
- `latest-metrics.json` contains timing + token counts
- `latest-report.md` contains full execution report

#### Test 2 — Obsidian sync is triggered

Check the logs of the crew-orchestrator container:

```bash
docker logs crew-orchestrator --tail 20 | grep "results_synced_to_vault"
```

Expected output:
```
{"event": "results_synced_to_vault", "task_id": "...", "sync_files": {...}}
```

#### Test 3 — Vault was updated on GitHub

Check the vault repo for a fresh commit:

```bash
cd ../BROski-Obsidian-Brain-for-HyperFocus-z0ne
git log --oneline | head -3
```

Expected output:
```
abc1234 feat: sync HyperAgent loop — 2026-06-04T...
def5678 previous commit
...
```

---

## What Happens End-to-End

```
1. POST /execute with task description
   ↓
2. Crew orchestrator runs agents, collects results
   ↓
3. POST-RUN HOOK triggers:
   ├─ result_writer.write_execution_results() 
   │  └─ Writes to ./results/latest-*.md
   ├─ result_writer.trigger_obsidian_sync()
   │  └─ Runs: docker compose -f docker-compose.obsidian-sync.yml run --rm obsidian-sync
   │     └─ Container clones vault fresh
   │     └─ Reads ./results/latest-*.md
   │     └─ Creates session note in PARA structure
   │     └─ Commits + pushes to GitHub
   └─ Response returned to client
   ↓
4. Your Obsidian vault is auto-updated 🧠
```

---

## Files Ready to Go

| File | Location | Status |
|---|---|---|
| `result_writer.py` | `agents/crew-orchestrator/result_writer.py` | ✅ Created |
| `docker-compose.obsidian-sync.yml` | Root | ✅ Updated (stateless) |
| `scripts/obsidian-sync.sh` | Root | ✅ Updated (stateless) |
| `main.py` (with hook) | `agents/crew-orchestrator/main.py` | 🔜 Manual edit needed |

---

## Rollback if Needed

If the sync causes issues, you can disable it by:

1. Setting `dry_run=True` in the `write_and_sync()` call (no git push)
2. Removing the entire try/except block (falls back to old behavior)
3. Setting `auto_sync=False` in the call (writes results but doesn't trigger container)

---

## Next: Test an Execution

Once you wire up main.py, run a test:

```bash
curl -X POST http://127.0.0.1:8081/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_ORCHESTRATOR_API_KEY" \
  -d '{
    "task": {
      "id": "test-sync-001",
      "type": "feature",
      "description": "Build a test HyperAgent loop to verify vault sync",
      "agents": ["backend_specialist"],
      "requires_approval": false
    }
  }'
```

Then watch:
1. Logs for `results_synced_to_vault` event
2. `./results/latest-summary.md` file updated
3. GitHub vault repo for new commits

---

**BROski♾️ — The nervous system is ready. Time to connect it.**

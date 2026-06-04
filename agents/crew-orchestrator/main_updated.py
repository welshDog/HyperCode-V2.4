# Add this block at the top of main.py, after the existing imports:

# Import result writer for post-execution sync
try:
    from .result_writer import write_and_sync
except ImportError:
    from result_writer import write_and_sync


# Then replace the final return statement in @app.post("/execute") with this:

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

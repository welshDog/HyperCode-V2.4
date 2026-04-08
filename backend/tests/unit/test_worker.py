from unittest.mock import MagicMock, patch, mock_open
import pytest


# ── Patch heavy imports before worker loads ──────────────────────────────────
@pytest.fixture(autouse=True)
def _patch_celery(monkeypatch):
    fake_celery = MagicMock()
    fake_celery.task = lambda *a, **kw: (lambda fn: fn)  # passthrough decorator
    monkeypatch.setattr("app.core.celery_app.celery_app", fake_celery, raising=False)


def _make_payload(task_id="abc-123", task_type="code", description="do stuff"):
    return {"id": task_id, "type": task_type, "description": description}


@patch("app.worker.os.makedirs")
@patch("app.worker.os.path.exists", return_value=False)
@patch("builtins.open", mock_open())
@patch("app.worker.SessionLocal")
@patch("app.worker.asyncio.run")
def test_process_agent_job_success(mock_run, mock_session, *_):
    """Happy path — task routed, DB updated, file written."""
    def fake_run(coro):
        coro.close()
        return "Agent plan output here"

    mock_run.side_effect = fake_run
    mock_db = MagicMock()
    mock_session.return_value = mock_db
    mock_task_record = MagicMock()
    mock_task_record.status = None
    mock_task_record.assignee_id = 1
    mock_task_record.project.owner_id = 1
    mock_db.query.return_value.filter.return_value.first.return_value = mock_task_record

    with patch("app.services.broski_service.award_coins") as _award_coins, \
         patch("app.services.broski_service.award_xp") as _award_xp, \
         patch("app.services.broski_service.get_wallet") as _get_wallet:
        wallet = MagicMock()
        wallet.last_first_task_date = None
        _get_wallet.return_value = wallet

        from app.worker import process_agent_job
        result = process_agent_job(_make_payload())

    assert result["status"] == "completed"
    assert "output_file" in result
    assert mock_task_record.status.name in ("DONE", "done") or mock_task_record.status is not None
    assert mock_db.commit.call_count >= 1
    mock_db.close.assert_called_once()


@patch("app.worker.SessionLocal")
@patch("app.worker.asyncio.run")
@patch("app.worker.os.path.exists", return_value=True)
@patch("builtins.open", mock_open())
def test_process_agent_job_task_not_in_db(_mock_exists, mock_run, mock_session):
    """Task missing from DB — logs warning, still returns completed."""
    def fake_run(coro):
        coro.close()
        return "some output"

    mock_run.side_effect = fake_run
    mock_db = MagicMock()
    mock_session.return_value = mock_db
    mock_db.query.return_value.filter.return_value.first.return_value = None

    from app.worker import process_agent_job
    result = process_agent_job(_make_payload(task_id="missing-99"))

    assert result["status"] == "completed"
    mock_db.commit.assert_not_called()
    mock_db.close.assert_called_once()


@patch("app.worker.asyncio.run")
def test_process_agent_job_router_failure(mock_run):
    """Router throws — worker catches and returns failed status."""
    def fake_run(coro):
        coro.close()
        raise RuntimeError("router exploded")

    mock_run.side_effect = fake_run
    from app.worker import process_agent_job
    result = process_agent_job(_make_payload())

    assert result["status"] == "failed"
    assert "router exploded" in result["error"]


@patch("app.worker.SessionLocal")
@patch("app.worker.asyncio.run")
@patch("app.worker.os.path.exists", return_value=True)
@patch("builtins.open", mock_open())
def test_process_agent_job_db_error(_mock_exists, mock_run, mock_session):
    """DB commit fails — rollback is called, still returns completed."""
    def fake_run(coro):
        coro.close()
        return "plan"

    mock_run.side_effect = fake_run
    mock_db = MagicMock()
    mock_session.return_value = mock_db
    mock_task_record = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_task_record
    mock_db.commit.side_effect = Exception("DB boom")

    from app.worker import process_agent_job
    result = process_agent_job(_make_payload())

    assert result["status"] == "completed"
    mock_db.rollback.assert_called_once()
    mock_db.close.assert_called_once()

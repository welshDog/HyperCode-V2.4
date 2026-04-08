from unittest.mock import MagicMock, patch


def test_get_db_yields_and_closes():
    """get_db should yield a session then close it."""
    mock_session = MagicMock()

    with patch("app.db.session.SessionLocal", return_value=mock_session):
        from app.db.session import get_db
        gen = get_db()
        db = next(gen)
        assert db == mock_session
        try:
            next(gen)
        except StopIteration:
            pass
        mock_session.close.assert_called_once()


def test_get_db_closes_on_exception():
    """get_db must close the session even when an exception is raised mid-use."""
    mock_session = MagicMock()

    with patch("app.db.session.SessionLocal", return_value=mock_session):
        from app.db.session import get_db
        gen = get_db()
        next(gen)
        try:
            gen.throw(RuntimeError("test error"))
        except RuntimeError:
            pass
        mock_session.close.assert_called_once()

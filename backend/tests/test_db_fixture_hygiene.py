"""Regression test for the flaky `QueuePool limit of size 5 overflow 10 reached` errors at teardown.

The shared `db` fixture (conftest.py) used to hand out a Session and never close it. A test that ends with a read (for
example the `wallet()` helper in test_crew_quests.py does `expire_all()` and a query) leaves a transaction open, and that
holds a connection checked out of the test engine's pool until the garbage collector happens to free the session. Enough of
those pile up and the next `drop_all` in the fixture teardown waits 30 seconds for a connection and errors, in whichever
test happens to be running. That is why the victim changed from run to run.

The two tests below must run in this order (pytest keeps file order). The check is relative, so unrelated leaks elsewhere
in the suite cannot make it fail.
"""
from sqlalchemy import text

_HELD = []


def test_a_test_that_leaves_a_read_transaction_open(db):
    bind = db.get_bind()
    baseline = bind.pool.checkedout()
    db.execute(text("select 1"))  # begins a transaction and checks a connection out of the pool
    assert bind.pool.checkedout() == baseline + 1
    # Keep the session alive: now only the db fixture's teardown can release the connection, not the garbage collector.
    _HELD.append((db, bind, baseline))


def test_the_db_fixture_released_that_connection():
    assert _HELD, "the previous test did not run (run this file in order)"
    _session, bind, baseline = _HELD.pop()  # `_session` is still referenced here, so GC cannot be what freed the connection
    assert bind.pool.checkedout() <= baseline, "db fixture teardown left a connection checked out"

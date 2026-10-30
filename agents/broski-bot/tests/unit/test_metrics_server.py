"""The cog bot must expose /metrics (the broski-bot scrape target was down)."""
import builtins
import socket
import urllib.request

import metrics_server


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_serves_metrics_with_ready_gauge(monkeypatch):
    monkeypatch.delenv("PROMETHEUS_ENABLED", raising=False)
    port = _free_port()
    assert metrics_server.start_metrics_server(port) is True
    metrics_server.set_ready(3)
    body = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=5).read().decode()
    assert "broski_bot_ready 1.0" in body
    assert "broski_bot_guilds 3.0" in body


def test_port_from_environment(monkeypatch):
    port = _free_port()
    monkeypatch.setenv("PROMETHEUS_PORT", str(port))
    assert metrics_server.start_metrics_server() is True
    assert urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=5).status == 200


def test_disabled_by_env(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_ENABLED", "false")
    port = _free_port()
    assert metrics_server.start_metrics_server(port) is False
    with socket.socket() as s:  # nothing is listening
        assert s.connect_ex(("127.0.0.1", port)) != 0


def test_busy_port_fails_open(monkeypatch):
    monkeypatch.delenv("PROMETHEUS_ENABLED", raising=False)
    def busy(_port):  # a real bind clash is platform-dependent (Windows allows it)
        raise OSError(98, "Address already in use")

    monkeypatch.setattr(metrics_server, "start_http_server", busy)
    assert metrics_server.start_metrics_server(_free_port()) is False


def test_missing_library_fails_open(monkeypatch):
    monkeypatch.delenv("PROMETHEUS_ENABLED", raising=False)
    monkeypatch.setattr(metrics_server, "start_http_server", None)
    assert metrics_server.start_metrics_server(_free_port()) is False

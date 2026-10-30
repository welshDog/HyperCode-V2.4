"""Tests for the docker-stats exporter's pure functions (no Docker needed)."""
import exporter

V2_STATS = {
    "cpu_stats": {"cpu_usage": {"total_usage": 2_500_000_000}},
    "memory_stats": {
        "usage": 300_000_000,
        "limit": 536_870_912,
        "stats": {"inactive_file": 50_000_000},
    },
    "networks": {
        "eth0": {"rx_bytes": 100, "tx_bytes": 40},
        "eth1": {"rx_bytes": 20, "tx_bytes": 2},
    },
}


def test_parse_stats_cgroup_v2():
    s = exporter.parse_stats(V2_STATS)
    assert s["cpu_seconds"] == 2.5
    assert s["mem_usage"] == 300_000_000
    assert s["mem_working_set"] == 250_000_000
    assert s["mem_limit"] == 536_870_912
    assert s["net_rx"] == 120
    assert s["net_tx"] == 42


def test_parse_stats_cgroup_v1_inactive_key():
    raw = {"memory_stats": {"usage": 100, "stats": {"total_inactive_file": 30}}}
    assert exporter.parse_stats(raw)["mem_working_set"] == 70


def test_working_set_never_negative():
    raw = {"memory_stats": {"usage": 10, "stats": {"inactive_file": 99}}}
    assert exporter.parse_stats(raw)["mem_working_set"] == 0


def test_unbounded_limit_reported_as_zero():
    raw = {"memory_stats": {"usage": 10, "limit": 2**63 - 1}}
    assert exporter.parse_stats(raw)["mem_limit"] == 0


def test_missing_fields_default_to_zero():
    s = exporter.parse_stats({})
    assert s == {
        "cpu_seconds": 0.0, "mem_usage": 0, "mem_working_set": 0,
        "mem_limit": 0, "net_rx": 0, "net_tx": 0,
    }


def test_label_escaping():
    assert exporter.esc('a"b\\c\nd') == 'a\\"b\\\\c\\nd'


def test_render_uses_cadvisor_metric_names_and_labels():
    sample = {"name": "hypercode-core", "image": "core:1", **exporter.parse_stats(V2_STATS)}
    text = exporter.render([sample], now=1000.0, errors=0, duration=0.5)
    assert 'container_memory_usage_bytes{name="hypercode-core",image="core:1"} 300000000' in text
    assert 'container_memory_working_set_bytes{name="hypercode-core",image="core:1"} 250000000' in text
    assert 'container_spec_memory_limit_bytes{name="hypercode-core",image="core:1"} 536870912' in text
    assert 'container_cpu_usage_seconds_total{name="hypercode-core",image="core:1"} 2.5' in text
    assert 'container_network_receive_bytes_total{name="hypercode-core",image="core:1"} 120' in text
    assert 'container_network_transmit_bytes_total{name="hypercode-core",image="core:1"} 42' in text
    assert 'container_last_seen{name="hypercode-core",image="core:1"} 1000.0' in text
    assert "docker_stats_exporter_containers 1" in text
    assert "# TYPE container_cpu_usage_seconds_total counter" in text


def test_render_empty_is_valid():
    text = exporter.render([], now=1.0, errors=2, duration=0.1)
    assert "docker_stats_exporter_containers 0" in text
    assert "docker_stats_exporter_errors 2" in text


def test_clean_name_strips_slash():
    assert exporter.clean_name({"Names": ["/grafana"]}) == "grafana"
    assert exporter.clean_name({"Names": []}) == ""

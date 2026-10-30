"""Tiny per-container metrics exporter for Docker Desktop hosts.

cAdvisor cannot read containers on the containerd image store, so this reads
`docker stats` data through the read-only docker-socket-proxy and exposes it
under cAdvisor's metric names, which the existing dashboards already query.

Only GET /containers/json and GET /containers/{id}/stats are used: never
inspect (it would expose container environment variables). Standard library only.
"""
import json
import os
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DOCKER_HOST = os.environ.get("DOCKER_HOST_URL", "http://docker-socket-proxy:2375")
INTERVAL = float(os.environ.get("COLLECT_INTERVAL_SECONDS", "30"))
PORT = int(os.environ.get("EXPORTER_PORT", "9417"))
WORKERS = int(os.environ.get("COLLECT_WORKERS", "4"))
HTTP_TIMEOUT = 10
UNBOUNDED = 2**60

METRICS = [
    ("container_memory_usage_bytes", "gauge", "mem_usage"),
    ("container_memory_working_set_bytes", "gauge", "mem_working_set"),
    ("container_spec_memory_limit_bytes", "gauge", "mem_limit"),
    ("container_cpu_usage_seconds_total", "counter", "cpu_seconds"),
    ("container_network_receive_bytes_total", "counter", "net_rx"),
    ("container_network_transmit_bytes_total", "counter", "net_tx"),
]


def esc(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def clean_name(container):
    names = container.get("Names") or []
    return names[0].lstrip("/") if names else ""


def parse_stats(raw):
    mem = raw.get("memory_stats") or {}
    detail = mem.get("stats") or {}
    usage = int(mem.get("usage") or 0)
    inactive = int(detail.get("inactive_file", detail.get("total_inactive_file", 0)) or 0)
    limit = int(mem.get("limit") or 0)
    nets = (raw.get("networks") or {}).values()
    cpu = ((raw.get("cpu_stats") or {}).get("cpu_usage") or {}).get("total_usage") or 0
    return {
        "cpu_seconds": cpu / 1e9,
        "mem_usage": usage,
        "mem_working_set": max(usage - inactive, 0),
        "mem_limit": 0 if limit >= UNBOUNDED else limit,
        "net_rx": sum(int(n.get("rx_bytes") or 0) for n in nets),
        "net_tx": sum(int(n.get("tx_bytes") or 0) for n in nets),
    }


def render(samples, now, errors, duration):
    lines = []
    for metric, kind, key in METRICS:
        lines.append(f"# TYPE {metric} {kind}")
        for s in samples:
            labels = f'name="{esc(s["name"])}",image="{esc(s["image"])}"'
            lines.append(f"{metric}{{{labels}}} {s[key]}")
    lines.append("# TYPE container_last_seen gauge")
    for s in samples:
        lines.append(f'container_last_seen{{name="{esc(s["name"])}",image="{esc(s["image"])}"}} {now}')
    lines += [
        "# TYPE docker_stats_exporter_containers gauge",
        f"docker_stats_exporter_containers {len(samples)}",
        "# TYPE docker_stats_exporter_errors gauge",
        f"docker_stats_exporter_errors {errors}",
        "# TYPE docker_stats_exporter_collect_duration_seconds gauge",
        f"docker_stats_exporter_collect_duration_seconds {duration:.3f}",
    ]
    return "\n".join(lines) + "\n"


def _get(path):
    with urllib.request.urlopen(DOCKER_HOST + path, timeout=HTTP_TIMEOUT) as resp:
        return json.load(resp)


def _one(container):
    stats = _get(f"/containers/{container['Id']}/stats?stream=false&one-shot=true")
    return {"name": clean_name(container), "image": container.get("Image", ""), **parse_stats(stats)}


def collect():
    started = time.time()
    containers = _get("/containers/json")
    samples, errors = [], 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for fut in [pool.submit(_one, c) for c in containers]:
            try:
                samples.append(fut.result())
            except Exception:
                errors += 1
    return render(samples, now=started, errors=errors, duration=time.time() - started)


_lock = threading.Lock()
_body = "# exporter starting\n"
_ready = False


def _loop():
    global _body, _ready
    while True:
        try:
            body = collect()
            with _lock:
                _body, _ready = body, True
        except Exception as exc:  # proxy down: keep serving the last good data
            print(f"collect failed: {type(exc).__name__}", flush=True)
        time.sleep(INTERVAL)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            code, body = (200, "ok\n") if _ready else (503, "no data yet\n")
        elif self.path == "/metrics":
            with _lock:
                code, body = 200, _body
        else:
            code, body = 404, "not found\n"
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

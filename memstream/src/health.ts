import os from "os";
import http from "http";
import net from "net";
import { logEvent, log } from "./logger.js";

export interface HealthSnapshot {
  ram_used_percent: number;
  ram_free_gb: number;
  tokens_per_sec: number;
  current_mode: string;
  pressure: "🟢 LOW" | "🟡 MEDIUM" | "🔴 HIGH";
  timestamp: string;
}

let _latestSnapshot: HealthSnapshot = {
  ram_used_percent: 0,
  ram_free_gb: 0,
  tokens_per_sec: 0,
  current_mode: "idle",
  pressure: "🟢 LOW",
  timestamp: new Date().toISOString()
};

let _throttleDelayMs = 0;

let lastPressure: HealthSnapshot["pressure"] = "🟢 LOW";
let lastHighLogMs = 0;

export function updateHealth(patch: Partial<HealthSnapshot>) {
  const total = os.totalmem();
  const free = os.freemem();
  const usedPct = ((total - free) / total) * 100;

  const pressure = usedPct > 85 ? "🔴 HIGH" : usedPct > 70 ? "🟡 MEDIUM" : "🟢 LOW";

  _latestSnapshot = {
    ..._latestSnapshot,
    ...patch,
    ram_used_percent: usedPct,
    ram_free_gb: free / 1024 ** 3,
    pressure,
    timestamp: new Date().toISOString()
  };

  if (pressure !== lastPressure) {
    if (pressure === "🔴 HIGH") {
      log.warn("RAM pressure is HIGH — Healer notified!");
      logEvent({ event: "ram_pressure_high", ram_free_gb: _latestSnapshot.ram_free_gb });
    }
    lastPressure = pressure;
  }
}

export function getHealthSnapshot(): HealthSnapshot {
  return _latestSnapshot;
}

export function getThrottleDelay(): number {
  return _throttleDelayMs;
}

async function findFreePort(startPort = 8009, maxAttempts = 20): Promise<number> {
  let port = startPort;
  for (let i = 0; i < maxAttempts; i++) {
    const candidate = port + i;
    try {
      await new Promise<void>((resolve, reject) => {
        const probe = net.createServer();
        probe.unref();
        probe.once("error", (err: any) => {
          probe.close();
          reject(err);
        });
        probe.listen(candidate, "127.0.0.1", () => {
          probe.close(() => resolve());
        });
      });
      return candidate;
    } catch (err: any) {
      if (err?.code === "EADDRINUSE") continue;
      throw err;
    }
  }
  throw new Error(`No free ports available in range ${startPort}-${startPort + maxAttempts - 1}`);
}

export async function startHealthServer(
  preferredPort = 8009
): Promise<{ server: http.Server; port: number } | null> {
  const token = process.env.MEMSTREAM_HEALTH_TOKEN ?? "";
  if (!token) {
    log.warn("Health server disabled — set MEMSTREAM_HEALTH_TOKEN to enable.");
    return null;
  }

  const envPortRaw = process.env.MEMSTREAM_HEALTH_PORT;
  const envPort = envPortRaw ? Number.parseInt(envPortRaw, 10) : null;
  const effectivePreferred = Number.isFinite(envPort as any) && (envPort as any) > 0 ? (envPort as any) : preferredPort;

  let scanStart = effectivePreferred;
  if (scanStart === 8008) scanStart = 8009;

  let chosenPort: number;
  try {
    chosenPort = await findFreePort(scanStart, 20);
  } catch (err: any) {
    log.error(err?.message ?? String(err));
    return null;
  }

  if (chosenPort !== effectivePreferred) {
    log.info(`Port ${effectivePreferred} in use — using ${chosenPort} instead`);
  }

  const server = http.createServer((req, res) => {
    res.setHeader("Cache-Control", "no-store");

    const auth = String(req.headers["authorization"] ?? "");
    if (auth !== `Bearer ${token}`) {
      res.writeHead(401);
      res.end("Unauthorized");
      return;
    }

    if (req.url === "/throttle" && req.method === "POST") {
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
        if (body.length > 1024 * 1024) req.destroy();
      });
      req.on("end", () => {
        try {
          const parsed = JSON.parse(body || "{}");
          const delay = Number(parsed?.delay_ms ?? 0);
          if (!Number.isFinite(delay) || delay < 0) {
            res.writeHead(400, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ ok: false, error: "invalid_delay_ms" }));
            return;
          }
          _throttleDelayMs = Math.floor(delay);
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ ok: true, delay_ms: _throttleDelayMs }));
        } catch {
          res.writeHead(400, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ ok: false, error: "invalid_json" }));
        }
      });
      return;
    }

    if (req.url === "/health/memstream") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify(_latestSnapshot));
      return;
    }

    if (req.url === "/metrics") {
      res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
      res.end(
        [
          `memstream_ram_used_percent ${_latestSnapshot.ram_used_percent.toFixed(2)}`,
          `memstream_ram_free_gb ${_latestSnapshot.ram_free_gb.toFixed(2)}`,
          `memstream_tokens_per_sec ${_latestSnapshot.tokens_per_sec.toFixed(2)}`
        ].join("\n")
      );
      return;
    }

    res.writeHead(404);
    res.end("Not found");
  });

  await new Promise<void>((resolve) => {
    server.once("error", async (err: any) => {
      if (err?.code !== "EADDRINUSE") {
        log.error(err?.message ?? String(err));
        resolve();
        return;
      }
      try {
        const fallback = await findFreePort(chosenPort + 1, 20);
        log.info(`Port ${chosenPort} in use — using ${fallback} instead`);
        chosenPort = fallback;
        server.listen(chosenPort, "127.0.0.1", () => resolve());
      } catch (e: any) {
        log.error(e?.message ?? String(e));
        resolve();
      }
    });
    server.listen(chosenPort, "127.0.0.1", () => resolve());
  });

  if (!server.listening) return null;

  log.success(`Healer health → http://127.0.0.1:${chosenPort}/health/memstream`);
  return { server, port: chosenPort };
}

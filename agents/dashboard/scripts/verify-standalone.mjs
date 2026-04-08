import fs from "node:fs/promises";
import net from "node:net";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dashboardDir = path.resolve(__dirname, "..");
const standaloneDir = path.join(dashboardDir, ".next", "standalone", "agents", "dashboard");

async function findFreePort() {
  return await new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const addr = srv.address();
      srv.close(() => resolve(addr.port));
    });
  });
}

async function waitFor(url, timeoutMs = 60_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url, { redirect: "follow" });
      if (res.ok) return;
    } catch {
      // ignore
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Timeout waiting for ${url}`);
}

async function main() {
  const dstStatic = path.join(standaloneDir, ".next", "static");
  await fs.rm(dstStatic, { recursive: true, force: true });

  const prep = spawn(process.execPath, [path.join(__dirname, "prepare-standalone.mjs")], {
    cwd: dashboardDir,
    stdio: "inherit",
    env: process.env,
  });
  const prepCode = await new Promise((resolve) => prep.on("exit", resolve));
  if (prepCode !== 0) process.exit(prepCode ?? 1);

  const port = await findFreePort();
  const child = spawn(process.execPath, [path.join(standaloneDir, "server.js")], {
    cwd: standaloneDir,
    stdio: "inherit",
    env: { ...process.env, HOSTNAME: "127.0.0.1", PORT: String(port) },
  });

  try {
    const base = `http://127.0.0.1:${port}`;
    await waitFor(`${base}/`);

    const healthRes = await fetch(`${base}/api/health`);
    if (!healthRes.ok) throw new Error(`/api/health failed: ${healthRes.status}`);

    const html = await fetch(`${base}/`).then((r) => r.text());
    const m = html.match(/\/_next\/static\/chunks\/[^"']+\.js/);
    if (!m) throw new Error("No chunk reference found in HTML");

    const chunkUrl = base + m[0];
    const chunkRes = await fetch(chunkUrl);
    if (!chunkRes.ok) throw new Error(`Static chunk fetch failed: ${chunkUrl} -> ${chunkRes.status}`);

    process.stdout.write("ok: standalone serves _next/static chunks and /api/health\n");
  } finally {
    child.kill("SIGTERM");
  }
}

main().catch((err) => {
  process.stderr.write(String(err?.stack || err) + "\n");
  process.exit(1);
});


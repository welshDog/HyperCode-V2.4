import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dashboardDir = path.resolve(__dirname, "..");
const standaloneDir = path.join(dashboardDir, ".next", "standalone", "agents", "dashboard");
const serverJs = path.join(standaloneDir, "server.js");

async function main() {
  const prepare = spawn(process.execPath, [path.join(__dirname, "prepare-standalone.mjs")], {
    cwd: dashboardDir,
    stdio: "inherit",
    env: process.env,
  });
  const code = await new Promise((resolve) => prepare.on("exit", resolve));
  if (code !== 0) process.exit(code ?? 1);

  const child = spawn(process.execPath, [serverJs], {
    cwd: standaloneDir,
    stdio: "inherit",
    env: process.env,
  });

  child.on("exit", (c) => process.exit(c ?? 0));
}

main().catch((err) => {
  process.stderr.write(String(err?.stack || err) + "\n");
  process.exit(1);
});


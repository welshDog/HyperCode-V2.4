import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dashboardDir = path.resolve(__dirname, "..");
const standaloneDir = path.join(dashboardDir, ".next", "standalone", "agents", "dashboard");
const srcStatic = path.join(dashboardDir, ".next", "static");
const dstStatic = path.join(standaloneDir, ".next", "static");

async function exists(p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function ensureCopiedDir(src, dst) {
  if (!(await exists(src))) {
    throw new Error(`Missing source directory: ${src}`);
  }
  await fs.mkdir(dst, { recursive: true });
  await fs.cp(src, dst, { recursive: true, force: true });
}

async function main() {
  if (!(await exists(standaloneDir))) {
    throw new Error(
      `Missing standalone output at ${standaloneDir}. Run \`npm run build\` first (next output: standalone).`
    );
  }

  await ensureCopiedDir(srcStatic, dstStatic);

  const publicDir = path.join(dashboardDir, "public");
  const dstPublic = path.join(standaloneDir, "public");
  if (await exists(publicDir)) {
    await ensureCopiedDir(publicDir, dstPublic);
  }

  process.stdout.write("ok: prepared standalone (static/public)\n");
}

main().catch((err) => {
  process.stderr.write(String(err?.stack || err) + "\n");
  process.exit(1);
});


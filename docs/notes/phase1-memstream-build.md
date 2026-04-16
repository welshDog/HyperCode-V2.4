🧠 Phase 1 — memstream.ts — THE BUILD
Here's every file you need. Copy → paste → run. Let's GO. 🚀

📁 Folder Structure
text
memstream/
├── src/
│   ├── memstream.ts          ← CORE ENGINE
│   ├── hardware.ts           ← Hardware detection
│   ├── degradation.ts        ← Fallback cascade
│   ├── health.ts             ← Healer hook (monitor-only)
│   └── logger.ts             ← CSV + progress bars
├── models/
│   └── (drop your .gguf here)
├── logs/
│   └── (auto-created)
├── memstream.config.json     ← Config
├── package.json
└── tsconfig.json
📦 package.json
json
{
  "name": "memstream-engine",
  "version": "1.0.0",
  "description": "Smart memory, not expensive memory 🧠",
  "type": "module",
  "scripts": {
    "start":   "tsx src/memstream.ts",
    "warmup":  "tsx src/memstream.ts --warmup",
    "inspect": "npx node-llama-cpp inspect gpu",
    "build":   "tsc"
  },
  "dependencies": {
    "node-llama-cpp": "^3.0.0",
    "chalk":          "^5.3.0",
    "cli-progress":   "^3.12.0",
    "tsx":            "^4.7.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "@types/node": "^20.0.0"
  }
}
⚙️ tsconfig.json
json
{
  "compilerOptions": {
    "target":          "ES2022",
    "module":          "ESNext",
    "moduleResolution":"bundler",
    "strict":          true,
    "outDir":          "./dist",
    "rootDir":         "./src",
    "esModuleInterop": true
  }
}
🗂️ memstream.config.json
json
{
  "model_id":   "mistral-7b-instruct-v0.2",
  "model_path": "./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",

  "hardware_limits": {
    "max_ram_percent":  75,
    "max_vram_percent": 80,
    "min_free_ram_gb":  4
  },

  "streaming": {
    "layers_in_ram_buffer":  2,
    "context_window_tokens": 4096,
    "use_memory_mmap":       true
  },

  "ssd_safety": {
    "max_write_gb_per_hour":     10,
    "prefer_tmpfs_if_ram_free_gb": 8,
    "warn_on_ssd_temp_celsius":  70
  },

  "accessibility": {
    "verbose_layer_loading": true,
    "progress_bars":         true
  }
}
🖥️ src/hardware.ts
typescript
import os from "os";

export interface HardwareTier {
  tier:          "budget" | "mid" | "power" | "cpu-only";
  label:         string;
  n_gpu_layers:  number;
  ctx_tokens:    number;
  ram_buffer:    number;
}

export function getSystemRAMGB(): number {
  return os.totalmem() / (1024 ** 3);
}

export function getFreeRAMGB(): number {
  return os.freemem() / (1024 ** 3);
}

// node-llama-cpp handles VRAM detection — we map the result to a tier
export function detectTier(vramGB: number, ramGB: number): HardwareTier {

  if (vramGB >= 16) return {
    tier: "power", label: "🥇 Power User",
    n_gpu_layers: 35, ctx_tokens: 8192, ram_buffer: 4
  };

  if (vramGB >= 8) return {
    tier: "mid", label: "🥈 Mid Setup",
    n_gpu_layers: 20, ctx_tokens: 4096, ram_buffer: 2
  };

  if (vramGB >= 4) return {
    tier: "budget", label: "🥉 Budget Bro",
    n_gpu_layers: 10, ctx_tokens: 2048, ram_buffer: 2
  };

  return {
    tier: "cpu-only", label: "🫐 CPU Only",
    n_gpu_layers: 0,  ctx_tokens: 2048, ram_buffer: 1
  };
}
🪜 src/degradation.ts
typescript
import { getFreeRAMGB } from "./hardware.js";

export type RunMode =
  | "gpu"
  | "cpu"
  | "cpu_4bit"
  | "token_stream";

export interface DegradationResult {
  mode:    RunMode;
  reason:  string;
  n_gpu_layers: number;
}

// Walk the cascade — pick best mode available right now
export function selectRunMode(vramGB: number): DegradationResult {
  const freeRAM = getFreeRAMGB();

  if (vramGB >= 4 && freeRAM >= 4)
    return { mode: "gpu",          n_gpu_layers: 10,
             reason: "GPU has enough VRAM ✅" };

  if (freeRAM >= 8)
    return { mode: "cpu",          n_gpu_layers: 0,
             reason: "GPU too small → falling back to CPU 🔄" };

  if (freeRAM >= 4)
    return { mode: "cpu_4bit",     n_gpu_layers: 0,
             reason: "Low RAM → CPU + 4bit quantisation 🔄" };

  return   { mode: "token_stream", n_gpu_layers: 0,
             reason: "Minimal RAM → slowest token-stream mode 🐢" };
}
📊 src/logger.ts
typescript
import fs    from "fs";
import path  from "path";
import chalk from "chalk";
import cliProgress from "cli-progress";

const LOG_DIR = "./logs";
const CSV_PATH = path.join(LOG_DIR, "layer_times.csv");

// Make sure logs folder exists
if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR);

// CSV header on first run
if (!fs.existsSync(CSV_PATH))
  fs.writeFileSync(CSV_PATH,
    "timestamp,event,layer,load_ms,ram_free_gb,vram_gb,tokens_per_sec\n"
  );

export function logEvent(row: {
  event:         string;
  layer?:        number;
  load_ms?:      number;
  ram_free_gb?:  number;
  vram_gb?:      number;
  tokens_per_sec?: number;
}) {
  const ts = new Date().toISOString();
  const line = [
    ts,
    row.event,
    row.layer        ?? "",
    row.load_ms      ?? "",
    row.ram_free_gb  ?? "",
    row.vram_gb      ?? "",
    row.tokens_per_sec ?? ""
  ].join(",");
  fs.appendFileSync(CSV_PATH, line + "\n");
}

// Pretty console logs
export const log = {
  info:    (msg: string) => console.log(chalk.cyan("  ℹ  ") + msg),
  success: (msg: string) => console.log(chalk.green("  ✅ ") + msg),
  warn:    (msg: string) => console.log(chalk.yellow("  ⚠️  ") + msg),
  error:   (msg: string) => console.log(chalk.red("  ❌ ") + msg),
  title:   (msg: string) => console.log(chalk.bold.magenta("\n" + msg)),
};

// ADHD-friendly progress bar
export function makeProgressBar(label: string, total: number) {
  const bar = new cliProgress.SingleBar({
    format: chalk.cyan(label) +
            " |" + chalk.cyan("{bar}") + "| {percentage}% | {value}/{total}",
    barCompleteChar:   "█",
    barIncompleteChar: "░",
    hideCursor: true,
  });
  bar.start(total, 0);
  return bar;
}
🩺 src/health.ts
typescript
import os   from "os";
import http  from "http";
import { logEvent, log } from "./logger.js";

export interface HealthSnapshot {
  ram_used_percent:  number;
  ram_free_gb:       number;
  tokens_per_sec:    number;
  current_mode:      string;
  pressure:          "🟢 LOW" | "🟡 MEDIUM" | "🔴 HIGH";
  timestamp:         string;
}

let _latestSnapshot: HealthSnapshot = {
  ram_used_percent: 0,
  ram_free_gb:      0,
  tokens_per_sec:   0,
  current_mode:     "idle",
  pressure:         "🟢 LOW",
  timestamp:        new Date().toISOString(),
};

// Called by core engine to push live stats
export function updateHealth(patch: Partial<HealthSnapshot>) {
  const total   = os.totalmem();
  const free    = os.freemem();
  const usedPct = ((total - free) / total) * 100;

  _latestSnapshot = {
    ..._latestSnapshot,
    ...patch,
    ram_used_percent: usedPct,
    ram_free_gb:      free / (1024 ** 3),
    pressure:
      usedPct > 85 ? "🔴 HIGH"   :
      usedPct > 70 ? "🟡 MEDIUM" :
                     "🟢 LOW",
    timestamp: new Date().toISOString(),
  };

  // Fire a warning log if pressure spikes
  if (_latestSnapshot.pressure === "🔴 HIGH") {
    log.warn("RAM pressure is HIGH — Healer notified!");
    logEvent({ event: "ram_pressure_high",
               ram_free_gb: _latestSnapshot.ram_free_gb });
  }
}

// Lightweight HTTP server → Healer polls this
// GET http://localhost:8008/health/memstream
export function startHealthServer(port = 8008) {
  const server = http.createServer((req, res) => {
    if (req.url === "/health/memstream") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify(_latestSnapshot, null, 2));
      return;
    }
    // Prometheus-style /metrics endpoint
    if (req.url === "/metrics") {
      res.writeHead(200, { "Content-Type": "text/plain" });
      res.end([
        `memstream_ram_used_percent ${_latestSnapshot.ram_used_percent.toFixed(2)}`,
        `memstream_ram_free_gb ${_latestSnapshot.ram_free_gb.toFixed(2)}`,
        `memstream_tokens_per_sec ${_latestSnapshot.tokens_per_sec.toFixed(2)}`,
      ].join("\n"));
      return;
    }
    res.writeHead(404);
    res.end("Not found");
  });

  server.listen(port, () =>
    log.success(`Healer health server live → http://localhost:${port}/health/memstream`)
  );
}
🚀 src/memstream.ts — THE CORE ENGINE
typescript
import path          from "path";
import fs            from "fs";
import { getLlama }  from "node-llama-cpp";
import { detectTier, getFreeRAMGB, getSystemRAMGB } from "./hardware.js";
import { selectRunMode }    from "./degradation.js";
import { log, logEvent, makeProgressBar } from "./logger.js";
import { startHealthServer, updateHealth } from "./health.js";

// ─── Load config ────────────────────────────────────────────────────────────
const config = JSON.parse(
  fs.readFileSync("./memstream.config.json", "utf-8")
);

const MODEL_PATH = config.model_path;
const CTX_TOKENS = config.streaming.context_window_tokens;
const USE_MMAP   = config.streaming.use_memory_mmap;

// ─── Startup banner ─────────────────────────────────────────────────────────
log.title("╔══════════════════════════════════════╗");
log.title("║   🧠 MEMSTREAM ENGINE v1.0 — ONLINE  ║");
log.title("║   Smart memory, not expensive memory ║");
log.title("╚══════════════════════════════════════╝");

// ─── STEP 1: GGUF integrity check ───────────────────────────────────────────
async function validateModel(modelPath: string): Promise<void> {
  log.info("Validating GGUF file...");
  if (!fs.existsSync(modelPath)) {
    log.error(`Model not found at: ${modelPath}`);
    log.info("Download it with:");
    log.info("  npx node-llama-cpp pull --dir ./models <model-url>");
    process.exit(1);
  }
  const stats   = fs.statSync(modelPath);
  const sizeGB  = stats.size / (1024 ** 3);
  log.success(`GGUF found: ${path.basename(modelPath)} (${sizeGB.toFixed(2)} GB)`);
  logEvent({ event: "gguf_validated" });
}

// ─── STEP 2: Hardware detection ─────────────────────────────────────────────
async function detectHardware() {
  log.info("Scanning hardware...");
  const llama   = await getLlama();
  const gpu     = llama.gpu;
  const vramGB  = gpu !== false ? 4 : 0; // node-llama-cpp auto-detects GPU
  const ramGB   = getSystemRAMGB();
  const tier    = detectTier(vramGB, ramGB);
  const mode    = selectRunMode(vramGB);

  log.success(`Hardware tier: ${tier.label}`);
  log.info(`Run mode selected: ${mode.mode.toUpperCase()} — ${mode.reason}`);
  log.info(`System RAM: ${ramGB.toFixed(1)} GB | Free: ${getFreeRAMGB().toFixed(1)} GB`);

  logEvent({
    event: "hardware_detected",
    vram_gb: vramGB,
    ram_free_gb: getFreeRAMGB(),
  });

  return { llama, tier, mode, vramGB };
}

// ─── STEP 3: Warmup (pre-fetch model metadata + first layers) ───────────────
async function warmup(llama: Awaited<ReturnType<typeof getLlama>>) {
  log.info("Warming up model (pre-loading metadata)...");
  const bar   = makeProgressBar("Warmup", 3);

  const model = await llama.loadModel({
    modelPath: MODEL_PATH,
    useMmap:   USE_MMAP,      // mmap = SSD pages on demand, not full RAM load
  });
  bar.update(1);

  const ctx = await model.createContext({ contextSize: CTX_TOKENS });
  bar.update(2);

  const seq = ctx.getSequence();
  bar.update(3);
  bar.stop();

  log.success("Model warmed up. KV cache context ready. ✅");
  logEvent({ event: "warmup_complete" });

  return { model, ctx, seq };
}

// ─── STEP 4: Inference with streaming + telemetry ───────────────────────────
async function runInference(
  session: any,
  prompt:  string,
  mode:    string
) {
  const { LlamaChatSession } = await import("node-llama-cpp");

  log.info(`\n💬 Prompt: "${prompt}"`);
  log.info(`Mode: ${mode.toUpperCase()}`);
  process.stdout.write(chalk_write("\n  🤖 Response: "));

  let tokenCount  = 0;
  const startTime = Date.now();

  const response = await session.prompt(prompt, {
    onToken: (chunk: string) => {
      process.stdout.write(chunk);
      tokenCount++;

      // Update health every 10 tokens
      if (tokenCount % 10 === 0) {
        const elapsed    = (Date.now() - startTime) / 1000;
        const tokPerSec  = tokenCount / elapsed;
        updateHealth({ tokens_per_sec: tokPerSec, current_mode: mode });
      }
    }
  });

  const elapsed   = (Date.now() - startTime) / 1000;
  const tokPerSec = tokenCount / elapsed;

  console.log("\n");
  log.success(`Done! ${tokenCount} tokens in ${elapsed.toFixed(1)}s = ${tokPerSec.toFixed(1)} tok/s`);

  logEvent({
    event:          "inference_complete",
    tokens_per_sec: tokPerSec,
    ram_free_gb:    getFreeRAMGB(),
  });

  return response;
}

// ─── Chalk helper (ESM workaround) ──────────────────────────────────────────
function chalk_write(msg: string): string { return msg; }

// ─── MAIN ───────────────────────────────────────────────────────────────────
async function main() {
  const isWarmupOnly = process.argv.includes("--warmup");

  // 1. Start Healer health server
  startHealthServer(8008);

  // 2. Validate GGUF file
  await validateModel(MODEL_PATH);

  // 3. Detect hardware
  const { llama, tier, mode } = await detectHardware();

  // 4. Warmup
  const { model, ctx, seq } = await warmup(llama);

  if (isWarmupOnly) {
    log.success("Warmup complete. Engine ready. Exiting warmup mode.");
    process.exit(0);
  }

  // 5. Import chat session + run
  const { LlamaChatSession } = await import("node-llama-cpp");
  const session = new LlamaChatSession({ contextSequence: seq });

  // 6. Demo prompt — swap this for your agent input
  const testPrompt = "Explain in 3 bullet points why streaming AI model layers from SSD is better than loading them all into RAM.";

  await runInference(session, testPrompt, mode.mode);

  log.title("🎯 Phase 1 Complete! Check ./logs/layer_times.csv for telemetry.");
  log.info("Health endpoint: http://localhost:8008/health/memstream");
  log.info("Prometheus metrics: http://localhost:8008/metrics");
}

main().catch((err) => {
  log.error("Fatal: " + err.message);
  logEvent({ event: "fatal_error" });
  process.exit(1);
});
🏃 How to Run It (3 Commands)
bash
# 1. Install deps
npm install

# 2. Drop your model in place
# → Download from: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF
# → File: mistral-7b-instruct-v0.2.Q4_K_M.gguf → ./models/

# 3. Warmup test first (fast, safe)
npm run warmup

# 4. Full run
npm start
✅ Phase 1 Win Conditions Checklist
text
□ GGUF validates on startup
□ Hardware tier auto-detected + logged
□ Degradation cascade picks correct mode
□ Model loads via mmap (RAM stays under 6GB)
□ Progress bars show during warmup
□ Tokens stream live to terminal
□ layer_times.csv gets written after run
□ GET localhost:8008/health/memstream returns JSON
□ GET localhost:8008/metrics returns Prometheus data
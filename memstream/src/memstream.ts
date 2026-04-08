import path from "path";
import fs from "fs";
import chalk from "chalk";
import { getLlama } from "node-llama-cpp";
import { detectTier, getFreeRAMGB, getSystemRAMGB, getRealVRAMStateGB } from "./hardware.js";
import { selectRunMode } from "./degradation.js";
import { log, logEvent, makeProgressBar } from "./logger.js";
import { getThrottleDelay, startHealthServer, updateHealth } from "./health.js";

type MemstreamConfig = {
  model_id: string;
  model_path: string;
  hardware_limits: {
    max_ram_percent: number;
    max_vram_percent: number;
    min_free_ram_gb: number;
  };
  streaming: {
    context_window_tokens: number;
    use_memory_mmap: boolean;
  };
  accessibility: {
    progress_bars: boolean;
  };
};

function loadConfig(): MemstreamConfig {
  const text = fs.readFileSync("./memstream.config.json", "utf-8");
  return JSON.parse(text) as MemstreamConfig;
}

const config = loadConfig();
const MODEL_PATH = config.model_path;
const USE_MMAP = config.streaming.use_memory_mmap;
const PROGRESS_BARS = config.accessibility.progress_bars;
const GPU_LAYERS_OVERRIDE = (() => {
  const raw = process.env.MEMSTREAM_GPU_LAYERS;
  if (!raw) return null;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n >= 0 ? n : null;
})();
const CTX_TOKENS_OVERRIDE = (() => {
  const raw = process.env.MEMSTREAM_CTX_TOKENS;
  if (!raw) return null;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : null;
})();

log.title("╔══════════════════════════════════════╗");
log.title("║   🧠 MEMSTREAM ENGINE v1.0 — ONLINE  ║");
log.title("║   Smart memory, not expensive memory ║");
log.title("╚══════════════════════════════════════╝");

async function validateModel(modelPath: string): Promise<void> {
  log.info("Validating GGUF file...");
  if (!fs.existsSync(modelPath)) {
    log.error(`Model not found at: ${modelPath}`);
    log.info("Download it with:");
    log.info("  npx node-llama-cpp pull --dir ./models <model-url>");
    process.exit(1);
  }
  const stats = fs.statSync(modelPath);
  const sizeGB = stats.size / 1024 ** 3;
  log.success(`GGUF found: ${path.basename(modelPath)} (${sizeGB.toFixed(2)} GB)`);
  logEvent({ event: "gguf_validated" });
}

async function detectHardware() {
  log.info("Scanning hardware...");
  const llama = await getLlama();
  const ramGB = getSystemRAMGB();

  const vramState = await getRealVRAMStateGB(llama);
  const vramTotalGB = vramState?.totalGB ?? 0;
  const vramUsedGB = vramState?.usedGB ?? null;

  const tier = detectTier(vramTotalGB, ramGB);
  const mode = selectRunMode({
    vramTotalGB,
    vramUsedGB,
    preferredGpuLayers: GPU_LAYERS_OVERRIDE ?? tier.n_gpu_layers,
    limits: config.hardware_limits
  });

  log.success(`Hardware tier: ${tier.label}`);
  log.info(`Run mode selected: ${mode.mode.toUpperCase()} — ${mode.reason}`);
  if (mode.mode === "gpu") {
    log.info(`GPU layers: ${mode.n_gpu_layers}${GPU_LAYERS_OVERRIDE != null ? " (override)" : ""}`);
  }
  log.info(
    `System RAM: ${ramGB.toFixed(1)} GB | Free: ${getFreeRAMGB().toFixed(1)} GB | VRAM: ${vramTotalGB.toFixed(
      1
    )} GB`
  );

  logEvent({
    event: "hardware_detected",
    vram_total_gb: vramTotalGB,
    vram_used_gb: vramUsedGB ?? undefined,
    ram_free_gb: getFreeRAMGB()
  });

  return { llama, tier, mode };
}

async function warmup(args: { llama: Awaited<ReturnType<typeof getLlama>>; tier: any; mode: any }) {
  log.info("Warming up model (pre-loading metadata)...");
  const bar = makeProgressBar("Warmup", 3, PROGRESS_BARS);

  const model = await args.llama.loadModel({
    modelPath: MODEL_PATH,
    useMmap: USE_MMAP,
    gpuLayers: args.mode.n_gpu_layers
  });
  bar.update(1);

  const desiredCtx = CTX_TOKENS_OVERRIDE ?? config.streaming.context_window_tokens;
  const ctxTokens = Math.min(desiredCtx, args.tier.ctx_tokens);
  const ctx = await model.createContext({ contextSize: ctxTokens });
  bar.update(2);

  const seq = ctx.getSequence();
  bar.update(3);
  bar.stop();

  log.success("Model warmed up. KV cache context ready. ✅");
  log.info(`Context size: ${ctxTokens} tokens${CTX_TOKENS_OVERRIDE != null ? " (override)" : ""}`);
  logEvent({ event: "warmup_complete" });

  return { model, ctx, seq, ctxTokens };
}

async function runInference(session: any, prompt: string, mode: string) {
  const VERBOSE = process.env.MEMSTREAM_VERBOSE === "1";

  log.info(`\n💬 Prompt received`);
  if (VERBOSE) log.info(`Prompt length: ${prompt.length} chars`);
  log.info(`Mode: ${mode.toUpperCase()}`);

  process.stdout.write(chalk.cyan("\n  🤖 Response: "));

  let tokenCount = 0;
  const startTime = Date.now();
  let lastHealthUpdateMs = 0;
  const pending: string[] = [];
  let flushing = false;
  let generationDone = false;
  let resolveDrain: (() => void) | null = null;
  const drain = new Promise<void>((resolve) => {
    resolveDrain = resolve;
  });

  const pump = async () => {
    if (flushing) return;
    flushing = true;
    try {
      while (pending.length > 0) {
        const chunk = pending.shift();
        if (chunk == null) continue;
        process.stdout.write(String(chunk));
        tokenCount++;

        const now = Date.now();
        if (now - lastHealthUpdateMs >= 250) {
          lastHealthUpdateMs = now;
          const elapsed = (now - startTime) / 1000;
          const tokPerSec = elapsed > 0 ? tokenCount / elapsed : 0;
          updateHealth({ tokens_per_sec: tokPerSec, current_mode: mode });
        }

        const delay = getThrottleDelay();
        if (delay > 0) await new Promise((r) => setTimeout(r, delay));
      }
    } finally {
      flushing = false;
      if (generationDone && pending.length === 0) resolveDrain?.();
    }
  };

  await session.prompt(prompt, {
  onTextChunk: (chunk: string) => {
    pending.push(chunk);
    void pump();
  }
});
  generationDone = true;
  void pump();
  await drain;

  const elapsed = (Date.now() - startTime) / 1000;
  const tokPerSec = tokenCount / Math.max(elapsed, 0.001);

  console.log("\n");
  log.success(`Done! ${tokenCount} tokens in ${elapsed.toFixed(1)}s = ${tokPerSec.toFixed(1)} tok/s`);

  logEvent({
    event: "inference_complete",
    tokens_per_sec: tokPerSec,
    ram_free_gb: getFreeRAMGB()
  });
}

async function main() {
  startHealthServer(8008);

  const isWarmupOnly = process.argv.includes("--warmup");

  await validateModel(MODEL_PATH);

  const { llama, tier, mode } = await detectHardware();

  const { seq } = await warmup({ llama, tier, mode });

  if (isWarmupOnly) {
    log.success("Warmup complete. Engine ready. Exiting warmup mode.");
    process.exit(0);
  }

  const { LlamaChatSession } = await import("node-llama-cpp");
  const session = new LlamaChatSession({ contextSequence: seq });

  const testPrompt =
    "Explain in 3 bullet points why streaming AI model layers from SSD is better than loading them all into RAM.";

  await runInference(session, testPrompt, mode.mode);

  log.title("🎯 Phase 1 Complete! Check ./logs/layer_times.csv for telemetry.");
}

main().catch((err: any) => {
  log.error("Fatal: " + (err?.message ?? String(err)));
  logEvent({ event: "fatal_error" });
  process.exit(1);
});

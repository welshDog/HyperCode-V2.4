import fs from "fs";
import path from "path";
import { getLlama } from "node-llama-cpp";
import { log, logEvent, makeProgressBar } from "./logger.js";
import { detectTier, getFreeRAMGB, getSystemRAMGB, getRealVRAMStateGB } from "./hardware.js";
import { selectRunMode } from "./degradation.js";
import { startHealthServer } from "./health.js";
import { startApiServer } from "./api.js";

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
  return JSON.parse(fs.readFileSync("./memstream.config.json", "utf-8")) as MemstreamConfig;
}

function resolveModelName(modelPath: string): string {
  const base = path.basename(modelPath);
  return base.replace(/\.gguf$/i, "");
}

async function validateModel(modelPath: string): Promise<void> {
  if (!fs.existsSync(modelPath)) {
    throw new Error(`Model not found at: ${modelPath}`);
  }
  const stats = fs.statSync(modelPath);
  const sizeGB = stats.size / 1024 ** 3;
  log.success(`GGUF found: ${path.basename(modelPath)} (${sizeGB.toFixed(2)} GB)`);
  logEvent({ event: "gguf_validated" });
}

async function main() {
  const config = loadConfig();
  const MODEL_PATH = config.model_path;
  const USE_MMAP = config.streaming.use_memory_mmap;
  const PROGRESS_BARS = config.accessibility.progress_bars;

  log.title("╔══════════════════════════════════════╗");
  log.title("║   🧠 MEMSTREAM SERVER v1.0 — ONLINE  ║");
  log.title("╚══════════════════════════════════════╝");

  await validateModel(MODEL_PATH);

  const llama = await getLlama();
  const ramGB = getSystemRAMGB();
  const vramState = await getRealVRAMStateGB(llama);
  const vramTotalGB = vramState?.totalGB ?? 0;
  const vramUsedGB = vramState?.usedGB ?? null;

  const tier = detectTier(vramTotalGB, ramGB);
  const mode = selectRunMode({
    vramTotalGB,
    vramUsedGB,
    preferredGpuLayers: tier.n_gpu_layers,
    limits: config.hardware_limits
  });

  log.success(`Hardware tier: ${tier.label}`);
  log.info(`Run mode selected: ${mode.mode.toUpperCase()} — ${mode.reason}`);
  log.info(
    `System RAM: ${ramGB.toFixed(1)} GB | Free: ${getFreeRAMGB().toFixed(1)} GB | VRAM: ${vramTotalGB.toFixed(1)} GB`
  );

  logEvent({
    event: "hardware_detected",
    vram_total_gb: vramTotalGB,
    vram_used_gb: vramUsedGB ?? undefined,
    ram_free_gb: getFreeRAMGB()
  });

  const bar = makeProgressBar("Warmup", 2, PROGRESS_BARS);

  const model = await llama.loadModel({
    modelPath: MODEL_PATH,
    useMmap: USE_MMAP,
    gpuLayers: mode.n_gpu_layers
  });
  bar.update(1);

  const ctxTokens = Math.min(config.streaming.context_window_tokens, tier.ctx_tokens);
  const ctx = await model.createContext({ contextSize: ctxTokens });
  const seq = ctx.getSequence();
  bar.update(2);
  bar.stop();

  const { LlamaChatSession } = await import("node-llama-cpp");
  const session = new LlamaChatSession({ contextSequence: seq });

  await startHealthServer(8009);

  const apiPortRaw = process.env.MEMSTREAM_API_PORT;
  const apiPort = apiPortRaw ? Number.parseInt(apiPortRaw, 10) : 8011;

  const modelName = resolveModelName(MODEL_PATH);
  await startApiServer({ session, model, modelName, port: apiPort });

  log.success("MemStream server ready.");
}

main().catch((err: any) => {
  log.error("Fatal: " + (err?.message ?? String(err)));
  logEvent({ event: "fatal_error" });
  process.exit(1);
});


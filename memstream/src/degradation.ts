import os from "os";
import { getFreeRAMGB } from "./hardware.js";

export type RunMode = "gpu" | "cpu" | "cpu_4bit" | "token_stream";

export interface HardwareLimits {
  max_ram_percent?: number;
  max_vram_percent?: number;
  min_free_ram_gb?: number;
}

export interface DegradationResult {
  mode: RunMode;
  reason: string;
  n_gpu_layers: number;
}

export function selectRunMode(args: {
  vramTotalGB: number;
  vramUsedGB: number | null;
  preferredGpuLayers: number;
  limits: HardwareLimits;
}): DegradationResult {
  const freeRAM = getFreeRAMGB();
  const envMinFree = process.env.MEMSTREAM_MIN_FREE_RAM_GB ? Math.max(0, parseFloat(process.env.MEMSTREAM_MIN_FREE_RAM_GB)) : NaN;
  const minFree = args.limits.min_free_ram_gb ?? (!isNaN(envMinFree) && envMinFree > 0 ? envMinFree : 2.0);
  const maxRamPct = args.limits.max_ram_percent ?? 75;
  const maxVramPct = args.limits.max_vram_percent ?? 80;

  const total = args.vramTotalGB;
  const used = args.vramUsedGB;
  const vramUsedPct = total > 0 && used != null ? (used / total) * 100 : null;

  const totalMemBytes = os.totalmem();
  const freeMemBytes = os.freemem();
  const ramUsedPct = totalMemBytes > 0 ? ((totalMemBytes - freeMemBytes) / totalMemBytes) * 100 : 0;

  const vramOk = total >= 3.5 && (vramUsedPct == null || vramUsedPct <= maxVramPct);
  const ramOk = freeRAM >= minFree && ramUsedPct <= maxRamPct;

  if (vramOk && ramOk) {
    return { mode: "gpu", n_gpu_layers: args.preferredGpuLayers, reason: "GPU has enough VRAM ✅" };
  }

  if (freeRAM >= 8) {
    return { mode: "cpu", n_gpu_layers: 0, reason: "GPU constrained → falling back to CPU 🔄" };
  }

  if (freeRAM >= minFree) {
    return { mode: "cpu_4bit", n_gpu_layers: 0, reason: "Low RAM → CPU + 4bit quantisation 🔄" };
  }

  return { mode: "token_stream", n_gpu_layers: 0, reason: "Minimal RAM → slowest token-stream mode 🐢" };
}

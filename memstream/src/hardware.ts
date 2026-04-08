import os from "os";
import { log } from "./logger.js";

export interface HardwareTier {
  tier: "budget" | "mid" | "power" | "cpu-only";
  label: string;
  n_gpu_layers: number;
  ctx_tokens: number;
  ram_buffer: number;
}

export interface VramStateGB {
  totalGB: number;
  usedGB: number | null;
}

export function getSystemRAMGB(): number {
  return os.totalmem() / 1024 ** 3;
}

export function getFreeRAMGB(): number {
  return os.freemem() / 1024 ** 3;
}

export async function getRealVRAMStateGB(llama: any): Promise<VramStateGB | null> {
  try {
    const gpu = llama?.gpu;
    if (gpu === false) return { totalGB: 0, usedGB: 0 };

    const maybe = llama?.getVramState ? await llama.getVramState() : null;
    const usedBytes = Number(maybe?.used ?? maybe?.usedBytes ?? maybe?.vramUsed ?? 0);
    const freeBytes = Number(maybe?.free ?? maybe?.freeBytes ?? 0);
    const totalBytes = Number(maybe?.total ?? maybe?.totalBytes ?? maybe?.vramTotal ?? 0) || usedBytes + freeBytes;

    if (totalBytes > 0) {
      const totalGB = totalBytes / 1024 ** 3;
      const usedGB = usedBytes > 0 ? usedBytes / 1024 ** 3 : null;
      return { totalGB, usedGB: Number.isFinite(usedGB) ? usedGB : null };
    }

    const info = gpu && typeof gpu === "object" ? gpu : null;
    const total2 = Number(info?.vramTotal ?? info?.totalVram ?? info?.total ?? 0);
    const used2 = info?.vramUsed ?? info?.usedVram ?? info?.used ?? null;
    if (total2 > 0) {
      const totalGB = total2 / 1024 ** 3;
      const usedGB = used2 != null ? Number(used2) / 1024 ** 3 : null;
      return { totalGB, usedGB: Number.isFinite(usedGB) ? usedGB : null };
    }

    const devices = llama?.getGpuDeviceNames ? await llama.getGpuDeviceNames() : null;
    if (Array.isArray(devices) && devices.length > 0) {
      return { totalGB: 0, usedGB: null };
    }

    return { totalGB: 0, usedGB: 0 };
  } catch {
    log.warn("Could not detect VRAM — defaulting to CPU-only mode.");
    return { totalGB: 0, usedGB: 0 };
  }
}

export function detectTier(vramGB: number, ramGB: number): HardwareTier {
  if (vramGB >= 16)
    return {
      tier: "power",
      label: "🥇 Power User",
      n_gpu_layers: 35,
      ctx_tokens: 8192,
      ram_buffer: 4
    };

  if (vramGB >= 8)
    return {
      tier: "mid",
      label: "🥈 Mid Setup",
      n_gpu_layers: 20,
      ctx_tokens: 4096,
      ram_buffer: 2
    };

  if (vramGB >= 4)
    return {
      tier: "budget",
      label: "🥉 Budget Bro",
      n_gpu_layers: 10,
      ctx_tokens: 2048,
      ram_buffer: 2
    };

  return {
    tier: "cpu-only",
    label: "🫐 CPU Only",
    n_gpu_layers: 0,
    ctx_tokens: 2048,
    ram_buffer: 1
  };
}

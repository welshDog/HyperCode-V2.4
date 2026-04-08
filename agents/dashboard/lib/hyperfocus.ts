export type HyperfocusPreset = "micro" | "standard" | "deep";

export type HyperfocusConfig = {
  focusMinutes: number;
  breakMinutes: number;
  cycles: number;
  label: string;
};

export const HYPERFOCUS_PRESETS: Record<HyperfocusPreset, HyperfocusConfig> = {
  micro: { focusMinutes: 10, breakMinutes: 2, cycles: 3, label: "Micro" },
  standard: { focusMinutes: 25, breakMinutes: 5, cycles: 4, label: "Standard" },
  deep: { focusMinutes: 45, breakMinutes: 10, cycles: 3, label: "Deep" },
};

export type HyperfocusPhase = "focus" | "break";

export type HyperfocusState = {
  preset: HyperfocusPreset;
  phase: HyperfocusPhase;
  cycle: number;
  secondsRemaining: number;
  running: boolean;
};

export const HYPERFOCUS_STORAGE_KEY = "hc-hyperfocus-state";

export function formatMmSs(totalSeconds: number) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export function initialHyperfocusState(preset: HyperfocusPreset): HyperfocusState {
  const cfg = HYPERFOCUS_PRESETS[preset];
  return {
    preset,
    phase: "focus",
    cycle: 1,
    secondsRemaining: cfg.focusMinutes * 60,
    running: false,
  };
}

export type TickResult =
  | { type: "tick"; state: HyperfocusState }
  | { type: "transition"; state: HyperfocusState; announcement: string; nextPhase: HyperfocusPhase }
  | { type: "complete"; state: HyperfocusState; announcement: string };

export function tickHyperfocus(prev: HyperfocusState): TickResult {
  if (!prev.running) return { type: "tick", state: prev };
  if (prev.secondsRemaining > 1) {
    return { type: "tick", state: { ...prev, secondsRemaining: prev.secondsRemaining - 1 } };
  }

  const cfg = HYPERFOCUS_PRESETS[prev.preset];

  if (prev.phase === "focus") {
    const nextPhase: HyperfocusPhase = "break";
    const state: HyperfocusState = {
      ...prev,
      phase: nextPhase,
      secondsRemaining: cfg.breakMinutes * 60,
    };
    return { type: "transition", state, nextPhase, announcement: "Focus complete. Take a break." };
  }

  const nextCycle = prev.cycle + 1;
  if (nextCycle > cfg.cycles) {
    const done: HyperfocusState = { ...prev, running: false, secondsRemaining: 0 };
    return { type: "complete", state: done, announcement: "Session complete. Great work." };
  }

  const nextPhase: HyperfocusPhase = "focus";
  const state: HyperfocusState = {
    ...prev,
    cycle: nextCycle,
    phase: nextPhase,
    secondsRemaining: cfg.focusMinutes * 60,
  };
  return { type: "transition", state, nextPhase, announcement: "Break complete. Back to focus." };
}


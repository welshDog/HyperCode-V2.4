"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Pause, Play, RotateCcw } from "lucide-react";
import { motion } from "framer-motion";
import { LiveRegion } from "@/components/a11y/LiveRegion";
import {
  formatMmSs,
  HYPERFOCUS_PRESETS,
  HYPERFOCUS_STORAGE_KEY,
  initialHyperfocusState,
  tickHyperfocus,
  type HyperfocusPreset,
  type HyperfocusState,
} from "@/lib/hyperfocus";

function loadStoredState(): HyperfocusState | null {
  try {
    const raw = localStorage.getItem(HYPERFOCUS_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as HyperfocusState;
    if (!parsed || typeof parsed !== "object") return null;
    if (!("secondsRemaining" in parsed) || typeof parsed.secondsRemaining !== "number") return null;
    if (!("preset" in parsed) || typeof parsed.preset !== "string") return null;
    if (!("phase" in parsed) || typeof parsed.phase !== "string") return null;
    if (!("cycle" in parsed) || typeof parsed.cycle !== "number") return null;
    if (!("running" in parsed) || typeof parsed.running !== "boolean") return null;
    return parsed;
  } catch {
    return null;
  }
}

function saveState(s: HyperfocusState) {
  localStorage.setItem(HYPERFOCUS_STORAGE_KEY, JSON.stringify(s));
}

export function HyperfocusTimer() {
  const [state, setState] = useState<HyperfocusState>(() => loadStoredState() ?? initialHyperfocusState("standard"));
  const [srAssertive, setSrAssertive] = useState("");
  const intervalRef = useRef<number | null>(null);

  const cfg = useMemo(() => HYPERFOCUS_PRESETS[state.preset], [state.preset]);

  const announce = (msg: string) => {
    setSrAssertive(msg);
    window.setTimeout(() => setSrAssertive(""), 900);
  };

  useEffect(() => {
    if (typeof window === "undefined") return;
    saveState(state);
  }, [state]);

  useEffect(() => {
    if (!state.running) {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }
    if (intervalRef.current) return;
    intervalRef.current = window.setInterval(() => {
      setState((prev) => {
        const res = tickHyperfocus(prev);
        if (res.type === "transition" || res.type === "complete") announce(res.announcement);
        return res.state;
      });
    }, 1000);
    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    };
  }, [state.running]);

  const setPresetAndReset = (p: HyperfocusPreset) => {
    setState(initialHyperfocusState(p));
  };

  const toggle = () => setState((s) => ({ ...s, running: !s.running }));
  const reset = () => setState(initialHyperfocusState(state.preset));

  const badge =
    state.phase === "focus"
      ? "text-cyan-300 border-cyan-900/40 bg-cyan-950/20"
      : "text-emerald-300 border-emerald-900/40 bg-emerald-950/20";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="bg-zinc-900/50 backdrop-blur border border-zinc-800 p-4 rounded-lg"
      aria-labelledby="hyperfocus-title"
    >
      <LiveRegion message={srAssertive} politeness="assertive" atomic relevant="additions text" />

      <div className="flex items-center justify-between mb-3">
        <h3 id="hyperfocus-title" className="text-sm font-bold text-zinc-300 uppercase tracking-wider">
          Hyperfocus Timer
        </h3>
        <span className={`text-[10px] font-bold tracking-widest px-2 py-1 rounded border ${badge}`}>
          {state.phase.toUpperCase()} {state.cycle}/{cfg.cycles}
        </span>
      </div>

      <div className="flex items-end gap-2 mb-3">
        <span className="text-3xl font-bold text-white" aria-label="Time remaining">
          {formatMmSs(state.secondsRemaining)}
        </span>
        <span className="text-xs text-zinc-500 mb-1">
          {cfg.focusMinutes}m focus / {cfg.breakMinutes}m break
        </span>
      </div>

      <div className="flex items-center gap-2 mb-3" role="group" aria-label="Hyperfocus preset">
        {(Object.keys(HYPERFOCUS_PRESETS) as HyperfocusPreset[]).map((p) => (
          <button
            key={p}
            onClick={() => setPresetAndReset(p)}
            aria-pressed={state.preset === p}
            className={`px-3 py-1.5 rounded text-xs font-bold tracking-wide border transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-black ${
              state.preset === p
                ? "border-[var(--hc-color-accent)] bg-[var(--hc-color-accent)] text-black"
                : "border-[var(--hc-color-border)] text-[var(--hc-color-text-secondary)] hover:border-[var(--hc-color-accent)]"
            }`}
          >
            {HYPERFOCUS_PRESETS[p].label.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="flex gap-2">
        <button
          onClick={toggle}
          className="flex-1 py-2 bg-cyan-900/20 border border-cyan-800 text-cyan-400 hover:bg-cyan-500 hover:text-black transition-all font-bold uppercase text-xs tracking-wider flex items-center justify-center gap-2"
        >
          {state.running ? <Pause size={14} aria-hidden="true" /> : <Play size={14} aria-hidden="true" />}
          {state.running ? "Pause" : "Start"}
        </button>
        <button
          onClick={reset}
          className="px-3 py-2 bg-zinc-900/40 border border-zinc-700 text-zinc-300 hover:bg-zinc-800 transition-all font-bold uppercase text-xs tracking-wider flex items-center justify-center gap-2"
        >
          <RotateCcw size={14} aria-hidden="true" />
          Reset
        </button>
      </div>
    </motion.div>
  );
}


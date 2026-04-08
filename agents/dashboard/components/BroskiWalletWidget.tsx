"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Coins, GraduationCap } from "lucide-react";
import { fetchBroskiWallet, type BroskiWallet } from "@/lib/api";

const XP_LEVELS = [0, 100, 250, 500, 1000, 2000, 5000];

function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n));
}

function getXpProgress(xp: number, level: number) {
  const idx = clamp(level - 1, 0, XP_LEVELS.length - 1);
  const prev = XP_LEVELS[idx] ?? 0;
  const next = XP_LEVELS[idx + 1];
  if (next === undefined) {
    return { prev, next: prev, percent: 100, isMax: true };
  }
  const raw = ((xp - prev) / (next - prev)) * 100;
  return { prev, next, percent: clamp(raw, 0, 100), isMax: false };
}

export function BroskiWalletWidget() {
  const [wallet, setWallet] = useState<BroskiWallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const load = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const data = await fetchBroskiWallet();
      setWallet(data);
      setError(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load wallet";
      setError(msg);
    } finally {
      setLoading(false);
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  const progress = useMemo(() => {
    if (!wallet) return null;
    return getXpProgress(wallet.xp, wallet.level);
  }, [wallet]);

  if (loading && !wallet) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 w-full">
        <div className="flex items-center gap-2 mb-4">
          <Coins className="w-5 h-5 text-zinc-400" />
          <h3 className="font-semibold text-zinc-200">BROski$ Wallet</h3>
        </div>
        <div className="animate-pulse space-y-3">
          <div className="h-7 bg-zinc-800 rounded w-2/3" />
          <div className="h-2 bg-zinc-800 rounded w-full" />
          <div className="h-7 bg-zinc-800 rounded w-1/2" />
        </div>
      </div>
    );
  }

  if (!wallet) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 w-full">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Coins className="w-5 h-5 text-yellow-400" />
            <h3 className="font-semibold text-zinc-200">BROski$ Wallet</h3>
          </div>
        </div>
        <div className="text-xs text-red-400 mb-3">
          {error || "Failed to load wallet"}
        </div>
        <button
          type="button"
          onClick={load}
          className="text-xs font-bold uppercase tracking-wider px-3 py-2 rounded border border-zinc-700 text-zinc-200 hover:bg-zinc-800 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 w-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Coins className="w-5 h-5 text-yellow-400" />
          <h3 className="font-semibold text-zinc-200">BROski$ Wallet</h3>
        </div>
        <span
          data-testid="level-badge"
          className="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
          title={wallet.level_name}
        >
          LVL {wallet.level}
        </span>
      </div>

      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs text-zinc-500">Coins</div>
          <div
            data-testid="coins-value"
            className="text-2xl font-bold text-yellow-300 tracking-tight"
          >
            {wallet.coins.toLocaleString()}
          </div>
          <div className="text-[10px] text-zinc-500 truncate" title={wallet.level_name}>
            {wallet.level_name}
          </div>
        </div>
        <div className="flex items-center gap-2 text-zinc-500 shrink-0">
          <GraduationCap className="w-4 h-4" />
          <span className="text-[10px] font-bold uppercase tracking-wider">
            XP
          </span>
        </div>
      </div>

      <div className="mt-3">
        <div className="flex justify-between text-[10px] text-zinc-500 mb-1">
          <span data-testid="xp-label">
            {progress?.isMax ? `${wallet.xp.toLocaleString()} XP` : `${wallet.xp.toLocaleString()} / ${progress?.next.toLocaleString()} XP`}
          </span>
          <span data-testid="xp-percent">
            {Math.round(progress?.percent ?? 0)}%
          </span>
        </div>
        <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
          <div
            data-testid="xp-progress-bar"
            className="h-full bg-emerald-500 transition-all"
            style={{ width: `${progress?.percent ?? 0}%` }}
          />
        </div>
        {error && (
          <div className="mt-2 text-[10px] text-yellow-400">
            Sync issue: {error}
          </div>
        )}
      </div>
    </div>
  );
}


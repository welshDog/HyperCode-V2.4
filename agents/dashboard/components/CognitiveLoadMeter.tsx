"use client";

import { Activity, AlertTriangle, Zap } from "lucide-react";
import { motion } from "framer-motion";
import { computeCognitiveLoad } from "@/lib/cognitiveLoad";
import type { Task } from "@/lib/api";

type AgentLike = { id: number | string; name: string; status: string };
type LogLike = { level?: string; msg?: string };

function countPending(tasks: Task[]) {
  return tasks.filter((t) => !["done", "completed"].includes(String(t.status).toLowerCase())).length;
}

function countErrorAgents(agents: AgentLike[]) {
  return agents.filter((a) => String(a.status).toLowerCase() === "error").length;
}

function countRecentErrorLogs(logs: LogLike[]) {
  return logs.filter((l) => String(l.level).toLowerCase() === "error").slice(0, 20).length;
}

export function CognitiveLoadMeter({
  connected,
  agents,
  tasks,
  logs,
}: {
  connected: boolean;
  agents: AgentLike[];
  tasks: Task[];
  logs: LogLike[];
}) {
  const pendingTasks = countPending(tasks);
  const errorAgents = countErrorAgents(agents);
  const recentErrorLogs = countRecentErrorLogs(logs);

  const { score, band, label, recommendation } = computeCognitiveLoad({
    connected,
    pendingTasks,
    errorAgents,
    totalAgents: agents.length,
    recentErrorLogs,
  });

  const color =
    band === "overload"
      ? "text-red-400"
      : band === "high"
        ? "text-yellow-400"
        : band === "medium"
          ? "text-cyan-300"
          : "text-emerald-400";

  const border =
    band === "overload"
      ? "border-red-900/50"
      : band === "high"
        ? "border-yellow-900/50"
        : "border-zinc-800";

  const icon =
    band === "overload" || band === "high" ? (
      <AlertTriangle className={`w-4 h-4 ${color}`} aria-hidden="true" />
    ) : band === "medium" ? (
      <Activity className={`w-4 h-4 ${color}`} aria-hidden="true" />
    ) : (
      <Zap className={`w-4 h-4 ${color}`} aria-hidden="true" />
    );

  const meterTextId = "cognitive-load-meter-text";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className={`bg-zinc-900/50 backdrop-blur border ${border} p-4 rounded-lg`}
      aria-labelledby="cognitive-load-title"
      aria-describedby={meterTextId}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {icon}
          <h3 id="cognitive-load-title" className="text-sm font-bold text-zinc-300 uppercase tracking-wider">
            Cognitive Load
          </h3>
        </div>
        <span className={`text-xs font-bold tracking-widest ${color}`}>{label}</span>
      </div>

      <div className="flex items-end gap-2 mb-2">
        <span className="text-3xl font-bold text-white">{score}</span>
        <span className="text-sm text-zinc-500 mb-1">/ 100</span>
      </div>

      <meter
        min={0}
        max={100}
        value={score}
        className="w-full h-2"
        aria-label="Cognitive load"
      />

      <div id={meterTextId} className="mt-2 text-[10px] text-zinc-500">
        {recommendation}
      </div>
    </motion.div>
  );
}


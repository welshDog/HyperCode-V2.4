"use client";

import { useDockerServices } from "@/hooks/useDockerServices";
import { Activity, AlertTriangle, CheckCircle, Loader2, ServerCrash } from "lucide-react";

// --- Status style map — covers every state the backend can return ---
type ServiceStatus = "healthy" | "starting" | "degraded" | "unknown" | "down" | "unhealthy" | string;

function getStatusStyle(status: ServiceStatus) {
  switch (status) {
    case "healthy":
      return {
        card: "bg-green-500/5 border-green-500/20 text-green-200",
        icon: <CheckCircle className="w-3 h-3 text-green-500" />,
        badge: <span className="text-zinc-500" />,
      };
    case "starting":
    case "degraded":
      return {
        card: "bg-yellow-500/5 border-yellow-500/20 text-yellow-200",
        icon: <Loader2 className="w-3 h-3 text-yellow-400 animate-spin" />,
        badge: <span className="text-yellow-400 font-medium">{status.toUpperCase()}</span>,
      };
    case "unknown":
      return {
        card: "bg-zinc-800/50 border-zinc-700 text-zinc-400",
        icon: <Activity className="w-3 h-3 text-zinc-500" />,
        badge: <span className="text-zinc-500 font-medium">UNKNOWN</span>,
      };
    case "down":
    case "unhealthy":
    default:
      return {
        card: "bg-red-500/5 border-red-500/20 text-red-200",
        icon: <ServerCrash className="w-3 h-3 text-red-500" />,
        badge: <span className="text-red-400 font-medium">DOWN</span>,
      };
  }
}

export function SystemHealth() {
  const { services: healthData, loading } = useDockerServices(15_000);

  if (loading || Object.keys(healthData).length === 0) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 w-full">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-zinc-400" />
          <h3 className="font-semibold text-zinc-200">System Health</h3>
        </div>
        <div className="animate-pulse space-y-2">
          <div className="h-8 bg-zinc-800 rounded w-full"></div>
          <div className="h-8 bg-zinc-800 rounded w-full"></div>
          <div className="h-8 bg-zinc-800 rounded w-full"></div>
        </div>
      </div>
    );
  }

  // Only genuinely broken services count toward alert level
  const failedCount = Object.values(healthData).filter(
    (a) => a.status === "down" || a.status === "unhealthy"
  ).length;
  const startingCount = Object.values(healthData).filter(
    (a) => a.status === "starting" || a.status === "degraded"
  ).length;

  let statusColor = "border-zinc-800";
  let statusIconColor = "text-green-500";
  let statusLabel = null;

  if (failedCount >= 4) {
    statusColor = "border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.2)]";
    statusIconColor = "text-red-500";
    statusLabel = (
      <span className="flex items-center gap-1 text-xs font-bold text-red-500 bg-red-500/10 px-2 py-1 rounded-full animate-pulse">
        <AlertTriangle className="w-3 h-3" /> CRITICAL
      </span>
    );
  } else if (failedCount > 0) {
    statusColor = "border-red-500/40 shadow-[0_0_10px_rgba(239,68,68,0.1)]";
    statusIconColor = "text-red-400";
    statusLabel = (
      <span className="flex items-center gap-1 text-xs font-bold text-red-400 bg-red-500/10 px-2 py-1 rounded-full">
        <AlertTriangle className="w-3 h-3" /> {failedCount} DOWN
      </span>
    );
  } else if (startingCount > 0) {
    // Starting/degraded — amber, not red
    statusColor = "border-yellow-500/50 shadow-[0_0_10px_rgba(234,179,8,0.1)]";
    statusIconColor = "text-yellow-500";
    statusLabel = (
      <span className="flex items-center gap-1 text-xs font-bold text-yellow-500 bg-yellow-500/10 px-2 py-1 rounded-full">
        <Loader2 className="w-3 h-3 animate-spin" /> STARTING
      </span>
    );
  }

  return (
    <div className={`bg-zinc-900 border rounded-lg p-4 w-full transition-colors ${statusColor}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className={`w-5 h-5 ${statusIconColor}`} />
          <h3 className="font-semibold text-zinc-200">System Health</h3>
        </div>
        {statusLabel}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
        {Object.entries(healthData).map(([name, service]) => {
          const { card, icon, badge } = getStatusStyle(service.status);
          return (
            <div
              key={name}
              className={`flex items-center justify-between p-2 rounded border text-xs ${card}`}
            >
              <div className="flex items-center gap-2">
                {icon}
                <span className="capitalize truncate max-w-[120px]" title={name}>
                  {name.replace(/_/g, " ")}
                </span>
              </div>
              <div className="text-right">
                {service.status === "healthy" ? (
                  <span className="text-zinc-500">{Math.round(service.latency_ms || 0)}ms</span>
                ) : (
                  badge
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

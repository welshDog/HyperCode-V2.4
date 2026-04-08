"use client";

import { useEffect, useState } from "react";
import { fetchTasks, fetchSystemHealth, type Task, type SystemHealthData } from "@/lib/api";
import { 
  Database, 
  Server, 
  ShieldCheck, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  HardDrive 
} from "lucide-react";
import { motion } from "framer-motion";

export function MetricsPanel() {
  const [stats, setStats] = useState({
    tasks: { total: 0, completed: 0, pending: 0 },
    infra: { 
      redis: "unknown", 
      postgres: "unknown", 
      minio: "unknown",
      tempo: "unknown"
    },
    compliance: 100 // Hardcoded for now based on report
  });

  useEffect(() => {
    async function loadData() {
      const [tasksData, healthData] = await Promise.all([
        fetchTasks(),
        fetchSystemHealth()
      ]);

      // Process Tasks
      const total = tasksData.length;
      const completed = tasksData.filter((t: Task) => t.status === "done" || t.status === "completed").length;
      
      // Process Health
      // Health data structure from api.ts: { "service_name": { status: "healthy"|"down" } }
      const infra = {
        redis: healthData["redis"]?.status || "unknown",
        postgres: healthData["postgres"]?.status || "unknown",
        minio: healthData["minio"]?.status || "unknown",
        tempo: healthData["tempo"]?.status || "unknown"
      };

      setStats({
        tasks: { total, completed, pending: total - completed },
        infra,
        compliance: 100
      });
    }

    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    if (status === "healthy") return "text-emerald-500";
    if (status === "degraded") return "text-yellow-500";
    if (status === "down") return "text-red-500";
    return "text-zinc-500";
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* Infrastructure Status */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-zinc-900/50 backdrop-blur border border-zinc-800 p-4 rounded-lg"
      >
        <div className="flex items-center gap-2 mb-3">
          <Server className="w-4 h-4 text-cyan-500" />
          <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-wider">Infrastructure</h3>
        </div>
        <div className="space-y-2 text-xs font-mono">
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2 text-zinc-400">
              <Database className="w-3 h-3" /> Redis (Cache)
            </span>
            <span className={getStatusColor(stats.infra.redis)}>{stats.infra.redis}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2 text-zinc-400">
              <Database className="w-3 h-3" /> PostgreSQL
            </span>
            <span className={getStatusColor(stats.infra.postgres)}>{stats.infra.postgres}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2 text-zinc-400">
              <HardDrive className="w-3 h-3" /> MinIO (S3)
            </span>
            <span className={getStatusColor(stats.infra.minio)}>{stats.infra.minio}</span>
          </div>
           <div className="flex justify-between items-center">
            <span className="flex items-center gap-2 text-zinc-400">
              <Activity className="w-3 h-3" /> Tempo (Trace)
            </span>
            <span className={getStatusColor(stats.infra.tempo)}>{stats.infra.tempo}</span>
          </div>
        </div>
      </motion.div>

      {/* Task Velocity */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-zinc-900/50 backdrop-blur border border-zinc-800 p-4 rounded-lg"
      >
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-4 h-4 text-purple-500" />
          <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-wider">Task Velocity</h3>
        </div>
        <div className="flex items-end gap-2 mb-2">
          <span className="text-3xl font-bold text-white">{stats.tasks.completed}</span>
          <span className="text-sm text-zinc-500 mb-1">/ {stats.tasks.total} tasks</span>
        </div>
        <div className="h-2 w-full bg-zinc-800 rounded-full overflow-hidden">
          <div 
            className="h-full bg-purple-500 transition-all duration-500"
            style={{ width: `${stats.tasks.total > 0 ? (stats.tasks.completed / stats.tasks.total) * 100 : 0}%` }}
          />
        </div>
        <p className="mt-2 text-[10px] text-zinc-500">
          {stats.tasks.pending} tasks pending in queue
        </p>
      </motion.div>

      {/* Compliance & Security */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-zinc-900/50 backdrop-blur border border-zinc-800 p-4 rounded-lg"
      >
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-wider">Fediversity Ready</h3>
        </div>
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-3 h-3" />
            <span>AGPL-3.0 License Enforced</span>
          </div>
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-3 h-3" />
            <span>WCAG 2.2 AAA Accessibility</span>
          </div>
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-3 h-3" />
            <span>Local-First Data Sovereignty</span>
          </div>
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-3 h-3" />
            <span>No External Cloud Dependencies</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

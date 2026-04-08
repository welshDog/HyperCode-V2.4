export type CognitiveLoadBand = "low" | "medium" | "high" | "overload";

export type CognitiveLoadInputs = {
  connected: boolean;
  pendingTasks: number;
  errorAgents: number;
  totalAgents: number;
  recentErrorLogs: number;
};

export type CognitiveLoadResult = {
  score: number;
  band: CognitiveLoadBand;
  label: string;
  recommendation: string;
};

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

export function computeCognitiveLoad(i: CognitiveLoadInputs): CognitiveLoadResult {
  const taskScore = clamp(i.pendingTasks * 6, 0, 48);
  const agentErrorScore = clamp(i.errorAgents * 25, 0, 50);
  const logScore = clamp(i.recentErrorLogs * 8, 0, 24);
  const connectivityScore = i.connected ? 0 : 20;

  const score = clamp(taskScore + agentErrorScore + logScore + connectivityScore, 0, 100);

  const band: CognitiveLoadBand =
    score >= 80 ? "overload" : score >= 55 ? "high" : score >= 30 ? "medium" : "low";

  const label =
    band === "overload" ? "OVERLOAD" : band === "high" ? "HIGH" : band === "medium" ? "MEDIUM" : "LOW";

  const recommendation =
    band === "overload"
      ? "Switch to CALM and reduce inputs. Do one task only."
      : band === "high"
        ? "Pause non-urgent work. Chunk the next task."
        : band === "medium"
          ? "Stay focused. Keep the queue small."
          : "All clear. Maintain flow.";

  return { score, band, label, recommendation };
}


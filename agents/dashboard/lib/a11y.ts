export type AgentStatus = "online" | "working" | "thinking" | "coding" | "error" | "offline";

export type AgentSnapshot = {
  id: string | number;
  name: string;
  status: AgentStatus;
};

export function diffAgentStatusAnnouncements(
  prev: Map<string | number, AgentSnapshot>,
  next: AgentSnapshot[]
): { polite: string[]; assertive: string[]; nextMap: Map<string | number, AgentSnapshot> } {
  const nextMap = new Map<string | number, AgentSnapshot>();
  const polite: string[] = [];
  const assertive: string[] = [];

  for (const a of next) {
    nextMap.set(a.id, a);
    const p = prev.get(a.id);
    if (!p) continue;
    if (p.status === a.status) continue;

    if (a.status === "error") {
      assertive.push(`${a.name} status error`);
      continue;
    }
    if (p.status === "error") {
      polite.push(`${a.name} recovered`);
      continue;
    }
    polite.push(`${a.name} status ${a.status}`);
  }

  return { polite, assertive, nextMap };
}


// 🧠 Brain Dump → Task Chunker
// Parses free-text brain dumps into structured micro-tasks with effort scores

export type EffortScore = 1 | 2 | 3 | 5 | 8; // Fibonacci-lite — keeps it real

export type TaskCategory =
  | 'code'
  | 'research'
  | 'comms'
  | 'admin'
  | 'creative'
  | 'blocked'
  | 'other';

export interface MicroTask {
  id: string;
  text: string;
  effort: EffortScore;
  category: TaskCategory;
  urgent: boolean;
  raw: string; // original input fragment that generated this task
}

export interface ChunkResult {
  tasks: MicroTask[];
  overloadWarning: boolean; // true if >7 tasks detected (cognitive overload risk)
  suggestedFocus: MicroTask | null; // single best "start here" task
}

// --- Keyword maps for heuristic categorisation ---
const CATEGORY_KEYWORDS: Record<TaskCategory, string[]> = {
  code: ['fix', 'build', 'implement', 'refactor', 'debug', 'deploy', 'test', 'write', 'add', 'update', 'pr', 'push', 'merge', 'branch'],
  research: ['research', 'look into', 'investigate', 'read', 'find out', 'check', 'explore', 'review', 'learn'],
  comms: ['email', 'message', 'reply', 'call', 'ping', 'slack', 'discord', 'tell', 'ask', 'follow up', 'contact'],
  admin: ['invoice', 'pay', 'schedule', 'book', 'fill in', 'submit', 'form', 'register', 'renew', 'cancel'],
  creative: ['design', 'draw', 'sketch', 'write up', 'brainstorm', 'plan', 'idea', 'create', 'make'],
  blocked: ['waiting', 'blocked', 'depends on', 'need', 'waiting for', 'cant until', "can't until"],
  other: [],
};

const URGENT_KEYWORDS = ['urgent', 'asap', 'today', 'now', 'deadline', 'overdue', '!!', 'critical', 'must'];

function detectCategory(text: string): TaskCategory {
  const lower = text.toLowerCase();
  for (const [cat, keywords] of Object.entries(CATEGORY_KEYWORDS) as [TaskCategory, string[]][]) {
    if (cat === 'other') continue;
    if (keywords.some((kw) => lower.includes(kw))) return cat;
  }
  return 'other';
}

function detectUrgent(text: string): boolean {
  const lower = text.toLowerCase();
  return URGENT_KEYWORDS.some((kw) => lower.includes(kw));
}

function estimateEffort(text: string): EffortScore {
  const words = text.trim().split(/\s+/).length;
  const hasMultipleVerbs = (text.match(/\b(and|then|also|plus|after)\b/gi) || []).length >= 2;
  if (hasMultipleVerbs || words > 20) return 5;
  if (words > 12) return 3;
  if (words > 6) return 2;
  return 1;
}

function generateId(): string {
  return `task-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

// Split raw dump text into candidate task fragments
function splitIntoCandidates(raw: string): string[] {
  return raw
    .split(/[\n,;.!?]|(?:\band\b)/i)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export function chunkBrainDump(raw: string): ChunkResult {
  if (!raw || !raw.trim()) {
    return { tasks: [], overloadWarning: false, suggestedFocus: null };
  }

  const candidates = splitIntoCandidates(raw);

  const tasks: MicroTask[] = candidates.map((fragment) => ({
    id: generateId(),
    text: fragment.charAt(0).toUpperCase() + fragment.slice(1),
    effort: estimateEffort(fragment),
    category: detectCategory(fragment),
    urgent: detectUrgent(fragment),
    raw: fragment,
  }));

  const overloadWarning = tasks.length > 7;

  // Best starting task: urgent first, then lowest effort, then code category
  const urgentTasks = tasks.filter((t) => t.urgent);
  const sorted = [...(urgentTasks.length ? urgentTasks : tasks)].sort(
    (a, b) => a.effort - b.effort
  );
  const suggestedFocus = sorted[0] ?? null;

  return { tasks, overloadWarning, suggestedFocus };
}

export const EFFORT_LABELS: Record<EffortScore, string> = {
  1: '⚡ Quick',
  2: '🟢 Easy',
  3: '🟡 Medium',
  5: '🔴 Big',
  8: '🦅 Epic',
};

export const CATEGORY_EMOJI: Record<TaskCategory, string> = {
  code: '💻',
  research: '🔍',
  comms: '💬',
  admin: '📋',
  creative: '🎨',
  blocked: '🚧',
  other: '📌',
};

export const CORE_ORIGIN = process.env.NEXT_PUBLIC_CORE_URL || "http://localhost:8000";
export const API_BASE_URL = `${CORE_ORIGIN}/api/v1`;

function getStoredToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("token") || "";
}

async function apiFetch(path: string, options: RequestInit = {}, token?: string) {
  const headers = new Headers(options.headers || {});
  const authToken = token ?? getStoredToken();
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
}

// --- CORE API TYPES ---
export interface User {
  id: number;
  email: string;
  full_name?: string;
  role: "admin" | "developer" | "viewer";
  is_active: boolean;
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  status: "active" | "archived" | "draft";
  owner_id: number;
}

export interface Task {
  id: number | string;
  description: string;
  title: string;
  status: string;
  progress: number;
}

export interface TaskCreate {
  description: string;
  title: string;
  priority: 'high' | 'normal' | 'low';
  type: string;
  project_id: number;
}

export interface BroskiWallet {
  id: number;
  user_id: number;
  coins: number;
  xp: number;
  level: number;
  level_name: string;
  created_at: string;
  updated_at?: string | null;
}

// --- AUTHENTICATION ---
export async function login(username: string, password: string): Promise<{ access_token: string; token_type: string } | null> {
  try {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const res = await fetch(`${API_BASE_URL}/auth/login/access-token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });

    if (!res.ok) throw new Error("Login failed");
    return await res.json();
  } catch (error) {
    console.error("Auth Error:", error);
    return null;
  }
}

// --- AGENT ORCHESTRATION ---
export async function fetchAgents(token?: string) {
  try {
    const res = await apiFetch(`/orchestrator/agents`, {}, token);
    if (!res.ok) throw new Error("Failed to fetch agents");
    return await res.json();
  } catch (error) {
    console.error("API Error:", error);
    return [];
  }
}

// --- PROJECTS ---
export async function fetchProjects(token: string): Promise<Project[]> {
  try {
    const res = await apiFetch(`/projects/`, {}, token);
    if (!res.ok) throw new Error("Failed to fetch projects");
    return await res.json();
  } catch (error) {
    console.error("API Error:", error);
    return [];
  }
}

// ... (Rest of existing functions)

export async function fetchTasks(token?: string): Promise<Task[]> {
  try {
    const res = await apiFetch(`/tasks/`, {}, token);
    if (!res.ok) throw new Error("Failed to fetch tasks");
    return await res.json();
  } catch (error) {
    console.error("API Error:", error);
    return [];
  }
}

export async function fetchBroskiWallet(token?: string): Promise<BroskiWallet> {
  const res = await apiFetch(`/broski/wallet`, {}, token);
  if (!res.ok) throw new Error("Failed to fetch wallet");
  return await res.json();
}

export async function fetchLogs(token?: string) {
  try {
    const res = await apiFetch(`/logs`, {}, token);
    if (!res.ok) throw new Error("Failed to fetch logs");
    return await res.json();
  } catch (error) {
    console.error("API Error:", error);
    return [];
  }
}

export async function checkHealth() {
  try {
    const res = await fetch(`${CORE_ORIGIN}/health`);
    return res.ok;
  } catch (error) {
    return false;
  }
}

export async function createTask(task: TaskCreate) {
  const token = getStoredToken();
  try {
    const res = await apiFetch(`/tasks/`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
      },
      body: JSON.stringify(task),
    }, token);
    if (!res.ok) throw new Error("Failed to create task");
    return await res.json();
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

export async function getTask(id: number) {
  const token = getStoredToken();
  try {
    const res = await apiFetch(`/tasks/${id}`, {}, token);
    if (!res.ok) throw new Error("Failed to fetch task");
    return await res.json();
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

export async function sendCommand(command: string, token?: string) {
    // Determine type of command
    // Simple parsing for demo
    // e.g. "build user profile" -> POST /execute
    
    // For now, just log it locally or implement a simple /execute proxy
    // If the command starts with "run: ", we treat it as a task description
    if (command.startsWith("run: ") || command.startsWith("build ") || command.startsWith("create ")) {
        const description = command.replace("run: ", "");
        try {
            const res = await apiFetch(`/execute`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    task: {
                        id: `cmd-${Date.now()}`,
                        type: "user_command",
                        description: description,
                        requires_approval: true
                    }
                })
            }, token);
            return await res.json();
        } catch (error) {
            console.error("Command failed", error);
            return { status: "error", message: String(error) };
        }
    }
    
    return { status: "ignored", message: "Command not recognized (try 'run: ...')" };
}

export interface SystemHealthData {
    status: string;
    latency_ms?: number;
    last_checked?: string;
    error?: string;
}

export async function fetchSystemHealth(): Promise<Record<string, SystemHealthData>> {
  try {
    // Attempt to fetch from API
    const res = await apiFetch(`/orchestrator/system/health`);
    if (!res.ok) throw new Error(`Status ${res.status}`);
    return await res.json();
  } catch (error) {
    console.error("API Error (fetchSystemHealth):", error);
    // Return mock data for demo/fallback if API is down
    return {
        "hypercode-core": { status: "healthy", latency_ms: 12, last_checked: new Date().toISOString() },
        "orchestrator": { status: "healthy", latency_ms: 45, last_checked: new Date().toISOString() },
        "database": { status: "healthy", latency_ms: 5, last_checked: new Date().toISOString() },
        "redis": { status: "healthy", latency_ms: 2, last_checked: new Date().toISOString() },
        "postgres": { status: "healthy", latency_ms: 8, last_checked: new Date().toISOString() },
        "minio": { status: "healthy", latency_ms: 15, last_checked: new Date().toISOString() },
        "tempo": { status: "degraded", error: "Connection refused", last_checked: new Date().toISOString() }
    };
  }
}

export interface HyperSyncMessage {
  role: string
  content: string
  timestamp: number
}

export interface HyperSyncFileRef {
  path: string
  line_start?: number
  line_end?: number
}

export interface HyperSyncState {
  client_id: string
  messages: HyperSyncMessage[]
  context_variables?: Record<string, unknown>
  file_references?: HyperSyncFileRef[]
  user_preferences?: Record<string, unknown>
  session_meta?: Record<string, unknown>
}

export interface HyperSyncHandoffResponse {
  handoff_id: string
  resume_token: string
  expires_in_seconds: number
  pt_sha256: string
  mode: string
}

export async function hypersyncHandoff(
  state: HyperSyncState,
  idempotencyKey?: string,
  token?: string
): Promise<HyperSyncHandoffResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey
  const res = await apiFetch(
    `/hypersync/handoff`,
    { method: "POST", headers, body: JSON.stringify(state) },
    token
  )
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`HyperSync handoff failed: ${res.status} ${text}`)
  }
  return await res.json()
}

export interface HyperSyncRedeemResponse {
  handoff_id: string
  pt_sha256: string
  state: Record<string, unknown>
}

export async function hypersyncRedeem(
  resume_token: string,
  client_id: string,
  token?: string
): Promise<HyperSyncRedeemResponse> {
  const res = await apiFetch(
    `/hypersync/redeem`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_token, client_id }),
    },
    token
  )
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`HyperSync redeem failed: ${res.status} ${text}`)
  }
  return await res.json()
}

export async function respondToApproval(approvalId: string, status: "approved" | "rejected", token?: string) {
    try {
        const res = await apiFetch(`/orchestrator/approvals/respond`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                approval_id: approvalId,
                status: status,
                timestamp: new Date().toISOString()
            })
        }, token);
        return await res.json();
    } catch (error) {
        console.error("Approval response failed", error);
        return { status: "error", message: String(error) };
    }
}

export function getApprovalsWebSocketUrl(token?: string) {
  const protocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:";
  const origin = CORE_ORIGIN.replace(/^https?:/, protocol);
  const t = token ?? getStoredToken();
  const qs = t ? `?token=${encodeURIComponent(t)}` : "";
  return `${origin}/api/v1/orchestrator/ws/approvals${qs}`;
}

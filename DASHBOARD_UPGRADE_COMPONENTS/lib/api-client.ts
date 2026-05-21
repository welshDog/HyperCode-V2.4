// lib/api-client.ts
// Centralized API client for dashboard

const API_BASE = process.env.NEXT_PUBLIC_CORE_URL || 'http://hypercode-core:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'dev';

export const apiClient = {
  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
    });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  },

  async post<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  },

  // ─────────────────────────────────────────────────────────────────────
  // ENDPOINT STATUS — verified against backend/app/api/v1/endpoints/ on
  // 2026-05-21. ✅ = exists. ❌ = NOT built yet (calling it returns 404).
  // The dashboard tabs are only as real as the endpoints behind them.
  // ─────────────────────────────────────────────────────────────────────

  // Agent endpoints
  agents: {
    // ✅ EXISTS — orchestrator.py @router.get("/agents"). Poll this (no SSE).
    list: () => apiClient.get('/orchestrator/agents'),
    // ❌ NO SSE endpoint exists. AgentMonitor now polls `list()` instead.
    // stream: removed — `/agents/stream` was never built.
  },

  // ❌ Execution — `/execution/execute-hc` DOES NOT EXIST.
  // Closest real endpoints: POST /dashboard/execute, POST /orchestrator/execute.
  // HyperCodeIDE must be rewired to one of those before it works.
  execution: {
    executeHyperCode: (source: string, timeout?: number) =>
      apiClient.post('/dashboard/execute', { source, timeout }), // ⚠️ verify contract
  },

  // ❌ Missions — no `/missions` router. Closest: GET /tasks/ (tasks.py).
  missions: {
    getTasks: () => apiClient.get('/tasks/'), // ⚠️ verify shape vs MissionTimeline
    getTask: (id: string) => apiClient.get(`/tasks/${id}`),
  },

  // ❌ Docker — NO `/docker/*` router exists at all. DockerZone is non-functional
  // until a Docker control API is built (stop/start/restart/logs/list).
  docker: {
    listContainers: () => apiClient.get('/docker/containers'),       // ❌ 404
    stopContainer: (id: string) => apiClient.post(`/docker/containers/${id}/stop`),     // ❌ 404
    restartContainer: (id: string) => apiClient.post(`/docker/containers/${id}/restart`), // ❌ 404
    getLogs: (id: string) => apiClient.get(`/docker/containers/${id}/logs`),           // ❌ 404
  },

  // ❌ MCP — NO `/mcp/*` router exists. MCPToolBrowser is non-functional until
  // an MCP registry endpoint is built. (MCP server itself runs on :8823.)
  mcp: {
    listTools: () => apiClient.get('/mcp/tools'),                    // ❌ 404
    callTool: (name: string, input: unknown) =>
      apiClient.post(`/mcp/tools/${name}/call`, input),              // ❌ 404
  },

  // ❌ Metrics — `/metrics/prometheus` + `/metrics/system` not confirmed.
  // Prometheus itself is on :9090; query it directly or build a proxy route.
  metrics: {
    getPrometheus: (query: string) =>
      apiClient.get(`/metrics/prometheus?query=${encodeURIComponent(query)}`),
    getSystemMetrics: () => apiClient.get('/metrics/system'),
  },
};

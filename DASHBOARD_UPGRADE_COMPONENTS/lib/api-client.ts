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

  // Agent endpoints
  agents: {
    list: () => apiClient.get('/agents'),
    stream: () => new EventSource(`${API_BASE}/agents/stream`),
    get: (id: string) => apiClient.get(`/agents/${id}`),
  },

  // Execution endpoints
  execution: {
    executeHyperCode: (source: string, timeout?: number) =>
      apiClient.post('/execution/execute-hc', { source, timeout }),
  },

  // Mission endpoints
  missions: {
    getTasks: () => apiClient.get('/missions/tasks'),
    getTask: (id: string) => apiClient.get(`/missions/tasks/${id}`),
  },

  // Docker endpoints
  docker: {
    listContainers: () => apiClient.get('/docker/containers'),
    stopContainer: (id: string) => apiClient.post(`/docker/containers/${id}/stop`),
    restartContainer: (id: string) => apiClient.post(`/docker/containers/${id}/restart`),
    getLogs: (id: string) => apiClient.get(`/docker/containers/${id}/logs`),
  },

  // MCP endpoints
  mcp: {
    listTools: () => apiClient.get('/mcp/tools'),
    callTool: (name: string, input: any) =>
      apiClient.post(`/mcp/tools/${name}/call`, input),
  },

  // Metrics endpoints
  metrics: {
    getPrometheus: (query: string) =>
      apiClient.get(`/metrics/prometheus?query=${encodeURIComponent(query)}`),
    getSystemMetrics: () => apiClient.get('/metrics/system'),
  },
};

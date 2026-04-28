// 🗂️ HyperCode V2.4 — Complete known service roster from docker-compose.yml
// Used to detect offline/not-broadcasting agents and services
// Grouped by type for the dashboard panels

export type ServiceGroup = 'infra' | 'core' | 'agent' | 'observability' | 'proxy';

export interface KnownService {
  name: string;          // matches Docker container_name
  label: string;         // human-readable
  group: ServiceGroup;
  profiles: string[];    // which docker compose profiles start it — [] = always on
  port?: number;         // internal port for health ping
  isAgent: boolean;      // true = shows in agents panel
  color?: string;        // hex color for the agent tile
}

export const KNOWN_SERVICES: KnownService[] = [
  // --- INFRA (always on) ---
  { name: 'redis',                    label: 'Redis',                   group: 'infra',        profiles: [],                  port: 6379,  isAgent: false, color: '#FF4500' },
  { name: 'postgres',                 label: 'Postgres',                group: 'infra',        profiles: [],                  port: 5432,  isAgent: false, color: '#006400' },
  { name: 'hypercode-ollama',         label: 'Ollama',                  group: 'infra',        profiles: [],                  port: 11434, isAgent: false, color: '#FFD700' },
  { name: 'minio',                    label: 'MinIO',                   group: 'infra',        profiles: [],                  port: 9000,  isAgent: false, color: '#0078D4' },
  { name: 'chroma',                   label: 'Chroma',                  group: 'infra',        profiles: [],                  port: 8009,  isAgent: false },

  // --- CORE (always on) ---
  { name: 'hypercode-core',           label: 'HyperCode Core',          group: 'core',         profiles: [],                  port: 8000,  isAgent: false, color: '#00F0FF' },
  { name: 'hypercode-dashboard',      label: 'Dashboard',               group: 'core',         profiles: [],                  port: 3000,  isAgent: false, color: '#FF00FF' },
  { name: 'celery-worker',            label: 'Celery Worker',           group: 'core',         profiles: [],                  port: undefined, isAgent: false, color: '#00FF00' },
  { name: 'celery-exporter',          label: 'Celery Exporter',         group: 'core',         profiles: [],                  port: 9808,  isAgent: false, color: '#FFFF00' },
  { name: 'healer-agent',             label: 'Healer Agent',            group: 'core',         profiles: [],                  port: 8008,  isAgent: true,  color: '#FF0000' },
  { name: 'hypercode-mcp-server',     label: 'MCP Server',              group: 'core',         profiles: [],                  port: 8823,  isAgent: false },

  // --- PROXY ---
  { name: 'docker-socket-proxy',       label: 'Docker Proxy (read)',     group: 'proxy',        profiles: [],                  port: 2375,  isAgent: false, color: '#00F0FF' },
  { name: 'docker-socket-proxy-healer',label: 'Docker Proxy (healer)',   group: 'proxy',        profiles: [],                  port: 2375,  isAgent: false, color: '#00F0FF' },
  { name: 'docker-socket-proxy-build', label: 'Docker Proxy (build)',    group: 'proxy',        profiles: ['ops','health','hyper'], port: 2375, isAgent: false, color: '#00F0FF'  },

  // --- OBSERVABILITY ---
  { name: 'prometheus',               label: 'Prometheus',              group: 'observability', profiles: [],                  port: 9090,  isAgent: false, color: '#00F0FF' },
  { name: 'grafana',                  label: 'Grafana',                 group: 'observability', profiles: [],                  port: 3001,  isAgent: false, color: '#00F0FF' },
  { name: 'loki',                     label: 'Loki',                    group: 'observability', profiles: [],                  port: 3100,  isAgent: false },
  { name: 'tempo',                    label: 'Tempo',                   group: 'observability', profiles: [],                  port: 3200,  isAgent: false },
  { name: 'alertmanager',             label: 'Alertmanager',            group: 'observability', profiles: [],                  port: 9093,  isAgent: false },
  { name: 'node-exporter',            label: 'Node Exporter',           group: 'observability', profiles: [],                  port: 9100,  isAgent: false },
  { name: 'cadvisor',                 label: 'cAdvisor',                group: 'observability', profiles: [],                  port: 8090,  isAgent: false },
  { name: 'promtail',                 label: 'Promtail',                group: 'observability', profiles: [],                  port: undefined, isAgent: false },

  // --- AGENTS (profile: agents) ---
  { name: 'crew-orchestrator',        label: 'Crew Orchestrator',       group: 'agent',        profiles: ['agents'],           port: 8080,  isAgent: true  },
  { name: 'coder-agent',              label: 'Coder Agent',             group: 'agent',        profiles: ['agents'],           port: 8002,  isAgent: true  },
  { name: 'project-strategist',       label: 'Project Strategist',      group: 'agent',        profiles: ['agents'],           port: 8001,  isAgent: true  },
  { name: 'frontend-specialist',      label: 'Frontend Specialist',     group: 'agent',        profiles: ['agents'],           port: 8012,  isAgent: true  },
  { name: 'backend-specialist',       label: 'Backend Specialist',      group: 'agent',        profiles: ['agents'],           port: 8003,  isAgent: true  },
  { name: 'database-architect',       label: 'Database Architect',      group: 'agent',        profiles: ['agents'],           port: 8004,  isAgent: true  },
  { name: 'qa-engineer',              label: 'QA Engineer',             group: 'agent',        profiles: ['agents'],           port: 8005,  isAgent: true  },
  { name: 'devops-engineer',          label: 'DevOps Engineer',         group: 'agent',        profiles: ['agents'],           port: 8006,  isAgent: true  },
  { name: 'security-engineer',        label: 'Security Engineer',       group: 'agent',        profiles: ['agents'],           port: 8007,  isAgent: true  },
  { name: 'system-architect',         label: 'System Architect',        group: 'agent',        profiles: ['agents'],           port: 8008,  isAgent: true  },
  { name: 'test-agent',               label: 'Test Agent',              group: 'agent',        profiles: ['agents'],           port: 8080,  isAgent: true  },
  { name: 'throttle-agent',           label: 'Throttle Agent',          group: 'agent',        profiles: ['agents'],           port: 8014,  isAgent: true  },
  { name: 'tips-tricks-writer',       label: 'Tips & Tricks Writer',    group: 'agent',        profiles: ['agents'],           port: 8009,  isAgent: true  },
  { name: 'goal-keeper',              label: 'Goal Keeper',             group: 'agent',        profiles: ['agents','goal-keeper'], port: 8050, isAgent: true },
  { name: 'super-hyper-broski-agent', label: 'Super Hyper BROski',      group: 'agent',        profiles: ['agents'],           port: 8015,  isAgent: true  },
  { name: 'mcp-gateway',              label: 'MCP Gateway',             group: 'agent',        profiles: ['agents'],           port: 8820,  isAgent: false },
  { name: 'broski-pets-bridge',       label: 'BROski Pets Bridge',      group: 'agent',        profiles: ['agents'],           port: 8098,  isAgent: true  },
  { name: 'broski-bot',               label: 'BROski Discord Bot',      group: 'agent',        profiles: ['discord'],          port: undefined, isAgent: true },

  // --- HYPER AGENTS (profile: hyper) ---
  { name: 'hyper-architect',          label: 'Hyper Architect',         group: 'agent',        profiles: ['hyper'],            port: 8091,  isAgent: true  },
  { name: 'hyper-observer',           label: 'Hyper Observer',          group: 'agent',        profiles: ['hyper'],            port: 8092,  isAgent: true  },
  { name: 'hyper-worker',             label: 'Hyper Worker',            group: 'agent',        profiles: ['hyper'],            port: 8093,  isAgent: true  },
  { name: 'hyper-split-agent',        label: 'Hyper Split Agent',       group: 'agent',        profiles: ['hyper'],            port: 8096,  isAgent: true  },
  { name: 'session-snapshot',         label: 'Session Snapshot',        group: 'agent',        profiles: ['hyper'],            port: 8097,  isAgent: true  },
  { name: 'agent-x',                  label: 'Agent X',                 group: 'agent',        profiles: ['hyper'],            port: 8080,  isAgent: true  },

  // --- HEALTH (profile: health) ---
  { name: 'hyperhealth-api',          label: 'HyperHealth API',         group: 'agent',        profiles: ['health'],           port: 8090,  isAgent: false },
  { name: 'hyperhealth-worker',       label: 'HyperHealth Worker',      group: 'agent',        profiles: ['health'],           port: undefined, isAgent: false },

  // --- MISSION (profile: mission) ---
  { name: 'hyper-mission-api',        label: 'Mission API',             group: 'agent',        profiles: ['mission'],          port: 5000,  isAgent: false },
  { name: 'hyper-mission-ui',         label: 'Mission UI',              group: 'agent',        profiles: ['mission'],          port: 8099,  isAgent: false },

  // --- AI (profile: ai) ---
  { name: 'ai-backend',               label: 'AI Backend',              group: 'core',         profiles: ['ai'],               port: 8002,  isAgent: false },
];

// Helper — agent-only subset
export const KNOWN_AGENTS = KNOWN_SERVICES.filter((s) => s.isAgent);

// Helper — always-on services (no profiles required)
export const ALWAYS_ON = KNOWN_SERVICES.filter((s) => s.profiles.length === 0);

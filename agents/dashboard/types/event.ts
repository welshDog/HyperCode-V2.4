export type EventStatus = 'started' | 'success' | 'failed' | 'healing'

export interface AgentEvent {
  agentId:   string
  taskId:    string
  status:    EventStatus
  payload:   Record<string, unknown>
  errorTrace?: string
  xpEarned:  number
  timestamp: string
}

export type EventStatus = 'started' | 'success' | 'failed' | 'healing'

export interface AgentEvent {
  agentId:   string
  taskId:    string
  status:    EventStatus
  rawStatus?: string
  payload:   Record<string, unknown>
  errorTrace?: string
  xpEarned:  number
  timestamp: string
}

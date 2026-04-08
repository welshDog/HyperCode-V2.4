export type AgentStatus = 'healthy' | 'warning' | 'error' | 'idle'

export interface Agent {
  id:            string
  name:          string
  status:        AgentStatus
  xp:            number
  xpToNextLevel: number
  level:         number
  coins?:        number
  lastAction?:   string
  port?:         number
}

export interface AgentListResponse {
  agents:    Agent[]
  updatedAt: string
}

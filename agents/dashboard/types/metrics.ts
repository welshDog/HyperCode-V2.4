export interface MetricsSnapshot {
  requestsPerMin:  number | string
  avgResponseMs:   number | string
  healsToday:      number | string
  errorRatePct:    number | string
  activeAgents:    number | string
  redisQueueDepth: number | string
  collectedAt:     string
}

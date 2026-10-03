// AG-UI-shaped events served by hypercode-core: GET /api/v1/operator/tasks/{id}/events
// (backend/app/crew/agui.py). Event/field names follow the AG-UI research doc and have not been
// checked against the current AG-UI spec.

export type AguiEvent =
  | { type: 'RUN_STARTED'; threadId: string; runId: string }
  | { type: 'RUN_FINISHED'; threadId: string; runId: string }
  | { type: 'RUN_ERROR'; message: string; code: string }
  | { type: 'STEP_STARTED' | 'STEP_FINISHED'; stepName: string }
  | { type: 'TOOL_CALL_START'; toolCallId: string; toolCallName: string }
  | { type: 'TOOL_CALL_END'; toolCallId: string }
  | { type: 'TOOL_CALL_RESULT'; toolCallId: string; content: string }
  | { type: 'CUSTOM'; name: string; value: Record<string, unknown> }

export interface SequencedEvent {
  seq: number
  event: AguiEvent
}

export type CardStatus = 'running' | 'waiting_on_you' | 'paused' | 'blocked' | 'done'

export interface CalmCardData {
  status: CardStatus
  tldr: string[]
  next_action: string
  details: string[]
  details_collapsed: boolean
  plain_text: string
}

export type TaskStatus = 'working' | 'input_required' | 'completed' | 'failed' | 'cancelled'

export interface EventsPayload {
  taskId: string
  events: SequencedEvent[]
  nextAfter: number
  done: boolean
  paused?: boolean
  status: TaskStatus
  now: string | null
  calmCard: CalmCardData
  pollInterval: number | null
}

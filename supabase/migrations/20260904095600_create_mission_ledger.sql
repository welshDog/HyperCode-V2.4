-- Mission Ledger — HyperCode V3 Foundation
-- Migration: 20260904095600
-- Description: Create missions, mission_events, mission_proof tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Missions table
CREATE TABLE IF NOT EXISTS missions (
  mission_id TEXT PRIMARY KEY,
  goal TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
    'pending', 'in_progress', 'awaiting_review', 
    'approved', 'completed', 'failed', 'rolled_back'
  )),
  builder TEXT NOT NULL DEFAULT 'claude-code',
  branch TEXT,
  pr_url TEXT,
  pr_number INTEGER,
  preview_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  next_action TEXT,
  context_pack JSONB DEFAULT '{}',
  metadata JSONB DEFAULT '{}'
);

-- Mission events table (audit trail)
CREATE TABLE IF NOT EXISTS mission_events (
  event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mission_id TEXT NOT NULL REFERENCES missions(mission_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN (
    'created', 'started', 'task_completed', 
    'review_requested', 'approved', 'deployed', 
    'failed', 'rolled_back'
  )),
  event_data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Mission proof table (test results, scans, deployments)
CREATE TABLE IF NOT EXISTS mission_proof (
  proof_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mission_id TEXT NOT NULL REFERENCES missions(mission_id) ON DELETE CASCADE,
  proof_type TEXT NOT NULL CHECK (proof_type IN (
    'lint', 'tests', 'security_scan', 
    'playwright', 'deployment', 'rollback'
  )),
  status TEXT NOT NULL CHECK (status IN ('pending', 'passed', 'failed', 'skipped')),
  result_json JSONB DEFAULT '{}',
  artifact_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);
CREATE INDEX IF NOT EXISTS idx_missions_builder ON missions(builder);
CREATE INDEX IF NOT EXISTS idx_missions_created_at ON missions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mission_events_mission_id ON mission_events(mission_id);
CREATE INDEX IF NOT EXISTS idx_mission_proof_mission_id ON mission_proof(mission_id);

-- Row Level Security (RLS)
ALTER TABLE missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE mission_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE mission_proof ENABLE ROW LEVEL SECURITY;

-- Policies (adjust based on your auth setup)
-- For now: authenticated users can read all, write their own
CREATE POLICY "Authenticated users can view all missions"
  ON missions FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can insert missions"
  ON missions FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Authenticated users can update missions"
  ON missions FOR UPDATE
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can view all mission events"
  ON mission_events FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can insert mission events"
  ON mission_events FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Authenticated users can view all mission proof"
  ON mission_proof FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can insert mission proof"
  ON mission_proof FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_missions_updated_at
  BEFORE UPDATE ON missions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Function to generate mission_id
CREATE OR REPLACE FUNCTION generate_mission_id()
RETURNS TRIGGER AS $$
DECLARE
  next_id INTEGER;
BEGIN
  IF NEW.mission_id IS NULL THEN
    SELECT COALESCE(MAX(CAST(SUBSTRING(mission_id FROM 'HC-[0-9]{4}-[0-9]{2}-([0-9]{3})$') AS INTEGER)), 0) + 1
    INTO next_id
    FROM missions
    WHERE mission_id LIKE 'HC-' || to_char(now(), 'YYYY-MM') || '-%';
    
    NEW.mission_id := 'HC-' || to_char(now(), 'YYYY-MM') || '-' || lpad(next_id::text, 3, '0');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-generate mission_id
CREATE TRIGGER set_mission_id_before_insert
  BEFORE INSERT ON missions
  FOR EACH ROW
  EXECUTE FUNCTION generate_mission_id();

COMMENT ON TABLE missions IS 'Persistent record of all agent missions in HyperCode V3';
COMMENT ON TABLE mission_events IS 'Audit trail of mission state changes';
COMMENT ON TABLE mission_proof IS 'Evidence of work: test results, security scans, deployments';

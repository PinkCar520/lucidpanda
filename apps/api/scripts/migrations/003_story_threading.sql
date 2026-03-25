-- Phase 3: Story Threading persistence
-- Use `story_id` to link lead/follower records across processing rounds.

ALTER TABLE intelligence
    ADD COLUMN IF NOT EXISTS story_id TEXT;

ALTER TABLE intelligence
    ADD COLUMN IF NOT EXISTS is_story_lead BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_intel_story_id
    ON intelligence(story_id);


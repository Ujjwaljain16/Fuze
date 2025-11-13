-- Migration: Add UserFeedback table for enhanced recommendation learning
-- Created: 2024
-- Purpose: Track user interactions with recommendations for personalization

-- Create user_feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id INTEGER NOT NULL REFERENCES saved_content(id) ON DELETE CASCADE,
    recommendation_id INTEGER,
    feedback_type VARCHAR(20) NOT NULL,  -- 'clicked', 'saved', 'dismissed', 'not_relevant', 'helpful', 'completed'
    context_data JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_user_feedback_user ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_content ON user_feedback(content_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_timestamp ON user_feedback(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_feedback_type ON user_feedback(feedback_type);

-- Add composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_timestamp ON user_feedback(user_id, timestamp DESC);

-- Grant permissions (adjust based on your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON user_feedback TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE user_feedback_id_seq TO your_app_user;

COMMENT ON TABLE user_feedback IS 'Enhanced user feedback tracking for personalized recommendations';
COMMENT ON COLUMN user_feedback.feedback_type IS 'Type of interaction: clicked, saved, dismissed, not_relevant, helpful, completed';
COMMENT ON COLUMN user_feedback.context_data IS 'JSON data containing query context, project_id, etc.';


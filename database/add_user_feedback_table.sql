-- ============================================================================
-- USER FEEDBACK TABLE
-- ============================================================================
-- Purpose: Store user feedback after completing risk assessment
-- Used by: /api/feedback endpoint
-- Notification: Telegram message sent to team on new feedback
-- Created: 2025-10-18
-- ============================================================================

-- Drop table if exists (for development/testing only)
-- DROP TABLE IF EXISTS user_feedback CASCADE;

-- Create user_feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,

    -- User identification
    user_id VARCHAR(255),                    -- Firebase UID (optional if anonymous)
    session_id VARCHAR(255) NOT NULL,        -- Browser session UUID (localStorage)

    -- Quantitative feedback (scale 1-5)
    impression_ui INTEGER CHECK (impression_ui BETWEEN 1 AND 5),              -- UI first impression
    impression_utility INTEGER CHECK (impression_utility BETWEEN 1 AND 5),    -- Utility first impression
    ease_of_use INTEGER CHECK (ease_of_use BETWEEN 1 AND 4),                  -- Ease of use (1=Molto, 4=Per nulla)
    innovation INTEGER CHECK (innovation BETWEEN 1 AND 4),                    -- Innovation (1=Molto, 4=Per nulla)
    syd_helpfulness INTEGER CHECK (syd_helpfulness BETWEEN 1 AND 4),          -- Syd Agent usefulness
    assessment_clarity INTEGER CHECK (assessment_clarity BETWEEN 1 AND 4),    -- Assessment flow clarity

    -- Qualitative feedback (open text)
    liked_most TEXT,                         -- What did you like most?
    improvements TEXT,                       -- What would you improve/add/remove?

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    user_email VARCHAR(255),                 -- Optional: user email if authenticated

    -- Foreign key (optional - may not exist if user didn't save assessment)
    assessment_id INTEGER,                   -- Reference to assessments table (if exists)

    -- Indexes for performance
    CONSTRAINT user_feedback_session_unique UNIQUE (session_id)  -- One feedback per session
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id);

-- Add comment to table
COMMENT ON TABLE user_feedback IS 'User feedback collected after first risk assessment completion';

-- Add column comments
COMMENT ON COLUMN user_feedback.impression_ui IS 'UI first impression: 1=Molto positiva, 5=Molto negativa';
COMMENT ON COLUMN user_feedback.impression_utility IS 'Utility first impression: 1=Molto positiva, 5=Molto negativa';
COMMENT ON COLUMN user_feedback.ease_of_use IS 'Ease of use: 1=Molto, 2=Abbastanza, 3=Poco, 4=Per nulla';
COMMENT ON COLUMN user_feedback.innovation IS 'Innovation: 1=Molto, 2=Abbastanza, 3=Poco, 4=Per nulla';
COMMENT ON COLUMN user_feedback.syd_helpfulness IS 'Syd Agent helpfulness: 1=Molto, 2=Abbastanza, 3=Poco, 4=Per nulla';
COMMENT ON COLUMN user_feedback.assessment_clarity IS 'Assessment flow clarity: 1=Molto, 2=Abbastanza, 3=Poco, 4=Per nulla';

-- Grant permissions (adjust as needed for your database user)
-- GRANT SELECT, INSERT ON user_feedback TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE user_feedback_id_seq TO your_app_user;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check table structure
-- SELECT column_name, data_type, character_maximum_length, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'user_feedback'
-- ORDER BY ordinal_position;

-- Check indexes
-- SELECT indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename = 'user_feedback';

-- Check constraints
-- SELECT conname, contype, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conrelid = 'user_feedback'::regclass;

-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Get average ratings
-- SELECT
--     ROUND(AVG(impression_ui), 2) as avg_ui,
--     ROUND(AVG(impression_utility), 2) as avg_utility,
--     ROUND(AVG(ease_of_use), 2) as avg_ease,
--     ROUND(AVG(innovation), 2) as avg_innovation,
--     ROUND(AVG(syd_helpfulness), 2) as avg_syd,
--     ROUND(AVG(assessment_clarity), 2) as avg_clarity,
--     COUNT(*) as total_feedback
-- FROM user_feedback;

-- Get recent feedback
-- SELECT
--     id,
--     created_at,
--     impression_ui,
--     impression_utility,
--     ease_of_use,
--     liked_most,
--     improvements
-- FROM user_feedback
-- ORDER BY created_at DESC
-- LIMIT 10;

-- Get feedback with low ratings (potential issues)
-- SELECT *
-- FROM user_feedback
-- WHERE impression_ui >= 4 OR impression_utility >= 4 OR ease_of_use >= 3
-- ORDER BY created_at DESC;

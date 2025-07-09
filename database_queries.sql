-- Database Queries for Testing User Data in pgAdmin
-- Use these queries to check user information, streaks, sessions, etc.

-- =============================================================================
-- 1. BASIC USER INFO
-- =============================================================================
SELECT id, email, first_name, last_name, 
       primary_goal, training_experience, position, age_range,
       daily_training_time, weekly_training_days
FROM users 
WHERE email = 'test@user.com';

-- =============================================================================
-- 2. PROGRESS HISTORY (STREAK INFO)
-- =============================================================================
SELECT u.email, ph.current_streak, ph.highest_streak, 
       ph.completed_sessions_count, ph.updated_at
FROM users u
LEFT JOIN progress_history ph ON u.id = ph.user_id
WHERE u.email = 'test@user.com';

-- =============================================================================
-- 3. COMPLETED SESSIONS
-- =============================================================================
SELECT u.email, cs.date, cs.total_completed_drills, 
       cs.total_drills, cs.drills
FROM users u
LEFT JOIN completed_sessions cs ON u.id = cs.user_id
WHERE u.email = 'test@user.com'
ORDER BY cs.date DESC;

-- =============================================================================
-- 4. CURRENT SESSION DRILLS (ORDERED)
-- =============================================================================
SELECT u.email, d.title, osd.position, osd.sets, osd.reps, 
       osd.duration, osd.is_completed, osd.sets_done
FROM users u
LEFT JOIN training_sessions ts ON u.id = ts.user_id
LEFT JOIN ordered_session_drills osd ON ts.id = osd.session_id
LEFT JOIN drills d ON osd.drill_id = d.id
WHERE u.email = 'test@user.com'
ORDER BY osd.position;

-- =============================================================================
-- 5. DRILL GROUPS
-- =============================================================================
SELECT u.email, dg.name, dg.description, dg.is_liked_group,
       COUNT(dgi.drill_id) as drill_count
FROM users u
LEFT JOIN drill_groups dg ON u.id = dg.user_id
LEFT JOIN drill_group_items dgi ON dg.id = dgi.drill_group_id
WHERE u.email = 'test@user.com'
GROUP BY u.email, dg.id, dg.name, dg.description, dg.is_liked_group;

-- =============================================================================
-- 6. SESSION PREFERENCES
-- =============================================================================
SELECT u.email, sp.duration, sp.available_equipment, 
       sp.training_style, sp.training_location, sp.difficulty,
       sp.target_skills, sp.created_at, sp.updated_at
FROM users u
LEFT JOIN session_preferences sp ON u.id = sp.user_id
WHERE u.email = 'test@user.com';

-- =============================================================================
-- 7. REFRESH TOKENS (ACTIVE)
-- =============================================================================
SELECT u.email, rt.token, rt.expires_at, rt.created_at, rt.is_revoked
FROM users u
LEFT JOIN refresh_tokens rt ON u.id = rt.user_id
WHERE u.email = 'test@user.com'
AND rt.is_revoked = FALSE
AND rt.expires_at > NOW()
ORDER BY rt.created_at DESC;

-- =============================================================================
-- 8. COMPLETE USER PROFILE (ALL DATA)
-- =============================================================================
-- Get user ID first
WITH user_info AS (
    SELECT id, email FROM users WHERE email = 'test@user.com'
)
SELECT 
    'User Info' as data_type,
    json_build_object(
        'email', u.email,
        'training_experience', u.training_experience,
        'position', u.position,
        'daily_training_time', u.daily_training_time
    ) as data
FROM users u, user_info ui WHERE u.id = ui.id

UNION ALL

SELECT 
    'Progress History' as data_type,
    json_build_object(
        'current_streak', ph.current_streak,
        'highest_streak', ph.highest_streak,
        'completed_sessions_count', ph.completed_sessions_count,
        'updated_at', ph.updated_at
    ) as data
FROM progress_history ph, user_info ui WHERE ph.user_id = ui.id

UNION ALL

SELECT 
    'Session Preferences' as data_type,
    json_build_object(
        'duration', sp.duration,
        'training_style', sp.training_style,
        'difficulty', sp.difficulty,
        'available_equipment', sp.available_equipment
    ) as data
FROM session_preferences sp, user_info ui WHERE sp.user_id = ui.id;

-- =============================================================================
-- 9. QUICK STREAK CHECK (RECOMMENDED STARTING POINT)
-- =============================================================================
-- Simple streak info - USE THIS ONE FIRST
SELECT 
    u.email,
    COALESCE(ph.current_streak, 0) as current_streak,
    COALESCE(ph.highest_streak, 0) as highest_streak,
    COALESCE(ph.completed_sessions_count, 0) as total_sessions,
    ph.updated_at as last_updated
FROM users u
LEFT JOIN progress_history ph ON u.id = ph.user_id
WHERE u.email = 'test@user.com';

-- =============================================================================
-- 10. UPDATE STREAK FOR TESTING (USE CAREFULLY!)
-- =============================================================================
-- Uncomment and modify these to test streak functionality

-- Reset streak to 0
-- UPDATE progress_history 
-- SET current_streak = 0, updated_at = NOW()
-- WHERE user_id = (SELECT id FROM users WHERE email = 'test@user.com');

-- Set specific streak values for testing
-- UPDATE progress_history 
-- SET current_streak = 5, highest_streak = 10, completed_sessions_count = 15, updated_at = NOW()
-- WHERE user_id = (SELECT id FROM users WHERE email = 'test@user.com');

-- =============================================================================
-- 11. CHECK ALL USERS (FOR OVERVIEW)
-- =============================================================================
SELECT u.email, 
       COALESCE(ph.current_streak, 0) as current_streak,
       COALESCE(ph.completed_sessions_count, 0) as total_sessions,
       COUNT(cs.id) as completed_sessions_in_db
FROM users u
LEFT JOIN progress_history ph ON u.id = ph.user_id
LEFT JOIN completed_sessions cs ON u.id = cs.user_id
GROUP BY u.id, u.email, ph.current_streak, ph.completed_sessions_count
ORDER BY u.email;

-- =============================================================================
-- HOW TO USE:
-- 1. Open pgAdmin and connect to your 'bravoball' database
-- 2. Open Query Tool (Tools → Query Tool)
-- 3. Copy and paste any query above
-- 4. Change 'test@user.com' to the email you want to test
-- 5. Click Execute (F5)
-- 
-- START WITH QUERY #9 for a quick overview!
-- =============================================================================

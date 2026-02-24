-- ========================================
-- Migration: 003_create_goals_and_progress (DOWN)
-- Description: Откат создания таблиц goals и goal_progress
-- ========================================

DROP TABLE IF EXISTS goal_progress CASCADE;
DROP TABLE IF EXISTS goals CASCADE;

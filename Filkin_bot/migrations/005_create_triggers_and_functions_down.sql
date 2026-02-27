-- ========================================
-- Migration: 005_create_triggers_and_functions (DOWN)
-- Description: Откат создания триггеров и функций
-- ========================================

-- Удаление триггеров
DROP TRIGGER IF EXISTS trigger_calculate_next_occurrence ON transactions;
DROP TRIGGER IF EXISTS trigger_update_goal_progress ON goal_progress;
DROP TRIGGER IF EXISTS trigger_update_user_balance ON transactions;
DROP TRIGGER IF EXISTS trigger_goals_updated_at ON goals;
DROP TRIGGER IF EXISTS trigger_transactions_updated_at ON transactions;
DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;

-- Удаление функций
DROP FUNCTION IF EXISTS get_goal_completion_percentage(BIGINT);
DROP FUNCTION IF EXISTS get_user_balance(BIGINT);
DROP FUNCTION IF EXISTS calculate_next_occurrence();
DROP FUNCTION IF EXISTS update_goal_progress_amount();
DROP FUNCTION IF EXISTS update_user_balance();
DROP FUNCTION IF EXISTS update_updated_at_column();

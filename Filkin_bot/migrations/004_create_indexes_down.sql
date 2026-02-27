-- ========================================
-- Migration: 004_create_indexes (DOWN)
-- Description: Откат создания индексов
-- ========================================

-- Users
DROP INDEX IF EXISTS idx_users_active_created;
DROP INDEX IF EXISTS idx_users_last_activity;
DROP INDEX IF EXISTS idx_users_created_at;
DROP INDEX IF EXISTS idx_users_is_active;
DROP INDEX IF EXISTS idx_users_telegram_id;

-- Transactions
DROP INDEX IF EXISTS idx_transactions_metadata;
DROP INDEX IF EXISTS idx_transactions_tags;
DROP INDEX IF EXISTS idx_transactions_account;
DROP INDEX IF EXISTS idx_transactions_recurring;
DROP INDEX IF EXISTS idx_transactions_is_deleted;
DROP INDEX IF EXISTS idx_transactions_user_category_date;
DROP INDEX IF EXISTS idx_transactions_user_type;
DROP INDEX IF EXISTS idx_transactions_user_created;
DROP INDEX IF EXISTS idx_transactions_user_date;
DROP INDEX IF EXISTS idx_transactions_created_at;
DROP INDEX IF EXISTS idx_transactions_date;
DROP INDEX IF EXISTS idx_transactions_category;
DROP INDEX IF EXISTS idx_transactions_type;
DROP INDEX IF EXISTS idx_transactions_user_id;

-- Goals
DROP INDEX IF EXISTS idx_goals_near_completion;
DROP INDEX IF EXISTS idx_goals_user_priority;
DROP INDEX IF EXISTS idx_goals_user_target_date;
DROP INDEX IF EXISTS idx_goals_user_created;
DROP INDEX IF EXISTS idx_goals_user_status;
DROP INDEX IF EXISTS idx_goals_priority;
DROP INDEX IF EXISTS idx_goals_target_date;
DROP INDEX IF EXISTS idx_goals_created_at;
DROP INDEX IF EXISTS idx_goals_status;
DROP INDEX IF EXISTS idx_goals_user_id;

-- Goal Progress
DROP INDEX IF EXISTS idx_goal_progress_transaction;
DROP INDEX IF EXISTS idx_goal_progress_user_date;
DROP INDEX IF EXISTS idx_goal_progress_goal_date;
DROP INDEX IF EXISTS idx_goal_progress_created;
DROP INDEX IF EXISTS idx_goal_progress_date;
DROP INDEX IF EXISTS idx_goal_progress_user_id;
DROP INDEX IF EXISTS idx_goal_progress_goal_id;

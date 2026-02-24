-- ========================================
-- Migration: 004_create_indexes
-- Description: Создание индексов для оптимизации запросов
-- ========================================

-- UP Migration
-- ========================================

-- ========================================
-- Индексы для таблицы users
-- ========================================

-- Основные индексы
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_users_created_at ON users(created_at DESC);
CREATE INDEX idx_users_last_activity ON users(last_activity_at DESC);

-- Составные индексы для аналитики
CREATE INDEX idx_users_active_created ON users(is_active, created_at DESC) WHERE is_active = TRUE;

-- ========================================
-- Индексы для таблицы transactions
-- ========================================

-- Основные индексы
CREATE INDEX idx_transactions_user_id ON transactions(user_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_transactions_date ON transactions(transaction_date DESC);
CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);

-- Составные индексы (user_id + date) - критичные для производительности
CREATE INDEX idx_transactions_user_date ON transactions(user_id, transaction_date DESC) WHERE is_deleted = FALSE;
CREATE INDEX idx_transactions_user_created ON transactions(user_id, created_at DESC) WHERE is_deleted = FALSE;
CREATE INDEX idx_transactions_user_type ON transactions(user_id, transaction_type) WHERE is_deleted = FALSE;
CREATE INDEX idx_transactions_user_category_date ON transactions(user_id, category, transaction_date DESC) WHERE is_deleted = FALSE;

-- Индексы для специфических запросов
CREATE INDEX idx_transactions_is_deleted ON transactions(is_deleted, deleted_at) WHERE is_deleted = TRUE;
CREATE INDEX idx_transactions_recurring ON transactions(user_id, is_recurring, next_occurrence_date) 
    WHERE is_recurring = TRUE AND is_deleted = FALSE;
CREATE INDEX idx_transactions_account ON transactions(user_id, account_name) WHERE is_deleted = FALSE;

-- GIN индекс для массивов тегов (для полнотекстового поиска)
CREATE INDEX idx_transactions_tags ON transactions USING GIN(tags);

-- Индекс для JSONB метаданных (опционально, если будут поиски)
CREATE INDEX idx_transactions_metadata ON transactions USING GIN(metadata);

-- ========================================
-- Индексы для таблицы goals
-- ========================================

-- Основные индексы
CREATE INDEX idx_goals_user_id ON goals(user_id);
CREATE INDEX idx_goals_status ON goals(status);
CREATE INDEX idx_goals_created_at ON goals(created_at DESC);
CREATE INDEX idx_goals_target_date ON goals(target_date);
CREATE INDEX idx_goals_priority ON goals(priority DESC);

-- Составные индексы (user_id + другие поля)
CREATE INDEX idx_goals_user_status ON goals(user_id, status);
CREATE INDEX idx_goals_user_created ON goals(user_id, created_at DESC);
CREATE INDEX idx_goals_user_target_date ON goals(user_id, target_date) WHERE status = 'active';
CREATE INDEX idx_goals_user_priority ON goals(user_id, priority DESC, target_date) WHERE status = 'active';

-- Индекс для поиска активных целей близких к завершению
CREATE INDEX idx_goals_near_completion ON goals(user_id, status, current_amount, target_amount) 
    WHERE status = 'active' AND current_amount >= target_amount * 0.8;

-- ========================================
-- Индексы для таблицы goal_progress
-- ========================================

-- Основные индексы
CREATE INDEX idx_goal_progress_goal_id ON goal_progress(goal_id);
CREATE INDEX idx_goal_progress_user_id ON goal_progress(user_id);
CREATE INDEX idx_goal_progress_date ON goal_progress(progress_date DESC);
CREATE INDEX idx_goal_progress_created ON goal_progress(created_at DESC);

-- Составные индексы (goal_id / user_id + date)
CREATE INDEX idx_goal_progress_goal_date ON goal_progress(goal_id, progress_date DESC);
CREATE INDEX idx_goal_progress_user_date ON goal_progress(user_id, progress_date DESC);

-- Индекс для связи с транзакциями
CREATE INDEX idx_goal_progress_transaction ON goal_progress(transaction_id) WHERE transaction_id IS NOT NULL;

-- ========================================
-- DOWN Migration (откат)
-- ========================================

-- Для отката выполните:
-- 
-- -- Users
-- DROP INDEX IF EXISTS idx_users_telegram_id;
-- DROP INDEX IF EXISTS idx_users_is_active;
-- DROP INDEX IF EXISTS idx_users_created_at;
-- DROP INDEX IF EXISTS idx_users_last_activity;
-- DROP INDEX IF EXISTS idx_users_active_created;
-- 
-- -- Transactions
-- DROP INDEX IF EXISTS idx_transactions_user_id;
-- DROP INDEX IF EXISTS idx_transactions_type;
-- DROP INDEX IF EXISTS idx_transactions_category;
-- DROP INDEX IF EXISTS idx_transactions_date;
-- DROP INDEX IF EXISTS idx_transactions_created_at;
-- DROP INDEX IF EXISTS idx_transactions_user_date;
-- DROP INDEX IF EXISTS idx_transactions_user_created;
-- DROP INDEX IF EXISTS idx_transactions_user_type;
-- DROP INDEX IF EXISTS idx_transactions_user_category_date;
-- DROP INDEX IF EXISTS idx_transactions_is_deleted;
-- DROP INDEX IF EXISTS idx_transactions_recurring;
-- DROP INDEX IF EXISTS idx_transactions_account;
-- DROP INDEX IF EXISTS idx_transactions_tags;
-- DROP INDEX IF EXISTS idx_transactions_metadata;
-- 
-- -- Goals
-- DROP INDEX IF EXISTS idx_goals_user_id;
-- DROP INDEX IF EXISTS idx_goals_status;
-- DROP INDEX IF EXISTS idx_goals_created_at;
-- DROP INDEX IF EXISTS idx_goals_target_date;
-- DROP INDEX IF EXISTS idx_goals_priority;
-- DROP INDEX IF EXISTS idx_goals_user_status;
-- DROP INDEX IF EXISTS idx_goals_user_created;
-- DROP INDEX IF EXISTS idx_goals_user_target_date;
-- DROP INDEX IF EXISTS idx_goals_user_priority;
-- DROP INDEX IF EXISTS idx_goals_near_completion;
-- 
-- -- Goal Progress
-- DROP INDEX IF EXISTS idx_goal_progress_goal_id;
-- DROP INDEX IF EXISTS idx_goal_progress_user_id;
-- DROP INDEX IF EXISTS idx_goal_progress_date;
-- DROP INDEX IF EXISTS idx_goal_progress_created;
-- DROP INDEX IF EXISTS idx_goal_progress_goal_date;
-- DROP INDEX IF EXISTS idx_goal_progress_user_date;
-- DROP INDEX IF EXISTS idx_goal_progress_transaction;

-- ========================================
-- Migration: 006_create_views (DOWN)
-- Description: Откат создания представлений
-- ========================================

DROP VIEW IF EXISTS goals_near_completion;
DROP VIEW IF EXISTS top_expense_categories;
DROP VIEW IF EXISTS pending_recurring_transactions;
DROP VIEW IF EXISTS monthly_category_stats;
DROP VIEW IF EXISTS transactions_with_user;
DROP VIEW IF EXISTS goals_summary;
DROP VIEW IF EXISTS active_users;

-- ========================================
-- Migration: 002_create_users_and_transactions (DOWN)
-- Description: Откат создания таблиц users и transactions
-- ========================================

DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ========================================
-- Migration: 007_add_transaction_function (DOWN)
-- Description: Откат функций для работы с транзакциями
-- ========================================

DROP FUNCTION IF EXISTS get_recent_transactions(BIGINT, INTEGER);
DROP FUNCTION IF EXISTS add_transaction_simple(BIGINT, DECIMAL, transaction_type_enum, VARCHAR, TEXT);
DROP FUNCTION IF EXISTS add_transaction(BIGINT, DECIMAL, transaction_type_enum, VARCHAR, TIMESTAMP WITH TIME ZONE, TEXT, VARCHAR, VARCHAR, TEXT[], BOOLEAN, recurring_frequency_enum);

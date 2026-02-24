-- ========================================
-- Migration: 001_create_enum_types (DOWN)
-- Description: Откат создания ENUM типов
-- ========================================

DROP TYPE IF EXISTS recurring_frequency_enum CASCADE;
DROP TYPE IF EXISTS progress_type_enum CASCADE;
DROP TYPE IF EXISTS goal_status_enum CASCADE;
DROP TYPE IF EXISTS transaction_type_enum CASCADE;

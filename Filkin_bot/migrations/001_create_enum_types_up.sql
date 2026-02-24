-- ========================================
-- Migration: 001_create_enum_types
-- Description: Создание ENUM типов для типобезопасности
-- ========================================

-- UP Migration
-- ========================================

-- Тип транзакции
CREATE TYPE transaction_type_enum AS ENUM (
    'income',      -- доход
    'expense',     -- расход
    'transfer'     -- перевод между счетами
);

COMMENT ON TYPE transaction_type_enum IS 'Типы финансовых транзакций';

-- Статус цели
CREATE TYPE goal_status_enum AS ENUM (
    'active',      -- активная
    'completed',   -- достигнута
    'cancelled',   -- отменена
    'paused'       -- приостановлена
);

COMMENT ON TYPE goal_status_enum IS 'Статусы финансовых целей';

-- Тип изменения прогресса цели
CREATE TYPE progress_type_enum AS ENUM (
    'contribution',  -- вклад
    'withdrawal',    -- снятие
    'adjustment'     -- корректировка
);

COMMENT ON TYPE progress_type_enum IS 'Типы изменений прогресса целей';

-- Частота повторения транзакций
CREATE TYPE recurring_frequency_enum AS ENUM (
    'daily',       -- ежедневно
    'weekly',      -- еженедельно
    'monthly',     -- ежемесячно
    'yearly'       -- ежегодно
);

COMMENT ON TYPE recurring_frequency_enum IS 'Частота повторения регулярных транзакций';

-- ========================================
-- DOWN Migration (откат)
-- ========================================

-- Для отката выполните:
-- DROP TYPE IF EXISTS recurring_frequency_enum CASCADE;
-- DROP TYPE IF EXISTS progress_type_enum CASCADE;
-- DROP TYPE IF EXISTS goal_status_enum CASCADE;
-- DROP TYPE IF EXISTS transaction_type_enum CASCADE;

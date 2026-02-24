-- ========================================
-- Migration: 002_create_users_and_transactions
-- Description: Создание основных таблиц users и transactions
-- ========================================

-- UP Migration
-- ========================================

-- Таблица пользователей
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'ru',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Настройки пользователя
    default_currency VARCHAR(3) DEFAULT 'RUB',
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    
    -- Метаданные (денормализация для производительности)
    total_transactions INTEGER DEFAULT 0,
    total_income DECIMAL(15, 2) DEFAULT 0.00,
    total_expenses DECIMAL(15, 2) DEFAULT 0.00,
    current_balance DECIMAL(15, 2) DEFAULT 0.00,
    
    CONSTRAINT positive_totals CHECK (
        total_transactions >= 0 AND 
        total_income >= 0 AND 
        total_expenses >= 0
    )
);

-- Таблица транзакций
CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Основные данные транзакции
    amount DECIMAL(15, 2) NOT NULL CHECK (amount > 0),
    transaction_type transaction_type_enum NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Дата и время
    transaction_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Финансовые детали
    currency VARCHAR(3) DEFAULT 'RUB',
    account_name VARCHAR(100) DEFAULT 'main',
    
    -- Дополнительные поля для регулярных транзакций
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_frequency recurring_frequency_enum,
    parent_transaction_id BIGINT REFERENCES transactions(id) ON DELETE SET NULL,
    next_occurrence_date TIMESTAMP WITH TIME ZONE,
    
    -- Метаданные
    tags TEXT[],
    attachments JSONB,
    metadata JSONB,
    
    -- Мягкое удаление
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_recurring_setup CHECK (
        (is_recurring = FALSE) OR 
        (is_recurring = TRUE AND recurring_frequency IS NOT NULL)
    ),
    CONSTRAINT valid_deletion CHECK (
        (is_deleted = FALSE AND deleted_at IS NULL) OR
        (is_deleted = TRUE AND deleted_at IS NOT NULL)
    )
);

-- Комментарии
COMMENT ON TABLE users IS 'Пользователи Telegram-бота';
COMMENT ON TABLE transactions IS 'Финансовые транзакции (доходы и расходы)';

COMMENT ON COLUMN users.telegram_id IS 'Уникальный ID пользователя в Telegram';
COMMENT ON COLUMN users.current_balance IS 'Текущий баланс (income - expenses)';
COMMENT ON COLUMN users.total_transactions IS 'Счетчик транзакций (денормализация)';

COMMENT ON COLUMN transactions.transaction_type IS 'Тип транзакции: income (доход), expense (расход), transfer (перевод)';
COMMENT ON COLUMN transactions.is_recurring IS 'Является ли транзакция регулярной';
COMMENT ON COLUMN transactions.recurring_frequency IS 'Частота повтора: daily, weekly, monthly, yearly';
COMMENT ON COLUMN transactions.parent_transaction_id IS 'Ссылка на родительскую транзакцию (для регулярных)';
COMMENT ON COLUMN transactions.next_occurrence_date IS 'Дата следующего автоматического создания транзакции';
COMMENT ON COLUMN transactions.tags IS 'Массив тегов для категоризации';
COMMENT ON COLUMN transactions.is_deleted IS 'Флаг мягкого удаления (для сохранения истории)';

-- ========================================
-- DOWN Migration (откат)
-- ========================================

-- Для отката выполните:
-- DROP TABLE IF EXISTS transactions CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;

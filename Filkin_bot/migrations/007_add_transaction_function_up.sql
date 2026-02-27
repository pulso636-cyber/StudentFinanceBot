-- ========================================
-- Migration: 007_add_transaction_function
-- Description: Функция для добавления транзакций с валидацией
-- ========================================

-- UP Migration
-- ========================================

-- ========================================
-- Функция: Добавление транзакции
-- ========================================

CREATE OR REPLACE FUNCTION add_transaction(
    p_user_id BIGINT,
    p_amount DECIMAL(15, 2),
    p_transaction_type transaction_type_enum,
    p_category VARCHAR(100),
    p_transaction_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    p_description TEXT DEFAULT NULL,
    p_currency VARCHAR(3) DEFAULT 'RUB',
    p_account_name VARCHAR(100) DEFAULT 'main',
    p_tags TEXT[] DEFAULT NULL,
    p_is_recurring BOOLEAN DEFAULT FALSE,
    p_recurring_frequency recurring_frequency_enum DEFAULT NULL
)
RETURNS TABLE(
    transaction_id BIGINT,
    new_balance DECIMAL(15, 2),
    success BOOLEAN,
    message TEXT
) AS $$
DECLARE
    v_transaction_id BIGINT;
    v_user_exists BOOLEAN;
    v_new_balance DECIMAL(15, 2);
BEGIN
    -- Проверка существования пользователя
    SELECT EXISTS(SELECT 1 FROM users WHERE id = p_user_id AND is_active = TRUE)
    INTO v_user_exists;
    
    IF NOT v_user_exists THEN
        RETURN QUERY SELECT NULL::BIGINT, NULL::DECIMAL(15, 2), FALSE, 'User not found or inactive'::TEXT;
        RETURN;
    END IF;
    
    -- Валидация суммы
    IF p_amount <= 0 THEN
        RETURN QUERY SELECT NULL::BIGINT, NULL::DECIMAL(15, 2), FALSE, 'Amount must be greater than 0'::TEXT;
        RETURN;
    END IF;
    
    -- Валидация регулярной транзакции
    IF p_is_recurring = TRUE AND p_recurring_frequency IS NULL THEN
        RETURN QUERY SELECT NULL::BIGINT, NULL::DECIMAL(15, 2), FALSE, 'Recurring frequency is required for recurring transactions'::TEXT;
        RETURN;
    END IF;
    
    -- Вставка транзакции
    INSERT INTO transactions (
        user_id,
        amount,
        transaction_type,
        category,
        transaction_date,
        description,
        currency,
        account_name,
        tags,
        is_recurring,
        recurring_frequency,
        is_deleted
    ) VALUES (
        p_user_id,
        p_amount,
        p_transaction_type,
        p_category,
        COALESCE(p_transaction_date, CURRENT_TIMESTAMP),
        p_description,
        p_currency,
        p_account_name,
        p_tags,
        p_is_recurring,
        p_recurring_frequency,
        FALSE
    )
    RETURNING id INTO v_transaction_id;
    
    -- Получаем новый баланс пользователя (обновлен триггером)
    SELECT current_balance INTO v_new_balance
    FROM users
    WHERE id = p_user_id;
    
    -- Возвращаем результат
    RETURN QUERY SELECT 
        v_transaction_id,
        v_new_balance,
        TRUE,
        'Transaction added successfully'::TEXT;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN QUERY SELECT 
            NULL::BIGINT, 
            NULL::DECIMAL(15, 2), 
            FALSE, 
            ('Error: ' || SQLERRM)::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION add_transaction IS 'Добавление транзакции с валидацией и автоматическим пересчетом баланса';

-- ========================================
-- Функция: Быстрое добавление транзакции (упрощенная версия)
-- ========================================

CREATE OR REPLACE FUNCTION add_transaction_simple(
    p_telegram_id BIGINT,
    p_amount DECIMAL(15, 2),
    p_transaction_type transaction_type_enum,
    p_category VARCHAR(100),
    p_description TEXT DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_user_id BIGINT;
    v_transaction_id BIGINT;
BEGIN
    -- Получить user_id по telegram_id
    SELECT id INTO v_user_id
    FROM users
    WHERE telegram_id = p_telegram_id AND is_active = TRUE;
    
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'User with telegram_id % not found', p_telegram_id;
    END IF;
    
    -- Вставить транзакцию
    INSERT INTO transactions (
        user_id,
        amount,
        transaction_type,
        category,
        description
    ) VALUES (
        v_user_id,
        p_amount,
        p_transaction_type,
        p_category,
        p_description
    )
    RETURNING id INTO v_transaction_id;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION add_transaction_simple IS 'Упрощенная функция добавления транзакции по telegram_id';

-- ========================================
-- Функция: Получить последние транзакции пользователя
-- ========================================

CREATE OR REPLACE FUNCTION get_recent_transactions(
    p_telegram_id BIGINT,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE(
    id BIGINT,
    amount DECIMAL(15, 2),
    transaction_type transaction_type_enum,
    category VARCHAR(100),
    description TEXT,
    transaction_date TIMESTAMP WITH TIME ZONE,
    currency VARCHAR(3)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.amount,
        t.transaction_type,
        t.category,
        t.description,
        t.transaction_date,
        t.currency
    FROM transactions t
    JOIN users u ON t.user_id = u.id
    WHERE u.telegram_id = p_telegram_id
      AND t.is_deleted = FALSE
    ORDER BY t.transaction_date DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_recent_transactions IS 'Получить последние N транзакций пользователя по telegram_id';

-- ========================================
-- DOWN Migration (откат)
-- ========================================

-- Для отката выполните:
-- DROP FUNCTION IF EXISTS get_recent_transactions(BIGINT, INTEGER);
-- DROP FUNCTION IF EXISTS add_transaction_simple(BIGINT, DECIMAL, transaction_type_enum, VARCHAR, TEXT);
-- DROP FUNCTION IF EXISTS add_transaction(BIGINT, DECIMAL, transaction_type_enum, VARCHAR, TIMESTAMP WITH TIME ZONE, TEXT, VARCHAR, VARCHAR, TEXT[], BOOLEAN, recurring_frequency_enum);

-- ========================================
-- Migration: 005_create_triggers_and_functions
-- Description: Создание функций и триггеров для автоматизации
-- ========================================

-- UP Migration
-- ========================================

-- ========================================
-- Функция 1: Автоматическое обновление updated_at
-- ========================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS 'Автоматически обновляет поле updated_at при изменении записи';

-- ========================================
-- Функция 2: Обновление баланса пользователя
-- ========================================

CREATE OR REPLACE FUNCTION update_user_balance()
RETURNS TRIGGER AS $$
BEGIN
    -- Добавление новой транзакции
    IF TG_OP = 'INSERT' AND NEW.is_deleted = FALSE THEN
        UPDATE users
        SET 
            total_transactions = total_transactions + 1,
            total_income = CASE 
                WHEN NEW.transaction_type = 'income' THEN total_income + NEW.amount
                ELSE total_income
            END,
            total_expenses = CASE 
                WHEN NEW.transaction_type = 'expense' THEN total_expenses + NEW.amount
                ELSE total_expenses
            END,
            current_balance = CASE 
                WHEN NEW.transaction_type = 'income' THEN current_balance + NEW.amount
                WHEN NEW.transaction_type = 'expense' THEN current_balance - NEW.amount
                ELSE current_balance
            END,
            last_activity_at = CURRENT_TIMESTAMP
        WHERE id = NEW.user_id;
        
    -- Мягкое удаление транзакции
    ELSIF TG_OP = 'UPDATE' AND OLD.is_deleted = FALSE AND NEW.is_deleted = TRUE THEN
        UPDATE users
        SET 
            total_transactions = total_transactions - 1,
            total_income = CASE 
                WHEN OLD.transaction_type = 'income' THEN total_income - OLD.amount
                ELSE total_income
            END,
            total_expenses = CASE 
                WHEN OLD.transaction_type = 'expense' THEN total_expenses - OLD.amount
                ELSE total_expenses
            END,
            current_balance = CASE 
                WHEN OLD.transaction_type = 'income' THEN current_balance - OLD.amount
                WHEN OLD.transaction_type = 'expense' THEN current_balance + OLD.amount
                ELSE current_balance
            END
        WHERE id = OLD.user_id;
        
    -- Восстановление удаленной транзакции
    ELSIF TG_OP = 'UPDATE' AND OLD.is_deleted = TRUE AND NEW.is_deleted = FALSE THEN
        UPDATE users
        SET 
            total_transactions = total_transactions + 1,
            total_income = CASE 
                WHEN NEW.transaction_type = 'income' THEN total_income + NEW.amount
                ELSE total_income
            END,
            total_expenses = CASE 
                WHEN NEW.transaction_type = 'expense' THEN total_expenses + NEW.amount
                ELSE total_expenses
            END,
            current_balance = CASE 
                WHEN NEW.transaction_type = 'income' THEN current_balance + NEW.amount
                WHEN NEW.transaction_type = 'expense' THEN current_balance - NEW.amount
                ELSE current_balance
            END,
            last_activity_at = CURRENT_TIMESTAMP
        WHERE id = NEW.user_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_user_balance() IS 'Автоматически обновляет баланс и статистику пользователя при изменении транзакций';

-- ========================================
-- Функция 3: Обновление прогресса цели
-- ========================================

CREATE OR REPLACE FUNCTION update_goal_progress_amount()
RETURNS TRIGGER AS $$
DECLARE
    goal_record RECORD;
BEGIN
    -- Получаем текущее состояние цели
    SELECT * INTO goal_record FROM goals WHERE id = NEW.goal_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Goal with id % not found', NEW.goal_id;
    END IF;
    
    -- Сохраняем состояние до изменения
    NEW.goal_amount_before := goal_record.current_amount;
    
    -- Обновляем цель
    UPDATE goals
    SET 
        current_amount = CASE 
            WHEN NEW.progress_type = 'contribution' THEN current_amount + NEW.amount
            WHEN NEW.progress_type = 'withdrawal' THEN current_amount - NEW.amount
            WHEN NEW.progress_type = 'adjustment' THEN NEW.amount
            ELSE current_amount
        END,
        status = CASE 
            -- Автоматически завершаем цель при достижении
            WHEN NEW.progress_type = 'contribution' AND (current_amount + NEW.amount) >= target_amount 
                THEN 'completed'::goal_status_enum
            ELSE status
        END,
        completed_at = CASE 
            WHEN NEW.progress_type = 'contribution' AND (current_amount + NEW.amount) >= target_amount 
                THEN CURRENT_TIMESTAMP
            ELSE completed_at
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.goal_id
    RETURNING current_amount INTO NEW.goal_amount_after;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_goal_progress_amount() IS 'Автоматически обновляет прогресс цели и сохраняет историю изменений';

-- ========================================
-- Функция 4: Расчет следующей даты для регулярной транзакции
-- ========================================

CREATE OR REPLACE FUNCTION calculate_next_occurrence()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_recurring = TRUE AND NEW.recurring_frequency IS NOT NULL THEN
        NEW.next_occurrence_date := CASE NEW.recurring_frequency
            WHEN 'daily' THEN NEW.transaction_date + INTERVAL '1 day'
            WHEN 'weekly' THEN NEW.transaction_date + INTERVAL '1 week'
            WHEN 'monthly' THEN NEW.transaction_date + INTERVAL '1 month'
            WHEN 'yearly' THEN NEW.transaction_date + INTERVAL '1 year'
        END;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_next_occurrence() IS 'Автоматически рассчитывает дату следующего выполнения регулярной транзакции';

-- ========================================
-- ТРИГГЕРЫ
-- ========================================

-- Триггер: обновление updated_at для users
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггер: обновление updated_at для transactions
CREATE TRIGGER trigger_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггер: обновление updated_at для goals
CREATE TRIGGER trigger_goals_updated_at
    BEFORE UPDATE ON goals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггер: автоматический пересчет баланса пользователя
CREATE TRIGGER trigger_update_user_balance
    AFTER INSERT OR UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_user_balance();

-- Триггер: автоматическое обновление прогресса цели
CREATE TRIGGER trigger_update_goal_progress
    BEFORE INSERT ON goal_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_goal_progress_amount();

-- Триггер: расчет следующей даты для регулярных транзакций
CREATE TRIGGER trigger_calculate_next_occurrence
    BEFORE INSERT OR UPDATE ON transactions
    FOR EACH ROW
    WHEN (NEW.is_recurring = TRUE)
    EXECUTE FUNCTION calculate_next_occurrence();

-- ========================================
-- Дополнительные функции для удобства
-- ========================================

-- Функция: получить баланс пользователя по telegram_id
CREATE OR REPLACE FUNCTION get_user_balance(p_telegram_id BIGINT)
RETURNS TABLE(
    balance DECIMAL(15, 2),
    income DECIMAL(15, 2),
    expenses DECIMAL(15, 2),
    transaction_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.current_balance,
        u.total_income,
        u.total_expenses,
        u.total_transactions
    FROM users u
    WHERE u.telegram_id = p_telegram_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_user_balance(BIGINT) IS 'Получить баланс и статистику пользователя по telegram_id';

-- Функция: получить процент выполнения цели
CREATE OR REPLACE FUNCTION get_goal_completion_percentage(p_goal_id BIGINT)
RETURNS DECIMAL(5, 2) AS $$
DECLARE
    result DECIMAL(5, 2);
BEGIN
    SELECT 
        ROUND((current_amount / NULLIF(target_amount, 0)) * 100, 2)
    INTO result
    FROM goals
    WHERE id = p_goal_id;
    
    RETURN COALESCE(result, 0);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_goal_completion_percentage(BIGINT) IS 'Вычислить процент выполнения цели';

-- ========================================
-- DOWN Migration (откат)
-- ========================================

-- Для отката выполните:
-- 
-- -- Удаление триггеров
-- DROP TRIGGER IF EXISTS trigger_calculate_next_occurrence ON transactions;
-- DROP TRIGGER IF EXISTS trigger_update_goal_progress ON goal_progress;
-- DROP TRIGGER IF EXISTS trigger_update_user_balance ON transactions;
-- DROP TRIGGER IF EXISTS trigger_goals_updated_at ON goals;
-- DROP TRIGGER IF EXISTS trigger_transactions_updated_at ON transactions;
-- DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
-- 
-- -- Удаление функций
-- DROP FUNCTION IF EXISTS get_goal_completion_percentage(BIGINT);
-- DROP FUNCTION IF EXISTS get_user_balance(BIGINT);
-- DROP FUNCTION IF EXISTS calculate_next_occurrence();
-- DROP FUNCTION IF EXISTS update_goal_progress_amount();
-- DROP FUNCTION IF EXISTS update_user_balance();
-- DROP FUNCTION IF EXISTS update_updated_at_column();

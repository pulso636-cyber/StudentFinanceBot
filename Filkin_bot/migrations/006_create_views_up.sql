-- ========================================
-- Migration: 006_create_views
-- Description: Создание представлений для удобных запросов
-- ========================================

-- UP Migration
-- ========================================

-- ========================================
-- View 1: Активные пользователи с метриками
-- ========================================

CREATE VIEW active_users AS
SELECT 
    u.*,
    COUNT(t.id) as transaction_count_last_30_days,
    COALESCE(SUM(CASE WHEN t.transaction_type = 'income' THEN t.amount ELSE 0 END), 0) as income_last_30_days,
    COALESCE(SUM(CASE WHEN t.transaction_type = 'expense' THEN t.amount ELSE 0 END), 0) as expenses_last_30_days
FROM users u
LEFT JOIN transactions t ON u.id = t.user_id 
    AND t.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
    AND t.is_deleted = FALSE
WHERE u.is_active = TRUE
GROUP BY u.id;

COMMENT ON VIEW active_users IS 'Активные пользователи с метриками за последние 30 дней';

-- ========================================
-- View 2: Детальная информация о целях
-- ========================================

CREATE VIEW goals_summary AS
SELECT 
    g.*,
    ROUND((g.current_amount / NULLIF(g.target_amount, 0)) * 100, 2) as progress_percentage,
    g.target_amount - g.current_amount as amount_remaining,
    COUNT(gp.id) as contributions_count,
    COALESCE(SUM(CASE WHEN gp.progress_type = 'contribution' THEN gp.amount ELSE 0 END), 0) as total_contributions,
    COALESCE(SUM(CASE WHEN gp.progress_type = 'withdrawal' THEN gp.amount ELSE 0 END), 0) as total_withdrawals,
    u.telegram_id,
    u.username,
    u.first_name,
    u.last_name,
    -- Расчет средней скорости накопления (в день)
    CASE 
        WHEN g.created_at < CURRENT_TIMESTAMP THEN
            g.current_amount / NULLIF(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - g.created_at)) / 86400, 0)
        ELSE 0
    END as avg_daily_contribution,
    -- Прогнозируемая дата достижения (если сохранится текущая скорость)
    CASE 
        WHEN g.current_amount > 0 AND g.created_at < CURRENT_TIMESTAMP THEN
            CURRENT_TIMESTAMP + (
                (g.target_amount - g.current_amount) / 
                NULLIF(g.current_amount / NULLIF(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - g.created_at)) / 86400, 0), 0)
            ) * INTERVAL '1 day'
        ELSE NULL
    END as estimated_completion_date
FROM goals g
LEFT JOIN goal_progress gp ON g.id = gp.goal_id
LEFT JOIN users u ON g.user_id = u.id
GROUP BY g.id, u.telegram_id, u.username, u.first_name, u.last_name;

COMMENT ON VIEW goals_summary IS 'Детальная информация о целях с аналитикой и прогнозами';

-- ========================================
-- View 3: Транзакции с информацией о пользователе
-- ========================================

CREATE VIEW transactions_with_user AS
SELECT 
    t.*,
    u.telegram_id,
    u.username,
    u.first_name,
    u.last_name,
    u.default_currency as user_default_currency
FROM transactions t
JOIN users u ON t.user_id = u.id
WHERE t.is_deleted = FALSE;

COMMENT ON VIEW transactions_with_user IS 'Транзакции с полной информацией о пользователе (без удаленных)';

-- ========================================
-- View 4: Статистика по категориям за текущий месяц
-- ========================================

CREATE VIEW monthly_category_stats AS
SELECT 
    t.user_id,
    u.telegram_id,
    u.username,
    t.transaction_type,
    t.category,
    COUNT(*) as transaction_count,
    SUM(t.amount) as total_amount,
    AVG(t.amount) as avg_amount,
    MIN(t.amount) as min_amount,
    MAX(t.amount) as max_amount,
    DATE_TRUNC('month', CURRENT_TIMESTAMP) as month
FROM transactions t
JOIN users u ON t.user_id = u.id
WHERE 
    DATE_TRUNC('month', t.transaction_date) = DATE_TRUNC('month', CURRENT_TIMESTAMP)
    AND t.is_deleted = FALSE
GROUP BY t.user_id, u.telegram_id, u.username, t.transaction_type, t.category;

COMMENT ON VIEW monthly_category_stats IS 'Статистика по категориям транзакций за текущий месяц';

-- ========================================
-- View 5: Регулярные транзакции, требующие создания
-- ========================================

CREATE VIEW pending_recurring_transactions AS
SELECT 
    t.*,
    u.telegram_id,
    u.username,
    u.first_name
FROM transactions t
JOIN users u ON t.user_id = u.id
WHERE 
    t.is_recurring = TRUE
    AND t.is_deleted = FALSE
    AND t.next_occurrence_date IS NOT NULL
    AND t.next_occurrence_date <= CURRENT_TIMESTAMP
    AND u.is_active = TRUE
ORDER BY t.next_occurrence_date ASC;

COMMENT ON VIEW pending_recurring_transactions IS 'Регулярные транзакции, для которых пришло время создания новой записи';

-- ========================================
-- View 6: Топ категорий расходов за последние 30 дней
-- ========================================

CREATE VIEW top_expense_categories AS
SELECT 
    t.user_id,
    u.telegram_id,
    u.username,
    t.category,
    COUNT(*) as transaction_count,
    SUM(t.amount) as total_amount,
    ROUND(
        (SUM(t.amount) * 100.0) / NULLIF(
            (SELECT SUM(amount) 
             FROM transactions 
             WHERE user_id = t.user_id 
               AND transaction_type = 'expense' 
               AND is_deleted = FALSE
               AND transaction_date >= CURRENT_TIMESTAMP - INTERVAL '30 days'), 
            0
        ), 
        2
    ) as percentage_of_total
FROM transactions t
JOIN users u ON t.user_id = u.id
WHERE 
    t.transaction_type = 'expense'
    AND t.is_deleted = FALSE
    AND t.transaction_date >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY t.user_id, u.telegram_id, u.username, t.category
ORDER BY t.user_id, total_amount DESC;

COMMENT ON VIEW top_expense_categories IS 'Топ категорий расходов по пользователям за последние 30 дней';

-- ========================================
-- View 7: Цели, близкие к завершению
-- ========================================

CREATE VIEW goals_near_completion AS
SELECT 
    g.*,
    u.telegram_id,
    u.username,
    u.first_name,
    ROUND((g.current_amount / g.target_amount) * 100, 2) as completion_percentage,
    g.target_amount - g.current_amount as remaining_amount
FROM goals g
JOIN users u ON g.user_id = u.id
WHERE 
    g.status = 'active'
    AND g.current_amount >= g.target_amount * 0.8
    AND g.current_amount < g.target_amount
ORDER BY completion_percentage DESC;

COMMENT ON VIEW goals_near_completion IS 'Активные цели, близкие к завершению (выполнено >= 80%)';

-- ========================================
-- DOWN Migration (откат)
-- ========================================

-- Для отката выполните:
-- DROP VIEW IF EXISTS goals_near_completion;
-- DROP VIEW IF EXISTS top_expense_categories;
-- DROP VIEW IF EXISTS pending_recurring_transactions;
-- DROP VIEW IF EXISTS monthly_category_stats;
-- DROP VIEW IF EXISTS transactions_with_user;
-- DROP VIEW IF EXISTS goals_summary;
-- DROP VIEW IF EXISTS active_users;

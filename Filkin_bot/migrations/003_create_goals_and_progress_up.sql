-- ========================================
-- Migration: 003_create_goals_and_progress
-- Description: Создание таблиц для финансовых целей и отслеживания прогресса
-- ========================================

-- UP Migration
-- ========================================

-- Таблица финансовых целей
CREATE TABLE goals (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Основная информация о цели
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Финансовые параметры
    target_amount DECIMAL(15, 2) NOT NULL CHECK (target_amount > 0),
    current_amount DECIMAL(15, 2) DEFAULT 0.00 CHECK (current_amount >= 0),
    currency VARCHAR(3) DEFAULT 'RUB',
    
    -- Временные рамки
    start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    target_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Статус
    status goal_status_enum DEFAULT 'active',
    priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 5),
    
    -- Категория цели
    category VARCHAR(100),
    
    -- Метаданные для UI
    icon VARCHAR(50),
    color VARCHAR(20),
    metadata JSONB,
    
    -- Временные метки
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_target_date CHECK (
        target_date IS NULL OR target_date > start_date
    ),
    CONSTRAINT valid_completion CHECK (
        (status != 'completed') OR 
        (status = 'completed' AND completed_at IS NOT NULL)
    ),
    CONSTRAINT amount_not_exceed_target CHECK (
        current_amount <= target_amount * 1.5
    )
);

-- Таблица прогресса достижения целей
CREATE TABLE goal_progress (
    id BIGSERIAL PRIMARY KEY,
    goal_id BIGINT NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Данные о прогрессе
    amount DECIMAL(15, 2) NOT NULL CHECK (amount > 0),
    progress_type progress_type_enum DEFAULT 'contribution',
    description TEXT,
    
    -- Связь с транзакцией (опционально)
    transaction_id BIGINT REFERENCES transactions(id) ON DELETE SET NULL,
    
    -- Временные метки
    progress_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Метаданные
    metadata JSONB,
    
    -- Снимок состояния цели на момент изменения (для аналитики)
    goal_amount_before DECIMAL(15, 2),
    goal_amount_after DECIMAL(15, 2)
);

-- Комментарии
COMMENT ON TABLE goals IS 'Финансовые цели пользователей';
COMMENT ON TABLE goal_progress IS 'История прогресса достижения целей';

COMMENT ON COLUMN goals.target_amount IS 'Целевая сумма для накопления';
COMMENT ON COLUMN goals.current_amount IS 'Текущая накопленная сумма';
COMMENT ON COLUMN goals.status IS 'Статус цели: active, completed, cancelled, paused';
COMMENT ON COLUMN goals.priority IS 'Приоритет цели от 1 (низкий) до 5 (высокий)';
COMMENT ON COLUMN goals.target_date IS 'Желаемая дата достижения цели';

COMMENT ON COLUMN goal_progress.progress_type IS 'Тип изменения: contribution (вклад), withdrawal (снятие), adjustment (корректировка)';
COMMENT ON COLUMN goal_progress.transaction_id IS 'Опциональная связь с транзакцией';
COMMENT ON COLUMN goal_progress.goal_amount_before IS 'Сумма в цели до изменения (для истории)';
COMMENT ON COLUMN goal_progress.goal_amount_after IS 'Сумма в цели после изменения (для истории)';

-- ========================================
-- DOWN Migration (откат)
-- ========================================

-- Для отката выполните:
-- DROP TABLE IF EXISTS goal_progress CASCADE;
-- DROP TABLE IF EXISTS goals CASCADE;

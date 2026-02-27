-- ========================================
-- Таблица для отслеживания миграций
-- ========================================
-- Эта таблица должна быть создана первой перед запуском любых миграций

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    checksum VARCHAR(64),
    
    CONSTRAINT version_format CHECK (version ~ '^\d{3}$')
);

CREATE INDEX idx_schema_migrations_version ON schema_migrations(version);
CREATE INDEX idx_schema_migrations_applied_at ON schema_migrations(applied_at DESC);

COMMENT ON TABLE schema_migrations IS 'История применённых миграций базы данных';
COMMENT ON COLUMN schema_migrations.version IS 'Номер версии миграции (формат: 001, 002, и т.д.)';
COMMENT ON COLUMN schema_migrations.name IS 'Описательное название миграции';
COMMENT ON COLUMN schema_migrations.execution_time_ms IS 'Время выполнения миграции в миллисекундах';
COMMENT ON COLUMN schema_migrations.checksum IS 'Контрольная сумма файла миграции для проверки целостности';

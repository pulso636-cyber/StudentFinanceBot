# Миграции базы данных

Система управления версионированием базы данных для Telegram-бота учёта капитала.

## Структура миграций

```
migrations/
├── 000_schema_migrations.sql           # Таблица для отслеживания миграций
├── 001_create_enum_types_up.sql        # Создание ENUM типов
├── 001_create_enum_types_down.sql      # Откат ENUM типов
├── 002_create_users_and_transactions_up.sql
├── 002_create_users_and_transactions_down.sql
├── 003_create_goals_and_progress_up.sql
├── 003_create_goals_and_progress_down.sql
├── 004_create_indexes_up.sql
├── 004_create_indexes_down.sql
├── 005_create_triggers_and_functions_up.sql
├── 005_create_triggers_and_functions_down.sql
├── 006_create_views_up.sql
└── 006_create_views_down.sql
```

## Описание миграций

### 000 - Schema Migrations
Создание служебной таблицы `schema_migrations` для отслеживания примененных миграций.

### 001 - Create ENUM Types
Создание ENUM типов для типобезопасности:
- `transaction_type_enum` - типы транзакций (income, expense, transfer)
- `goal_status_enum` - статусы целей (active, completed, cancelled, paused)
- `progress_type_enum` - типы прогресса (contribution, withdrawal, adjustment)
- `recurring_frequency_enum` - частота повтора (daily, weekly, monthly, yearly)

### 002 - Create Users and Transactions
Создание основных таблиц:
- `users` - пользователи Telegram-бота
- `transactions` - финансовые транзакции

Включает:
- Внешние ключи и каскадное удаление
- CHECK constraints для валидации
- Денормализованные поля для производительности
- Поддержку мягкого удаления
- JSONB для метаданных

### 003 - Create Goals and Progress
Создание таблиц для целей:
- `goals` - финансовые цели пользователей
- `goal_progress` - история прогресса достижения целей

Включает:
- Связи с пользователями и транзакциями
- Автоматическую валидацию целевых сумм
- Хранение снимков состояния

### 004 - Create Indexes
Создание 30+ оптимизированных индексов:
- Составные индексы (user_id + date)
- GIN индексы для массивов и JSONB
- Partial индексы для условных выборок
- Индексы для всех внешних ключей

### 005 - Create Triggers and Functions
Создание автоматизации:

**Функции:**
- `update_updated_at_column()` - автообновление timestamp
- `update_user_balance()` - пересчет баланса пользователя
- `update_goal_progress_amount()` - обновление прогресса целей
- `calculate_next_occurrence()` - расчет следующей даты для регулярных транзакций
- `get_user_balance(telegram_id)` - получение баланса
- `get_goal_completion_percentage(goal_id)` - процент выполнения цели

**Триггеры:**
- Автоматическое обновление `updated_at`
- Автоматический пересчет баланса при изменении транзакций
- Автоматическое обновление прогресса целей
- Автоматический расчет дат для регулярных транзакций

### 006 - Create Views
Создание представлений для аналитики:
- `active_users` - активные пользователи с метриками за 30 дней
- `goals_summary` - детальная информация о целях с прогнозами
- `transactions_with_user` - транзакции с данными пользователя
- `monthly_category_stats` - статистика по категориям за текущий месяц
- `pending_recurring_transactions` - регулярные транзакции к выполнению
- `top_expense_categories` - топ категорий расходов
- `goals_near_completion` - цели близкие к завершению (>80%)

---

## Использование

### Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=filkin_bot
DB_USER=postgres
DB_PASSWORD=your_secure_password
```

Или экспортируйте переменные:

```bash
export DB_HOST=localhost
export DB_NAME=filkin_bot
export DB_USER=postgres
export DB_PASSWORD=your_secure_password
```

### Установка зависимостей

```bash
pip install psycopg2-binary python-dotenv
```

### Команды миграций

#### 1. Проверить статус миграций

```bash
python migrate.py status
```

Вывод:
```
======================================================================
СТАТУС МИГРАЦИЙ
======================================================================
База данных: filkin_bot
Применено миграций: 3
Доступно миграций: 6
======================================================================
001: Create Enum Types                   ✓ Применена
002: Create Users And Transactions       ✓ Применена
003: Create Goals And Progress           ✓ Применена
004: Create Indexes                      ○ Не применена
005: Create Triggers And Functions       ○ Не применена
006: Create Views                        ○ Не применена
======================================================================
```

#### 2. Применить все новые миграции

```bash
python migrate.py up
```

Применит все миграции, которые ещё не были применены.

#### 3. Откатить последнюю миграцию

```bash
python migrate.py down
```

Откатывает последнюю примененную миграцию.

#### 4. Применить до определенной версии

```bash
python migrate.py to 003
```

Применит или откатит миграции до указанной версии.

#### 5. Откатить все миграции

```bash
python migrate.py reset
```

⚠️ **ВНИМАНИЕ**: Удалит все данные! Запросит подтверждение.

---

## Процесс разработки

### Создание новой миграции

1. Создайте два файла:
   - `00X_description_up.sql` - применение изменений
   - `00X_description_down.sql` - откат изменений

2. Формат имени:
   - Версия: `001`, `002`, `003` и т.д. (3 цифры)
   - Описание: `create_enum_types`, `add_column_to_users`
   - Суффикс: `_up.sql` или `_down.sql`

3. Пример структуры UP миграции:

```sql
-- ========================================
-- Migration: 007_add_user_settings
-- Description: Добавление таблицы настроек пользователя
-- ========================================

-- UP Migration
-- ========================================

CREATE TABLE user_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id)
);

CREATE INDEX idx_user_settings_user_id ON user_settings(user_id);

COMMENT ON TABLE user_settings IS 'Настройки пользователей';
```

4. Пример структуры DOWN миграции:

```sql
-- ========================================
-- Migration: 007_add_user_settings (DOWN)
-- Description: Откат добавления таблицы настроек
-- ========================================

DROP TABLE IF EXISTS user_settings CASCADE;
```

### Тестирование миграций

```bash
# Применить миграцию
python migrate.py up

# Проверить что всё работает
python migrate.py status

# Откатить для проверки отката
python migrate.py down

# Применить снова
python migrate.py up
```

---

## Лучшие практики

### 1. Всегда создавайте DOWN миграцию
Каждая UP миграция должна иметь соответствующую DOWN для отката.

### 2. Делайте миграции атомарными
Одна миграция = одно логическое изменение. Не смешивайте разные изменения.

### 3. Используйте транзакции
PostgreSQL автоматически оборачивает каждую миграцию в транзакцию.

### 4. Тестируйте на копии продакшн данных
Перед применением в продакшене протестируйте на копии базы.

### 5. Создавайте индексы CONCURRENTLY в продакшене

Для больших таблиц используйте:
```sql
CREATE INDEX CONCURRENTLY idx_name ON table_name(column);
```

### 6. Осторожно с DROP COLUMN
В продакшене лучше сначала перестать использовать колонку в коде, затем удалить.

### 7. Используйте CHECK constraints осторожно
В продакшене добавление CHECK может блокировать таблицу. Используйте `NOT VALID`:

```sql
ALTER TABLE users ADD CONSTRAINT check_age 
CHECK (age >= 18) NOT VALID;

-- Позже, в off-peak время:
ALTER TABLE users VALIDATE CONSTRAINT check_age;
```

---

## Масштабирование

### Стратегии для больших баз данных

#### 1. Создание индексов без блокировки

```sql
-- Вместо:
CREATE INDEX idx_transactions_date ON transactions(transaction_date);

-- Используйте:
CREATE INDEX CONCURRENTLY idx_transactions_date ON transactions(transaction_date);
```

#### 2. Добавление колонок с DEFAULT

```sql
-- Может быть медленным на больших таблицах:
ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT FALSE;

-- Лучше:
ALTER TABLE users ADD COLUMN is_premium BOOLEAN;
UPDATE users SET is_premium = FALSE WHERE is_premium IS NULL;
ALTER TABLE users ALTER COLUMN is_premium SET DEFAULT FALSE;
ALTER TABLE users ALTER COLUMN is_premium SET NOT NULL;
```

#### 3. Партиционирование (для будущего роста)

Когда таблица `transactions` вырастет до миллионов записей:

```sql
-- Партиционирование по диапазону дат
CREATE TABLE transactions_partitioned (
    LIKE transactions INCLUDING ALL
) PARTITION BY RANGE (transaction_date);

CREATE TABLE transactions_2024_01 PARTITION OF transactions_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE transactions_2024_02 PARTITION OF transactions_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- и т.д.
```

#### 4. Архивация старых данных

```sql
-- Переместить старые транзакции в архивную таблицу
CREATE TABLE transactions_archive (LIKE transactions INCLUDING ALL);

INSERT INTO transactions_archive 
SELECT * FROM transactions 
WHERE transaction_date < CURRENT_DATE - INTERVAL '2 years';

DELETE FROM transactions 
WHERE transaction_date < CURRENT_DATE - INTERVAL '2 years';
```

---

## Мониторинг и обслуживание

### Проверка размера таблиц

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Проверка использования индексов

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

### VACUUM и ANALYZE

```bash
# Ручной запуск
psql -d filkin_bot -c "VACUUM ANALYZE;"

# Настройка автоматического в postgresql.conf
autovacuum = on
autovacuum_vacuum_scale_factor = 0.1
autovacuum_analyze_scale_factor = 0.05
```

---

## Откат в случае проблем

### Сценарий 1: Ошибка при применении миграции

Миграция автоматически откатится, так как выполняется в транзакции.

### Сценарий 2: Миграция применилась, но есть проблемы

```bash
# Откатить последнюю миграцию
python migrate.py down

# Или откатить до конкретной версии
python migrate.py to 003
```

### Сценарий 3: Полный откат (emergency)

```bash
# Откатить все миграции
python migrate.py reset

# Применить заново
python migrate.py up
```

---

## CI/CD интеграция

### GitHub Actions пример

```yaml
name: Database Migrations

on:
  push:
    branches: [main]

jobs:
  migrate:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: pip install psycopg2-binary python-dotenv
    
    - name: Run migrations
      env:
        DB_HOST: ${{ secrets.DB_HOST }}
        DB_NAME: ${{ secrets.DB_NAME }}
        DB_USER: ${{ secrets.DB_USER }}
        DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
      run: python migrate.py up
```

---

## Troubleshooting

### Проблема: "relation schema_migrations does not exist"

**Решение**: Запустите миграцию заново, таблица создастся автоматически.

### Проблема: "permission denied"

**Решение**: Убедитесь что пользователь БД имеет права CREATE.

```sql
GRANT CREATE ON DATABASE filkin_bot TO your_user;
```

### Проблема: "checksum mismatch"

**Решение**: Файл миграции был изменен после применения. Не меняйте примененные миграции!

---

## Контакты и поддержка

Для вопросов по миграциям создавайте issue в репозитории.

## Лицензия

MIT License

# Filkin Bot - Personal Finance Telegram Bot

**Stack**: Python 3.12 + aiogram 3.x + PostgreSQL 16 + SQLAlchemy 2.0 (async)

Telegram bot for personal finance management with income/expense tracking, goals, and statistics.

---

## Features

- User registration and authentication
- Income and expense tracking with categories
- Balance calculation with PostgreSQL triggers
- Financial goals with progress tracking
- Transaction history
- Monthly statistics by categories
- FSM (Finite State Machine) for dialogs

---

## Quick Start

### 1. Prerequisites

- **Python 3.12+**
- **PostgreSQL 16+**
- **Telegram Bot Token** (from @BotFather)

### 2. Installation

```bash
# Clone or download the project
cd E:\Filkin_bot

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Create database
createdb -U postgres filkin_bot

# Run migrations (apply all .sql files from migrations/)
cd migrations
psql -U postgres -d filkin_bot -f 000_schema_migrations.sql
psql -U postgres -d filkin_bot -f 001_create_enum_types_up.sql
psql -U postgres -d filkin_bot -f 002_create_users_and_transactions_up.sql
psql -U postgres -d filkin_bot -f 003_create_goals_and_progress_up.sql
psql -U postgres -d filkin_bot -f 004_create_indexes_up.sql
psql -U postgres -d filkin_bot -f 005_create_triggers_and_functions_up.sql
psql -U postgres -d filkin_bot -f 006_create_views_up.sql
psql -U postgres -d filkin_bot -f 007_add_transaction_function_up.sql
```

### 4. Configuration

Edit `.env` file:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=filkin_bot
DB_USER=postgres
DB_PASSWORD=your_password

# Telegram Bot
BOT_TOKEN=your_bot_token_from_botfather

# Other
DEBUG=True
```

### 5. Run Bot

```bash
# Option 1: Direct run
python bot.py

# Option 2: Using batch file (recommended on Windows)
.\start_bot.bat
```

---

## Project Structure

```
E:\Filkin_bot\
├── bot.py              # Main bot file with handlers
├── models.py           # SQLAlchemy ORM models
├── crud.py             # Database CRUD operations
├── database.py         # Database connection setup
├── .env                # Configuration (not in git)
├── requirements.txt    # Python dependencies
├── start_bot.bat       # Windows startup script
├── README.md           # This file
└── migrations/         # SQL migration files
    ├── 000_schema_migrations.sql
    ├── 001_create_enum_types_up.sql
    ├── 002_create_users_and_transactions_up.sql
    ├── 003_create_goals_and_progress_up.sql
    ├── 004_create_indexes_up.sql
    ├── 005_create_triggers_and_functions_up.sql
    ├── 006_create_views_up.sql
    └── 007_add_transaction_function_up.sql
```

---

## Bot Commands

### User Commands

- `/start` - Register and show main menu
- `/balance` - Show current balance
- `/add_income` - Add income (FSM dialog)
- `/add_expense` - Add expense (FSM dialog)
- `/history` - Show last 10 transactions
- `/goals` - Show active financial goals
- `/create_goal` - Create new goal (FSM dialog)
- `/stats` - Show monthly statistics

---

## Database Schema

### Tables

1. **users** - Telegram users
   - Balance fields (auto-updated by triggers)
   - Personal settings (currency, timezone)

2. **transactions** - Financial transactions
   - Income/expense/transfer types
   - Categories and descriptions
   - Recurring transactions support

3. **goals** - Financial goals
   - Target amount and deadline
   - Current progress tracking

4. **goal_progress** - Goal progress history
   - Contributions, withdrawals, adjustments

### ENUM Types

- `transaction_type_enum`: income, expense, transfer
- `goal_status_enum`: active, completed, cancelled, paused
- `progress_type_enum`: contribution, withdrawal, adjustment
- `recurring_frequency_enum`: daily, weekly, monthly, yearly

### Automatic Features

- **Balance Triggers**: Automatically update user balance on transaction insert/update/delete
- **Analytical Views**: Pre-calculated statistics for performance
- **Indexes**: Optimized queries for large datasets

---

## Development

### Adding New Features

1. **New Command**:
   - Add handler in `bot.py`
   - Create FSM states if needed
   - Add CRUD method in `crud.py`

2. **New Database Field**:
   - Create migration in `migrations/`
   - Update model in `models.py`
   - Update CRUD operations in `crud.py`

### Testing

```bash
# Test database connection
python -c "from database import init_db; import asyncio; asyncio.run(init_db())"

# Test models import
python -c "from models import User, Transaction, Goal; print('OK')"

# Test CRUD operations
python -c "from crud import UserCRUD; print('OK')"
```

---

## Troubleshooting

### Bot doesn't start

1. Check PostgreSQL is running:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Check .env file exists and has correct values

3. Check database migrations are applied:
   ```sql
   SELECT * FROM schema_migrations;
   ```

### Database errors

1. **"type X does not exist"**: Run migrations in correct order
2. **"column X does not exist"**: Check if all migrations applied
3. **"connection refused"**: Check PostgreSQL service is running

### Bot conflicts

If you see "Conflict: terminated by other getUpdates":
```bash
# Kill all Python processes
taskkill /F /IM python.exe
# Wait 10 seconds
timeout /t 10
# Start bot again
python bot.py
```

---

## Production Deployment

### Recommendations

1. **Use Redis for FSM** (currently using MemoryStorage)
2. **Set up systemd service** (Linux) or Windows Service
3. **Configure logging to file**
4. **Set up monitoring** (Sentry, Prometheus)
5. **Use environment variables** for secrets
6. **Set up database backups**
7. **Use connection pooling** (already configured)

### Example systemd service

```ini
[Unit]
Description=Filkin Telegram Bot
After=postgresql.service

[Service]
Type=simple
User=botuser
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Tech Stack Details

- **aiogram 3.16.0** - Modern async Telegram Bot framework
- **SQLAlchemy 2.0.36** - Async ORM with full type hints
- **asyncpg 0.30.0** - Fast async PostgreSQL driver
- **PostgreSQL 16** - ACID-compliant database with triggers
- **Python 3.12** - Latest Python with async/await support

---

## License

MIT License - feel free to use and modify

---

## Author

Created for personal finance management

Telegram Bot: @FilkinWallet_bot (ID: 8264949484)

---

## Support

For issues and questions:
1. Check Troubleshooting section
2. Review error logs
3. Check database migrations are applied
4. Verify .env configuration

---

**Last Updated**: February 2026
**Version**: 1.0.0
**Status**: Production Ready

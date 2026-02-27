"""
Telegram Bot для учёта личных финансов (Filkin Bot)
Stack: aiogram 3.x + FastAPI + PostgreSQL + SQLAlchemy + Redis

Основные команды:
- /start - Начало работы
- /balance - Текущий баланс
- /add_income - Добавить доход
- /add_expense - Добавить расход
- /history - История транзакций
- /goals - Мои цели
- /stats - Статистика
"""

import os
import logging
from decimal import Decimal
from datetime import date, datetime, timedelta

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from database import init_db, close_db, get_db
from crud import UserCRUD, TransactionCRUD, GoalCRUD, add_income, add_expense
from models import TransactionType

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)

# MemoryStorage для FSM (состояния в памяти)
# Для продакшена используй Redis:
# from aiogram.fsm.storage.redis import RedisStorage
# storage = RedisStorage.from_url("redis://localhost:6379/0")
storage = MemoryStorage()

# Dispatcher и Router
dp = Dispatcher(storage=storage)
router = Router()


# ==================== FSM States ====================


class AddIncomeState(StatesGroup):
    """Состояния для добавления дохода"""

    amount = State()
    category = State()
    description = State()


class AddExpenseState(StatesGroup):
    """Состояния для добавления расхода"""

    amount = State()
    category = State()
    description = State()


class CreateGoalState(StatesGroup):
    """Состояния для создания цели"""

    title = State()
    target_amount = State()
    target_date = State()


# ==================== Keyboards ====================


def get_main_menu_keyboard():
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Баланс", callback_data="balance")
    builder.button(text="➕ Доход", callback_data="add_income")
    builder.button(text="➖ Расход", callback_data="add_expense")
    builder.button(text="📊 История", callback_data="history")
    builder.button(text="🎯 Цели", callback_data="goals")
    builder.button(text="📈 Статистика", callback_data="stats")
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()


def get_income_categories_keyboard():
    """Категории доходов"""
    categories = [
        "💼 Зарплата",
        "💵 Фриланс",
        "🎁 Подарок",
        "📈 Инвестиции",
        "🏦 Проценты",
        "🔄 Другое",
    ]
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat, callback_data=f"income_cat:{cat.split()[1]}")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()


def get_expense_categories_keyboard():
    """Категории расходов"""
    categories = [
        "🛒 Продукты",
        "🏠 Жильё",
        "🚗 Транспорт",
        "👕 Одежда",
        "🎬 Развлечения",
        "💊 Здоровье",
        "📚 Образование",
        "📱 Связь",
        "🔄 Другое",
    ]
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat, callback_data=f"expense_cat:{cat.split()[1]}")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()


def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()


# ==================== Handlers ====================


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    async with get_db() as session:
        user, created = await UserCRUD.get_or_create(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code,
        )

    if created:
        text = (
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            f"Я помогу тебе вести учёт личных финансов.\n\n"
            f"📊 Доступные команды:\n"
            f"/balance - Текущий баланс\n"
            f"/add_income - Добавить доход\n"
            f"/add_expense - Добавить расход\n"
            f"/history - История транзакций\n"
            f"/goals - Мои финансовые цели\n"
            f"/stats - Статистика\n\n"
            f"Или просто используй меню ниже 👇"
        )
    else:
        text = f"С возвращением, {message.from_user.first_name}! 👋"

    await message.answer(text, reply_markup=get_main_menu_keyboard())


@router.message(Command("balance"))
@router.callback_query(F.data == "balance")
async def show_balance(event: Message | CallbackQuery):
    """Показать баланс"""
    if isinstance(event, CallbackQuery):
        message = event.message
        telegram_id = event.from_user.id
        await event.answer()
    else:
        message = event
        telegram_id = event.from_user.id

    async with get_db() as session:
        balance = await UserCRUD.get_balance(session, telegram_id)

    text = (
        f"💰 <b>Ваш баланс</b>\n\n"
        f"Текущий баланс: <b>{balance['current_balance']:,.2f} {balance['currency']}</b>\n"
        f"Всего доходов: <b>+{balance['total_income']:,.2f}</b>\n"
        f"Всего расходов: <b>-{balance['total_expenses']:,.2f}</b>\n"
        f"Транзакций: <b>{balance['total_transactions']}</b>"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_menu_keyboard())


# ==================== Add Income ====================


@router.message(Command("add_income"))
@router.callback_query(F.data == "add_income")
async def start_add_income(event: Message | CallbackQuery, state: FSMContext):
    """Начать добавление дохода"""
    if isinstance(event, CallbackQuery):
        message = event.message
        await event.answer()
    else:
        message = event

    await state.set_state(AddIncomeState.amount)
    await message.answer(
        "💰 <b>Добавление дохода</b>\n\nВведите сумму дохода (например: 5000):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddIncomeState.amount)
async def process_income_amount(message: Message, state: FSMContext):
    """Обработка суммы дохода"""
    try:
        amount = Decimal(message.text.replace(",", "."))

        # Проверка на положительное значение
        if amount <= 0:
            await message.answer(
                "[ERROR] Сумма должна быть положительной. Попробуйте ещё раз:"
            )
            return

        # Проверка максимального значения (NUMERIC(15,2) = max 9,999,999,999,999.99)
        if amount > Decimal("9999999999999.99"):  # Строгая проверка с учетом округления
            await message.answer(
                "[ERROR] Сумма слишком большая!\n\n"
                "Максимальная сумма: 9,999,999,999,999.99\n"
                "Попробуйте ещё раз:"
            )
            return

        await state.update_data(amount=amount)
        await state.set_state(AddIncomeState.category)

        await message.answer(
            f"[OK] Сумма: <b>{amount:,.2f}</b>\n\nВыберите категорию:",
            parse_mode="HTML",
            reply_markup=get_income_categories_keyboard(),
        )
    except (ValueError, Exception):
        await message.answer("[ERROR] Неверный формат. Введите число (например: 5000):")


@router.callback_query(F.data.startswith("income_cat:"))
async def process_income_category(callback: CallbackQuery, state: FSMContext):
    """Обработка категории дохода"""
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(AddIncomeState.description)
    await callback.answer()

    await callback.message.answer(
        f"✅ Категория: <b>{category}</b>\n\n"
        f"Введите описание (или напишите '-' для пропуска):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddIncomeState.description)
async def process_income_description(message: Message, state: FSMContext):
    """Финализация добавления дохода"""
    description = None if message.text == "-" else message.text
    data = await state.get_data()

    try:
        async with get_db() as session:
            result = await add_income(
                telegram_id=message.from_user.id,
                amount=data["amount"],
                category=data["category"],
                description=description,
                session=session,
            )

        await message.answer(
            f"✅ <b>Доход добавлен!</b>\n\n"
            f"Сумма: <b>+{data['amount']:,.2f} RUB</b>\n"
            f"Категория: <b>{data['category']}</b>\n"
            f"Новый баланс: <b>{result['new_balance']:,.2f} RUB</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )

        await state.clear()
    except Exception as e:
        logger.error(f"Error adding income: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при добавлении дохода: {str(e)}\n\nПопробуйте ещё раз.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()


# ==================== Add Expense ====================


@router.message(Command("add_expense"))
@router.callback_query(F.data == "add_expense")
async def start_add_expense(event: Message | CallbackQuery, state: FSMContext):
    """Начать добавление расхода"""
    if isinstance(event, CallbackQuery):
        message = event.message
        await event.answer()
    else:
        message = event

    await state.set_state(AddExpenseState.amount)
    await message.answer(
        "💸 <b>Добавление расхода</b>\n\nВведите сумму расхода (например: 1500):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddExpenseState.amount)
async def process_expense_amount(message: Message, state: FSMContext):
    """Обработка суммы расхода"""
    try:
        amount = Decimal(message.text.replace(",", "."))

        # Проверка на положительное значение
        if amount <= 0:
            await message.answer(
                "[ERROR] Сумма должна быть положительной. Попробуйте ещё раз:"
            )
            return

        # Проверка максимального значения (NUMERIC(15,2) = max 9,999,999,999,999.99)
        if amount > Decimal("9999999999999.99"):  # Строгая проверка с учетом округления
            await message.answer(
                "[ERROR] Сумма слишком большая!\n\n"
                "Максимальная сумма: 9,999,999,999,999.99\n"
                "Попробуйте ещё раз:"
            )
            return

        await state.update_data(amount=amount)
        await state.set_state(AddExpenseState.category)

        await message.answer(
            f"[OK] Сумма: <b>{amount:,.2f}</b>\n\nВыберите категорию:",
            parse_mode="HTML",
            reply_markup=get_expense_categories_keyboard(),
        )
    except (ValueError, Exception):
        await message.answer("[ERROR] Неверный формат. Введите число (например: 1500):")


@router.callback_query(F.data.startswith("expense_cat:"))
async def process_expense_category(callback: CallbackQuery, state: FSMContext):
    """Обработка категории расхода"""
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(AddExpenseState.description)
    await callback.answer()

    await callback.message.answer(
        f"✅ Категория: <b>{category}</b>\n\n"
        f"Введите описание (или напишите '-' для пропуска):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddExpenseState.description)
async def process_expense_description(message: Message, state: FSMContext):
    """Финализация добавления расхода"""
    description = None if message.text == "-" else message.text
    data = await state.get_data()

    try:
        async with get_db() as session:
            result = await add_expense(
                telegram_id=message.from_user.id,
                amount=data["amount"],
                category=data["category"],
                description=description,
                session=session,
            )

        await message.answer(
            f"✅ <b>Расход добавлен!</b>\n\n"
            f"Сумма: <b>-{data['amount']:,.2f} RUB</b>\n"
            f"Категория: <b>{data['category']}</b>\n"
            f"Новый баланс: <b>{result['new_balance']:,.2f} RUB</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )

        await state.clear()
    except Exception as e:
        logger.error(f"Error adding expense: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при добавлении расхода: {str(e)}\n\nПопробуйте ещё раз.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()


# ==================== History ====================


@router.message(Command("history"))
@router.callback_query(F.data == "history")
async def show_history(event: Message | CallbackQuery):
    """Показать историю транзакций"""
    if isinstance(event, CallbackQuery):
        message = event.message
        telegram_id = event.from_user.id
        await event.answer()
    else:
        message = event
        telegram_id = event.from_user.id

    async with get_db() as session:
        transactions = await TransactionCRUD.get_recent(session, telegram_id, limit=10)

    if not transactions:
        await message.answer(
            "📊 История транзакций пуста.\n\nДобавьте первую транзакцию!",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    text = "📊 <b>Последние 10 транзакций:</b>\n\n"

    for t in transactions:
        emoji = "➕" if t.transaction_type == TransactionType.INCOME else "➖"
        sign = "+" if t.transaction_type == TransactionType.INCOME else "-"

        text += (
            f"{emoji} <b>{sign}{t.amount:,.2f}</b> | {t.category}\n"
            f"   {t.transaction_date.strftime('%Y-%m-%d %H:%M:%S')} | {t.description or 'Без описания'}\n\n"
        )

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_menu_keyboard())


# ==================== Goals ====================


@router.message(Command("goals"))
@router.callback_query(F.data == "goals")
async def show_goals(event: Message | CallbackQuery):
    """Показать цели"""
    if isinstance(event, CallbackQuery):
        message = event.message
        telegram_id = event.from_user.id
        await event.answer()
    else:
        message = event
        telegram_id = event.from_user.id

    async with get_db() as session:
        goals = await GoalCRUD.get_active(session, telegram_id)

    if not goals:
        await message.answer(
            "🎯 У вас пока нет целей.\n\nСоздайте первую цель командой /create_goal",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    text = "🎯 <b>Ваши цели:</b>\n\n"

    for goal in goals:
        progress_bar = "█" * int(goal.progress_percentage / 10) + "░" * (
            10 - int(goal.progress_percentage / 10)
        )

        text += (
            f"<b>{goal.title}</b>\n"
            f"{progress_bar} {goal.progress_percentage:.1f}%\n"
            f"{goal.current_amount:,.2f} / {goal.target_amount:,.2f} {goal.currency}\n"
        )

        if goal.target_date:
            date_text = (
                goal.target_date.strftime("%d.%m.%Y")
                if isinstance(goal.target_date, datetime)
                else goal.target_date.strftime("%d.%m.%Y")
            )
            text += f"📅 До: {date_text}\n"

        text += "\n"

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_menu_keyboard())


# ==================== Statistics ====================


@router.message(Command("stats"))
@router.callback_query(F.data == "stats")
async def show_stats(event: Message | CallbackQuery):
    """Показать статистику"""
    if isinstance(event, CallbackQuery):
        message = event.message
        telegram_id = event.from_user.id
        await event.answer()
    else:
        message = event
        telegram_id = event.from_user.id

    async with get_db() as session:
        # Получаем баланс
        balance = await UserCRUD.get_balance(session, telegram_id)

        # Получаем транзакции за последний месяц
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        transactions = await TransactionCRUD.get_by_period(
            session, telegram_id, start_date, end_date
        )

    if not transactions:
        await message.answer(
            "📈 <b>Статистика</b>\n\nНедостаточно данных для отображения статистики.\n\nДобавьте транзакции!",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    # Подсчитываем статистику
    income_total = sum(
        t.amount for t in transactions if t.transaction_type == TransactionType.INCOME
    )
    expense_total = sum(
        t.amount for t in transactions if t.transaction_type == TransactionType.EXPENSE
    )

    # Группируем расходы по категориям
    expense_by_category = {}
    for t in transactions:
        if t.transaction_type == TransactionType.EXPENSE:
            category = t.category or "Другое"
            expense_by_category[category] = (
                expense_by_category.get(category, Decimal("0")) + t.amount
            )

    # Формируем текст
    text = (
        f"📈 <b>Статистика за последние 30 дней</b>\n\n"
        f"💰 Текущий баланс: <b>{balance['current_balance']:,.2f} {balance['currency']}</b>\n\n"
        f"📊 За месяц:\n"
        f"➕ Доходы: <b>+{income_total:,.2f}</b>\n"
        f"➖ Расходы: <b>-{expense_total:,.2f}</b>\n"
        f"📉 Разница: <b>{income_total - expense_total:,.2f}</b>\n"
    )

    if expense_by_category:
        text += "\n<b>Расходы по категориям:</b>\n"
        sorted_categories = sorted(
            expense_by_category.items(), key=lambda x: x[1], reverse=True
        )
        for category, amount in sorted_categories[:5]:  # Топ-5 категорий
            percentage = (amount / expense_total * 100) if expense_total > 0 else 0
            text += f"  • {category}: {amount:,.2f} ({percentage:.1f}%)\n"

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_menu_keyboard())


# ==================== Create Goal ====================


@router.message(Command("create_goal"))
async def cmd_create_goal(message: Message, state: FSMContext):
    """Команда создания цели"""
    await state.set_state(CreateGoalState.title)
    await message.answer(
        "🎯 <b>Создание цели</b>\n\nВведите название цели (например: Новый iPhone):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(CreateGoalState.title)
async def process_goal_title(message: Message, state: FSMContext):
    """Обработка названия цели"""
    title = message.text.strip()
    if len(title) < 3:
        await message.answer("❌ Название слишком короткое. Введите минимум 3 символа:")
        return

    await state.update_data(title=title)
    await state.set_state(CreateGoalState.target_amount)

    await message.answer(
        f"✅ Название: <b>{title}</b>\n\nВведите целевую сумму (например: 150000):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(CreateGoalState.target_amount)
async def process_goal_target_amount(message: Message, state: FSMContext):
    """Обработка целевой суммы"""
    try:
        target_amount = Decimal(message.text.replace(",", "."))

        # Проверка на положительное значение
        if target_amount <= 0:
            await message.answer(
                "[ERROR] Сумма должна быть положительной. Попробуйте ещё раз:"
            )
            return

        # Проверка максимального значения
        if target_amount >= Decimal("10000000000000"):  # 10 триллионов
            await message.answer(
                "[ERROR] Сумма слишком большая!\n\n"
                "Максимальная сумма: 9,999,999,999,999.99\n"
                "Попробуйте ещё раз:"
            )
            return

        await state.update_data(target_amount=target_amount)
        await state.set_state(CreateGoalState.target_date)

        await message.answer(
            f"[OK] Целевая сумма: <b>{target_amount:,.2f}</b>\n\n"
            f"Введите дедлайн в формате ДД.ММ.ГГГГ (например: 31.12.2026)\n"
            f"или напишите '-' для пропуска:",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard(),
        )
    except (ValueError, Exception):
        await message.answer(
            "[ERROR] Неверный формат. Введите число (например: 150000):"
        )


@router.message(CreateGoalState.target_date)
async def process_goal_target_date(message: Message, state: FSMContext):
    """Финализация создания цели"""
    target_date = None
    if message.text != "-":
        try:
            # Парсим дату в формате ДД.ММ.ГГГГ
            day, month, year = message.text.split(".")
            parsed_date = date(int(year), int(month), int(day))

            # Проверяем, что дата в будущем
            if parsed_date <= date.today():
                await message.answer(
                    "❌ Дедлайн должен быть в будущем. Введите дату или '-' для пропуска:"
                )
                return

            target_date = datetime(int(year), int(month), int(day))
        except (ValueError, Exception):
            await message.answer(
                "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 31.12.2026) или '-' для пропуска:"
            )
            return

    data = await state.get_data()

    try:
        async with get_db() as session:
            goal = await GoalCRUD.create(
                session,
                telegram_id=message.from_user.id,
                title=data["title"],
                target_amount=data["target_amount"],
                target_date=target_date,
            )

        deadline_text = (
            f"📅 Дедлайн: {target_date.strftime('%d.%m.%Y')}"
            if target_date
            else "📅 Без дедлайна"
        )

        await message.answer(
            f"✅ <b>Цель создана!</b>\n\n"
            f"🎯 {data['title']}\n"
            f"💰 Целевая сумма: <b>{data['target_amount']:,.2f} RUB</b>\n"
            f"{deadline_text}\n\n"
            f"Используйте /goals чтобы посмотреть все цели.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )

        await state.clear()
    except Exception as e:
        logger.error(f"Error creating goal: {e}")
        await message.answer(
            f"❌ Ошибка при создании цели. Попробуйте ещё раз.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()


# ==================== Cancel ====================


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await callback.answer("❌ Отменено")
    await callback.message.answer(
        "Действие отменено.", reply_markup=get_main_menu_keyboard()
    )


# ==================== Main ====================


async def on_startup():
    """Выполняется при запуске бота"""
    await init_db()
    logger.info("[OK] Bot started")


async def on_shutdown():
    """Выполняется при остановке бота"""
    await close_db()
    await bot.session.close()
    logger.info("[OK] Bot stopped")


async def main():
    """Главная функция"""
    # Регистрация роутера
    dp.include_router(router)

    # Startup/Shutdown events
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запуск polling
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

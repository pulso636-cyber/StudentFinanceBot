"""
CRUD операции для Filkin Bot (SQLAlchemy async)
Stack: aiogram + FastAPI + PostgreSQL + SQLAlchemy + Redis

Все операции используют async SQLAlchemy.
Баланс пользователя обновляется автоматически через PostgreSQL triggers.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, or_, desc, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import (
    User,
    Transaction,
    Goal,
    GoalProgress,
    TransactionType,
    GoalStatus,
    ProgressType,
)
from database import get_db


# ==================== User CRUD ====================


class UserCRUD:
    """CRUD операции для пользователей"""

    @staticmethod
    async def get_by_telegram_id(
        session: AsyncSession, telegram_id: int
    ) -> Optional[User]:
        """Получить пользователя по telegram_id"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> tuple[User, bool]:
        """
        Получить или создать пользователя

        Returns:
            tuple[User, bool]: (пользователь, создан_ли_новый)
        """
        user = await UserCRUD.get_by_telegram_id(session, telegram_id)

        if user:
            # Обновляем last_activity_at
            user.last_activity_at = datetime.utcnow()
            await session.commit()
            await session.refresh(user)
            return user, False

        # Создаём нового пользователя
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            last_activity_at=datetime.utcnow(),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user, True

    @staticmethod
    async def update_balance(session: AsyncSession, user_id: int) -> User:
        """
        DEPRECATED: Баланс обновляется автоматически через triggers!
        Оставлено для совместимости.
        """
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        await session.refresh(user)
        return user

    @staticmethod
    async def get_balance(session: AsyncSession, telegram_id: int) -> Dict[str, Any]:
        """
        Получить баланс пользователя

        Returns:
            dict: {
                "current_balance": Decimal,
                "total_income": Decimal,
                "total_expenses": Decimal,
                "total_transactions": int
            }
        """
        user = await UserCRUD.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id={telegram_id} not found")

        return {
            "current_balance": user.current_balance,
            "total_income": user.total_income,
            "total_expenses": user.total_expenses,
            "total_transactions": user.total_transactions,
            "currency": user.default_currency,
        }


# ==================== Transaction CRUD ====================


class TransactionCRUD:
    """CRUD операции для транзакций"""

    @staticmethod
    async def create(
        session: AsyncSession,
        telegram_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        category: str,
        description: Optional[str] = None,
        transaction_date: Optional[datetime] = None,
        currency: Optional[str] = None,
        account: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_recurring: bool = False,
        recurring_frequency: Optional[str] = None,
        # recurring_end_date УДАЛЕН - отсутствует в БД
        extra_data: Optional[dict] = None,
        attachments: Optional[dict] = None,
    ) -> tuple[Transaction, Decimal]:
        """
        Создать транзакцию

        ВАЖНО: Баланс обновляется автоматически через PostgreSQL trigger!

        Returns:
            tuple[Transaction, Decimal]: (транзакция, новый_баланс)
        """
        # Получаем пользователя
        user = await UserCRUD.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id={telegram_id} not found")

        # Валидация
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if is_recurring and not recurring_frequency:
            raise ValueError("Recurring frequency required for recurring transactions")

        # Создаём транзакцию
        transaction = Transaction(
            user_id=user.id,
            amount=amount,
            transaction_type=transaction_type,
            category=category,
            description=description,
            transaction_date=transaction_date or datetime.utcnow(),
            currency=currency or user.default_currency,
            account=account,
            tags=tags,
            is_recurring=is_recurring,
            recurring_frequency=recurring_frequency,
            # recurring_end_date удален - отсутствует в БД
            extra_data=extra_data,
            attachments=attachments,
        )

        # Вычисляем next_occurrence для recurring
        if is_recurring and recurring_frequency:
            transaction.next_occurrence = TransactionCRUD._calculate_next_occurrence(
                transaction.transaction_date, recurring_frequency
            )

        session.add(transaction)
        await session.commit()

        # Обновляем пользователя (trigger уже обновил баланс)
        await session.refresh(user)
        await session.refresh(transaction)

        return transaction, user.current_balance

    @staticmethod
    def _calculate_next_occurrence(base_date: datetime, frequency: str) -> datetime:
        """Вычислить следующую дату для recurring транзакции"""
        if frequency == "daily":
            return base_date + timedelta(days=1)
        elif frequency == "weekly":
            return base_date + timedelta(weeks=1)
        elif frequency == "monthly":
            # Добавляем месяц (примерно)
            return base_date + timedelta(days=30)
        elif frequency == "yearly":
            return base_date + timedelta(days=365)
        else:
            return base_date + timedelta(days=1)

    @staticmethod
    async def get_recent(
        session: AsyncSession,
        telegram_id: int,
        limit: int = 10,
        include_deleted: bool = False,
    ) -> List[Transaction]:
        """Получить последние N транзакций"""
        user = await UserCRUD.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id={telegram_id} not found")

        query = select(Transaction).where(Transaction.user_id == user.id)

        if not include_deleted:
            query = query.where(Transaction.is_deleted == False)

        query = query.order_by(
            desc(Transaction.transaction_date), desc(Transaction.created_at)
        )
        query = query.limit(limit)

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_period(
        session: AsyncSession,
        telegram_id: int,
        start_date: datetime,  # Изменено
        end_date: datetime,  # Изменено
        transaction_type: Optional[TransactionType] = None,
        category: Optional[str] = None,
    ) -> List[Transaction]:
        """Получить транзакции за период"""
        user = await UserCRUD.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id={telegram_id} not found")

        query = select(Transaction).where(
            and_(
                Transaction.user_id == user.id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_deleted == False,
            )
        )

        if transaction_type:
            query = query.where(Transaction.transaction_type == transaction_type)

        if category:
            query = query.where(Transaction.category == category)

        query = query.order_by(desc(Transaction.transaction_date))

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_category_stats(
        session: AsyncSession,
        telegram_id: int,
        start_date: datetime,
        end_date: datetime,  # Изменено
    ) -> List[Dict[str, Any]]:
        """Статистика по категориям за период"""
        user = await UserCRUD.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id={telegram_id} not found")

        result = await session.execute(
            select(
                Transaction.category,
                Transaction.transaction_type,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .where(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_deleted == False,
                )
            )
            .group_by(Transaction.category, Transaction.transaction_type)
            .order_by(desc("total"))
        )

        return [
            {
                "category": row.category,
                "type": row.transaction_type,
                "total": row.total,
                "count": row.count,
            }
            for row in result
        ]

    @staticmethod
    async def soft_delete(session: AsyncSession, transaction_id: int) -> bool:
        """Мягкое удаление транзакции"""
        result = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            return False

        transaction.is_deleted = True
        transaction.deleted_at = datetime.utcnow()
        await session.commit()

        # Баланс обновится автоматически через trigger
        return True

    @staticmethod
    async def restore(session: AsyncSession, transaction_id: int) -> bool:
        """Восстановить удалённую транзакцию"""
        result = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            return False

        transaction.is_deleted = False
        transaction.deleted_at = None
        await session.commit()

        # Баланс обновится автоматически через trigger
        return True


# ==================== Goal CRUD ====================


class GoalCRUD:
    """CRUD операции для целей"""

    @staticmethod
    async def create(
        session: AsyncSession,
        telegram_id: int,
        title: str,
        target_amount: Decimal,
        description: Optional[str] = None,
        target_date: Optional[datetime] = None,
        currency: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
    ) -> Goal:
        """Создать цель"""
        user = await UserCRUD.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id={telegram_id} not found")

        if target_amount <= 0:
            raise ValueError("Target amount must be positive")

        goal = Goal(
            user_id=user.id,
            title=title,
            target_amount=target_amount,
            description=description,
            target_date=target_date,
            currency=currency or user.default_currency,
            icon=icon,
            color=color,
        )

        session.add(goal)
        await session.commit()
        await session.refresh(goal)

        return goal

    @staticmethod
    async def get_active(session: AsyncSession, telegram_id: int) -> List[Goal]:
        """Получить активные цели"""
        user = await UserCRUD.get_by_telegram_id(session, telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id={telegram_id} not found")

        result = await session.execute(
            select(Goal)
            .where(and_(Goal.user_id == user.id, Goal.status == GoalStatus.ACTIVE))
            .order_by(Goal.target_date.asc().nullslast())
        )
        return result.scalars().all()

    @staticmethod
    async def add_progress(
        session: AsyncSession,
        goal_id: int,
        amount: Decimal,
        progress_type: ProgressType = ProgressType.CONTRIBUTION,  # Исправлено
        description: Optional[str] = None,
    ) -> tuple[GoalProgress, Goal]:
        """
        Добавить прогресс к цели

        Returns:
            tuple[GoalProgress, Goal]: (прогресс, обновлённая_цель)
        """
        result = await session.execute(select(Goal).where(Goal.id == goal_id))
        goal = result.scalar_one_or_none()

        if not goal:
            raise ValueError(f"Goal with id={goal_id} not found")

        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Создаём прогресс
        progress = GoalProgress(
            goal_id=goal_id,
            amount=amount,
            progress_type=progress_type,
            description=description,
        )

        session.add(progress)

        # Обновляем current_amount
        if progress_type == ProgressType.CONTRIBUTION:  # Было: DEPOSIT
            goal.current_amount += amount
        elif progress_type == ProgressType.WITHDRAWAL:
            goal.current_amount -= amount
            if goal.current_amount < 0:
                goal.current_amount = Decimal("0")
        # ADJUSTMENT не меняет баланс напрямую

        # Проверяем достижение цели
        if goal.current_amount >= goal.target_amount:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.utcnow()

        await session.commit()
        await session.refresh(goal)
        await session.refresh(progress)

        return progress, goal


# ==================== Helper Functions ====================


async def add_income(
    telegram_id: int,
    amount: Decimal,
    category: str,
    description: Optional[str] = None,
    transaction_date: Optional[datetime] = None,
    session: Optional[AsyncSession] = None,  # Добавлено
) -> Dict[str, Any]:
    """
    Быстрое добавление дохода

    Returns:
        dict: {"transaction_id": int, "new_balance": Decimal, "success": bool}
    """
    if session:
        # Используем переданную сессию
        transaction, new_balance = await TransactionCRUD.create(
            session=session,
            telegram_id=telegram_id,
            amount=amount,
            transaction_type=TransactionType.INCOME,
            category=category,
            description=description,
            transaction_date=transaction_date,
        )

        return {
            "transaction_id": transaction.id,
            "new_balance": new_balance,
            "success": True,
        }
    else:
        # Создаем свою сессию (для standalone вызовов)
        async with get_db() as session:
            transaction, new_balance = await TransactionCRUD.create(
                session=session,
                telegram_id=telegram_id,
                amount=amount,
                transaction_type=TransactionType.INCOME,
                category=category,
                description=description,
                transaction_date=transaction_date,
            )

            return {
                "transaction_id": transaction.id,
                "new_balance": new_balance,
                "success": True,
            }


async def add_expense(
    telegram_id: int,
    amount: Decimal,
    category: str,
    description: Optional[str] = None,
    transaction_date: Optional[datetime] = None,
    session: Optional[AsyncSession] = None,  # Добавлено
) -> Dict[str, Any]:
    """
    Быстрое добавление расхода

    Returns:
        dict: {"transaction_id": int, "new_balance": Decimal, "success": bool}
    """
    if session:
        # Используем переданную сессию
        transaction, new_balance = await TransactionCRUD.create(
            session=session,
            telegram_id=telegram_id,
            amount=amount,
            transaction_type=TransactionType.EXPENSE,
            category=category,
            description=description,
            transaction_date=transaction_date,
        )

        return {
            "transaction_id": transaction.id,
            "new_balance": new_balance,
            "success": True,
        }
    else:
        # Создаем свою сессию (для standalone вызовов)
        async with get_db() as session:
            transaction, new_balance = await TransactionCRUD.create(
                session=session,
                telegram_id=telegram_id,
                amount=amount,
                transaction_type=TransactionType.EXPENSE,
                category=category,
                description=description,
                transaction_date=transaction_date,
            )

            return {
                "transaction_id": transaction.id,
                "new_balance": new_balance,
                "success": True,
            }


# ==================== Example Usage ====================

if __name__ == "__main__":
    import asyncio
    from database import init_db, close_db

    async def main():
        """Примеры использования CRUD"""

        await init_db()

        # 1. Создание/получение пользователя
        async with get_db() as session:
            user, created = await UserCRUD.get_or_create(
                session, telegram_id=123456789, username="test_user", first_name="Test"
            )
            print(f"User: {user.username}, Created: {created}")

        # 2. Добавление дохода
        result = await add_income(
            telegram_id=123456789,
            amount=Decimal("5000.00"),
            category="Зарплата",
            description="Январь 2026",
        )
        print(f"Income added: {result}")

        # 3. Добавление расхода
        result = await add_expense(
            telegram_id=123456789,
            amount=Decimal("1500.00"),
            category="Продукты",
            description="Магазин",
        )
        print(f"Expense added: {result}")

        # 4. Получение баланса
        async with get_db() as session:
            balance = await UserCRUD.get_balance(session, 123456789)
            print(f"Balance: {balance}")

        # 5. Получение последних транзакций
        async with get_db() as session:
            transactions = await TransactionCRUD.get_recent(
                session, telegram_id=123456789, limit=5
            )
            print(f"\nRecent transactions:")
            for t in transactions:
                print(
                    f"  {t.transaction_date} | {t.transaction_type} | {t.amount} | {t.category}"
                )

        # 6. Создание цели
        async with get_db() as session:
            goal = await GoalCRUD.create(
                session,
                telegram_id=123456789,
                title="Новый iPhone",
                target_amount=Decimal("150000.00"),
                target_date=datetime(2026, 12, 31),
            )
            print(f"\nGoal created: {goal.title}")

        # 7. Добавление прогресса к цели
        async with get_db() as session:
            progress, updated_goal = await GoalCRUD.add_progress(
                session,
                goal_id=goal.id,
                amount=Decimal("10000.00"),
                description="Откладываем на iPhone",
            )
            print(
                f"Progress: {updated_goal.current_amount}/{updated_goal.target_amount} ({updated_goal.progress_percentage:.1f}%)"
            )

        await close_db()

    asyncio.run(main())

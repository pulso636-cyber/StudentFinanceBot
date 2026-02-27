"""
SQLAlchemy async models for Filkin Bot
Stack: aiogram + FastAPI + PostgreSQL + SQLAlchemy + Redis

Модели полностью совместимы с существующей PostgreSQL схемой.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    String,
    Numeric,
    DateTime,
    Date,
    Boolean,
    Text,
    Index,
    ForeignKey,
    CheckConstraint,
    ARRAY,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


# ==================== Base ====================
class Base(DeclarativeBase):
    """Base class for all models"""

    pass


# ==================== Python Enums ====================
class TransactionType(str, PyEnum):
    """Тип транзакции"""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class GoalStatus(str, PyEnum):
    """Статус цели"""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"  # Новый статус из БД


class ProgressType(str, PyEnum):
    """Тип прогресса цели"""

    CONTRIBUTION = "contribution"  # Было: DEPOSIT
    WITHDRAWAL = "withdrawal"
    ADJUSTMENT = "adjustment"  # Новый тип из БД


class RecurringFrequency(str, PyEnum):
    """Частота повторения транзакций"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


# ==================== PostgreSQL ENUM Types ====================
# Создаём ENUM типы для PostgreSQL (имена должны совпадать с PostgreSQL)
transaction_type_enum = ENUM(
    TransactionType,
    name="transaction_type_enum",
    create_type=False,  # Не создавать тип (уже существует в БД)
    values_callable=lambda x: [e.value for e in x],  # Используем .value вместо .name
)

goal_status_enum = ENUM(
    GoalStatus,
    name="goal_status_enum",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)

progress_type_enum = ENUM(
    ProgressType,
    name="progress_type_enum",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)

recurring_frequency_enum = ENUM(
    RecurringFrequency,
    name="recurring_frequency_enum",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)


# ==================== Models ====================


class User(Base):
    """
    Пользователь Telegram бота

    Связи:
    - transactions: List[Transaction] - все транзакции пользователя
    - goals: List[Goal] - все цели пользователя
    """

    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Telegram Info (UNIQUE)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Financial Data (Denormalized для производительности)
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=0, server_default="0"
    )
    total_income: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=0, server_default="0"
    )
    total_expenses: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=0, server_default="0"
    )
    total_transactions: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )

    # Settings
    default_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="RUB", server_default="RUB"
    )
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="UTC", server_default="UTC"
    )

    # Metadata
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_premium: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Timestamps (автоматические)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        "last_activity_at", DateTime(timezone=True), nullable=True
    )

    # Relationships
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    goals: Mapped[List["Goal"]] = relationship(
        "Goal", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    # Indexes определены через __table_args__
    __table_args__ = (
        Index("idx_users_telegram_id", "telegram_id"),
        Index("idx_users_username", "username"),
        Index("idx_users_is_active", "is_active"),
        Index("idx_users_created_at", "created_at"),
        CheckConstraint("current_balance >= 0", name="check_balance_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Transaction(Base):
    """
    Транзакция (доход/расход/перевод)

    Связи:
    - user: User - владелец транзакции

    Triggers (работают автоматически в PostgreSQL):
    - trigger_update_user_balance: обновляет баланс пользователя
    - trigger_update_transaction_timestamp: обновляет updated_at
    """

    __tablename__ = "transactions"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Transaction Data
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        transaction_type_enum, nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Date & Currency
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="RUB", server_default="RUB"
    )

    # Account & Tags
    account: Mapped[Optional[str]] = mapped_column(
        "account", String(100), nullable=True
    )
    account_name: Mapped[Optional[str]] = mapped_column(
        "account_name", String(100), nullable=True
    )
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)

    # Recurring Transactions
    is_recurring: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    recurring_frequency: Mapped[Optional[RecurringFrequency]] = mapped_column(
        recurring_frequency_enum, nullable=True
    )
    next_occurrence: Mapped[Optional[datetime]] = mapped_column(
        "next_occurrence_date", DateTime(timezone=True), nullable=True
    )
    # Поле recurring_end_date отсутствует в БД, удалено

    # Soft Delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadata (JSONB для гибкости)
    # Используем extra_data вместо metadata (конфликт с SQLAlchemy)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    attachments: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")

    # Indexes и Constraints
    __table_args__ = (
        # Composite indexes для производительности
        Index("idx_transactions_user_date", "user_id", "transaction_date"),
        Index("idx_transactions_user_type", "user_id", "transaction_type"),
        Index("idx_transactions_user_category", "user_id", "category"),
        # Single column indexes
        Index("idx_transactions_date", "transaction_date"),
        Index("idx_transactions_type", "transaction_type"),
        Index("idx_transactions_category", "category"),
        Index("idx_transactions_currency", "currency"),
        # Partial indexes (только для не удалённых)
        Index(
            "idx_transactions_not_deleted",
            "user_id",
            "transaction_date",
            postgresql_where=(is_deleted == False),
        ),
        # GIN indexes для массивов и JSONB
        Index("idx_transactions_tags", "tags", postgresql_using="gin"),
        Index("idx_transactions_metadata", "metadata", postgresql_using="gin"),
        # Recurring transactions index
        Index(
            "idx_transactions_recurring",
            "is_recurring",
            "next_occurrence_date",  # Исправлено: было next_occurrence
            postgresql_where=(is_recurring == True),
        ),
        # Constraints
        CheckConstraint("amount > 0", name="check_amount_positive"),
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, type={self.transaction_type})>"


class Goal(Base):
    """
    Финансовая цель пользователя

    Связи:
    - user: User - владелец цели
    - progress: List[GoalProgress] - история прогресса
    """

    __tablename__ = "goals"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Goal Data
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=0, server_default="0"
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="RUB", server_default="RUB"
    )

    # Category and Priority (новые поля из БД)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    priority: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Status
    status: Mapped[GoalStatus] = mapped_column(
        goal_status_enum,
        nullable=False,
        default=GoalStatus.ACTIVE,
        server_default="active",
    )

    # Dates
    start_date: Mapped[Optional[datetime]] = mapped_column(
        "start_date", DateTime(timezone=True), nullable=True
    )
    target_date: Mapped[Optional[datetime]] = mapped_column(
        "target_date", DateTime(timezone=True), nullable=True
    )
    # deadline удален - не существует в БД, используется target_date
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadata
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="goals")
    progress: Mapped[List["GoalProgress"]] = relationship(
        "GoalProgress",
        back_populates="goal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes и Constraints
    __table_args__ = (
        # Composite indexes
        Index("idx_goals_user_status", "user_id", "status"),
        Index("idx_goals_user_target_date", "user_id", "target_date"),
        # Single column indexes
        Index("idx_goals_status", "status"),
        Index("idx_goals_target_date", "target_date"),
        # GIN index для JSONB
        Index("idx_goals_metadata", "metadata", postgresql_using="gin"),
        # Constraints
        CheckConstraint("target_amount > 0", name="check_target_positive"),
        CheckConstraint("current_amount >= 0", name="check_current_non_negative"),
        CheckConstraint(
            "current_amount <= target_amount", name="check_current_not_exceeds_target"
        ),
    )

    def __repr__(self) -> str:
        return f"<Goal(id={self.id}, user_id={self.user_id}, title={self.title}, status={self.status})>"

    @property
    def progress_percentage(self) -> float:
        """Процент выполнения цели"""
        if self.target_amount == 0:
            return 0.0
        return float((self.current_amount / self.target_amount) * 100)


class GoalProgress(Base):
    """
    История прогресса цели (вклады/снятия)

    Связи:
    - goal: Goal - цель, к которой относится прогресс
    """

    __tablename__ = "goal_progress"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key
    goal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Progress Data
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    progress_type: Mapped[ProgressType] = mapped_column(
        progress_type_enum, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    goal: Mapped["Goal"] = relationship("Goal", back_populates="progress")

    # Indexes и Constraints
    __table_args__ = (
        # Composite index
        Index("idx_goal_progress_goal_created", "goal_id", "created_at"),
        # Single column index
        Index("idx_goal_progress_type", "progress_type"),
        # GIN index для JSONB
        Index("idx_goal_progress_metadata", "metadata", postgresql_using="gin"),
        # Constraints
        CheckConstraint("amount > 0", name="check_progress_amount_positive"),
    )

    def __repr__(self) -> str:
        return f"<GoalProgress(id={self.id}, goal_id={self.goal_id}, amount={self.amount}, type={self.progress_type})>"

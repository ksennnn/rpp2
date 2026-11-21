from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Account(Base):
    __tablename__ = "accounts"

    customer_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class Operation(Base):
    __tablename__ = "operations"

    operation_id: Mapped[str] = mapped_column(String(150), primary_key=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    check_number: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    amount: Mapped[object | None] = mapped_column(Numeric(14, 2), nullable=True)
    points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reject_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    occurred_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)

Index("ix_operations_check_type", Operation.check_number, Operation.type)
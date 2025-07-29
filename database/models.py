from datetime import datetime, UTC, timedelta
from enum import Enum, auto
from typing import Optional

from sqlalchemy import DateTime, Text, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SubscriptionTier(Enum):
    PLUS = auto()
    PREMIUM = auto()
    SUPREME = auto()


SUBSCRIPTION_CONFIG = {
    SubscriptionTier.PLUS: {
        "price": 199,
        "dino_slots": 3,
        "discord_role_id": 1395453023727390863
    },
    SubscriptionTier.PREMIUM: {
        "price": 599,
        "dino_slots": 6,
        "discord_role_id": 1395452649045753936
    },
    SubscriptionTier.SUPREME: {
        "price": 899,
        "dino_slots": 8,
        "discord_role_id": 1395452801970344017
    }
}


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    steam_id: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    tier: Mapped[SubscriptionTier] = mapped_column(SQLEnum(SubscriptionTier), nullable=False)
    dino_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_renewal: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    purchase_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), nullable=False
    )
    expiration_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    @classmethod
    def create(
            cls,
            steam_id: str,
            tier: SubscriptionTier,
            duration_days: int = 30
    ) -> "Subscription":
        if tier not in SUBSCRIPTION_CONFIG:
            raise ValueError(f"Unknown subscription tier: {tier}")

        now = datetime.now(UTC)
        return cls(
            steam_id=steam_id,
            tier=tier,
            dino_slots=SUBSCRIPTION_CONFIG[tier]["dino_slots"],
            is_active=True,
            auto_renewal=True,
            purchase_date=now,
            expiration_date=now + timedelta(days=duration_days)
        )


class Players(Base):
    __tablename__ = "players"

    discord_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    steam_id: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    tk: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    registry_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), nullable=False
    )


class DinoStorage(Base):
    __tablename__ = "dino_storage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dino_class: Mapped[str] = mapped_column(Text, nullable=False)
    growth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hunger: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thirst: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    health: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steam_id: Mapped[str] = mapped_column(Text, nullable=False)


class PendingDinoStorage(Base):
    __tablename__ = "pending_dino_storage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    steam_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    discord_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    dino_class: Mapped[str] = mapped_column(Text, nullable=False)
    growth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hunger: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thirst: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    health: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self):
        return (
            f"<PendingDinoStorage(id={self.id}, steam_id={self.steam_id}, "
            f"discord_id={self.discord_id}, created_at={self.created_at}, url={self.url})>"
        )

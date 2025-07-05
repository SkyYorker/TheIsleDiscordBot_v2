from datetime import datetime, UTC

from sqlalchemy import (
    DateTime,
    Text,
    Integer,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Players(Base):
    __tablename__ = "players"

    discord_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    steam_id: Mapped[str] = mapped_column(Text, unique=True)
    tk: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    registry_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), nullable=False
    )

    dinos: Mapped[list["DinoStorage"]] = relationship(
        "DinoStorage", back_populates="player"
    )


class DinoStorage(Base):
    __tablename__ = "dino_storage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dino_class: Mapped[str] = mapped_column(Text, nullable=False)
    growth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hunger: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thirst: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    health: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steam_id: Mapped[str] = mapped_column(
        ForeignKey("players.steam_id"), nullable=False, index=True
    )

    player: Mapped["Players"] = relationship("Players", back_populates="dinos")

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

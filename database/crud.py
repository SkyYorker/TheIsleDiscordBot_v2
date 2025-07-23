from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import delete, outerjoin
from sqlalchemy import select, update

from . import async_session_maker
from . import engine
from .models import PendingDinoStorage
from .models import Players, DinoStorage, Base, Subscription, SubscriptionTier


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class SubscriptionCRUD:
    @staticmethod
    async def get_active_subscription_by_steamid(steam_id: str) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Subscription)
                .where(Subscription.steam_id == steam_id)
                .where(Subscription.is_active == True)
                .where(Subscription.expiration_date > datetime.now(UTC))
                .order_by(Subscription.expiration_date.desc())
            )
            sub = result.scalars().first()
            return {
                "id": sub.id,
                "tier": sub.tier.name,
                "dino_slots": sub.dino_slots,
                "is_active": sub.is_active,
                "auto_renewal": sub.auto_renewal,
                "expiration_date": sub.expiration_date
            } if sub else None

    @staticmethod
    async def get_active_subscription_by_discord_id(discord_id: int) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            player = await session.scalar(
                select(Players).where(Players.discord_id == discord_id)
            )
            if not player or not player.steam_id:
                return None
            result = await session.execute(
                select(Subscription)
                .where(Subscription.steam_id == player.steam_id)
                .where(Subscription.is_active == True)
                .where(Subscription.expiration_date > datetime.now(UTC))
                .order_by(Subscription.expiration_date.desc())
            )
            sub = result.scalars().first()
            return {
                "id": sub.id,
                "tier": sub.tier.name,
                "dino_slots": sub.dino_slots,
                "is_active": sub.is_active,
                "auto_renewal": sub.auto_renewal,
                "expiration_date": sub.expiration_date
            } if sub else None

    @staticmethod
    async def add_subscription_by_steamid(
            steam_id: str,
            tier: SubscriptionTier,
            duration_days: int = 30,
            auto_renewal: bool = True
    ) -> Dict[str, Any]:
        async with async_session_maker() as session:
            sub = Subscription.create(
                steam_id=steam_id,
                tier=tier,
                duration_days=duration_days
            )
            sub.auto_renewal = auto_renewal

            session.add(sub)
            await session.commit()
            await session.refresh(sub)

            return {
                "id": sub.id,
                "tier": sub.tier.name,
                "dino_slots": sub.dino_slots,
                "expiration_date": sub.expiration_date,
                "auto_renewal": sub.auto_renewal
            }

    @staticmethod
    async def add_subscription_by_discord_id(
            discord_id: int,
            tier: SubscriptionTier,
            duration_days: int = 30,
            auto_renewal: bool = True
    ) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            player = await session.scalar(
                select(Players).where(Players.discord_id == discord_id)
            )
            if not player or not player.steam_id:
                return None
            sub = Subscription.create(
                steam_id=player.steam_id,
                tier=tier,
                duration_days=duration_days
            )
            sub.auto_renewal = auto_renewal

            session.add(sub)
            await session.commit()
            await session.refresh(sub)

            return {
                "id": sub.id,
                "tier": sub.tier.name,
                "dino_slots": sub.dino_slots,
                "expiration_date": sub.expiration_date,
                "auto_renewal": sub.auto_renewal
            }

    @staticmethod
    async def update_subscription(
            subscription_id: int,
            updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.execute(
                update(Subscription)
                .where(Subscription.id == subscription_id)
                .values(**updates)
                .returning(Subscription)
            )
            await session.commit()
            sub = result.fetchone()
            if sub:
                sub = sub[0]
                return {
                    "id": sub.id,
                    "tier": sub.tier.name,
                    "dino_slots": sub.dino_slots,
                    "is_active": sub.is_active,
                    "auto_renewal": sub.auto_renewal,
                    "expiration_date": sub.expiration_date
                }
            return None

    @staticmethod
    async def cancel_subscription(subscription_id: int) -> bool:
        async with async_session_maker() as session:
            result = await session.execute(
                update(Subscription)
                .where(Subscription.id == subscription_id)
                .values(is_active=False)
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def expire_subscription(subscription_id: int) -> bool:
        async with async_session_maker() as session:
            result = await session.execute(
                update(Subscription)
                .where(Subscription.id == subscription_id)
                .values(is_active=False)
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def get_player_subscriptions(
            steam_id: str,
            active_only: bool = False
    ) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            query = select(Subscription).where(Subscription.steam_id == steam_id)
            if active_only:
                now = datetime.now(UTC)
                query = query.where(Subscription.is_active == True, Subscription.expiration_date > now)
            result = await session.execute(query)
            return [
                {
                    "id": sub.id,
                    "tier": sub.tier.name,
                    "dino_slots": sub.dino_slots,
                    "is_active": sub.is_active,
                    "auto_renewal": sub.auto_renewal,
                    "expiration_date": sub.expiration_date
                }
                for sub in result.scalars()
            ]

    @staticmethod
    async def renew_subscription(
            subscription_id: int,
            duration_days: int = 30
    ) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Subscription).where(Subscription.id == subscription_id)
            )
            sub = result.scalars().first()
            if not sub:
                return None
            now = datetime.now(UTC)
            new_expiration = max(sub.expiration_date, now) + timedelta(days=duration_days)
            sub.expiration_date = new_expiration
            sub.is_active = True
            await session.commit()
            await session.refresh(sub)
            return {
                "id": sub.id,
                "tier": sub.tier.name,
                "dino_slots": sub.dino_slots,
                "is_active": sub.is_active,
                "auto_renewal": sub.auto_renewal,
                "expiration_date": sub.expiration_date
            }

    @staticmethod
    async def get_expiring_subscriptions(
            hours_before: int = 24
    ) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            now = datetime.now(UTC)
            expiration_threshold = now + timedelta(hours=hours_before)

            result = await session.execute(
                select(Subscription)
                .where(Subscription.is_active == True)
                .where(Subscription.expiration_date <= expiration_threshold)
                .where(Subscription.expiration_date > now)
            )
            return [
                {
                    "id": sub.id,
                    "steam_id": sub.steam_id,
                    "tier": sub.tier.name,
                    "auto_renewal": sub.auto_renewal,
                    "expiration_date": sub.expiration_date
                }
                for sub in result.scalars()
            ]

    @staticmethod
    async def get_expired_subscriptions() -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            stmt = (
                select(
                    Subscription,
                    Players.discord_id.label("player_id")
                )
                .select_from(
                    outerjoin(Subscription, Players, Subscription.steam_id == Players.steam_id)
                )
                .where(Subscription.is_active == True)
                .where(Subscription.expiration_date <= datetime.now(UTC))
            )
            result = await session.execute(stmt)
            return [
                {
                    "id": sub.id,
                    "steam_id": sub.steam_id,
                    "player_id": player_id,
                    "tier": sub.tier.name,
                    "auto_renewal": sub.auto_renewal,
                    "expiration_date": sub.expiration_date
                }
                for sub, player_id in result.all()
            ]

    @staticmethod
    async def bulk_update_subscriptions(
            subscription_ids: List[int],
            updates: Dict[str, Any]
    ) -> int:
        async with async_session_maker() as session:
            result = await session.execute(
                update(Subscription)
                .where(Subscription.id.in_(subscription_ids))
                .values(**updates)
            )
            await session.commit()
            return result.rowcount


class DonationCRUD:
    @staticmethod
    async def get_tk(discord_id: int) -> Optional[int]:
        async with async_session_maker() as session:
            player = await session.scalar(
                select(Players).where(Players.discord_id == discord_id)
            )
            if not player:
                return None
            return player.tk

    @staticmethod
    async def add_tk(discord_id: int, amount: int) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            player = await session.scalar(
                select(Players).where(Players.discord_id == discord_id)
            )
            if not player:
                return None
            player.tk += amount
            await session.commit()
            await session.refresh(player)
            return {
                "discord_id": player.discord_id,
                "steam_id": player.steam_id,
                "tk": player.tk,
                "registry_date": player.registry_date,
            }

    @staticmethod
    async def remove_tk(discord_id: int, amount: int) -> bool:
        async with async_session_maker() as session:
            current_tk = await session.execute(
                select(Players.tk).where(Players.discord_id == discord_id)
            )
            current_tk = current_tk.scalar_one_or_none()

            if current_tk is None or current_tk < amount:
                return False

            result = await session.execute(
                update(Players)
                .where(Players.discord_id == discord_id)
                .values(tk=Players.tk - amount)
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def check_balance_by_discordid(discord_id: int, amount: int) -> bool:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Players.tk)
                .where(Players.discord_id == discord_id)
            )
            balance = result.scalar()
            return balance >= amount if balance is not None else False

    @staticmethod
    async def check_balance_by_steamid(steam_id: str, amount: int) -> bool:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Players.tk)
                .where(Players.steam_id == steam_id)
            )
            balance = result.scalar()
            return balance >= amount if balance is not None else False

class PlayerDinoCRUD:
    @staticmethod
    async def add_player(
            discord_id: int,
            steam_id: str,
            tk: int = 0,
            registry_date: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            existing = await session.scalar(
                select(Players).where(
                    (Players.discord_id == discord_id) | (Players.steam_id == steam_id)
                )
            )
            if existing:
                updated = False
                if existing.steam_id != steam_id:
                    existing.steam_id = steam_id
                    updated = True
                if updated:
                    await session.commit()
                    await session.refresh(existing)
                return PlayerDinoCRUD._player_dict(existing)

            player = Players(
                discord_id=discord_id,
                steam_id=steam_id,
                tk=tk,
                registry_date=registry_date
            ) if registry_date else Players(
                discord_id=discord_id,
                steam_id=steam_id,
                tk=tk
            )
            session.add(player)
            await session.commit()
            await session.refresh(player)
            return PlayerDinoCRUD._player_dict(player)

    @staticmethod
    async def delete_player(discord_id: int) -> bool:
        async with async_session_maker() as session:
            player = await session.scalar(
                select(Players).where(Players.discord_id == discord_id)
            )
            if not player:
                return False
            player.steam_id = None
            await session.commit()
            await session.refresh(player)
            return True

    @staticmethod
    async def get_player_info(discord_id: int, full: bool = False) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            player: Optional[Players] = await session.scalar(
                select(Players).where(Players.discord_id == discord_id)
            )
            if not player:
                return None

            dinos: List[DinoStorage] = (
                await session.scalars(
                    select(DinoStorage).where(DinoStorage.steam_id == player.steam_id)
                )
            ).all() if player.steam_id else []

            player_dict = PlayerDinoCRUD._player_dict(player)
            dinos_list = [PlayerDinoCRUD._dino_dict(d, full) for d in dinos]

            return {
                "player": player_dict,
                "dinos": dinos_list,
            }

    @staticmethod
    def _player_dict(player: Players) -> Dict[str, Any]:
        data = {
            "discord_id": player.discord_id,
            "steam_id": player.steam_id,
            "tk": player.tk,
            "registry_date": player.registry_date,
        }
        return data

    @staticmethod
    def _dino_dict(dino: DinoStorage, full: bool) -> Dict[str, Any]:
        data = {
            "id": dino.id,
            "dino_class": dino.dino_class,
            "growth": dino.growth,
            "hunger": dino.hunger,
            "thirst": dino.thirst,
            "health": dino.health,
        }
        if full:
            data["steam_id"] = dino.steam_id
        return data

    @staticmethod
    async def add_dino(
            steam_id: str,
            dino_class: str,
            growth: int = 0,
            hunger: int = 0,
            thirst: int = 0,
            health: int = 0
    ) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            player = await session.scalar(
                select(Players).where(Players.steam_id == steam_id)
            )
            if not player:
                return None

            new_dino = DinoStorage(
                dino_class=dino_class,
                growth=growth,
                hunger=hunger,
                thirst=thirst,
                health=health,
                steam_id=steam_id
            )
            session.add(new_dino)
            await session.commit()
            await session.refresh(new_dino)
            return PlayerDinoCRUD._dino_dict(new_dino, full=True)

    @staticmethod
    async def delete_dino(steam_id: str, dino_id: int) -> bool:
        async with async_session_maker() as session:
            dino = await session.scalar(
                select(DinoStorage).where(
                    DinoStorage.id == dino_id,
                    DinoStorage.steam_id == steam_id
                )
            )
            if not dino:
                return False
            await session.delete(dino)
            await session.commit()
            return True

    @staticmethod
    async def get_dino_by_id(dino_id: int) -> DinoStorage | None:
        async with async_session_maker() as session:
            dino = await session.scalar(
                select(DinoStorage).where(
                    DinoStorage.id == dino_id
                )
            )
            if not dino:
                return None
            return dino


class PendingDinoCRUD:
    @staticmethod
    async def add_pending_dino(
            steam_id: str,
            discord_id: int,
            url: str,
            dino_class: str,
            growth: int,
            hunger: int,
            thirst: int,
            health: int
    ) -> Dict[str, Any]:
        async with async_session_maker() as session:
            pending = PendingDinoStorage(
                steam_id=steam_id,
                discord_id=discord_id,
                url=url,
                dino_class=dino_class,
                growth=growth,
                hunger=hunger,
                thirst=thirst,
                health=health
            )
            session.add(pending)
            await session.commit()
            await session.refresh(pending)
            return PendingDinoCRUD._pending_dino_dict(pending)

    @staticmethod
    async def get_by_steam_id(steam_id: str) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.scalars(
                select(PendingDinoStorage).where(PendingDinoStorage.steam_id == steam_id)
            )
            return [PendingDinoCRUD._pending_dino_dict(row) for row in result.all()]

    @staticmethod
    async def get_by_discord_id(discord_id: int) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.scalars(
                select(PendingDinoStorage).where(PendingDinoStorage.discord_id == discord_id)
            )
            return [PendingDinoCRUD._pending_dino_dict(row) for row in result.all()]

    @staticmethod
    async def delete_by_steam_id(steam_id: str) -> int:
        async with async_session_maker() as session:
            result = await session.execute(
                delete(PendingDinoStorage).where(PendingDinoStorage.steam_id == steam_id)
            )
            await session.commit()
            return result.rowcount or 0

    @staticmethod
    async def delete_by_discord_id(discord_id: int) -> int:
        async with async_session_maker() as session:
            result = await session.execute(
                delete(PendingDinoStorage).where(PendingDinoStorage.discord_id == discord_id)
            )
            await session.commit()
            return result.rowcount or 0

    @staticmethod
    async def cleanup_old_entries(minutes: int = 5) -> int:
        threshold = datetime.now(UTC) - timedelta(minutes=minutes)
        async with async_session_maker() as session:
            result = await session.execute(
                delete(PendingDinoStorage).where(PendingDinoStorage.created_at < threshold)
            )
            await session.commit()
            return result.rowcount or 0

    @staticmethod
    def _pending_dino_dict(obj: PendingDinoStorage) -> Dict[str, Any]:
        return {
            "id": obj.id,
            "steam_id": obj.steam_id,
            "discord_id": obj.discord_id,
            "created_at": obj.created_at,
            "url": obj.url,
            "dino_class": obj.dino_class,
            "growth": obj.growth,
            "hunger": obj.hunger,
            "thirst": obj.thirst,
            "health": obj.health,
        }

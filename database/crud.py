from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import delete
from sqlalchemy import select, update

from . import async_session_maker
from . import engine
from .models import PendingDinoStorage
from .models import Players, DinoStorage, Base, Subscription, SubscriptionTier, RoleBonusUsage


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_steam_id_by_discord_id(discord_id: int) -> Optional[str]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Players.steam_id).where(Players.discord_id == discord_id)
        )
        steam_id = result.scalar()
        return steam_id


class SubscriptionCRUD:
    @staticmethod
    async def get_active_subscription(discord_id: int) -> Optional[Dict[str, Any]]:
        steam_id = await get_steam_id_by_discord_id(discord_id)
        if not steam_id:
            return None
        async with async_session_maker() as session:
            result = await session.execute(
                select(Subscription)
                .where(Subscription.steam_id == steam_id)
                .where(Subscription.is_active == True)
                .where(Subscription.expiration_date > datetime.now())
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
    async def add_subscription(
            discord_id: int,
            tier: SubscriptionTier,
            duration_days: int = 30,
            auto_renewal: bool = True
    ) -> Dict[str, Any]:
        steam_id = await get_steam_id_by_discord_id(discord_id)
        if not steam_id:
            raise ValueError("No steam_id for this discord_id")
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
            updated_sub = result.scalars().first()
            if not updated_sub:
                return None

            await session.commit()
            await session.refresh(updated_sub)

            return {
                "id": updated_sub.id,
                "tier": updated_sub.tier.name,
                "is_active": updated_sub.is_active,
                "auto_renewal": updated_sub.auto_renewal,
                "expiration_date": updated_sub.expiration_date
            }

    @staticmethod
    async def cancel_subscription(subscription_id: int) -> bool:
        async with async_session_maker() as session:
            result = await session.execute(
                update(Subscription)
                .where(Subscription.id == subscription_id)
                .values(auto_renewal=False)
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
            discord_id: int,
            active_only: bool = False
    ) -> List[Dict[str, Any]]:
        steam_id = await get_steam_id_by_discord_id(discord_id)
        if not steam_id:
            return []
        async with async_session_maker() as session:
            query = select(Subscription).where(Subscription.steam_id == steam_id)

            if active_only:
                query = query.where(
                    Subscription.is_active == True,
                    Subscription.expiration_date > datetime.now(UTC)
                )

            result = await session.execute(query.order_by(Subscription.expiration_date.desc()))
            return [
                {
                    "id": sub.id,
                    "tier": sub.tier.name,
                    "dino_slots": sub.dino_slots,
                    "is_active": sub.is_active,
                    "auto_renewal": sub.auto_renewal,
                    "purchase_date": sub.purchase_date,
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
            sub = await session.scalar(
                select(Subscription).where(Subscription.id == subscription_id)
            )
            if not sub:
                return None

            sub.expiration_date = max(
                datetime.now(),
                sub.expiration_date
            ) + timedelta(days=duration_days)
            sub.is_active = True

            await session.commit()
            await session.refresh(sub)

            return {
                "id": sub.id,
                "new_expiration_date": sub.expiration_date,
                "tier": sub.tier.name
            }

    @staticmethod
    async def get_expiring_subscriptions(days: int = 3) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            now = datetime.now()
            expire_threshold = now + timedelta(days=days)
            stmt = (
                select(
                    Subscription.id,
                    Subscription.steam_id,
                    Subscription.tier,
                    Subscription.dino_slots,
                    Subscription.is_active,
                    Subscription.auto_renewal,
                    Subscription.purchase_date,
                    Subscription.expiration_date,
                    Players.discord_id.label("player_id"),
                )
                .outerjoin(Players, Players.steam_id == Subscription.steam_id)
                .where(
                    Subscription.expiration_date <= expire_threshold,
                    Subscription.expiration_date > now,
                    Subscription.is_active == True,
                )
            )
            result = await session.execute(stmt)
            subscriptions = []
            for row in result.fetchall():
                subscriptions.append({
                    "id": row.id,
                    "steam_id": row.steam_id,
                    "tier": row.tier.name if row.tier else None,
                    "dino_slots": row.dino_slots,
                    "is_active": row.is_active,
                    "auto_renewal": row.auto_renewal,
                    "purchase_date": row.purchase_date,
                    "expiration_date": row.expiration_date,
                    "player_id": row.player_id,
                })
            return subscriptions

    @staticmethod
    async def get_expired_subscriptions() -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            now = datetime.now()
            stmt = (
                select(
                    Subscription.id,
                    Subscription.steam_id,
                    Subscription.tier,
                    Subscription.dino_slots,
                    Subscription.is_active,
                    Subscription.auto_renewal,
                    Subscription.purchase_date,
                    Subscription.expiration_date,
                    Players.discord_id.label("player_id"),
                )
                .outerjoin(Players, Players.steam_id == Subscription.steam_id)
                .where(
                    Subscription.expiration_date <= now,
                    Subscription.is_active == True,
                )
            )
            result = await session.execute(stmt)
            subscriptions = []
            for row in result.fetchall():
                subscriptions.append({
                    "id": row.id,
                    "steam_id": row.steam_id,
                    "tier": row.tier.name if row.tier else None,
                    "dino_slots": row.dino_slots,
                    "is_active": row.is_active,
                    "auto_renewal": row.auto_renewal,
                    "purchase_date": row.purchase_date,
                    "expiration_date": row.expiration_date,
                    "player_id": row.player_id,
                })
            return subscriptions

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
    async def check_balance(discord_id: int, amount: int) -> bool:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Players.tk)
                .where(Players.discord_id == discord_id)
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


class RoleBonusCRUD:
    """CRUD операции для бонусов по ролям"""
    
    @staticmethod
    def get_week_start(dt: datetime) -> datetime:
        """Получить начало недели (понедельник) для даты"""
        # Получаем понедельник текущей недели
        days_since_monday = dt.weekday()
        week_start = dt.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
        # Убеждаемся, что время имеет timezone
        if week_start.tzinfo is None:
            week_start = week_start.replace(tzinfo=UTC)
        return week_start
    
    @staticmethod
    async def get_weekly_usage_count(discord_id: int, role_name: str) -> int:
        """Получить количество использований бонуса в текущей неделе"""
        async with async_session_maker() as session:
            now = datetime.now(UTC)
            week_start = RoleBonusCRUD.get_week_start(now)
            
            result = await session.execute(
                select(RoleBonusUsage)
                .where(RoleBonusUsage.discord_id == discord_id)
                .where(RoleBonusUsage.role_name == role_name)
                .where(RoleBonusUsage.week_start == week_start)
            )
            usages = result.scalars().all()
            return len(usages)
    
    @staticmethod
    async def can_use_bonus(discord_id: int, role_name: str, max_uses_per_week: int) -> tuple[bool, int, Optional[str]]:
        """
        Проверить, может ли пользователь использовать бонус
        
        Returns:
            (can_use, current_uses, error_message)
        """
        current_uses = await RoleBonusCRUD.get_weekly_usage_count(discord_id, role_name)
        
        if current_uses >= max_uses_per_week:
            week_start = RoleBonusCRUD.get_week_start(datetime.now(UTC))
            next_week = week_start + timedelta(days=7)
            return False, current_uses, f"Вы уже использовали все бесплатные кормления на эту неделю. Следующее доступно: {next_week.strftime('%d.%m.%Y')}"
        
        return True, current_uses, None
    
    @staticmethod
    async def record_bonus_usage(discord_id: int, role_name: str) -> Dict[str, Any]:
        """Записать использование бонуса"""
        async with async_session_maker() as session:
            now = datetime.now(UTC)
            week_start = RoleBonusCRUD.get_week_start(now)
            
            usage = RoleBonusUsage(
                discord_id=discord_id,
                role_name=role_name,
                week_start=week_start
            )
            session.add(usage)
            await session.commit()
            await session.refresh(usage)
            
            return {
                "id": usage.id,
                "discord_id": usage.discord_id,
                "role_name": usage.role_name,
                "used_at": usage.used_at,
                "week_start": usage.week_start
            }
    
    @staticmethod
    async def get_user_bonus_history(discord_id: int, role_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получить историю использования бонусов пользователем"""
        async with async_session_maker() as session:
            query = select(RoleBonusUsage).where(RoleBonusUsage.discord_id == discord_id)
            if role_name:
                query = query.where(RoleBonusUsage.role_name == role_name)
            
            result = await session.execute(query.order_by(RoleBonusUsage.used_at.desc()))
            return [
                {
                    "id": usage.id,
                    "discord_id": usage.discord_id,
                    "role_name": usage.role_name,
                    "used_at": usage.used_at,
                    "week_start": usage.week_start
                }
                for usage in result.scalars()
            ]

from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy import delete
from sqlalchemy import select, update

from . import async_session_maker
from . import engine
from .models import PendingDinoStorage
from .models import Players, DinoStorage, Base, Subscription, SubscriptionTier
from .models import Item, ItemType, PlayerInventory, BonusCode, BonusCodeUsage, RoleBonusUsage


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Выполняем миграцию для добавления колонки bonus_type
    try:
        from database.add_bonus_type_column import add_bonus_type_column
        await add_bonus_type_column()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Не удалось выполнить миграцию bonus_type: {e}")

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
        import logging
        logger = logging.getLogger(__name__)
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(Players.tk)
                .where(Players.discord_id == discord_id)
            )
            balance = result.scalar()
            
            # Если баланс None, значит игрок не найден или tk = None
            if balance is None:
                logger.warning(f"[DonationCRUD] Баланс None для пользователя {discord_id}. Игрок не найден или tk = None")
                return False
            
            # Проверяем, достаточно ли средств
            has_enough = balance >= amount
            logger.debug(f"[DonationCRUD] Проверка баланса для {discord_id}: баланс={balance}, требуется={amount}, достаточно={has_enough}")
            return has_enough


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
    async def get_by_steam_id(steam_id: str, with_lock: bool = False) -> List[Dict[str, Any]]:
        """
        Получает список pending_dino по steam_id.
        
        Args:
            steam_id: Steam ID игрока
            with_lock: Если True, использует SELECT FOR UPDATE для блокировки строки
        
        Returns:
            Список словарей с данными pending_dino
        """
        async with async_session_maker() as session:
            query = select(PendingDinoStorage).where(PendingDinoStorage.steam_id == steam_id)
            if with_lock:
                query = query.with_for_update()
            result = await session.scalars(query)
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
    async def get_and_delete_by_steam_id(steam_id: str) -> Optional[Dict[str, Any]]:
        """
        Атомарная операция: получает и удаляет pending_dino в одной транзакции с блокировкой строки.
        Использует SELECT FOR UPDATE для предотвращения race condition.
        Для SQLite использует BEGIN IMMEDIATE для правильной работы блокировок.
        
        Returns:
            Dict с данными pending_dino или None, если запись не найдена
        """
        # Используем engine.begin() для явного контроля транзакции
        # Это гарантирует BEGIN IMMEDIATE для SQLite, что необходимо для SELECT FOR UPDATE
        async with engine.begin() as conn:
            # Выполняем SELECT FOR UPDATE с блокировкой строки
            result = await conn.execute(
                select(PendingDinoStorage)
                .where(PendingDinoStorage.steam_id == steam_id)
                .with_for_update()
            )
            pending_dinos = result.scalars().all()
            
            if not pending_dinos:
                return None
            
            if len(pending_dinos) > 1:
                # Если найдено несколько записей, удаляем все и возвращаем None
                # Это предотвращает ошибку "Запущено несколько процессов сохранения динозавров"
                await conn.execute(
                    delete(PendingDinoStorage).where(PendingDinoStorage.steam_id == steam_id)
                )
                return None
            
            # Получаем данные перед удалением
            pending_dino = pending_dinos[0]
            dino_dict = PendingDinoCRUD._pending_dino_dict(pending_dino)
            
            # Удаляем запись в той же транзакции
            await conn.execute(
                delete(PendingDinoStorage).where(PendingDinoStorage.id == pending_dino.id)
            )
            
            # Транзакция автоматически коммитится при выходе из контекста
            return dino_dict

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


class ItemCRUD:
    @staticmethod
    async def get_all_items(active_only: bool = True) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            query = select(Item)
            if active_only:
                query = query.where(Item.is_active == True)
            
            result = await session.execute(query.order_by(Item.name))
            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "item_type": item.item_type.value,
                    "price": item.price,
                    "max_stack": item.max_stack,
                    "game_data": item.game_data,
                    "created_at": item.created_at
                }
                for item in result.scalars()
            ]

    @staticmethod
    async def get_item_by_id(item_id: int) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            item = await session.scalar(select(Item).where(Item.id == item_id))
            if not item:
                return None
            return {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "item_type": item.item_type.value,
                "price": item.price,
                "max_stack": item.max_stack,
                "game_data": item.game_data,
                "is_active": item.is_active,
                "created_at": item.created_at
            }

    @staticmethod
    async def create_item(
        name: str,
        description: str,
        item_type: ItemType,
        price: int,
        max_stack: int = 1,
        game_data: Optional[str] = None
    ) -> Dict[str, Any]:
        async with async_session_maker() as session:
            item = Item(
                name=name,
                description=description,
                item_type=item_type,
                price=price,
                max_stack=max_stack,
                game_data=game_data
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "item_type": item.item_type.value,
                "price": item.price,
                "max_stack": item.max_stack,
                "game_data": item.game_data,
                "created_at": item.created_at
            }

    @staticmethod
    async def update_item(item_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.execute(
                update(Item)
                .where(Item.id == item_id)
                .values(**updates)
                .returning(Item)
            )
            updated_item = result.scalars().first()
            if not updated_item:
                return None
            
            await session.commit()
            await session.refresh(updated_item)
            return {
                "id": updated_item.id,
                "name": updated_item.name,
                "description": updated_item.description,
                "item_type": updated_item.item_type.value,
                "price": updated_item.price,
                "max_stack": updated_item.max_stack,
                "game_data": updated_item.game_data,
                "is_active": updated_item.is_active,
                "created_at": updated_item.created_at
            }

    @staticmethod
    async def delete_item(item_id: int) -> bool:
        async with async_session_maker() as session:
            result = await session.execute(delete(Item).where(Item.id == item_id))
            await session.commit()
            return result.rowcount > 0


class InventoryCRUD:
    @staticmethod
    async def get_player_inventory(discord_id: int, unused_only: bool = False) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            query = (
                select(PlayerInventory, Item)
                .join(Item, PlayerInventory.item_id == Item.id)
                .where(PlayerInventory.discord_id == discord_id)
            )
            if unused_only:
                query = query.where(PlayerInventory.is_used == False)
            
            result = await session.execute(query.order_by(PlayerInventory.purchased_at.desc()))
            inventory = []
            for inv_item, item in result.fetchall():
                inventory.append({
                    "inventory_id": inv_item.id,
                    "item_id": item.id,
                    "item_name": item.name,
                    "item_description": item.description,
                    "item_type": item.item_type.value,
                    "quantity": inv_item.quantity,
                    "purchased_at": inv_item.purchased_at,
                    "used_at": inv_item.used_at,
                    "is_used": inv_item.is_used,
                    "game_data": item.game_data
                })
            return inventory

    @staticmethod
    async def add_item_to_inventory(
        discord_id: int,
        item_id: int,
        quantity: int = 1
    ) -> Dict[str, Any]:
        async with async_session_maker() as session:
            # Проверяем существование предмета
            item = await session.scalar(select(Item).where(Item.id == item_id, Item.is_active == True))
            if not item:
                raise ValueError("Item not found or inactive")
            
            # Проверяем максимальный стек
            if quantity > item.max_stack:
                raise ValueError(f"Quantity exceeds max stack of {item.max_stack}")
            
            inv_item = PlayerInventory(
                discord_id=discord_id,
                item_id=item_id,
                quantity=quantity
            )
            session.add(inv_item)
            await session.commit()
            await session.refresh(inv_item)
            
            return {
                "inventory_id": inv_item.id,
                "discord_id": inv_item.discord_id,
                "item_id": inv_item.item_id,
                "quantity": inv_item.quantity,
                "purchased_at": inv_item.purchased_at,
                "is_used": inv_item.is_used
            }

    @staticmethod
    async def use_item(inventory_id: int, discord_id: int) -> bool:
        async with async_session_maker() as session:
            inv_item = await session.scalar(
                select(PlayerInventory)
                .where(
                    PlayerInventory.id == inventory_id,
                    PlayerInventory.discord_id == discord_id,
                    PlayerInventory.is_used == False
                )
            )
            if not inv_item:
                return False
            
            inv_item.is_used = True
            inv_item.used_at = datetime.now(UTC)
            await session.commit()
            return True

    @staticmethod
    async def remove_item_from_inventory(inventory_id: int, discord_id: int) -> bool:
        async with async_session_maker() as session:
            result = await session.execute(
                delete(PlayerInventory)
                .where(
                    PlayerInventory.id == inventory_id,
                    PlayerInventory.discord_id == discord_id
                )
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def get_item_count(discord_id: int, item_id: int, unused_only: bool = True) -> int:
        async with async_session_maker() as session:
            query = select(PlayerInventory.quantity).where(
                PlayerInventory.discord_id == discord_id,
                PlayerInventory.item_id == item_id
            )
            if unused_only:
                query = query.where(PlayerInventory.is_used == False)
            
            result = await session.execute(query)
            quantities = result.scalars().all()
            return sum(quantities) if quantities else 0


class BonusCodeCRUD:
    @staticmethod
    async def create_bonus_code(
        code: str,
        description: str,
        reward_type: str,
        reward_value: str,
        max_uses: int = 1,
        expires_at: Optional[datetime] = None,
        created_by: int = 0
    ) -> Dict[str, Any]:
        async with async_session_maker() as session:
            bonus_code = BonusCode(
                code=code.upper().strip(),
                description=description,
                reward_type=reward_type,
                reward_value=reward_value,
                max_uses=max_uses,
                expires_at=expires_at,
                created_by=created_by
            )
            session.add(bonus_code)
            await session.commit()
            await session.refresh(bonus_code)
            return {
                "id": bonus_code.id,
                "code": bonus_code.code,
                "description": bonus_code.description,
                "reward_type": bonus_code.reward_type,
                "reward_value": bonus_code.reward_value,
                "max_uses": bonus_code.max_uses,
                "current_uses": bonus_code.current_uses,
                "is_active": bonus_code.is_active,
                "expires_at": bonus_code.expires_at,
                "created_at": bonus_code.created_at,
                "created_by": bonus_code.created_by
            }

    @staticmethod
    async def get_bonus_code(code: str) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            bonus_code = await session.scalar(
                select(BonusCode).where(BonusCode.code == code.upper().strip())
            )
            if not bonus_code:
                return None
            return {
                "id": bonus_code.id,
                "code": bonus_code.code,
                "description": bonus_code.description,
                "reward_type": bonus_code.reward_type,
                "reward_value": bonus_code.reward_value,
                "max_uses": bonus_code.max_uses,
                "current_uses": bonus_code.current_uses,
                "is_active": bonus_code.is_active,
                "expires_at": bonus_code.expires_at,
                "created_at": bonus_code.created_at,
                "created_by": bonus_code.created_by
            }

    @staticmethod
    async def use_bonus_code(code: str, discord_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        async with async_session_maker() as session:
            bonus_code = await session.scalar(
                select(BonusCode).where(BonusCode.code == code.upper().strip())
            )
            if not bonus_code:
                return False, "Код не найден", None
            
            if not bonus_code.is_active:
                return False, "Код неактивен", None
            
            if bonus_code.current_uses >= bonus_code.max_uses:
                return False, "Код исчерпан", None
            
            now = datetime.now(UTC)
            if bonus_code.expires_at and bonus_code.expires_at < now:
                return False, "Код истек", None
            
            # Проверяем, не использовал ли уже этот пользователь
            existing_usage = await session.scalar(
                select(BonusCodeUsage).where(
                    BonusCodeUsage.code_id == bonus_code.id,
                    BonusCodeUsage.discord_id == discord_id
                )
            )
            if existing_usage:
                return False, "Вы уже использовали этот код", None
            
            # Увеличиваем счетчик использований
            bonus_code.current_uses += 1
            
            # Записываем использование
            usage = BonusCodeUsage(
                code_id=bonus_code.id,
                discord_id=discord_id,
                reward_received=bonus_code.reward_value
            )
            session.add(usage)
            await session.commit()
            
            return True, "Код успешно использован", {
                "reward_type": bonus_code.reward_type,
                "reward_value": bonus_code.reward_value,
                "description": bonus_code.description
            }

    @staticmethod
    async def get_all_bonus_codes(active_only: bool = True) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            query = select(BonusCode)
            if active_only:
                query = query.where(BonusCode.is_active == True)
            
            result = await session.execute(query.order_by(BonusCode.created_at.desc()))
            return [
                {
                    "id": code.id,
                    "code": code.code,
                    "description": code.description,
                    "reward_type": code.reward_type,
                    "reward_value": code.reward_value,
                    "max_uses": code.max_uses,
                    "current_uses": code.current_uses,
                    "is_active": code.is_active,
                    "expires_at": code.expires_at,
                    "created_at": code.created_at,
                    "created_by": code.created_by
                }
                for code in result.scalars()
            ]

    @staticmethod
    async def update_bonus_code(code_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.execute(
                update(BonusCode)
                .where(BonusCode.id == code_id)
                .values(**updates)
                .returning(BonusCode)
            )
            updated_code = result.scalars().first()
            if not updated_code:
                return None
            
            await session.commit()
            await session.refresh(updated_code)
            return {
                "id": updated_code.id,
                "code": updated_code.code,
                "description": updated_code.description,
                "reward_type": updated_code.reward_type,
                "reward_value": updated_code.reward_value,
                "max_uses": updated_code.max_uses,
                "current_uses": updated_code.current_uses,
                "is_active": updated_code.is_active,
                "expires_at": updated_code.expires_at,
                "created_at": updated_code.created_at,
                "created_by": updated_code.created_by
            }

    @staticmethod
    async def delete_bonus_code(code_id: int) -> bool:
        async with async_session_maker() as session:
            result = await session.execute(delete(BonusCode).where(BonusCode.id == code_id))
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def get_code_usage_stats(code_id: int) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(BonusCodeUsage)
                .where(BonusCodeUsage.code_id == code_id)
                .order_by(BonusCodeUsage.used_at.desc())
            )
            return [
                {
                    "id": usage.id,
                    "discord_id": usage.discord_id,
                    "used_at": usage.used_at,
                    "reward_received": usage.reward_received
                }
                for usage in result.scalars()
            ]

    @staticmethod
    async def get_user_bonus_code_usage(discord_id: int) -> List[Dict[str, Any]]:
        """Получить историю использования бонус-кодов пользователем"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(BonusCodeUsage)
                .where(BonusCodeUsage.discord_id == discord_id)
                .order_by(BonusCodeUsage.used_at.desc())
            )
            return [
                {
                    "id": usage.id,
                    "code_id": usage.code_id,
                    "discord_id": usage.discord_id,
                    "used_at": usage.used_at,
                    "reward_received": usage.reward_received
                }
                for usage in result.scalars()
            ]


# Конфигурация бонусов по ролям
ROLE_BONUS_CONFIG = {
    "Nitro Booster": {
        "growth": 2,  # 2× рост на динозавра
        "full_restore": 2,  # 2× пополнение всех характеристик
        "nutrients": 0  # нет пополнения нутриентов
    },
    "Первопроходец": {
        "growth": 1,  # 1× рост на динозавра
        "full_restore": 0,  # нет пополнения всех характеристик
        "nutrients": 1  # 1× пополнение нутриентов
    }
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
    async def get_weekly_usage_count(discord_id: int, bonus_type: str) -> int:
        """Получить количество использований конкретного типа бонуса в текущей неделе"""
        async with async_session_maker() as session:
            now = datetime.now(UTC)
            week_start = RoleBonusCRUD.get_week_start(now)
            
            result = await session.execute(
                select(RoleBonusUsage)
                .where(RoleBonusUsage.discord_id == discord_id)
                .where(RoleBonusUsage.bonus_type == bonus_type)
                .where(RoleBonusUsage.week_start == week_start)
            )
            usages = result.scalars().all()
            return len(usages)
    
    @staticmethod
    async def get_max_bonus_uses(user_roles: List[str], bonus_type: str) -> int:
        """Получить максимальное количество использований бонуса для пользователя с учетом всех его ролей"""
        max_uses = 0
        for role_name in user_roles:
            if role_name in ROLE_BONUS_CONFIG:
                role_bonuses = ROLE_BONUS_CONFIG[role_name]
                max_uses += role_bonuses.get(bonus_type, 0)
        return max_uses
    
    @staticmethod
    async def can_use_bonus(discord_id: int, user_roles: List[str], bonus_type: str) -> Tuple[bool, int, int, Optional[str]]:
        """
        Проверить, может ли пользователь использовать конкретный тип бонуса
        
        Args:
            discord_id: ID пользователя в Discord
            user_roles: Список ролей пользователя
            bonus_type: Тип бонуса ("growth", "full_restore", "nutrients")
        
        Returns:
            (can_use, current_uses, max_uses, error_message)
        """
        # Получаем максимальное количество использований с учетом всех ролей
        max_uses = await RoleBonusCRUD.get_max_bonus_uses(user_roles, bonus_type)
        
        # Если нет доступа к этому типу бонуса
        if max_uses == 0:
            return False, 0, 0, f"У вас нет доступа к бонусу '{bonus_type}'"
        
        # Получаем текущее количество использований
        current_uses = await RoleBonusCRUD.get_weekly_usage_count(discord_id, bonus_type)
        
        if current_uses >= max_uses:
            week_start = RoleBonusCRUD.get_week_start(datetime.now(UTC))
            next_week = week_start + timedelta(days=7)
            return False, current_uses, max_uses, f"Вы уже использовали все доступные бонусы этого типа на эту неделю ({current_uses}/{max_uses}). Следующее доступно: {next_week.strftime('%d.%m.%Y')}"
        
        return True, current_uses, max_uses, None
    
    @staticmethod
    async def record_bonus_usage(discord_id: int, role_name: str, bonus_type: str) -> Dict[str, Any]:
        """Записать использование бонуса"""
        async with async_session_maker() as session:
            now = datetime.now(UTC)
            week_start = RoleBonusCRUD.get_week_start(now)
            
            usage = RoleBonusUsage(
                discord_id=discord_id,
                role_name=role_name,
                bonus_type=bonus_type,
                week_start=week_start
            )
            session.add(usage)
            await session.commit()
            await session.refresh(usage)
            
            return {
                "id": usage.id,
                "discord_id": usage.discord_id,
                "role_name": usage.role_name,
                "bonus_type": usage.bonus_type,
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

import os
from typing import Optional, Tuple, Union, List, Dict, Any

from database.crud import PlayerDinoCRUD, PendingDinoCRUD, SubscriptionCRUD
from .clicker_api import slay_dino, restore_dino
from .rcon_isle import fetch_player_by_id, PlayerData, send_dm_message

HOST = os.getenv("RCON_HOST")
PORT = int(os.getenv("RCON_PORT"))
PASSWORD = os.getenv("RCON_PASSWORD")


async def _get_player_data(discord_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    player = await PlayerDinoCRUD.get_player_info(discord_id)
    if not player:
        return None, "Нет привязки к Steam"

    steam_id = player.get("player", {}).get("steam_id", "")
    if not steam_id:
        return None, "Нет привязки к Steam"

    return player, steam_id


async def _get_isle_player(steam_id: str) -> Tuple[Optional[PlayerData], Optional[str]]:
    isle_player = await fetch_player_by_id(HOST, PORT, PASSWORD, steam_id)
    if not isle_player:
        return None, "Игрок не на сервере"
    return isle_player, None


async def save_dino(discord_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    player, steam_id = await _get_player_data(discord_id)
    if not player:
        return None, steam_id

    isle_player, error = await _get_isle_player(steam_id)
    if error:
        return None, error

    result = await PlayerDinoCRUD.add_dino(
        steam_id,
        isle_player.dino_class,
        min(int(isle_player.growth * 100), 99),
        int(isle_player.hunger * 100),
        int(isle_player.thirst * 100),
        int(isle_player.health * 100)
    )
    return result if result else (None, "Техническая ошибка. Обратитесь к администратору")


async def get_pending_dino(steam_id: str) -> Union[Dict[str, Any], Tuple[None, str]]:
    pending_dinos = await PendingDinoCRUD.get_by_steam_id(steam_id)
    if not pending_dinos:
        return None, "Динозавр для сохранения не найден"
    if len(pending_dinos) > 1:
        return None, "Запущено несколько процессов сохранения динозавров"
    return pending_dinos[0]


async def save_dino_to_db(steam_id: str, dino_class: str, growth: float) -> Tuple[
    Optional[Dict[str, Any]], Optional[str]]:
    current_dino = await get_pending_dino(steam_id)
    if isinstance(current_dino, tuple):
        return current_dino

    if dino_class not in current_dino["dino_class"]:
        return None, "Сохраняемые динозавры отличаются"

    result = await PlayerDinoCRUD.add_dino(
        steam_id,
        current_dino["dino_class"],
        min(int(current_dino["growth"]), 99),
        int(current_dino["thirst"]),
        int(current_dino["hunger"]),
        int(current_dino["health"])
    )
    return result if result else (None, "Техническая ошибка. Обратитесь к администратору")


async def del_pending_dino_by_steamid(steam_id: str) -> int:
    return await PendingDinoCRUD.delete_by_steam_id(steam_id)


async def del_pending_dino_by_discordid(discord_id: int) -> int:
    return await PendingDinoCRUD.delete_by_discord_id(discord_id)


async def check_max_limit_dino(discord_id: int):
    player, steam_id = await _get_player_data(discord_id)
    if not player:
        return None, steam_id
    max_dino = 6
    subscribe = await SubscriptionCRUD.get_active_subscription(discord_id)
    if subscribe:
        max_dino += subscribe.get("dino_slots", 0)
    if len(player.get("dinos", [])) >= max_dino:
        return None, "Превышено количество сохраняемых динозавров в слоты. Сперва удалите динозавров из слотов"
    return True


async def pending_save_dino(discord_id: int, callback_url: str) -> Tuple[Optional[bool], Optional[str]]:
    player, steam_id = await _get_player_data(discord_id)
    if not player:
        return None, steam_id

    checked = check_max_limit_dino(discord_id)
    if isinstance(checked, tuple):
        return checked

    isle_player, error = await _get_isle_player(steam_id)
    if error:
        return None, error

    await PendingDinoCRUD.cleanup_old_entries(2)

    await PendingDinoCRUD.add_pending_dino(
        steam_id, discord_id, callback_url,
        isle_player.dino_class,
        min(int(isle_player.growth * 100), 99),
        int(isle_player.hunger * 100),
        int(isle_player.thirst * 100),
        int(isle_player.health * 100)
    )
    return True


async def buy_dino(discord_id: int, dino_class: str, growth: int, hunger: int, thirst: int, health: int) -> Tuple[
    Optional[Dict[str, Any]], Optional[str]]:
    player, steam_id = await _get_player_data(discord_id)
    if not player:
        return None, steam_id

    checked = check_max_limit_dino(discord_id)
    if isinstance(checked, tuple):
        return checked

    result = await PlayerDinoCRUD.add_dino(steam_id, dino_class, growth, hunger, thirst, health)
    return result if result else (None, "Игрок не найден")


async def get_all_dinos(discord_id: int) -> Union[List[Dict[str, Any]], Tuple[None, str]]:
    player, steam_id = await _get_player_data(discord_id)
    if not player:
        return None, steam_id
    return player.get("dinos", [])


async def del_dino(discord_id: int, dino_id: int) -> Tuple[Optional[bool], Optional[str]]:
    player, steam_id = await _get_player_data(discord_id)
    if not player:
        return None, steam_id

    result = await PlayerDinoCRUD.delete_dino(steam_id, dino_id)
    return (True, None) if result else (None, "Ошибка во время удаления динозавра")


async def get_current_dino(discord_id: int) -> Union[PlayerData, Tuple[None, str]]:
    player, steam_id = await _get_player_data(discord_id)
    if not player:
        return None, steam_id

    isle_player, error = await _get_isle_player(steam_id)
    return isle_player if isle_player else (None, error)


async def kill_current_dino(discord_id: int) -> Tuple[Optional[bool], Optional[str]]:
    player, steam_id = await _get_player_data(discord_id)
    if not player:
        return None, steam_id

    result = await slay_dino(steam_id)
    if not isinstance(result, dict) or not result.get("success"):
        return None, "Игрока нет на сервере" if isinstance(result,
                                                           dict) else "Неизвестная ошибка во время убийства динозавра"
    return True


async def restore_dino_script(discord_id: int, dino_id: int) -> Tuple[Optional[bool], Optional[str]]:
    current_dino = await get_current_dino(discord_id)
    if isinstance(current_dino, tuple):
        return None, current_dino[1]

    dino = await PlayerDinoCRUD.get_dino_by_id(dino_id)
    if not dino:
        return None, "Динозавр не найден"

    if current_dino.dino_class != dino.dino_class:
        return None, "Активируемый динозавр отличается от того, что выбран сейчас в игре"
    if dino.steam_id != current_dino.player_id:
        return None, "Этот динозавр Вам не принадлежит"

    result = await restore_dino(
        current_dino.player_id,
        dino.growth, dino.hunger,
        dino.thirst, dino.health
    )

    if not isinstance(result, dict) or not result.get("success"):
        return None, "Игрока нет на сервере" if isinstance(result,
                                                           dict) else "Неизвестная ошибка во время восстановления динозавра"

    delete_result = await del_dino(discord_id, dino_id)

    await send_dm_message(HOST, PORT, PASSWORD, current_dino.player_id, "Ваш динозавр успешно активирован")
    return True

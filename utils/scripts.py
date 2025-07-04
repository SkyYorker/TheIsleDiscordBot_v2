import os

from database.crud import PlayerDinoCRUD, PendingDinoCRUD
from .clicker_api import slay_dino, restore_dino
from .rcon_isle import fetch_player_by_id, PlayerData

HOST = os.getenv("RCON_HOST")
PORT = int(os.getenv("RCON_PORT"))
PASSWORD = os.getenv("RCON_PASSWORD")


async def save_dino(discord_id: int):
    player = await PlayerDinoCRUD.get_player_info(discord_id)
    # TODO: Сделать ограничение на кол-во сохранений
    if not player:
        return None, "Нет привязки к Steam"

    steam_id = player.get("player", {}).get("steam_id", "")
    if not steam_id:
        return None, "Нет привязки к Steam"

    isle_player = await fetch_player_by_id(HOST, PORT, PASSWORD, steam_id)
    if not isle_player:
        return None, "Игрок не на сервере"

    result = await PlayerDinoCRUD.add_dino(
        steam_id,
        isle_player.dino_class,
        min(int(isle_player.growth * 100), 99),
        int(isle_player.hunger * 100),
        int(isle_player.thirst * 100),
        int(isle_player.health * 100)
    )
    if not result:
        return None, "Техническая ошибка. Обратитесь к администратору"

    return result


async def get_pending_dino(steam_id: str):
    pending_dino = await PendingDinoCRUD.get_by_steam_id(steam_id)
    if not pending_dino or len(pending_dino) == 0:
        return None, "Динозавр для сохранения не найден"
    if len(pending_dino) > 1:
        return None, "Запущено несколько процессов сохранения динозавров"
    return pending_dino[0]


async def save_dino_to_db(steam_id: str, dino_class: str, growth: float):
    current_dino = await get_pending_dino(steam_id)
    if isinstance(current_dino, tuple):
        return current_dino

    if dino_class not in current_dino["dino_class"]:
        return None, "Сохраняемые динозавры отличаются"

    result = await PlayerDinoCRUD.add_dino(
        steam_id,
        current_dino["dino_class"],
        min(int(current_dino["growth"] * 100), 99),
        int(current_dino["thirst"]),
        int(current_dino["hunger"]),
        int(current_dino["health"])
    )
    if not result:
        return None, "Техническая ошибка. Обратитесь к администратору"

    return result


async def del_pending_dino(steam_id: str):
    return await PendingDinoCRUD.delete_by_steam_id(steam_id)


async def pending_save_dino(discord_id: int, callback_url: str):
    player = await PlayerDinoCRUD.get_player_info(discord_id)
    # TODO: Сделать ограничение на кол-во сохранений
    if not player:
        return None, "Нет привязки к Steam"

    steam_id = player.get("player", {}).get("steam_id", "")
    if not steam_id:
        return None, "Нет привязки к Steam"

    isle_player = await fetch_player_by_id(HOST, PORT, PASSWORD, steam_id)
    if not isle_player:
        return None, "Игрок не на сервере"

    await PendingDinoCRUD.cleanup_old_entries(2)

    await PendingDinoCRUD.add_pending_dino(steam_id, discord_id, callback_url,
                                           isle_player.dino_class,
                                           min(int(isle_player.growth * 100), 99),
                                           int(isle_player.hunger * 100),
                                           int(isle_player.thirst * 100),
                                           int(isle_player.health * 100))

    return True


async def buy_dino(discord_id: int, dino_class, growth, hunger, thirst, health):
    player = await PlayerDinoCRUD.get_player_info(discord_id)
    # TODO: Сделать ограничение на кол-во сохранений
    if not player:
        return None, "Нет привязки к Steam"

    steam_id = player.get("player", {}).get("steam_id", "")
    if not steam_id:
        return None, "Нет привязки к Steam"

    result = await PlayerDinoCRUD.add_dino(steam_id, dino_class, growth, hunger, thirst, health)

    if not result:
        return None, "Игрок не найден"

    return result


async def get_all_dinos(discord_id: int) -> list | tuple[None, str]:
    player = await PlayerDinoCRUD.get_player_info(discord_id)
    # TODO: Сделать ограничение на кол-во сохранений
    if not player:
        return None, "Нет привязки к Steam"

    steam_id = player.get("player", {}).get("steam_id", "")
    if not steam_id:
        return None, "Нет привязки к Steam"

    return player.get("dinos", [])


async def del_dino(discord_id: int, dino_id: int):
    player = await PlayerDinoCRUD.get_player_info(discord_id)
    # TODO: Сделать ограничение на кол-во сохранений
    if not player:
        return None, "Нет привязки к Steam"

    steam_id = player.get("player", {}).get("steam_id", "")
    if not steam_id:
        return None, "Нет привязки к Steam"

    result = await PlayerDinoCRUD.delete_dino(steam_id, dino_id)
    if not result:
        return None, "Ошибка во время удаления динозавра"

    return True


async def get_current_dino(discord_id: int) -> PlayerData | tuple[None, str]:
    player = await PlayerDinoCRUD.get_player_info(discord_id)
    # TODO: Сделать ограничение на кол-во сохранений
    if not player:
        return None, "Нет привязки к Steam"

    steam_id = player.get("player", {}).get("steam_id", "")
    if not steam_id:
        return None, "Нет привязки к Steam"

    isle_player = await fetch_player_by_id(HOST, PORT, PASSWORD, steam_id)
    if not isle_player:
        return None, "Игрок не на сервере"

    return isle_player


async def kill_current_dino(discord_id: int):
    player = await PlayerDinoCRUD.get_player_info(discord_id)
    # TODO: Сделать ограничение на кол-во сохранений
    if not player:
        return None, "Нет привязки к Steam"

    steam_id = player.get("player", {}).get("steam_id", "")
    if not steam_id:
        return None, "Нет привязки к Steam"
    result = await slay_dino(steam_id)
    if not isinstance(result, dict):
        return None, "Неизвестная ошибка во время убийства динозавра"
    if not result.get("success"):
        return None, "Игрока нет на сервере"

    return True


async def restore_dino_script(discord_id: int, dino_id: int):
    current_dino = await get_current_dino(discord_id)
    if isinstance(current_dino, tuple):
        return None, current_dino[1]
    dino = await PlayerDinoCRUD.get_dino_by_id(dino_id)
    if current_dino.dino_class != dino.dino_class:
        return None, "Активируемый динозавр отличается от того, что выбран сейчас в игре"
    if dino.steam_id != current_dino.player_id:
        return None, "Этот динозавр Вам не принадлежит"
    result = await restore_dino(current_dino.player_id,
                                dino.growth, dino.hunger,
                                dino.thirst, dino.health)
    if not isinstance(result, dict):
        return None, "Неизвестная ошибка во время восстановления динозавра"
    if not result.get("success"):
        return None, "Игрока нет на сервере"

    result = await del_dino(discord_id, dino_id)

    if isinstance(result, tuple):
        return None, result[1]

    return True

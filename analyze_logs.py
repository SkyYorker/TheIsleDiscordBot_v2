import asyncio
import logging
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from utils.discord_api import edit_ephemeral_message, send_dm
from utils.scripts import save_dino_to_db, get_pending_dino, del_pending_dino_by_steamid

BOT_TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class LogFileHandler(FileSystemEventHandler):
    def __init__(self, file_path, callback, loop):
        self.file_path = file_path
        self.callback = callback
        self.position = 0
        self._update_position()
        self.last_size = self._get_file_size()
        self.loop = loop

    def _get_file_size(self):
        return os.path.getsize(self.file_path)

    def _update_position(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            f.seek(0, 2)
            self.position = f.tell()

    def on_modified(self, event):
        if event.src_path != self.file_path:
            return

        try:
            current_size = self._get_file_size()

            if current_size < self.last_size:
                logger.info("Файл был сброшен, начинаем чтение с начала.")
                self.position = 0

            self.last_size = current_size

            with open(self.file_path, "r", encoding="utf-8") as f:
                f.seek(self.position)
                while True:
                    line = f.readline()
                    if not line:
                        break
                    asyncio.run_coroutine_threadsafe(self.callback(line.strip()), self.loop)
                self.position = f.tell()
        except PermissionError as e:
            logger.error(f"Доступ к файлу запрещен: {e}")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Неизвестная ошибка при чтении файла: {e}")


def parse_log_line(line):
    if "Left The Server whilebeing safelogged" not in line:
        return None, None, None

    steamid_match = re.search(r"\[(\d{17})\]", line)
    dino_match = re.search(r"Was playing as: ([^,]+)", line)
    growth_match = re.search(r"Growth: ([\d.]+)", line)

    steamid = steamid_match.group(1) if steamid_match else None
    dino_type = dino_match.group(1) if dino_match else None
    growth = float(growth_match.group(1)) if growth_match else None

    return steamid, dino_type, growth


async def activate_dino(steamid, dino_type, growth):
    try:
        dino = await get_pending_dino(steamid)
    except Exception as e:
        logger.error(f"Ошибка при получении pending_dino для steamid={steamid}: {e}", exc_info=True)
        return None, None, "pending_error"

    if isinstance(dino, tuple):
        logger.warning(f"Ошибка при получении pending_dino: {dino[1]}")
        return None, None, "pending_tuple"

    try:
        result = await save_dino_to_db(steamid, dino_type, growth)
        if isinstance(result, tuple):
            return dino, result, "save_error"
        await del_pending_dino_by_steamid(steamid)
    except Exception as e:
        logger.error(f"Ошибка при сохранении динозавра в БД: {e}", exc_info=True)
        return dino, None, "db_exception"

    if isinstance(result, tuple):
        logger.warning(f"Ошибка при сохранении динозавра в БД: {result[1]}")
        return dino, result, "save_tuple"

    return dino, result, None


def make_activation_embed(dino_type, growth):
    return {
        "title": "Динозавр активирован!",
        "description": f"Ваш динозавр **{dino_type}** был успешно активирован.",
        "color": 0x43B581,
        "fields": [
            {
                "name": "Тип динозавра",
                "value": dino_type,
                "inline": True
            },
            {
                "name": "Рост",
                "value": f"{growth * 100:.3f}%",
                "inline": True
            }
        ],
        "footer": {
            "text": "Поздравляем с активацией!"
        }
    }


async def send_activation_embeds(bot_token, dino, dino_type, growth):
    embed = make_activation_embed(dino_type, growth)
    try:
        await edit_ephemeral_message(
            bot_token,
            dino.get("url", ""),
            "",
            embeds=[embed]
        )
    except Exception as e:
        logger.error(f"Ошибка при редактировании эфемерного сообщения: {e}", exc_info=True)

    try:
        await send_dm(
            bot_token,
            dino.get("discord_id", ""),
            "",
            embeds=[embed]
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке ЛС: {e}", exc_info=True)


async def process_line(line):
    steamid, dino_type, growth = parse_log_line(line)
    if not steamid or not dino_type or not growth:
        return None

    dino, result, error = await activate_dino(steamid, dino_type, growth)
    if error:
        return None

    await send_activation_embeds(BOT_TOKEN, dino, dino_type, growth)
    return None


def main():
    log_path = r"C:\Servers\servers\2\serverfiles\TheIsle\Saved\Logs\TheIsle-Shipping.log"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    event_handler = LogFileHandler(log_path, process_line, loop)
    observer = Observer()
    observer.schedule(event_handler, os.path.dirname(log_path), recursive=False)
    observer.start()

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        observer.stop()
    finally:
        observer.join()
        loop.stop()


if __name__ == "__main__":
    main()

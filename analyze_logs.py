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
from utils.scripts import save_dino_to_db, get_pending_dino, del_pending_dino

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


async def process_line(line):
    if "Left The Server whilebeing safelogged" not in line:
        return None

    # Пример строки:
    # [15:52][LogTheIsleJoinData]: DayBot [76561199671085032] Left The Server whilebeing safelogged, Was playing as: Diabloceratops, Gender: Male, Growth: 0.281349
    steamid_match = re.search(r"\[(\d{17})\]", line)
    dino_match = re.search(r"Was playing as: ([^,]+)", line)
    growth_match = re.search(r"Growth: ([\d.]+)", line)

    steamid = steamid_match.group(1) if steamid_match else None
    dino_type = dino_match.group(1) if dino_match else None
    growth = float(growth_match.group(1)) if growth_match else None

    logger.debug(f"Результаты парсинга: steamid={steamid}, dino_type={dino_type}, growth={growth}")

    if not steamid or not dino_type or not growth:
        logger.warning(
            f"Не удалось распарсить необходимые данные из строки: steamid={steamid}, dino_type={dino_type}, growth={growth}"
        )
        return None

    try:
        logger.info(f"Пробуем получить pending_dino для steamid={steamid}")
        dino = await get_pending_dino(steamid)
    except Exception as e:
        logger.error(f"Ошибка при получении pending_dino для steamid={steamid}: {e}", exc_info=True)
        return None

    if isinstance(dino, tuple):
        logger.warning(f"Ошибка при получении pending_dino: {dino[1]}")
        return None

    try:
        logger.info(f"Пробуем сохранить динозавра в БД: steamid={steamid}, dino_type={dino_type}, growth={growth}")
        result = await save_dino_to_db(steamid, dino_type, growth)
        if isinstance(result, tuple):
            return
        await del_pending_dino(steamid)
    except Exception as e:
        logger.error(f"Ошибка при сохранении динозавра в БД: {e}", exc_info=True)
        return None



    if isinstance(result, tuple):
        logger.warning(f"Ошибка при сохранении динозавра в БД: {result[1]}")
        return None

    try:
        logger.info(f"Пробуем отредактировать эфемерное сообщение для discord_id={dino.get('discord_id')}, url={dino.get('url')}")
        await edit_ephemeral_message(BOT_TOKEN, dino.get("url", ""), "Активация успешна")
    except Exception as e:
        logger.error(f"Ошибка при редактировании эфемерного сообщения: {e}", exc_info=True)

    try:
        logger.info(f"Пробуем отправить ЛС пользователю discord_id={dino.get('discord_id')}")
        await send_dm(BOT_TOKEN, dino.get("discord_id", ""), "Ваш динозавр успешно активирован")
    except Exception as e:
        logger.error(f"Ошибка при отправке ЛС: {e}", exc_info=True)

    logger.info(f"Успешно обработана строка: SteamID={steamid}, Dino={dino_type}, Growth={growth}")
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

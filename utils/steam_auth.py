import asyncio
import base64
import io
import logging
import os

import aiohttp
from discord import File

STEAM_AUTH_URL = os.getenv("STEAM_AUTH_URL", "").rstrip("/")
STEAM_API_KEY = os.getenv("STEAM_AUTH_API_KEY", "discord")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class SteamAuth:
    @staticmethod
    async def generate_auth_link(discord_id: int) -> dict:
        if not STEAM_AUTH_URL:
            logger.error("URL для Steam Auth не настроен")
            return {"error": "Не настроен STEAM_AUTH_URL"}

        if not discord_id:
            logger.error("Получен пустой discord_id")
            return {"error": "discord_id не может быть пустым"}

        url = f"{STEAM_AUTH_URL}/generate-link/{discord_id}"
        headers = {
            "X-API-Key": STEAM_API_KEY,
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        url,
                        headers=headers,
                        timeout=10
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Ошибка от API Steam: {resp.status} - {error_text}")
                        return {"error": f"API ошибка: {resp.status}", "details": error_text}

                    data = await resp.json()
                    logger.info(f"Успешно сгенерирована ссылка для discord_id: {discord_id}")
                    return data

        except asyncio.TimeoutError:
            logger.error(f"Таймаут при запросе к Steam API для discord_id: {discord_id}")
            return {"error": "Таймаут соединения"}

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при запросе к Steam API: {str(e)}")
            return {"error": "Ошибка сети", "details": str(e)}

        except Exception as e:
            logger.error(f"Неожиданная ошибка: {str(e)}")
            return {"error": "Внутренняя ошибка", "details": str(e)}

    @staticmethod
    def create_qrcode_file(qrcode_base64: str) -> File:
        if qrcode_base64.startswith('data:image'):
            qrcode_base64 = qrcode_base64.split(',', 1)[1]

        image_data = base64.b64decode(qrcode_base64)
        return File(io.BytesIO(image_data), filename="steam_qrcode.png")

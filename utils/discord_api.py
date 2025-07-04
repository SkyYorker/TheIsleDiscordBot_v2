import aiohttp
import logging

logger = logging.getLogger(__name__)

async def edit_ephemeral_message(bot_token: str, url: str, new_content: str, embeds = []) -> bool:
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "content": new_content,
        "flags": 64,
        "embeds": embeds
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Эфемерное сообщение по адресу {url} успешно отредактировано")
                    return True

                text = await response.text()
                logger.warning(
                    f"Не удалось отредактировать эфемерное сообщение по адресу {url}. "
                    f"Код статуса: {response.status}, Ответ: {text}"
                )
                return False
    except Exception as e:
        logger.error(f"Произошла ошибка при редактировании эфемерного сообщения по адресу {url}: {e}", exc_info=True)
        return False


async def send_dm(bot_token: str, user_id: str, message: str, embeds = []) -> bool:
    create_dm_url = "https://discord.com/api/v10/users/@me/channels"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }
    dm_payload = {"recipient_id": user_id}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(create_dm_url, headers=headers, json=dm_payload) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.warning(
                        f"Не удалось создать личный канал для пользователя {user_id}. "
                        f"Код статуса: {response.status}, Ответ: {text}"
                    )
                    return False

                resp_json = await response.json()
                channel_id = resp_json.get("id")
                if not channel_id:
                    logger.error(f"Ответ при создании ЛС не содержит 'id': {resp_json}")
                    return False

            send_message_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            message_payload = {"content": message, "embeds": embeds}

            async with session.post(send_message_url, headers=headers, json=message_payload) as response:
                if response.status == 200:
                    logger.info(f"Личное сообщение пользователю {user_id} в канале {channel_id} успешно отправлено")
                    return True

                text = await response.text()
                logger.warning(
                    f"Не удалось отправить ЛС пользователю {user_id} в канал {channel_id}. "
                    f"Код статуса: {response.status}, Ответ: {text}"
                )
                return False

    except Exception as e:
        logger.error(f"Произошла ошибка при отправке ЛС пользователю {user_id}: {e}", exc_info=True)
        return False
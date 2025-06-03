import asyncio
import logging

import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class SteamAPI:
    BASE_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"

    def __init__(self, api_key: str):
        self.api_key = api_key
        logger.info("SteamAPI initialized with API key")

    async def get_player_info(self, steam_id: str) -> dict:
        params = {
            "key": self.api_key,
            "steamids": steam_id
        }
        logger.debug(f"Requesting player info for SteamID: {steam_id}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=10) as resp:
                    data = await resp.json()
                    logger.debug(f"Received response for SteamID {steam_id}: {data}")

                    players = data.get("response", {}).get("players", [])
                    if players:
                        logger.info(f"Successfully retrieved info for SteamID: {steam_id}")
                        return players[0]
                    logger.warning(f"No player data found for SteamID: {steam_id}")
                    return {}
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Error fetching player info for SteamID {steam_id}: {str(e)}")
            return {}

    async def get_avatar_url(self, steam_id: str, size: str = "full") -> str:
        logger.debug(f"Requesting avatar for SteamID: {steam_id}, size: {size}")
        player = await self.get_player_info(steam_id)

        if not player:
            logger.warning(f"No player found for SteamID: {steam_id}, cannot get avatar")
            return ""

        if size == "small":
            avatar_url = player.get("avatar", "")
        elif size == "medium":
            avatar_url = player.get("avatarmedium", "")
        else:
            avatar_url = player.get("avatarfull", "")

        logger.debug(f"Avatar URL for SteamID {steam_id}: {avatar_url}")
        return avatar_url

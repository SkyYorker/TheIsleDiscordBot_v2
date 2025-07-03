import os

from aiohttp import ClientSession, BasicAuth

API_URL = os.getenv("CLICKER_SERVER_API_URL")
USERNAME = os.getenv("CLICKER_SERVER_USERNAME")
PASSWORD = os.getenv("CLICKER_SERVER_PASSWORD")


async def run_enter():
    async with ClientSession() as session:
        async with session.post(
                f"http://{API_URL}/run-enter",
                auth=BasicAuth(USERNAME, PASSWORD)
        ) as response:
            return await response.json()


async def restore_dino(
        steamid: str,
        growth: int,
        hunger: int,
        thirst: int,
        health: int
):
    data = {
        "steamid": steamid,
        "growth": growth,
        "hunger": hunger,
        "thirst": thirst,
        "health": health
    }
    async with ClientSession() as session:
        async with session.post(
                f"http://{API_URL}/run-restore-dino",
                json=data,
                auth=BasicAuth(USERNAME, PASSWORD)
        ) as response:
            return await response.json()


async def slay_dino(steamid: str):
    data = {"steamid": steamid}
    async with ClientSession() as session:
        async with session.post(
                f"http://{API_URL}/run-slay-dino",
                json=data,
                auth=BasicAuth(USERNAME, PASSWORD)
        ) as response:
            return await response.json()


async def set_nutrients(
        steamid: str,
        prot: float,
        carb: float,
        lipid: float
):
    data = {
        "steamid": steamid,
        "prot": prot,
        "carb": carb,
        "lipid": lipid
    }
    async with ClientSession() as session:
        async with session.post(
                f"http://{API_URL}/run-set-nutrients",
                json=data,
                auth=BasicAuth(USERNAME, PASSWORD)
        ) as response:
            return await response.json()

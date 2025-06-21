import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from gamercon_async import EvrimaRCON


@dataclass
class PlayerData:
    name: Optional[str] = None
    player_id: Optional[str] = None
    location: Optional[Dict[str, float]] = field(default_factory=dict)
    dino_class: Optional[str] = None
    growth: Optional[float] = None
    health: Optional[float] = None
    stamina: Optional[float] = None
    hunger: Optional[float] = None
    thirst: Optional[float] = None

    def __str__(self):
        return f"PlayerData(name={self.name}, player_id={self.player_id}, location={self.location}, dino_class={self.dino_class}, growth={self.growth}, health={self.health}, stamina={self.stamina}, hunger={self.hunger}, thirst={self.thirst})"


def parse_player_data(response: str) -> List[PlayerData]:
    player_blocks = re.split(
        r'(?:\[\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}\]\s*)?Name: |(?:\[\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}\]\s*)?PlayerDataName: ',
        response)
    players = []
    for block in player_blocks:
        if not block.strip():
            continue

        if not block.startswith("Name:") and not block.startswith("PlayerDataName:"):
            block = "Name: " + block

        name_match = re.search(r"Name: ([^,]+)", block)
        if not name_match:
            name_match = re.search(r"PlayerDataName: ([^,]+)", block)
        name = name_match.group(1).strip() if name_match else None

        player_id_match = re.search(r"PlayerID: (\d+)", block)
        player_id = player_id_match.group(1) if player_id_match else None

        location_match = re.search(r"Location: X=([-\d\.]+) Y=([-\d\.]+) Z=([-\d\.]+)", block)
        location = {}
        if location_match:
            location = {
                "X": float(location_match.group(1)),
                "Y": float(location_match.group(2)),
                "Z": float(location_match.group(3)),
            }

        dino_class_match = re.search(r"Class: ([^,]+)", block)
        dino_class = dino_class_match.group(1) if dino_class_match else None

        def extract_float(field: str) -> Optional[float]:
            m = re.search(rf"{field}: ([\d\.]+)", block)
            return float(m.group(1)) if m else None

        growth = extract_float("Growth")
        health = extract_float("Health")
        stamina = extract_float("Stamina")
        hunger = extract_float("Hunger")
        thirst = extract_float("Thirst")

        players.append(PlayerData(
            name=name,
            player_id=player_id,
            location=location,
            dino_class=dino_class,
            growth=growth,
            health=health,
            stamina=stamina,
            hunger=hunger,
            thirst=thirst,
        ))
    return players


def find_player_by_id(players: List[PlayerData], player_id: str) -> Optional[PlayerData]:
    for player in players:
        if player.player_id == player_id:
            return player
    return None


async def fetch_all_players(rcon_host: str, rcon_port: int, rcon_password: str) -> List[PlayerData]:
    rcon = EvrimaRCON(rcon_host, rcon_port, rcon_password)
    await rcon.connect()
    response = await rcon.send_command(b"\x02" + b"\x77" + b"\x00")
    return parse_player_data(response)


async def fetch_player_by_id(rcon_host: str, rcon_port: int, rcon_password: str, player_id: str) -> Optional[
    PlayerData]:
    all_players = await fetch_all_players(rcon_host, rcon_port, rcon_password)
    return find_player_by_id(all_players, player_id)

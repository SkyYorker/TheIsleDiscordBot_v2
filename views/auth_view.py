import os

import discord
from discord.ui import View, Button

from utils.steam_api import SteamAPI
from views.main_menu import MainMenuView

steam_api = SteamAPI(api_key=os.getenv("STEAM_API_KEY"))


class AuthView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Открыть меню", style=discord.ButtonStyle.blurple, emoji="🎮", custom_id="open_menu_button")
    async def open_menu(self, button: Button, interaction: discord.Interaction):
        is_linked = await self.check_steam_link(interaction.user.id)

        if not is_linked:
            embed = discord.Embed(
                title="❌ Steam не привязан",
                description="Чтобы пользоваться меню, привяжите свой аккаунт Steam.",
                color=discord.Color.red()
            )
            view = View()
            view.add_item(
                Button(label="Привязать Steam", url="https://example.com/link-steam", style=discord.ButtonStyle.link))
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        steam_data = await self.get_steam_data(interaction.user.id)
        view = MainMenuView(steam_data, interaction.user.id)
        await interaction.response.send_message(embed=view.embed, view=view,
                                                ephemeral=True)

    async def check_steam_link(self, user_id: int) -> bool:
        # TODO: Снять заглушку на check_steam_link (подключить к БД)
        return True

    async def get_steam_data(self, user_id: int) -> dict:
        # TODO: Снять заглушку на get_steam_data (подключить к БД)
        steam_id = "76561198329325277"
        player = await steam_api.get_player_info(steam_id)
        return {
            "username": player.get("personaname", "Unknown"),
            "avatar": player.get("avatarfull", ""),
            "steamid": steam_id
        }

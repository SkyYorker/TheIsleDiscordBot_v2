import logging

import discord
from discord.ui import View, Button, Modal, InputText

from database.crud import PlayerDinoCRUD
from utils.steam_api import steam_api
from utils.steam_auth import SteamAuth
from views.main_menu import MainMenuView

# Настройка логирования для отладки
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SteamLinkModal(Modal):
    def __init__(self, user_id: int):
        super().__init__(timeout=None, title="Привязка Steam аккаунта")
        self.user_id = user_id
        self.steamid = InputText(
            label="Введите ваш SteamID64",
            placeholder="Например: 76561198329325277",
            required=True,
            min_length=17,
            max_length=20,
        )
        self.add_item(self.steamid)

    async def callback(self, interaction: discord.Interaction):
        steam_id = self.steamid.value.strip()
        logger.info(f"Пользователь {self.user_id} пытается привязать SteamID: {steam_id}")

        if not steam_id.isdigit() or len(steam_id) < 17:
            await interaction.response.send_message(
                "❌ Неверный формат SteamID. Попробуйте снова.", ephemeral=True
            )
            return

        player_info = await steam_api.get_player_info(steam_id)
        if not player_info or not player_info.get("personaname") or player_info.get("error"):
            await interaction.response.send_message(
                "❌ Возникла ошибка при привязке. Попробуйте еще раз или обратитесь к администратору.", ephemeral=True
            )
            return

        await PlayerDinoCRUD.add_player(
            discord_id=interaction.user.id,
            steam_id=steam_id
        )

        embed = discord.Embed(
            title="✅ Аккаунт Steam привязан!",
            description=f"Ваш Steam-аккаунт [{player_info.get('personaname')}]"
                        f"(https://steamcommunity.com/profiles/{steam_id}) успешно привязан.",
            color=discord.Color.green()
        )
        embed.set_footer(text="🔗 Это окно можно скрыть. Чтобы начать пользоваться функционалом бота, нажмите кнопку "
                              "'Открыть меню' сверху.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Пользователь {self.user_id} успешно привязал SteamID {steam_id}")


class AuthView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Открыть меню", style=discord.ButtonStyle.blurple, emoji="🎮", custom_id="open_menu_button")
    async def open_menu(self, button: Button, interaction: discord.Interaction):
        logger.info(f"Пользователь {interaction.user.id} нажал 'Открыть меню'")
        is_linked = await self.check_steam_link(interaction.user.id)

        if not is_linked:
            embed = discord.Embed(
                title="❌ Steam не привязан",
                description="Чтобы пользоваться меню, привяжите свой аккаунт Steam.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, view=AuthView(), ephemeral=True)
            return

        steam_data = await steam_api.get_steam_data(interaction.user.id)
        view = MainMenuView(steam_data, interaction.user.id)
        await view.update_player_data(interaction.user.id)
        await interaction.response.send_message(embed=view.embed, view=view, ephemeral=True)

    @discord.ui.button(label="Привязать Steam", style=discord.ButtonStyle.green, custom_id="link_steam_button", row=1)
    async def link_steam(self, button: Button, interaction: discord.Interaction):
        logger.info(f"Пользователь {interaction.user.id} нажал 'Привязать Steam'")

        await interaction.response.defer(ephemeral=True)

        try:
            result = await SteamAuth.generate_auth_link(interaction.user.id)
            if "error" in result:
                logger.info(f"Произошла ошибка при привязке Steam у {interaction.user.id}")
                await interaction.followup.send(f"❌ Ошибка: {result['error']}", ephemeral=True)
                return

            auth_url = result.get("Url", "")
            qrcode_base64 = result.get("Qrcode", "")

            if not auth_url or not qrcode_base64:
                await interaction.followup.send("⚠️ Не удалось получить данные аутентификации", ephemeral=True)
                return

            embed = discord.Embed(
                title="Steam Аутентификация",
                description=f"Ссылка для входа: [Нажмите здесь]({auth_url})",
                color=discord.Color.blue()
            )
            embed.set_footer(text="QR-код действителен в течение 5 минут")

            qrcode_file = SteamAuth.create_qrcode_file(qrcode_base64)

            await interaction.followup.send(
                embed=embed,
                file=qrcode_file,
                ephemeral=True
            )

            logger.info(f"Успешно отправлена Steam аутентификация для {interaction.user}")
        except Exception as e:
            logger.error(f"Ошибка при отправке: {str(e)}")
            await interaction.followup.send("⚠️ Произошла ошибка при создании сообщения", ephemeral=True)

    async def check_steam_link(self, discord_id: int) -> bool:
        player = await PlayerDinoCRUD.get_player_info(discord_id)
        steam_id = ""
        if isinstance(player, dict):
            steam_id = player.get("player", {}).get("steam_id")
        logger.info(
            f"Проверка привязки Steam для пользователя {discord_id}: {'есть' if player and steam_id else 'нет'}")
        return player is not None and steam_id

    async def get_steam_data(self, discord_id: int) -> dict:
        player = await PlayerDinoCRUD.get_player_info(discord_id)
        if not player:
            return {}
        player = player["player"]
        steam_id = player["steam_id"]
        if not steam_id:
            return {}
        steam_info = await steam_api.get_player_info(steam_id)
        if not steam_info or not steam_info.get("personaname") or steam_info.get("error"):
            return {}
        return {
            "username": steam_info.get("personaname", "Unknown"),
            "avatar": steam_info.get("avatarfull", ""),
            "steamid": steam_id,
            "tk": player["tk"]
        }

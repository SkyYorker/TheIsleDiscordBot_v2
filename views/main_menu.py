import os

import discord
from discord.ui import View, Button

from database.crud import PlayerDinoCRUD
from utils.rcon_isle import PlayerData
from utils.scripts import get_all_dinos, get_current_dino, kill_current_dino
from views.deposit_view import DepositView
from views.dino_shop import DinoShopView
from views.dinosaurs import DinosaurSelectView, DinosaurDeleteSelectView
from views.kill_dino_confirm import KillDinoConfirmView, kill_dino_confirm_embed
from views.save_dino import SaveDinoView

LOGO_URL = os.getenv("LOGO_URL")


class KillDinoResultView(View):
    def __init__(self, main_menu_embed, main_menu_view):
        super().__init__(timeout=None)
        self.main_menu_embed = main_menu_embed
        self.main_menu_view = main_menu_view
        self.add_item(Button(
            label="Главное меню",
            style=discord.ButtonStyle.green,
            emoji="🏠",
            custom_id="back_to_main_menu",
            row=0
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        if custom_id == "back_to_main_menu":
            await interaction.response.edit_message(embed=self.main_menu_embed, view=self.main_menu_view)
        return False


class MainMenuView(View):
    def __init__(self, steam_data: dict, user_id: int):
        super().__init__(timeout=None)

        self.steam_data = steam_data
        self.user_id = user_id

        self.add_item(Button(
            label="Пополнить баланс",
            style=discord.ButtonStyle.green,
            emoji="💵",
            custom_id="deposit",
            row=0
        ))

        self.add_item(Button(
            label="Магазинчик",
            style=discord.ButtonStyle.green,
            emoji="🛒",
            custom_id="shop",
            row=0
        ))

        self.add_item(Button(
            label="Сохранить динозавра",
            style=discord.ButtonStyle.grey,
            emoji="💾",
            custom_id="save_dino",
            row=1
        ))

        self.add_item(Button(
            label="Мои динозавры",
            style=discord.ButtonStyle.blurple,
            emoji="🦖",
            custom_id="dinosaurs",
            row=1
        ))

        self.add_item(Button(
            label="Освободить динозавра",
            style=discord.ButtonStyle.red,
            emoji="🗑️",
            custom_id="delete_dino",
            row=1
        ))

        self.add_item(Button(
            label="Убить текущего динозавра",
            style=discord.ButtonStyle.red,
            emoji="💀",
            custom_id="kill_current_dino",
            row=2
        ))

        self.add_item(Button(
            label="Выйти из аккаунта",
            style=discord.ButtonStyle.red,
            emoji="🚪",
            custom_id="logout",
            row=2
        ))

        self.add_item(Button(
            label="Закрыть",
            style=discord.ButtonStyle.grey,
            emoji="❌",
            custom_id="close",
            row=3
        ))

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🔹 Профиль",
            description=(
                f"💬 **DiscordID:** `{self.user_id}`\n"
                f"👤 **Steam Никнейм:** `{self.steam_data.get('username', 'Неизвестно')}`\n"
                f"🆔 **SteamID:** `{self.steam_data.get('steamid', 'Неизвестно')}`\n"
                f"🌐 [Открыть профиль Steam](https://steamcommunity.com/profiles/{self.steam_data.get('steamid', '')})\n"
                f"\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💎 **Количество ТС:** `{self.steam_data.get('tk', 'Неизвестно')}`\n"
                f"━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.green(),
            image=LOGO_URL
        )
        embed.set_thumbnail(url=self.steam_data.get("avatar"))
        embed.set_footer(text="🔗 Используйте кнопки ниже для управления профилем")
        return embed

    async def kill_dino_confirm_callback(self, interaction: discord.Interaction, dino_data: PlayerData):
        await interaction.response.defer()

        try:
            result = await kill_current_dino(interaction.user.id)
            if result is True:
                embed = discord.Embed(
                    title="💀 Текущий динозавр убит",
                    description="Ваш текущий динозавр был убит по вашему запросу.",
                    color=discord.Color.dark_red()
                )
            else:
                # result = (None, error_message)
                embed = discord.Embed(
                    title="Ошибка",
                    description=result[1] if isinstance(result, tuple) else "Не удалось убить динозавра.",
                    color=discord.Color.orange()
                )
            kill_view = KillDinoResultView(self.embed, self)
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=kill_view)
        except Exception as e:
            error_embed = discord.Embed(
                title="Ошибка",
                description=f"Произошла ошибка при обработке запроса: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data["custom_id"]

        if custom_id == "dinosaurs":
            dinos = await get_all_dinos(interaction.user.id)
            view = DinosaurSelectView(interaction.message.embeds[0], self, dinos)
            await interaction.response.edit_message(embed=view.embed, view=view)

        elif custom_id == "save_dino":
            view = SaveDinoView(self, interaction.message.embeds[0])
            await interaction.response.edit_message(embed=view.embed, view=view)

        elif custom_id == "delete_dino":
            dinos = await get_all_dinos(interaction.user.id)
            view = DinosaurDeleteSelectView(interaction.message.embeds[0], self, dinos)
            await interaction.response.edit_message(embed=view.embed, view=view)

        elif custom_id == "logout":
            await PlayerDinoCRUD.delete_player(interaction.user.id)
            embed = discord.Embed(
                title="🔒 Аккаунт отвязан",
                description="Ваш Steam-аккаунт успешно отвязан.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)

        elif custom_id == "shop":
            view = DinoShopView(interaction.message.embeds[0], self)
            await interaction.response.edit_message(embed=view.embed, view=view)

        elif custom_id == "kill_current_dino":
            current_dino = await get_current_dino(interaction.user.id)
            if not current_dino or isinstance(current_dino, tuple):
                embed = discord.Embed(
                    title="Ошибка",
                    description=current_dino[1] if isinstance(current_dino,
                                                              tuple) else "У вас нет активного динозавра.",
                    color=discord.Color.orange()
                )
                error_view = discord.ui.View(timeout=60)
                error_view.add_item(Button(
                    label="Главное меню",
                    style=discord.ButtonStyle.green,
                    emoji="🏠",
                    custom_id="back_to_main_menu",
                    row=0
                ))
                error_view.add_item(Button(
                    label="Закрыть",
                    style=discord.ButtonStyle.grey,
                    emoji="❌",
                    custom_id="close",
                    row=0
                ))

                async def error_interaction_check(interaction: discord.Interaction) -> bool:
                    custom_id = interaction.data.get("custom_id")
                    if custom_id == "back_to_main_menu":
                        await interaction.response.edit_message(embed=self.embed, view=self)
                    elif custom_id == "close":
                        await interaction.response.defer()
                        await interaction.delete_original_response()
                    return False

                error_view.interaction_check = error_interaction_check
                await interaction.response.edit_message(embed=embed, view=error_view)
            else:
                confirm_embed = kill_dino_confirm_embed(current_dino)
                confirm_view = KillDinoConfirmView(
                    dino_data=current_dino,
                    main_menu_embed=self.embed,
                    main_menu_view=self,
                    on_confirm_callback=self.kill_dino_confirm_callback
                )
                await interaction.response.edit_message(embed=confirm_embed, view=confirm_view)
        elif custom_id == "deposit":
            deposit_view = DepositView(self.embed, self)
            await deposit_view.show_deposit_modal(interaction)
        elif custom_id == "close":
            await interaction.response.defer()
            await interaction.delete_original_response()
        return False

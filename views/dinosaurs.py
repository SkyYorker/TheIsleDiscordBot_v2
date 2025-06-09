from typing import List

import discord
from discord import Embed
from discord.ui import View, Select, Button


class DinosaurSelectView(View):
    def __init__(self, original_embed: Embed, original_view: View, dinosaurs: List[str]):
        super().__init__(timeout=180)
        self.original_view = original_view
        self.original_embed = original_embed
        self.selected_dino = None
        self.dinosaurs = dinosaurs

        # Инициализация Select с placeholder
        self.select_menu = self.create_select_menu()
        self.add_item(self.select_menu)

        self.activate_button = Button(
            label="Активировать",
            style=discord.ButtonStyle.green,
            custom_id="activate_dino",
            disabled=True,
            row=1
        )
        self.add_item(self.activate_button)

        self.add_item(Button(
            label="Вернуться",
            style=discord.ButtonStyle.red,
            custom_id="go_back",
            row=2
        ))

        self.add_item(Button(
            label="Закрыть",
            style=discord.ButtonStyle.grey,
            custom_id="close",
            row=2
        ))

    def create_select_menu(self) -> Select:
        """Создает Select с динамическим placeholder"""
        placeholder = (
            f"Вы выбрали: {self.selected_dino}"
            if self.selected_dino
            else "Выберите динозавра"
        )
        return Select(
            placeholder=placeholder,
            options=[discord.SelectOption(label=dino) for dino in self.dinosaurs],
            custom_id="select_dino"
        )

    @property
    def embed(self) -> Embed:
        """Создает embed с правилами активации динозавра"""
        embed = discord.Embed(
            title="🦖 Моя коллекция динозавров 🦕",
            description="*Перед активацией динозавра, пожалуйста, ознакомьтесь с правилами ниже:*",
            color=discord.Color.dark_green()
        )

        rules = (
            "1️⃣ **Находитесь на сервере во время активации.**\n"
            "2️⃣ **В игре выберите нужного динозавра и появитесь на острове.**\n"
            "3️⃣ **Переместитесь в безопасное место.**\n"
            "4️⃣ **Нажмите кнопку активации.**\n"
            "5️⃣ **После активации:**\n"
            "       • В течение 2 минут запрещено нападать на других игроков.\n"
            "       • Рост динозавра будет изменён.\n"
            "       • Все мутации будут сброшены."
        )

        embed.add_field(
            name="📋 Правила активации",
            value=rules,
            inline=False
        )

        embed.set_footer(
            text="ℹ️ Следуйте правилам для успешной активации динозавра",
            icon_url="https://emojicdn.elk.sh/ℹ️"
        )

        embed.set_thumbnail(url="https://emojicdn.elk.sh/🦖")

        return embed

    async def update_view(self, interaction: discord.Interaction):
        """Обновляет состояние кнопок, embed и Select"""
        self.activate_button.disabled = self.selected_dino is None

        # Удаляем старый Select и добавляем новый с обновленным placeholder
        self.remove_item(self.select_menu)
        self.select_menu = self.create_select_menu()
        self.add_item(self.select_menu)

        await interaction.response.edit_message(embed=self.embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        interaction.response: discord.InteractionResponse
        custom_id = interaction.data["custom_id"]

        if custom_id == "go_back":
            await interaction.response.edit_message(embed=self.original_embed, view=self.original_view)

        elif custom_id == "close":
            await interaction.response.defer()
            await interaction.delete_original_response()

        elif custom_id == "select_dino":
            self.selected_dino = interaction.data["values"][0]
            await self.update_view(interaction)

        elif custom_id == "activate_dino":
            if self.selected_dino:
                # TODO: Активировать динозавра
                await interaction.response.edit_message(embed=None, view=None,
                    content=f"Динозавр {self.selected_dino} успешно активирован!",
                )

            else:
                await interaction.response.send_message(
                    "Сначала выберите динозавра!",
                    ephemeral=True
                )

        return False

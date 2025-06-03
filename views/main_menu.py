import discord
from discord.ui import View, Button


class MainMenuView(View):
    def __init__(self):
        super().__init__(timeout=180)

        self.add_item(Button(
            label="Пополнить баланс",
            style=discord.ButtonStyle.green,
            emoji="💵",
            url="https://example.com/deposit",
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
            label="Удалить динозавра",
            style=discord.ButtonStyle.red,
            emoji="🗑️",
            custom_id="delete_dino",
            row=1
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

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data["custom_id"]

        if custom_id == "dinosaurs":
            await interaction.response.send_message("Список ваших динозавров...", ephemeral=True)

        elif custom_id == "save_dino":
            await interaction.response.send_message("Динозавр сохранён!", ephemeral=True)

        elif custom_id == "delete_dino":
            await interaction.response.send_message("Динозавр удалён!", ephemeral=True)

        elif custom_id == "logout":
            embed = discord.Embed(
                title="🔒 Аккаунт отвязан",
                description="Ваш Steam-аккаунт успешно отвязан.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)

        elif custom_id == "close":
            await interaction.response.defer()
            await interaction.delete_original_response()

        return False

import discord
from discord.ui import View, Button

from views.save_dino import SaveDinoView
from views.dinosaurs import DinosaurSelectView, DinosaurDeleteSelectView
from views.dino_shop import DinoShopView


class MainMenuView(View):
    def __init__(self, steam_data: dict, user_id: int):
        super().__init__(timeout=180)

        self.steam_data = steam_data
        self.user_id = user_id

        self.add_item(Button(
            label="Пополнить баланс",
            style=discord.ButtonStyle.green,
            emoji="💵",
            url="https://example.com/deposit",
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

    @property
    def embed(self) -> discord.Embed:
        """Создает и возвращает embed с текущими данными"""
        embed = discord.Embed(
            title="🔹 Профиль",
            description=(
                f"💬 **DiscordID:** `{self.user_id}`\n"
                f"👤 **Steam Никнейм:** `{self.steam_data.get('username', 'Неизвестно')}`\n"
                f"🆔 **SteamID:** `{self.steam_data.get('steamid', 'Неизвестно')}`\n"
                f"🌐 [Открыть профиль Steam](https://steamcommunity.com/profiles/{self.steam_data.get('steamid', '')})"
            ),
            color=discord.Color.green(),
            image="https://media.discordapp.net/attachments/1376971745621315726/1380547758200717394/ChatGPT_Image_6_._2025_._17_03_38.png?ex=6847928a&is=6846410a&hm=74722d1a946cebd70c1dc426f37d9e527f29e121a6f400985bb5d776418fa6af&=&format=webp&quality=lossless&width=1240&height=826"
        )
        embed.set_thumbnail(url=self.steam_data.get("avatar"))
        embed.set_footer(text="🔗 Используйте кнопки ниже для управления профилем")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data["custom_id"]

        if custom_id == "dinosaurs":
            # TODO: Заменить на процесс получения динозавров пользователя
            example_dinosaurs = ["Тираннозавр", "Трицератопс", "Велоцираптор", "Стегозавр"]

            view = DinosaurSelectView(interaction.message.embeds[0], self, example_dinosaurs)
            await interaction.response.edit_message(embed=view.embed, view=view)

        elif custom_id == "save_dino":
            view = SaveDinoView(self, interaction.message.embeds[0])
            await interaction.response.edit_message(embed=view.embed, view=view)

        elif custom_id == "delete_dino":
            example_dinosaurs = ["Тираннозавр", "Трицератопс", "Велоцираптор", "Стегозавр"]

            view = DinosaurDeleteSelectView(interaction.message.embeds[0], self, example_dinosaurs)
            await interaction.response.edit_message(embed=view.embed, view=view)

        elif custom_id == "logout":
            embed = discord.Embed(
                title="🔒 Аккаунт отвязан",
                description="Ваш Steam-аккаунт успешно отвязан.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
        elif custom_id == "shop":
            view = DinoShopView(interaction.message.embeds[0], self)
            await interaction.response.edit_message(embed=view.embed, view=view)
        elif custom_id == "close":
            await interaction.response.defer()
            await interaction.delete_original_response()
        return False

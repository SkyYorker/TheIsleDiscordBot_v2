import discord
from discord.ui import View, Button

from utils.scripts import save_dino, pending_save_dino

from data.dinosaurus import find_name_by_class, DINOSAURS

class SaveDinoView(View):
    def __init__(self, main_menu_view: View, main_menu_embed: discord.Embed):
        super().__init__(timeout=180)
        self.rules_accepted = False
        self.main_menu_view = main_menu_view
        self.main_menu_embed = main_menu_embed

        self.accept_rules_button = Button(
            label="Я согласен с правилами",
            style=discord.ButtonStyle.green,
            custom_id="accept_rules",
            row=0
        )
        self.start_save_button = Button(
            label="Начать сохранение",
            style=discord.ButtonStyle.blurple,
            custom_id="start_save",
            disabled=True,
            row=1
        )
        self.back_button = Button(
            label="В главное меню",
            style=discord.ButtonStyle.grey,
            custom_id="back_to_menu",
            row=2
        )
        self.close_button = Button(
            label="Закрыть",
            style=discord.ButtonStyle.red,
            custom_id="close",
            row=2
        )

        self.add_item(self.accept_rules_button)
        self.add_item(self.start_save_button)
        self.add_item(self.back_button)
        self.add_item(self.close_button)

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="💾 Сохранение динозавра",
            description="Перед сохранением динозавра, пожалуйста, внимательно ознакомьтесь с правилами:",
            color=discord.Color.blue()
        )
        rules = (
            "1️⃣ **Находитесь на сервере во время сохранения.**\n"
            "2️⃣ **Нажмите кнопку 'Начать сохранение'.**\n"
            "3️⃣ **Радуйтесь!**\n"
        )
        embed.add_field(
            name="📋 Инструкция по сохранению",
            value=rules,
            inline=False
        )
        embed.set_footer(
            text="ℹ️ Для продолжения подтвердите согласие с правилами",
            icon_url="https://emojicdn.elk.sh/ℹ️"
        )
        embed.set_thumbnail(url="https://emojicdn.elk.sh/🦖")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data["custom_id"]

        if custom_id == "accept_rules":
            self.rules_accepted = True
            self.start_save_button.disabled = False
            self.accept_rules_button.disabled = True
            await interaction.response.edit_message(embed=self.embed, view=self)

        elif custom_id == "start_save":
            callback_url = (f"https://discord.com/api/v10/webhooks/{interaction.application_id}"
                            f"/{interaction.token}/messages/@original")
            result = await pending_save_dino(interaction.user.id, callback_url)
            if not result or isinstance(result, tuple):
                await interaction.response.edit_message(
                    content=f"Ошибка: {result[1]}",
                    view=None,
                    embed=None
                )
                return True

            embed = discord.Embed(
                title="Процесс сохранения динозавра начался!",
                description="Укройтесь в безопасном месте, затем нажмите H, чтобы уйти в сон",
                color=discord.Color.green()
            )

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=None
            )

        elif custom_id == "back_to_menu":
            await interaction.response.edit_message(embed=self.main_menu_embed, view=self.main_menu_view)

        elif custom_id == "close":
            await interaction.response.defer()
            await interaction.delete_original_response()

        return False
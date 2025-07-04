import asyncio
import datetime

import discord
from discord.ui import View, Button

from utils.scripts import pending_save_dino, del_pending_dino_by_discordid


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

    async def start_save_timeout(self, interaction: discord.Interaction):
        await asyncio.sleep(120)
        if "успешно активирован" in interaction.message.content:
            return

        await del_pending_dino_by_discordid(interaction.user.id)
        await interaction.response.edit_message(
            content="⏰ Время на сохранение истекло!",
            ephemeral=True,
            view=None,
            embeds=None
        )

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="💾 Сохранение динозавра",
            description="Перед сохранением динозавра, пожалуйста, внимательно ознакомьтесь с правилами:",
            color=discord.Color.blue()
        )
        rules = (
            "1️⃣ **Находитесь на сервере во время сохранения.**\n"
            "2️⃣ **Нажмите кнопку 'Начать сохранение'. Затем у вас будет 2 минуты, чтобы выполнить следующие пункты**\n"
            "3️⃣ **Перейдите в режим отдыха в игре (Клавиша H)**\n"
            "4️⃣ **Ждите уведомления от бота о сохранении динозавра**\n"
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
                reason = result[1] if isinstance(result, tuple) and len(
                    result) > 1 else "Не удалось сохранить динозавра."
                embed = discord.Embed(
                    title="❌ Ошибка сохранения",
                    description=reason,
                    color=discord.Color.red()
                )
                await interaction.followup.edit_message(
                    interaction.message.id,
                    embed=embed,
                    view=None,
                    content=None
                )
                return False

            now = datetime.datetime.now(datetime.timezone.utc)

            two_minutes_later = now + datetime.timedelta(minutes=2)
            embed = discord.Embed(
                title="Процесс сохранения динозавра начался!",
                description="Укройтесь в безопасном месте, затем перейдите в режим отдыха в игре (Клавиша H)\n"
                            "Затем ждите уведомления от бота об успешном сохранении.",
                color=discord.Color.green()
            )

            embed.add_field(
                name="⏳ До отмены сохранения осталось...",
                value=f"<t:{int(two_minutes_later.timestamp())}:R>",
                inline=False
            )

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=None
            )
            asyncio.create_task(self.start_save_timeout(interaction))


        elif custom_id == "back_to_menu":
            await interaction.response.edit_message(embed=self.main_menu_embed, view=self.main_menu_view)

        elif custom_id == "close":
            await interaction.response.defer()
            await interaction.delete_original_response()

        return False

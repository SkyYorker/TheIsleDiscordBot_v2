import logging
import os

import discord
from discord.ext import commands
from discord.ext import tasks

from views.auth_view import AuthView

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('bot.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

LOGO_URL = os.getenv("LOGO_URL")


class MainMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.menu_message_id = 1395526823135150141
        self.menu_channel_id = 1431019870086234235
        self.menu_embed = self._create_menu_embed()
        self.refresh_auth_view.start()

    def _create_menu_embed(self):
        embed = discord.Embed(
            title="Добро пожаловать в TAPKIN SUPREME BOT",
            description="""🦖 В этом боте вы найдете: **автоматизированный магазин и систему слотов.** В будущем функционал бота будет значительно расти.

💠 Чтобы начать пользоваться ботом, пройдите авторизацию (кнопка "Привязать Steam"), если ещё не прошли, после чего нажмите **"Открыть меню"**!""",
            color=discord.Color.blue(),
        )

        if LOGO_URL:
            embed.set_image(url=LOGO_URL)

        return embed

    def cog_unload(self):
        self.refresh_auth_view.cancel()

    @commands.slash_command(name="setup_menu", description="Обновить сообщение с меню")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def setup_menu(self, ctx):
        logger.info(f"Команда setup_menu вызвана пользователем {ctx.author} в канале {ctx.channel}")

        try:
            channel = self.bot.get_channel(self.menu_channel_id)
            if not channel:
                await ctx.respond("Канал с указанным ID не найден!", ephemeral=True)
                return

            message = await channel.fetch_message(self.menu_message_id)
            await message.edit(embed=self.menu_embed, view=AuthView())

            logger.info(f"Сообщение {self.menu_message_id} успешно обновлено")
            await ctx.respond("Меню успешно обновлено!", ephemeral=True)

        except discord.NotFound:
            await ctx.respond("Сообщение с указанным ID не найдено!", ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"Ошибка при обновлении сообщения: {e}")
            await ctx.respond("Не удалось обновить сообщение!", ephemeral=True)

    @tasks.loop(hours=1)
    async def refresh_auth_view(self):
        try:
            logger.debug("Начинаем обновление view")

            channel = self.bot.get_channel(self.menu_channel_id)
            if not channel:
                logger.warning(f"Канал с ID {self.menu_channel_id} не найден")
                return

            try:
                message = await channel.fetch_message(self.menu_message_id)
            except discord.NotFound:
                logger.warning(f"Сообщение с меню (ID: {self.menu_message_id}) было удалено")
                return

            await message.edit(embed=self.menu_embed, view=AuthView())
            logger.info(f"View и embed успешно обновлены для сообщения {message.id} в канале {channel.name}")

        except discord.HTTPException as e:
            logger.error(f"HTTP ошибка при обновлении view: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обновлении view: {e}")

    @refresh_auth_view.before_loop
    async def before_refresh_auth_view(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(MainMenuCog(bot))

import os

import discord
from discord.ext import commands

from views.auth_view import AuthView

LOGO_URL = os.getenv("LOGO_URL")


class MainMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="setup_menu", description="Отправить кнопку 'Открыть меню'")
    @commands.has_permissions(administrator=True)
    async def setup_menu(self, ctx):
        embed = discord.Embed(
            title="Добро пожаловать в TAPKIN SUPREME BOT",
            description="""🦖 В этом боте вы найдете: **автоматизированный магазин и систему слотов.** В будущем функционал бота будет значительно расти.

💠 Чтобы начать пользоваться ботом, пройдите авторизацию (кнопка "Привязать Steam"), если ещё не прошли, после чего нажмите **"Открыть меню"**!""",
            color=discord.Color.blue(),
            image=LOGO_URL
        )
        await ctx.send(embed=embed, view=AuthView())
        await ctx.respond("Кнопка отправлена!", ephemeral=True)


def setup(bot):
    bot.add_cog(MainMenuCog(bot))

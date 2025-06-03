import discord
from discord.ext import commands

from views.auth_view import AuthView


class MainMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="setup_menu", description="Отправить кнопку 'Открыть меню'")
    @commands.has_permissions(administrator=True)
    async def setup_menu(self, ctx):
        embed = discord.Embed(
            title="🔹 Меню пользователя",
            description="Нажмите кнопку ниже, чтобы открыть меню.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=AuthView())
        await ctx.respond("Кнопка отправлена!", ephemeral=True)


def setup(bot):
    bot.add_cog(MainMenuCog(bot))

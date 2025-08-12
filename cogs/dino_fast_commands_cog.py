import discord
from discord import Option
from discord.ext import commands

from utils.scripts import restore_dino


class DinoFastCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="restore_dino",
        description="Выдать рост/голод/здоровье/жажду игроку"
    )
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def setup_menu(
            self,
            ctx: discord.ApplicationContext,
            steamid: Option(str, description="SteamID64 игрока (17 цифр)"),
            growth: Option(int, description="Рост"),
            hunger: Option(int, description="Голод"),
            thirst: Option(int, description="Жажда"),
            health: Option(int, description="Здоровье")
    ):
        await ctx.defer(ephemeral=True)

        try:
            result = await restore_dino(steamid, growth, hunger, thirst, health)
        except Exception as e:
            embed = discord.Embed(
                title="Ошибка!",
                description=f"Произошла ошибка при попытке выдать характеристики:\n```{e}```",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        status = result.get("status")
        message = result.get("message", "")

        if status == "success":
            embed = discord.Embed(
                title="✅ Восстановление динозавра",
                description="Динозавр успешно восстановлен!",
                color=discord.Color.green()
            )
            embed.add_field(name="SteamID", value=steamid, inline=True)
            embed.add_field(name="Рост", value=str(growth), inline=True)
            embed.add_field(name="Голод", value=str(hunger), inline=True)
            embed.add_field(name="Жажда", value=str(thirst), inline=True)
            embed.add_field(name="Здоровье", value=str(health), inline=True)
            if message:
                embed.add_field(name="Сообщение", value=message, inline=False)
        else:
            embed = discord.Embed(
                title="❌ Не удалось восстановить динозавра",
                description=message or "Произошла неизвестная ошибка.",
                color=discord.Color.red()
            )
            embed.add_field(name="SteamID", value=steamid, inline=True)

        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(DinoFastCommandsCog(bot))

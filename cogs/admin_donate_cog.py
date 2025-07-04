import discord
from discord import Option
from discord.ext import commands

from database.crud import DonationCRUD


class AdminDonateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="give_tk",
        description="Выдать ТК пользователю"
    )
    @commands.has_permissions(administrator=True)
    async def give_tk(
            self,
            ctx: discord.ApplicationContext,
            user: Option(discord.Member, "Выберите пользователя"),
            amount: Option(int, "Количество ТК для выдачи", min_value=1)
    ):
        discord_id = user.id
        user_tk = await DonationCRUD.add_tk(discord_id, amount)
        if user_tk is None:
            await ctx.respond(f"❌ Пользователь с Discord ID `{discord_id}` не найден в базе данных.", ephemeral=True)
            return
        await ctx.respond(
            f"✅ Выдано {amount} ТК пользователю {user.mention} (Discord ID `{discord_id}`). Теперь у него {user_tk['tk']} ТК.",
            ephemeral=True
        )

    @commands.slash_command(
        name="take_tk",
        description="Отобрать ТК у пользователя"
    )
    @commands.has_permissions(administrator=True)
    async def take_tk(
            self,
            ctx: discord.ApplicationContext,
            user: Option(discord.Member, "Выберите пользователя"),
            amount: Option(int, "Количество ТК для изъятия", min_value=1)
    ):
        discord_id = user.id
        user_tk = await DonationCRUD.remove_tk(discord_id, amount)
        if user_tk is None:
            await ctx.respond(f"❌ Пользователь с Discord ID `{discord_id}` не найден в базе данных.", ephemeral=True)
            return
        await ctx.respond(
            f"✅ Изъято {amount} ТК у пользователя {user.mention} (Discord ID `{discord_id}`). Теперь у него {user_tk['tk']} ТК.",
            ephemeral=True
        )


def setup(bot):
    bot.add_cog(AdminDonateCog(bot))

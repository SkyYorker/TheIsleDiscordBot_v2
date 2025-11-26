import discord
from discord import Option
from discord.ext import commands
import asyncio

from utils.scripts import get_current_dino
from utils.clicker_api import restore_dino as clicker_restore_dino, set_nutrients


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
            result = await clicker_restore_dino(steamid, growth, hunger, thirst, health)
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

    @commands.slash_command(
        name="restore_all",
        description="Полное восстановление всех характеристик динозавра (HP, голод, жажда, нутриенты)"
    )
    @commands.has_any_role("Admin", "Moderator", "PLUS", "PREMIUM", "SUPREME")
    async def restore_all_stats(self, ctx: discord.ApplicationContext):
        """
        Полностью восстанавливает все характеристики динозавра через Clicker API:
        - Здоровье (HP)
        - Голод
        - Жажда
        - Нутриенты (белки, углеводы, жиры)
        
        Примечание: Рост динозавра сохраняется текущим, не изменяется.
        """
        
        await ctx.defer(ephemeral=False)
        
        # Получаем steam_id пользователя
        from database.crud import PlayerDinoCRUD
        player_info = await PlayerDinoCRUD.get_player_info(ctx.author.id)
        if not player_info:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Ваш Steam аккаунт не привязан к боту. Используйте команду привязки аккаунта.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        steam_id = player_info.get("player", {}).get("steam_id")
        if not steam_id:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Ваш Steam аккаунт не привязан к боту.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔄 Полное восстановление динозавра",
            description=f"Восстановление всех характеристик через Clicker API",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="📋 Восстанавливаемые характеристики",
            value="• ❤️ Здоровье (HP) - 100\n• 🍖 Голод - 100\n• 💧 Жажда - 100\n• 🥩 Нутриенты (белки, углеводы, жиры) - 100",
            inline=False
        )
        
        await ctx.respond(embed=embed)
        
        success_count = 0
        total_operations = 4
        errors = []
        
        # 1. Получаем текущий рост динозавра, чтобы не менять его
        try:
            current_dino = await get_current_dino(ctx.author.id)
            if isinstance(current_dino, tuple):
                error_msg = current_dino[1]
                embed = discord.Embed(
                    title="❌ Ошибка",
                    description=f"Не удалось получить данные динозавра: {error_msg}",
                    color=discord.Color.red()
                )
                await ctx.edit(embed=embed)
                return
            
            # Сохраняем текущий рост (в процентах 0-100)
            current_growth = int(current_dino.growth * 100) if current_dino.growth else 0
            embed.add_field(
                name="ℹ️ Информация",
                value=f"Текущий рост сохранен: {current_growth}%",
                inline=False
            )
            await ctx.edit(embed=embed)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get current dino: {e}")
            current_growth = 0
        
        await asyncio.sleep(0.5)
        
        # 2. Восстанавливаем основные характеристики через Clicker API
        try:
            result = await clicker_restore_dino(
                steam_id,
                growth=current_growth,
                hunger=100,
                thirst=100,
                health=100
            )
            
            if isinstance(result, dict) and result.get("success"):
                success_count += 3
                embed.add_field(
                    name="✅ Основные характеристики восстановлены",
                    value="Здоровье, голод и жажда установлены на максимум через Clicker API",
                    inline=False
                )
            else:
                error_msg = result.get("message", "Неизвестная ошибка") if isinstance(result, dict) else "Ошибка API"
                errors.append(f"Восстановление характеристик: {error_msg}")
                embed.add_field(
                    name="⚠️ Ошибка восстановления характеристик",
                    value=f"Ошибка: {error_msg}",
                    inline=False
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Clicker API restore_dino failed: {e}")
            errors.append(f"Восстановление характеристик: {str(e)}")
            embed.add_field(
                name="⚠️ Ошибка Clicker API",
                value=f"Ошибка: {str(e)[:100]}",
                inline=False
            )
        
        await ctx.edit(embed=embed)
        await asyncio.sleep(0.5)
        
        # 3. Выдаем нутриенты через Clicker API
        try:
            nutrients_result = await set_nutrients(steam_id, 100.0, 100.0, 100.0)
            
            if isinstance(nutrients_result, dict) and nutrients_result.get("success"):
                success_count += 1
                embed.add_field(
                    name="✅ Нутриенты выданы",
                    value="Белки, углеводы и жиры установлены на максимум через Clicker API",
                    inline=False
                )
            else:
                error_msg = nutrients_result.get("message", "Неизвестная ошибка") if isinstance(nutrients_result, dict) else "Ошибка API"
                errors.append(f"Нутриенты: {error_msg}")
                embed.add_field(
                    name="⚠️ Нутриенты не выданы",
                    value=f"Ошибка: {error_msg}",
                    inline=False
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Clicker API set_nutrients failed: {e}")
            errors.append(f"Нутриенты: {str(e)}")
            embed.add_field(
                name="⚠️ Ошибка выдачи нутриентов",
                value=f"Ошибка: {str(e)[:100]}",
                inline=False
            )
        
        # Финальное сообщение
        embed.clear_fields()
        if success_count == total_operations:
            embed.color = discord.Color.green()
            embed.add_field(
                name="✅ Восстановление завершено успешно",
                value=f"**Успешно восстановлено:** {success_count}/{total_operations} характеристик\n\n"
                      f"✅ Здоровье (HP) - 100\n"
                      f"✅ Голод - 100\n"
                      f"✅ Жажда - 100\n"
                      f"✅ Нутриенты (белки, углеводы, жиры) - 100\n\n"
                      f"Рост сохранен: {current_growth}%",
                inline=False
            )
        elif success_count > 0:
            embed.color = discord.Color.orange()
            embed.add_field(
                name="⚠️ Частичное восстановление",
                value=f"**Восстановлено:** {success_count}/{total_operations} характеристик\n\n"
                      f"{'✅' if success_count >= 3 else '❌'} Основные характеристики (здоровье, голод, жажда)\n"
                      f"{'✅' if success_count == 4 else '❌'} Нутриенты\n\n"
                      f"**Ошибки:**\n" + "\n".join(f"• {e}" for e in errors[:3]),
                inline=False
            )
        else:
            embed.color = discord.Color.red()
            embed.add_field(
                name="❌ Восстановление не удалось",
                value=f"**Ошибки:**\n" + "\n".join(f"• {e}" for e in errors[:5]) + "\n\n"
                      f"Проверьте:\n"
                      f"• Игрок должен быть онлайн на сервере\n"
                      f"• Настройки Clicker API в .env файле\n"
                      f"• Попробуйте использовать команды отдельно",
                inline=False
            )
        
        await ctx.edit(embed=embed)


def setup(bot):
    bot.add_cog(DinoFastCommandsCog(bot))

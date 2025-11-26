import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

import logging

# Используем основной токен
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    print("[ERROR] Не найден DISCORD_TOKEN в .env файле!")
    exit(1)

TOKEN_TO_USE = DISCORD_TOKEN

from database.crud import init_models

from views.auth_view import AuthView

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)  # Изменено с WARNING на INFO для более подробных логов
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='a')  # Изменено на 'a' (append) чтобы не перезаписывать
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Также добавим вывод в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())


@bot.event
async def on_ready():
    bot.add_view(AuthView())
    logger.info(f"Бот {bot.user} готов!")
    logger.info(f"ID бота: {bot.user.id}")
    logger.info(f"Загружено расширений: {len(bot.extensions)}")
    logger.info(f"Загружено команд: {len(bot.commands)}")
    print(f"Бот {bot.user} готов!")
    print(f"Загружено расширений: {len(bot.extensions)}")
    print(f"Загружено команд: {len(bot.commands)}")
    
    # Выводим список всех слэш-команд
    slash_commands = [cmd for cmd in bot.application_commands if isinstance(cmd, discord.SlashCommand)]
    logger.info(f"Загружено слэш-команд: {len(slash_commands)}")
    print(f"Загружено слэш-команд: {len(slash_commands)}")
    for cmd in slash_commands:
        logger.info(f"  - /{cmd.name}")
        print(f"  - /{cmd.name}")

@bot.event
async def on_connect():
    logger.info("Бот подключился к Discord Gateway")

@bot.event
async def on_disconnect():
    logger.warning("Бот отключился от Discord Gateway")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Ошибка в событии {event}: {args}", exc_info=True)

@bot.event
async def on_application_command_error(ctx, error):
    """Обработка ошибок слэш-команд"""
    logger.error(f"Ошибка в команде {ctx.command.name}: {error}")
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond("❌ У вас нет прав для выполнения этой команды!", ephemeral=True)
    elif isinstance(error, commands.MissingRole):
        await ctx.respond("❌ У вас нет необходимой роли для выполнения этой команды!", ephemeral=True)
    else:
        await ctx.respond(f"❌ Произошла ошибка: {str(error)}", ephemeral=True)

# Загружаем расширения перед запуском бота
bot.load_extension("cogs.dino_fast_commands_cog")
bot.load_extension("cogs.main_menu_cog")
bot.load_extension("cogs.admin_donate_cog")
# bot.load_extension("cogs.subscription_tasks_cog")

asyncio.run(init_models())
bot.run(TOKEN_TO_USE)

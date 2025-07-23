import os
import logging
from typing import Optional

import discord
from discord.ext import tasks

from database.crud import SubscriptionCRUD, DonationCRUD
from database.models import SubscriptionTier, SUBSCRIPTION_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("подписки.log", encoding="utf-8")
    ]
)

logger = logging.getLogger("подписки")

GUILD_ID = int(os.getenv("GUILD_ID"))


class SubscriptionTasks:
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.subscription_check.start()
        logger.info("Задачи по подпискам запущены")

    def cog_unload(self):
        self.subscription_check.cancel()
        logger.info("Задачи по подпискам остановлены")

    @tasks.loop(hours=1)
    async def subscription_check(self):
        logger.info("Запуск проверки подписок...")
        await self.check_expiring_subscriptions()
        await self.process_expired_subscriptions()

    async def check_expiring_subscriptions(self):
        expiring_subs = await SubscriptionCRUD.get_expiring_subscriptions()
        logger.info(f"Найдено {len(expiring_subs)} подписок, истекающих через 24 часа")

        for sub in expiring_subs:
            try:
                user = await self.bot.get_or_fetch_user(sub['player_id'])
                if not user:
                    logger.warning(f"Пользователь {sub['player_id']} не найден")
                    continue

                message = (
                    f"Ваша подписка **{sub['tier']}** истекает через 24 часа. "
                    "Она будет автоматически продлена." if sub['auto_renewal'] else
                    "Пожалуйста, продлите подписку вручную."
                )
                await user.send(f"⚠️ {message}")
                logger.info(f"Уведомление отправлено пользователю {sub['player_id']}")

            except Exception as e:
                logger.error(f"Ошибка уведомления пользователя {sub['player_id']}: {str(e)}")

    async def process_expired_subscriptions(self):
        expired_subs = await SubscriptionCRUD.get_expired_subscriptions()
        logger.info(f"Обработка {len(expired_subs)} истекших подписок")

        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            logger.warning(f"Сервер {GUILD_ID} не найден")
            return

        for sub in expired_subs:
            try:
                if sub['auto_renewal'] and await self.try_auto_renew(sub):
                    continue

                await self.disable_subscription(guild, sub)

            except Exception as e:
                logger.error(f"Ошибка обработки подписки {sub['id']}: {str(e)}")

    async def try_auto_renew(self, sub: dict) -> bool:
        tier = SubscriptionTier[sub['tier']]
        price = SUBSCRIPTION_CONFIG[tier]['price']

        if not await DonationCRUD.check_balance_by_discordid(sub['player_id'], price):
            logger.info(f"Недостаточно средств для автопродления у пользователя {sub['player_id']}")
            return False

        await DonationCRUD.remove_tk(sub['player_id'], price)
        await SubscriptionCRUD.renew_subscription(sub['id'])

        user = await self.bot.get_or_fetch_user(sub['player_id'])
        if user:
            await user.send(f"✅ Подписка **{sub['tier']}** автоматически продлена!")

        logger.info(f"Подписка {sub['id']} автоматически продлена")
        return True

    async def disable_subscription(self, guild: discord.Guild, sub: dict):
        await SubscriptionCRUD.expire_subscription(sub['id'])
        logger.info(f"Подписка {sub['id']} отключена")

        member = await guild.fetch_member(sub['player_id'])
        if not member:
            logger.warning(f"Участник {sub['player_id']} не найден на сервере")
            return

        tier = SubscriptionTier[sub['tier']]
        role_id = SUBSCRIPTION_CONFIG[tier].get('discord_role_id')
        if role_id:
            role = guild.get_role(int(role_id))
            if role and role in member.roles:
                await member.remove_roles(role)
                logger.info(f"Роль {role_id} удалена у пользователя {member.id}")

        user = await self.bot.get_or_fetch_user(sub['player_id'])
        if user:
            await user.send(f"❌ Подписка **{sub['tier']}** истекла")
            logger.info(f"Уведомление об истечении отправлено пользователю {sub['player_id']}")
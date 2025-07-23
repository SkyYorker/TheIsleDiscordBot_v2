import logging
from datetime import UTC

import discord
from discord.ui import View, Button

from database.crud import SubscriptionCRUD, DonationCRUD
from database.models import SubscriptionTier, SUBSCRIPTION_CONFIG

logger = logging.getLogger(__name__)


class SubscriptionManagementView(View):
    def __init__(self, main_menu_embed, main_menu_view, user_id):
        super().__init__(timeout=None)
        self.main_menu_embed = main_menu_embed
        self.main_menu_view = main_menu_view
        self.user_id = user_id
        self._active_sub = None

        for tier in SubscriptionTier:
            self.add_item(Button(
                label=f"Подписка {tier.name}",
                style=discord.ButtonStyle.blurple,
                custom_id=f"subscribe_{tier.name.lower()}",
                row=0,
                disabled=False
            ))

        self.add_item(Button(
            label="Включить автопродление",
            style=discord.ButtonStyle.green,
            custom_id="toggle_auto_renew",
            row=1,
            disabled=True
        ))

        self.add_item(Button(
            label="Назад",
            style=discord.ButtonStyle.grey,
            emoji="⬅️",
            custom_id="back_to_main",
            row=2
        ))

    async def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🔹 Управление подпиской",
            description="Выберите уровень подписки или управляйте текущей подпиской",
            color=discord.Color.blue()
        )

        self._active_sub = await SubscriptionCRUD.get_active_subscription_by_discord_id(self.user_id)

        for item in self.children:
            if item.custom_id and item.custom_id.startswith("subscribe_"):
                item.disabled = self._active_sub is not None
            elif item.custom_id == "toggle_auto_renew":
                if self._active_sub:
                    item.disabled = False
                    item.label = "Отключить автопродление" if self._active_sub[
                        'auto_renewal'] else "Включить автопродление"
                    item.style = discord.ButtonStyle.red if self._active_sub[
                        'auto_renewal'] else discord.ButtonStyle.green
                else:
                    item.disabled = True

        if self._active_sub:
            expiration_date = self._active_sub['expiration_date']
            if expiration_date.tzinfo is None:
                expiration_date = expiration_date.replace(tzinfo=UTC)

            timestamp = int(expiration_date.timestamp())
            time_left_str = f"Истекает <t:{timestamp}:R>"

            embed.add_field(
                name="Текущая подписка",
                value=f"**{self._active_sub['tier']}** ({time_left_str})",
                inline=False
            )
            embed.add_field(
                name="Автопродление",
                value="✅ Включено" if self._active_sub['auto_renewal'] else "❌ Выключено",
                inline=False
            )
            embed.add_field(
                name="Информация",
                value="❕ У вас уже есть активная подписка. Новую можно оформить только после истечения текущей.",
                inline=False
            )

        for tier in SubscriptionTier:
            config = SUBSCRIPTION_CONFIG[tier]
            embed.add_field(
                name=f"{tier.name} - {config['price']} ТС",
                value=f"• +{config['dino_slots']} слот(а/ов) для динозавров\n"
                      f"• Роль <@&{config['discord_role_id']}>",
                inline=False
            )

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")

        if custom_id == "back_to_main":
            await interaction.response.edit_message(embed=self.main_menu_embed, view=self.main_menu_view)
            return True

        if custom_id == "toggle_auto_renew":
            if not self._active_sub:
                self._active_sub = await SubscriptionCRUD.get_active_subscription_by_discord_id(self.user_id)
                if not self._active_sub:
                    await interaction.response.defer()
                    return False

            new_state = not self._active_sub['auto_renewal']
            await SubscriptionCRUD.update_subscription(
                self._active_sub['id'],
                {'auto_renewal': new_state}
            )

            self._active_sub = await SubscriptionCRUD.get_active_subscription_by_discord_id(self.user_id)

            await interaction.response.edit_message(
                embed=await self.get_embed(),
                view=self
            )
            return True

        if custom_id.startswith("subscribe_"):
            for item in self.children:
                if item.custom_id == custom_id and item.disabled:
                    await interaction.response.defer()
                    return False

            tier_name = custom_id.split("_")[1].upper()
            tier = SubscriptionTier[tier_name]
            confirm_view = SubscriptionConfirmView(
                tier=tier,
                main_menu_embed=self.main_menu_embed,
                main_menu_view=self.main_menu_view,
                management_view=self,
                user_id=self.user_id
            )
            await interaction.response.edit_message(
                embed=await confirm_view.get_embed(),
                view=confirm_view
            )
            return True

        return False


class SubscriptionConfirmView(View):
    def __init__(self, tier, main_menu_embed, main_menu_view, management_view, user_id):
        super().__init__(timeout=None)
        self.tier = tier
        self.main_menu_embed = main_menu_embed
        self.main_menu_view = main_menu_view
        self.management_view = management_view
        self.user_id = user_id
        self.config = SUBSCRIPTION_CONFIG[tier]

        self.add_item(Button(
            label="Подтвердить покупку",
            style=discord.ButtonStyle.green,
            custom_id="confirm_purchase",
            row=0
        ))

        self.add_item(Button(
            label="Назад",
            style=discord.ButtonStyle.grey,
            emoji="⬅️",
            custom_id="back_to_management",
            row=1
        ))
        self.add_item(Button(
            label="Главное меню",
            style=discord.ButtonStyle.grey,
            emoji="🏠",
            custom_id="back_to_main",
            row=1
        ))

    async def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🔹 Подтверждение подписки {self.tier.name}",
            description=f"Вы уверены, что хотите приобрести подписку {self.tier.name} за {self.config['price']} ТС?",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Преимущества:",
            value=f"• +{self.config['dino_slots']} слотов для динозавров\n"
                  f"• Автоматическое продление\n"
                  f"• Роль <@&{self.config['discord_role_id']}>\n"
                  f"• Другие бонусы...",
            inline=False
        )

        embed.add_field(
            name="Срок действия:",
            value="30 дней",
            inline=False
        )

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")

        if custom_id == "back_to_management":
            await interaction.response.edit_message(
                embed=await self.management_view.get_embed(),
                view=self.management_view
            )
            return True

        if custom_id == "back_to_main":
            await self.main_menu_view.update_player_data(interaction.user.id)
            await interaction.response.edit_message(embed=self.main_menu_view.embed, view=self.main_menu_view)
            return True

        if custom_id == "confirm_purchase":
            active_sub = await SubscriptionCRUD.get_active_subscription_by_discord_id(self.user_id)
            if active_sub:
                embed = discord.Embed(
                    title="Ошибка",
                    description="У вас уже есть активная подписка. Новую можно оформить только после истечения текущей.",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=self)
                return True

            balance = await DonationCRUD.get_tk(self.user_id)
            if balance < self.config['price']:
                embed = discord.Embed(
                    title="Ошибка",
                    description="Недостаточно ТС для покупки подписки",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=self)
                return True

            sub = await SubscriptionCRUD.add_subscription_by_discord_id(
                discord_id=self.user_id,
                tier=self.tier,
                duration_days=30
            )

            await DonationCRUD.remove_tk(self.user_id, self.config['price'])

            try:
                role_id = self.config['discord_role_id']
                if role_id:
                    member = interaction.guild.get_member(self.user_id)
                    if member:
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            await member.add_roles(role)
            except Exception as e:
                logger.error(f"Ошибка при выдаче роли: {e}", exc_info=True)

            success_embed = discord.Embed(
                title="Подписка активирована!",
                description=f"Вы успешно приобрели подписку {self.tier.name}",
                color=discord.Color.green()
            )
            success_embed.add_field(
                name="Срок действия",
                value=f"до {sub['expiration_date'].strftime('%d.%m.%Y')}",
                inline=False
            )
            success_embed.add_field(
                name="Полученные бонусы",
                value=f"• Роль <@&{self.config['discord_role_id']}>",
                inline=False
            )

            await interaction.response.edit_message(embed=success_embed, view=self.main_menu_view)
            return True

        return False

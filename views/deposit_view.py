import discord
from discord.ui import View, Button, Modal, InputText

from utils.unitpay import UnitPayUrlGenerator


class DepositView(View):
    def __init__(self, main_menu_embed, main_menu_view):
        super().__init__(timeout=None)
        self.main_menu_embed = main_menu_embed
        self.main_menu_view = main_menu_view

    @staticmethod
    def create_deposit_modal() -> Modal:
        modal = Modal(title="Пополнение баланса")
        modal.add_item(InputText(
            label="Сумма пополнения",
            placeholder="Введите сумму в рублях (только цифры)",
            min_length=1,
            max_length=10
        ))
        return modal

    async def create_deposit_embed(self, amount: int, payment_url: str) -> discord.Embed:
        embed = discord.Embed(
            title="💳 Пополнение баланса",
            description=f"Вы собираетесь пополнить баланс на сумму **{amount}₽**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Инструкция",
            value=f"Нажмите кнопку 'Пополнить' ниже, чтобы перейти к оплате, либо перейдите по ссылке вручную\n"
                  f"{payment_url}",
            inline=False
        )
        return embed

    async def show_error_embed(self, interaction: discord.Interaction, error_message: str):
        error_embed = discord.Embed(
            title="❌ Ошибка",
            description=error_message,
            color=discord.Color.red()
        )
        error_view = View(timeout=None)
        error_view.add_item(Button(
            label="Попробовать снова",
            style=discord.ButtonStyle.green,
            custom_id="retry_deposit"
        ))
        error_view.add_item(Button(
            label="Главное меню",
            style=discord.ButtonStyle.blurple,
            custom_id="back_to_main_menu"
        ))

        async def error_interaction_check(interaction: discord.Interaction) -> bool:
            custom_id = interaction.data.get("custom_id")
            if custom_id == "retry_deposit":
                await self.show_deposit_modal(interaction)
            elif custom_id == "back_to_main_menu":
                await interaction.response.edit_message(
                    embed=self.main_menu_embed,
                    view=self.main_menu_view
                )
            return False

        error_view.interaction_check = error_interaction_check
        await interaction.response.edit_message(embed=error_embed, view=error_view)

    async def show_deposit_modal(self, interaction: discord.Interaction):
        modal = self.create_deposit_modal()

        async def modal_callback(interaction: discord.Interaction):
            amount_str = modal.children[0].value

            if not amount_str.isdigit():
                await self.show_error_embed(
                    interaction,
                    "Пожалуйста, введите только число без пробелов и других символов."
                )
                return

            amount = int(amount_str)

            if amount < 1:
                await self.show_error_embed(
                    interaction,
                    "Минимальная сумма пополнения - 1 рубль."
                )
                return

            payment_url = UnitPayUrlGenerator.generate_redirect_url(amount=amount,
                                                                    account=f"{interaction.user.id}_discord",
                                                                    description="Вы пополняете счёт для Tapkin Evrima Discord Bot")

            embed = await self.create_deposit_embed(amount, payment_url)
            view = View(timeout=None)

            view.add_item(Button(
                label="Пополнить",
                style=discord.ButtonStyle.green,
                url=payment_url
            ))

            view.add_item(Button(
                label="Главное меню",
                style=discord.ButtonStyle.blurple,
                custom_id="back_to_main_menu"
            ))

            async def view_interaction_check(interaction: discord.Interaction) -> bool:
                if interaction.data.get("custom_id") == "back_to_main_menu":
                    await interaction.response.edit_message(
                        embed=self.main_menu_embed,
                        view=self.main_menu_view
                    )
                return False

            view.interaction_check = view_interaction_check

            await interaction.response.edit_message(embed=embed, view=view)

        modal.callback = modal_callback
        await interaction.response.send_modal(modal)

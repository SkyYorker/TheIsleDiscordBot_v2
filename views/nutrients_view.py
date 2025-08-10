import discord
from discord.ui import View, Button

from database.crud import DonationCRUD
from utils.scripts import give_nutrients, give_food
from utils.steam_api import steam_api


class OtherServicesView(View):
    def __init__(self, shop_view):
        super().__init__(timeout=None)
        self.shop_view = shop_view

        self.handlers = {
            "refill_hunger_thirst": {
                "label": "Пополнение желудка и жажды",
                "action": give_food,
                "tk_cost": 30,
                "success_msg": "Еда/Вода Вашего динозавра успешно восполнены по максимуму",
                "error_msg": "Не удалось выдать еду/воду динозавру."
            },
            "refill_nutrients": {
                "label": "Пополнение нутриентов",
                "action": give_nutrients,
                "tk_cost": 60,
                "success_msg": "Нутриенты Вашего динозавра успешно восполнены по максимуму",
                "error_msg": "Не удалось выдать нутриенты динозавру."
            }
        }

        for custom_id, data in self.handlers.items():
            self.add_item(Button(
                label=data.get("label") + f" ({data.get('tk_cost')} ТС)",
                style=discord.ButtonStyle.blurple,
                custom_id=custom_id,
                row=0
            ))

        # self.add_item(Button(
        #     label="Пополнение желудка и жажды",
        #     style=discord.ButtonStyle.blurple,
        #     custom_id="refill_hunger_thirst",
        #     row=0
        # ))
        #
        # self.add_item(Button(
        #     label="Пополнение нутриентов",
        #     style=discord.ButtonStyle.blurple,
        #     custom_id="refill_nutrients",
        #     row=0
        # ))

        self.add_item(Button(
            label="Главное меню",
            style=discord.ButtonStyle.grey,
            custom_id="back_to_main_menu",
            row=1
        ))

    async def process_with_tk(self, interaction: discord.Interaction, total_price: int):
        discord_id = interaction.user.id
        has_enough_tk = await DonationCRUD.check_balance(discord_id, total_price)

        if not has_enough_tk:
            error_embed = discord.Embed(
                title="❌ Недостаточно ТC",
                description=f"У вас недостаточно ТC для покупки услуги.\n"
                            f"Требуется: {total_price} ТС\n"
                            f"Ваш баланс: {await DonationCRUD.get_tk(discord_id)} ТC",
                color=discord.Color.red()
            )
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=error_embed,
                                                    view=self.shop_view)
            return False

        result = await DonationCRUD.remove_tk(interaction.user.id, total_price)

        if result != 0:
            return True
        return False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        await interaction.response.defer()

        if custom_id in self.handlers:
            handler = self.handlers[custom_id]
            result = await handler["action"](interaction.user.id)

            if not result:
                await self._send_error(interaction, handler["error_msg"], result)
                return

            result = await self.process_with_tk(interaction, handler["tk_cost"])

            if not result:
                await self._send_error(interaction, handler["error_msg"], result)
                return

            embed = discord.Embed(
                title="Успех!",
                description=handler["success_msg"],
                color=discord.Color.dark_red()
            )
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=None)

        elif custom_id == "back_to_main_menu":
            from views.main_menu import MainMenuView
            steam_data = await steam_api.get_steam_data(interaction.user.id)
            view = MainMenuView(steam_data, interaction.user.id)
            await view.update_player_data(interaction.user.id)
            await interaction.followup.edit_message(interaction.message.id, embed=view.embed, view=view, content=None)

        return False

    async def _send_error(self, interaction: discord.Interaction, default_msg: str, result: any):
        embed = discord.Embed(
            title="Ошибка",
            description=result[1] if isinstance(result, tuple) else default_msg,
            color=discord.Color.orange()
        )
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=None)
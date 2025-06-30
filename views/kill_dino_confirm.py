import discord
from discord.ui import View, Button

from data.dinosaurus import find_name_by_class, DINOSAURS
from utils.rcon_isle import PlayerData


class KillDinoConfirmView(View):
    def __init__(self, dino_data: dict, main_menu_embed: discord.Embed, main_menu_view: View, on_confirm_callback):
        super().__init__(timeout=60)
        self.dino_data = dino_data
        self.main_menu_embed = main_menu_embed
        self.main_menu_view = main_menu_view
        self.on_confirm_callback = on_confirm_callback

        self.add_item(Button(
            label="Подтвердить убийство",
            style=discord.ButtonStyle.red,
            emoji="💀",
            custom_id="confirm_kill",
            row=0
        ))
        self.add_item(Button(
            label="Главное меню",
            style=discord.ButtonStyle.green,
            emoji="🏠",
            custom_id="back_to_main_menu",
            row=0
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        if custom_id == "confirm_kill":
            await self.on_confirm_callback(interaction, self.dino_data)
        elif custom_id == "back_to_main_menu":
            await interaction.response.edit_message(embed=self.main_menu_embed, view=self.main_menu_view)
        return False


def kill_dino_confirm_embed(dino_data: PlayerData) -> discord.Embed:
    dino_name = find_name_by_class(dino_data.dino_class)
    dino_image = DINOSAURS.get(dino_name, {}).get("image")
    embed = discord.Embed(
        title="Подтверждение убийства динозавра",
        description=f"Вы действительно хотите убить текущего динозавра?\n\n"
                    f"**Вид:** {dino_name}\n"
                    f"**Рост:** {dino_data.growth}%\n"
                    f"**Голод:** {dino_data.hunger}%\n"
                    f"**Жажда:** {dino_data.thirst}%",
        color=discord.Color.red()
    )
    embed.set_image(url=dino_image)
    embed.set_footer(text="Это действие необратимо!")
    return embed

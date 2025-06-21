import discord
from discord.ui import View, Select, Button
from typing import Optional, Dict, List

DINOSAUR_SHOP_DATA = {
    "Плотоядные": [
        ("Дейнозух", 270),
        ("Омнираптор", 100),
        ("Дилофозавр", 120),
        ("Цератозавр", 250),
        ("Геррерозавр", 70),
        ("Трооднон", 30),
        ("Карнотвар", 200),
        ("Птеранодон", 25),
    ],
    "Травоядные": [
        ("Стегозавр", 270),
        ("Трицератопс", 270),
        ("Тенонтозавр", 170),
        ("Пахицелафозавр", 130),
        ("Диаблоцератопс", 250),
        ("Дриозавр", 20),
        ("Майязавр", 220),
        ("Гипсилофодон", 10),
    ],
    "Всеядные": [
        ("Галлимимус", 90),
        ("Бэйпяозавр", 40),
    ]
}

class DinoShopView(View):
    def __init__(self, main_menu_embed: discord.Embed, main_menu_view: View):
        super().__init__(timeout=180)
        self.main_menu_view = main_menu_view
        self.main_menu_embed = main_menu_embed

        self.selected_category: Optional[str] = None
        self.selected_dino: Optional[str] = None
        self.selected_price: Optional[int] = None

        self.category_select = self.create_category_select()
        self.dino_select = self.create_dino_select()
        self.buy_button = Button(
            label="Купить",
            style=discord.ButtonStyle.green,
            custom_id="buy_dino",
            disabled=True,
            row=2
        )
        self.back_button = Button(
            label="В главное меню",
            style=discord.ButtonStyle.grey,
            custom_id="back_to_menu",
            row=3
        )
        self.close_button = Button(
            label="Закрыть",
            style=discord.ButtonStyle.red,
            custom_id="close",
            row=3
        )

        self.add_item(self.category_select)
        self.add_item(self.dino_select)
        self.add_item(self.buy_button)
        self.add_item(self.back_button)
        self.add_item(self.close_button)

    def create_category_select(self) -> Select:
        return Select(
            placeholder="Выберите категорию",
            options=[
                discord.SelectOption(label=cat) for cat in DINOSAUR_SHOP_DATA.keys()
            ],
            custom_id="select_category",
            row=0
        )

    def create_dino_select(self) -> Select:
        options = []
        if self.selected_category:
            for dino, price in DINOSAUR_SHOP_DATA[self.selected_category]:
                label = f"{dino} — {price} ТС"
                options.append(discord.SelectOption(label=label, value=dino))
        return Select(
            placeholder="Выберите динозавра",
            options=options if options else [discord.SelectOption(label="Сначала выберите категорию", value="none", default=True, description="")],
            custom_id="select_dino",
            disabled=not self.selected_category,
            row=1
        )

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🛒 Магазин динозавров",
            description="Выберите категорию и динозавра для покупки.",
            color=discord.Color.gold()
        )
        if self.selected_category:
            embed.add_field(
                name="Категория",
                value=f"**{self.selected_category}**",
                inline=True
            )
        if self.selected_dino and self.selected_price is not None:
            embed.add_field(
                name="Динозавр",
                value=f"**{self.selected_dino}**\nЦена: **{self.selected_price} ТС**",
                inline=True
            )
        embed.set_footer(text="💡 После выбора динозавра нажмите 'Купить'")
        embed.set_thumbnail(url="https://emojicdn.elk.sh/🦖")
        return embed

    async def update_view(self, interaction: discord.Interaction):
        self.remove_item(self.dino_select)
        self.dino_select = self.create_dino_select()
        self.add_item(self.dino_select)
        self.buy_button.disabled = not (self.selected_dino and self.selected_price is not None)
        await interaction.response.edit_message(embed=self.embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        if custom_id == "select_category":
            self.selected_category = interaction.data["values"][0]
            self.selected_dino = None
            self.selected_price = None
            await self.update_view(interaction)
        elif custom_id == "select_dino":
            if self.selected_category:
                dino_label = interaction.data["values"][0]
                for dino, price in DINOSAUR_SHOP_DATA[self.selected_category]:
                    if dino == dino_label:
                        self.selected_dino = dino
                        self.selected_price = price
                        break
            await self.update_view(interaction)
        elif custom_id == "buy_dino":
            if self.selected_dino and self.selected_price is not None:
                await interaction.response.edit_message(
                    content=f"Вы купили динозавра **{self.selected_dino}** за **{self.selected_price} ТС**!",
                    embed=None,
                    view=None
                )
            else:
                await interaction.response.send_message(
                    "Сначала выберите динозавра!",
                    ephemeral=True
                )
        elif custom_id == "back_to_menu":
            await interaction.response.edit_message(embed=self.main_menu_embed, view=self.main_menu_view)
        elif custom_id == "close":
            await interaction.response.defer()
            await interaction.delete_original_response()
        return False
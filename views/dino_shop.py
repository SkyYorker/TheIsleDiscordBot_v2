from typing import Optional, List

import discord
from discord.ui import View, Select, Button

from data.dinosaurus import DINOSAURS, CATEGORY_EMOJIS, find_name_by_class


def get_dinos_by_category(category: str) -> List[tuple[str, int]]:
    return [(name, data["price"]) for name, data in DINOSAURS.items()
            if data.get("category") == category and data.get("price") is not None]


def dino_characteristics_embed(dino_name: str) -> discord.Embed:
    """Создает embed с подробными характеристиками динозавра."""
    details = DINOSAURS.get(dino_name)
    if not details:
        return discord.Embed(
            title="Ошибка",
            description="Информация о динозавре не найдена.",
            color=discord.Color.red()
        )
    embed = discord.Embed(
        title=f"🦖 Характеристики: {dino_name}",
        color=discord.Color.green(),
        description=f"**Цена:** {details.get('price', '?')} ТС"
    )
    embed.add_field(name="Категория", value=f"{CATEGORY_EMOJIS.get(details.get('category'), '')} {details.get('category', '?')}", inline=True)
    embed.add_field(name="В группе разрешено", value=details.get("group_limit", "?"), inline=True)
    embed.add_field(name="Макс. вес", value=details.get("weight", '?'), inline=True)
    embed.add_field(name="Скорость бега", value=details.get("speed", '?'), inline=True)
    embed.add_field(name="Сила укуса", value=details.get("bite", '?'), inline=True)
    embed.set_image(url=details.get("image", ""))
    embed.set_footer(text="💡 Используйте кнопки ниже для дальнейших действий.")
    return embed


class DinoPurchaseConfirmationView(View):
    def __init__(self, shop_view: 'DinoShopView', main_menu_embed: discord.Embed, main_menu_view: View):
        super().__init__(timeout=120)
        self.shop_view = shop_view
        self.main_menu_embed = main_menu_embed
        self.main_menu_view = main_menu_view

        self.add_item(Button(
            label="Вернуться",
            style=discord.ButtonStyle.blurple,
            custom_id="back_to_shop",
            row=1
        ))
        self.add_item(Button(
            label="Главное меню",
            style=discord.ButtonStyle.grey,
            custom_id="back_to_menu",
            row=1
        ))
        self.add_item(Button(
            label="Закрыть",
            style=discord.ButtonStyle.red,
            custom_id="close",
            row=1
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        if custom_id == "back_to_shop":
            await interaction.response.edit_message(embed=self.shop_view.embed, view=self.shop_view)
        elif custom_id == "back_to_menu":
            await interaction.response.edit_message(embed=self.main_menu_embed, view=self.main_menu_view)
        elif custom_id == "close":
            await interaction.response.defer()
            await interaction.delete_original_response()
        return False


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
        categories = set(data["category"] for data in DINOSAURS.values() if data.get("category"))
        placeholder = (
            f"Выбрана категория: {self.selected_category}"
            if self.selected_category else "Выберите категорию"
        )
        return Select(
            placeholder=placeholder,
            options=[
                discord.SelectOption(
                    label=f"{cat}",
                    value=cat,
                    emoji=CATEGORY_EMOJIS[cat]
                ) for cat in sorted(categories)
            ],
            custom_id="select_category",
            row=0
        )
    def create_dino_select(self) -> Select:
        options = []
        if self.selected_category:
            for dino, price in get_dinos_by_category(self.selected_category):
                label = f"{dino} — {price} ТС"
                options.append(discord.SelectOption(label=label, value=DINOSAURS[dino]["class_name"]))
        placeholder = (
            f"Выбран динозавр: {self.selected_dino}"
            if self.selected_dino else "Выберите динозавра"
        )
        return Select(
            placeholder=placeholder,
            options=options if options else [
                discord.SelectOption(label="Сначала выберите категорию", value="none", default=True, description="")],
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
            emoji = CATEGORY_EMOJIS.get(self.selected_category, "")
            embed.add_field(
                name="Категория",
                value=f"{emoji} **{self.selected_category}**",
                inline=True
            )
        if self.selected_dino and self.selected_price is not None:
            embed.add_field(
                name="Динозавр",
                value=f"**{self.selected_dino}**\nЦена: **{self.selected_price} ТС**",
                inline=True
            )
            details = DINOSAURS.get(self.selected_dino)
            if details:
                embed.add_field(
                    name="В группе разрешено",
                    value=details.get("group_limit", "?"),
                    inline=True
                )
                embed.add_field(
                    name="Макс. вес",
                    value=details['weight'],
                    inline=False
                )
                embed.add_field(name="Скорость бега", value=details["speed"], inline=False)
                embed.add_field(name="Сила укуса", value=details["bite"], inline=False)
                embed.set_image(url=details["image"])
        embed.set_footer(text="💡 После выбора динозавра нажмите 'Купить'")
        embed.set_thumbnail(url="https://emojicdn.elk.sh/🦖")
        return embed

    async def update_view(self, interaction: discord.Interaction):
        self.remove_item(self.category_select)
        self.remove_item(self.dino_select)
        self.category_select = self.create_category_select()
        self.dino_select = self.create_dino_select()
        self.add_item(self.category_select)
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
                dino_class = interaction.data["values"][0]
                self.selected_dino = find_name_by_class(dino_class)
                self.selected_price = DINOSAURS.get(self.selected_dino).get("price", 0)
            await self.update_view(interaction)
        elif custom_id == "buy_dino":
            if self.selected_dino and self.selected_price is not None:
                confirmation_view = DinoPurchaseConfirmationView(self, self.main_menu_embed, self.main_menu_view)
                await interaction.response.edit_message(
                    content=f"Вы купили динозавра **{self.selected_dino}** за **{self.selected_price} ТС**!",
                    embed=dino_characteristics_embed(self.selected_dino),
                    view=confirmation_view
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
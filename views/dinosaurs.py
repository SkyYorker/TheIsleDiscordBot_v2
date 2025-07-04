from typing import List, Optional, Dict, Any

import discord
from discord import Embed
from discord.ui import View, Select, Button

from data.dinosaurus import find_name_by_class, DINOSAURS, CATEGORY_EMOJIS
from utils.scripts import restore_dino_script, del_dino


def filter_dinos_by_category(dinos: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
    return [
        d for d in dinos
        if DINOSAURS.get(find_name_by_class(d["dino_class"]), {}).get("category") == category
    ]


class DinosaurSelectView(View):
    def __init__(self, original_embed: Embed, original_view: View, dinosaurs: List[Dict[str, Any]]):
        super().__init__(timeout=180)
        self.original_view = original_view
        self.original_embed = original_embed
        self.dinosaurs = dinosaurs
        self.selected_category: Optional[str] = None
        self.selected_dino: Optional[str] = None
        self.limited = False
        self.state = "category"
        self.dinos_in_cat: List[Dict[str, Any]] = []

        self.build_category_buttons()

    def build_category_buttons(self):
        self.clear_items()
        if not self.dinosaurs:
            self.state = "empty"
            self.add_item(Button(
                label="В главное меню",
                style=discord.ButtonStyle.grey,
                custom_id="go_main_menu",
                row=0
            ))
        else:
            self.state = "category"
            category_counts = {category: 0 for category in CATEGORY_EMOJIS.keys()}
            for d in self.dinosaurs:
                category = DINOSAURS.get(find_name_by_class(d["dino_class"]), {}).get("category")
                if category in category_counts:
                    category_counts[category] += 1

            for label, emoji in CATEGORY_EMOJIS.items():
                count = category_counts.get(label, 0)
                disabled = count == 0
                self.add_item(Button(
                    label=f"{label} ({count} шт.)",
                    style=discord.ButtonStyle.blurple,
                    emoji=emoji,
                    custom_id=f"category_{label}",
                    disabled=disabled,
                    row=0
                ))

            self.add_item(Button(
                label="В главное меню",
                style=discord.ButtonStyle.grey,
                custom_id="go_main_menu",
                row=1
            ))
            self.add_item(Button(
                label="Назад",
                style=discord.ButtonStyle.red,
                custom_id="go_back",
                row=1
            ))

    def build_dino_select(self, category: str):
        self.clear_items()
        self.selected_category = category
        self.selected_dino = None
        self.dinos_in_cat = filter_dinos_by_category(self.dinosaurs, category)
        if not self.dinos_in_cat:
            self.state = "empty_category"
            self.add_item(Button(
                label="нет динозавров",
                style=discord.ButtonStyle.grey,
                disabled=True,
                row=0
            ))
            self.add_item(Button(
                label="Назад",
                style=discord.ButtonStyle.red,
                custom_id="go_back",
                row=1
            ))
            self.add_item(Button(
                label="В главное меню",
                style=discord.ButtonStyle.grey,
                custom_id="go_main_menu",
                row=1
            ))
        else:
            self.state = "dino"
            self.select_menu = self.create_select_menu()
            self.add_item(self.select_menu)
            self.activate_button = Button(
                label="Активировать",
                style=discord.ButtonStyle.green,
                custom_id="activate_dino",
                disabled=True,
                row=1
            )
            self.add_item(self.activate_button)
            self.add_item(Button(
                label="Назад",
                style=discord.ButtonStyle.red,
                custom_id="go_back",
                row=2
            ))
            self.add_item(Button(
                label="В главное меню",
                style=discord.ButtonStyle.grey,
                custom_id="go_main_menu",
                row=2
            ))

    def create_select_menu(self) -> Select:
        options = []
        saved_dino_class = ""
        for dino in self.dinosaurs[:25]:
            dino_name = find_name_by_class(dino["dino_class"])
            if DINOSAURS[dino_name]["category"] != self.selected_category:
                continue
            id = dino["id"]
            growth = dino["growth"]
            hunger = dino["hunger"]
            thirst = dino["thirst"]
            health = dino["health"]
            if str(id) == self.selected_dino:
                saved_dino_class = dino_name
            label = f"({id}) {dino_name} (Рост {growth}, Голод: {hunger}, Жажда: {thirst}, HP: {health})"
            options.append(discord.SelectOption(label=label, value=str(id)))
        placeholder = (
            f"Вы выбрали: {saved_dino_class}"
            if saved_dino_class
            else "Выберите динозавра для активации"
        )
        self.limited = len(self.dinos_in_cat) > 25
        return Select(
            placeholder=placeholder,
            options=options,
            custom_id="select_dino"
        )

    @property
    def embed(self) -> Embed:
        if self.state == "empty":
            return discord.Embed(
                title="🦖 Коллекция пуста",
                description="У вас нет сохранённых динозавров.\n\nНажмите 'Назад' или 'В главное меню'.",
                color=discord.Color.orange()
            )
        elif self.state == "category":
            return discord.Embed(
                title="Выберите категорию динозавров",
                description="Нажмите на одну из кнопок ниже, чтобы выбрать категорию.",
                color=discord.Color.blue()
            )
        elif self.state == "empty_category":
            return discord.Embed(
                title=f"🦖 Нет динозавров категории: {self.selected_category}",
                description="В этой категории нет сохранённых динозавров.\n\nНажмите 'Назад' или 'В главное меню'.",
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title=f"🦖 Динозавры категории: {self.selected_category}",
                description="*Перед активацией динозавра, пожалуйста, ознакомьтесь с правилами ниже:*",
                color=discord.Color.dark_green()
            )
            rules = (
                "1️⃣ **Находитесь на сервере во время активации.**\n"
                "2️⃣ **В игре выберите нужного динозавра и появитесь на острове.**\n"
                "3️⃣ **Переместитесь в безопасное место.**\n"
                "4️⃣ **Нажмите кнопку активации.**\n"
                "5️⃣ **После активации:**\n"
                "       • В течение 2 минут запрещено нападать на других игроков.\n"
                "       • Рост, голод, жажда динозавра будет изменены.\n"
                "       • Мутации динозавра не сохраняются. Перевыбрать их Вы сможете самостоятельно при получении "
                "самого роста в игре при активации слота"
            )
            embed.add_field(
                name="📋 Правила активации",
                value=rules,
                inline=False
            )
            if self.limited:
                embed.add_field(
                    name="ℹ️ Ограничение",
                    value="Показаны только первые 25 динозавров. Используйте фильтры или удалите лишних для отображения остальных.",
                    inline=False
                )
            embed.set_footer(
                text="ℹ️ Следуйте правилам для успешной активации динозавра",
                icon_url="https://emojicdn.elk.sh/ℹ️"
            )
            embed.set_thumbnail(url="https://emojicdn.elk.sh/🦖")
            return embed

    async def update_view(self, interaction: discord.Interaction):
        if self.state in ("empty", "empty_category"):
            await interaction.response.edit_message(embed=self.embed, view=self)
            return
        self.activate_button.disabled = self.selected_dino is None
        self.remove_item(self.select_menu)
        self.select_menu = self.create_select_menu()
        self.add_item(self.select_menu)
        await interaction.response.edit_message(embed=self.embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        interaction.response: discord.InteractionResponse
        custom_id = interaction.data.get("custom_id")
        if custom_id.startswith("category_"):
            category = custom_id.replace("category_", "")
            self.build_dino_select(category)
            await interaction.response.edit_message(embed=self.embed, view=self)
        elif custom_id == "go_main_menu":
            await interaction.response.edit_message(embed=self.original_embed, view=self.original_view)
        elif custom_id == "go_back":
            self.selected_category = None
            self.selected_dino = None
            self.build_category_buttons()
            await interaction.response.edit_message(embed=self.embed, view=self)
        elif custom_id == "select_dino":
            self.selected_dino = interaction.data["values"][0]
            await self.update_view(interaction)
        elif custom_id == "activate_dino":
            if self.selected_dino:
                # TODO: Переделать процесс активации
                wait_embed = discord.Embed(
                    title="⏳ Пожалуйста, подождите",
                    description="Происходит активация выбранного динозавра...\nЭто может занять несколько секунд.",
                    color=discord.Color.blurple()
                )
                await interaction.response.edit_message(
                    embed=wait_embed,
                    view=None
                )
                result = await restore_dino_script(interaction.user.id, self.selected_dino)
                if result is True:
                    embed = discord.Embed(
                        title="✅ Успешная активация",
                        description=f"Динозавр `{self.selected_dino}` успешно активирован!",
                        color=discord.Color.green()
                    )
                else:
                    reason = result[1] if isinstance(result, tuple) and len(
                        result) > 1 else "Не удалось активировать динозавра."
                    embed = discord.Embed(
                        title="❌ Ошибка активации",
                        description=reason,
                        color=discord.Color.red()
                    )
                await interaction.followup.edit_message(
                    interaction.message.id,
                    embed=embed,
                    view=None,
                    content=None
                )
            else:
                await interaction.response.send_message(
                    "Сначала выберите динозавра!",
                    ephemeral=True
                )
        return False


class DinosaurDeleteSelectView(View):
    def __init__(self, original_embed: Embed, original_view: View, dinosaurs: List[Dict[str, Any]]):
        super().__init__(timeout=180)
        self.original_view = original_view
        self.original_embed = original_embed
        self.selected_dino: Optional[str] = None
        self.dinosaurs = dinosaurs

        if not self.dinosaurs:
            self.add_item(Button(
                label="Вернуться",
                style=discord.ButtonStyle.red,
                custom_id="go_back",
                row=1
            ))
            self.empty = True
        else:
            self.empty = False
            self.select_menu = self.create_select_menu()
            self.add_item(self.select_menu)

            self.delete_button = Button(
                label="Удалить",
                style=discord.ButtonStyle.danger,
                custom_id="delete_dino",
                disabled=True,
                row=1
            )
            self.add_item(self.delete_button)

            self.add_item(Button(
                label="Вернуться",
                style=discord.ButtonStyle.red,
                custom_id="go_back",
                row=2
            ))

            self.add_item(Button(
                label="Закрыть",
                style=discord.ButtonStyle.grey,
                custom_id="close",
                row=2
            ))

    def create_select_menu(self) -> Select:
        options = []
        saved_dino_class = ""
        limited = False
        for dino in self.dinosaurs[:25]:
            id = dino["id"]
            growth = dino["growth"]
            hunger = dino["hunger"]
            thirst = dino["thirst"]
            health = dino["health"]
            dino_name = find_name_by_class(dino["dino_class"])
            if str(id) == self.selected_dino:
                saved_dino_class = dino_name
            label = f"({id}) {dino_name} (Рост {growth}, Голод: {hunger}, Жажда: {thirst}, HP: {health})"
            options.append(discord.SelectOption(label=label, value=str(id)))
        placeholder = (
            f"Вы выбрали: {saved_dino_class}"
            if saved_dino_class
            else "Выберите динозавра для удаления"
        )
        if len(self.dinosaurs) > 25:
            limited = True
        self.limited = limited
        return Select(
            placeholder=placeholder,
            options=options,
            custom_id="select_dino_delete"
        )

    @property
    def embed(self) -> Embed:
        if self.empty:
            embed = discord.Embed(
                title="🦖 Нет сохранённых динозавров",
                description="У вас нет динозавров для удаления.\n\nНажмите 'Вернуться', чтобы выйти.",
                color=discord.Color.orange()
            )
            return embed

        embed = discord.Embed(
            title="🦖 Удаление сохраненного динозавра",
            description="*Перед удалением динозавра, убедитесь, что выбрали правильного!*",
            color=discord.Color.red()
        )

        rules = (
            "⚠️ **Внимание:**\n"
            "• После удаления динозавра восстановить его будет невозможно.\n"
            "• Проверьте, что вы выбрали нужного динозавра.\n"
            "• Это действие нельзя отменить."
        )

        embed.add_field(
            name="Правила удаления",
            value=rules,
            inline=False
        )

        if getattr(self, "limited", False):
            embed.add_field(
                name="ℹ️ Ограничение",
                value="Показаны только первые 25 динозавров. Используйте фильтры или удалите лишних для отображения остальных.",
                inline=False
            )

        embed.set_footer(
            text="Удаляйте динозавров с осторожностью",
            icon_url="https://emojicdn.elk.sh/⚠️"
        )

        embed.set_thumbnail(url="https://emojicdn.elk.sh/🦖")

        return embed

    async def update_view(self, interaction: discord.Interaction):
        if self.empty:
            await interaction.response.edit_message(embed=self.embed, view=self)
            return

        self.delete_button.disabled = self.selected_dino is None

        self.remove_item(self.select_menu)
        self.select_menu = self.create_select_menu()
        self.add_item(self.select_menu)

        await interaction.response.edit_message(embed=self.embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")

        if custom_id == "go_back":
            await interaction.response.edit_message(embed=self.original_embed, view=self.original_view)

        elif custom_id == "close":
            await interaction.response.defer()
            await interaction.delete_original_response()

        elif custom_id == "select_dino_delete":
            self.selected_dino = interaction.data["values"][0]
            await self.update_view(interaction)

        elif custom_id == "delete_dino":
            if self.selected_dino:
                result = await del_dino(interaction.user.id, int(self.selected_dino))
                if not result or isinstance(result, tuple):
                    reason = result[1] if isinstance(result, tuple) and len(
                        result) > 1 else "Не удалось удалить сохраненного динозавра."
                    embed = discord.Embed(
                        title="❌ Ошибка удаления",
                        description=reason,
                        color=discord.Color.red()
                    )
                    await interaction.followup.edit_message(
                        interaction.message.id,
                        embed=embed,
                        view=None,
                        content=None
                    )
                await interaction.response.edit_message(
                    embed=None,
                    view=None,
                    content=f"Динозавр {self.selected_dino} успешно удалён из сохранённых!"
                )
            else:
                await interaction.response.send_message(
                    "Сначала выберите динозавра для удаления!",
                    ephemeral=True
                )

        return False

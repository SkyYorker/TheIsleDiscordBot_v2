from typing import Dict

DINOSAURS = {
    "Трицератопс": {
        "class_name": "BP_Triceratops_C",
        "weight": "9500 кг",
        "speed": "24,6 км/ч",
        "bite": "900 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/1b/triceratops-the-isle-1bcea988.webp",
        "group_limit": "2 особи",
        "price": 270,
        "category": "Травоядные"
    },
    "Диаблоцератопс": {
        "class_name": "BP_Diabloceratops_C",
        "weight": "3000 кг",
        "speed": "36 км/ч",
        "bite": "275 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/0f/diabloceratops-0f22361c.webp",
        "group_limit": "4 особи",
        "price": 250,
        "category": "Травоядные"
    },
    "Майязавр": {
        "class_name": "BP_Maiasaura_C",
        "weight": "3700 кг",
        "speed": "46,9 км/ч",
        "bite": "40 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/65/maiasaurus-1-65e8cf86.webp",
        "group_limit": "5 особей",
        "price": 220,
        "category": "Травоядные"
    },
    "Пахицефалозавр": {
        "class_name": "BP_Pachycephalosaurus_C",
        "weight": "500 кг",
        "speed": "41,8 км/ч",
        "bite": "20 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/df/Pachycephalosaurus-dffbd063.webp",
        "group_limit": "10 особей",
        "price": 130,
        "category": "Травоядные"
    },
    "Дриозавр": {
        "class_name": "BP_Dryosaurus_C",
        "weight": "130 кг",
        "speed": "45 км/ч",
        "bite": "20 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/b6/Dryosausurs-b6c974e5.webp",
        "group_limit": "Безлимит",
        "price": 20,
        "category": "Травоядные"
    },
    "Тенонтозавр": {
        "class_name": "BP_Tenontosaurus_C",
        "weight": "1600 кг",
        "speed": "40,5 км/ч",
        "bite": "25 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/a2/Tenontosaurus-a2be29a5.webp",
        "group_limit": "5 особей",
        "price": 170,
        "category": "Травоядные"
    },
    "Гипсилофодон": {
        "class_name": "BP_Hypsilophodon_C",
        "weight": "20 кг",
        "speed": "39,6 км/ч",
        "bite": "2 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/89/Hypsilophodon-89c22fef.webp",
        "group_limit": "Безлимит",
        "price": 10,
        "category": "Травоядные"
    },
    "Стегозавр": {
        "class_name": "BP_Stegosaurus_C",
        "weight": "6 тонн",
        "speed": "26,2 км/ч",
        "bite": "50 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/7a/stegosaurier-7af21820.webp",
        "group_limit": "2 особи",
        "price": 270,
        "category": "Травоядные"
    },
    "Дейнозух": {
        "class_name": "BP_Deinosuchus_C",
        "weight": "8000 кг",
        "speed": "18 км/ч",
        "bite": "500 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/4a/deinosuchus-4a658aae.webp",
        "group_limit": "2 особи",
        "price": 270,
        "category": "Плотоядные"
    },
    "Т-Рекс": {
        "class_name": "BP_Trex_C",
        "weight": "> 9000 кг",
        "speed": "уточняется",
        "bite": "уточняется",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/2b/trex-the-isle-2b9bd174.webp",
        "group_limit": "?",
        "price": None,
        "category": None
    },
    "Геррерозавр": {
        "class_name": "BP_Herrerasaurus_C",
        "weight": "175 кг",
        "speed": "45 км/ч",
        "bite": "30 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/fb/herrerrasaurus-the-isle-fbdf21cc.webp",
        "group_limit": "8 особей",
        "price": 70,
        "category": "Плотоядные"
    },
    "Дилофозавр": {
        "class_name": "BP_Dilophosaurus_C",
        "weight": "700 кг",
        "speed": "47,5 км/ч",
        "bite": "75 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/7f/dilophosaurus-the-isle-final-7f345180.webp",
        "group_limit": "5 особей",
        "price": 120,
        "category": "Плотоядные"
    },
    "Цератозавр": {
        "class_name": "BP_Ceratosaurus_C",
        "weight": "1300 кг",
        "speed": "40,2 км/ч",
        "bite": "150 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/99/Ceratosaurus-99a74c42.webp",
        "group_limit": "4 особи",
        "price": 250,
        "category": "Плотоядные"
    },
    "Троодон": {
        "class_name": "BP_Troodon_C",
        "weight": "45 кг",
        "speed": "28,5 км/ч",
        "bite": "15 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/2d/Troodon-2d452567.webp",
        "group_limit": "10 особей",
        "price": 30,
        "category": "Плотоядные"
    },
    "Омнираптор": {
        "class_name": "BP_Omniraptor_C",
        "weight": "450 кг",
        "speed": "46,8 км/ч",
        "bite": "65 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/d7/Utahraptor-d7cdcd0d.webp",
        "group_limit": "10 особей",
        "price": 100,
        "category": "Плотоядные"
    },
    "Птеранодон": {
        "class_name": "BP_Pteranodon_C",
        "weight": "45 кг",
        "speed": "28,5 км/ч",
        "bite": "20 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/c6/Pteranodon-c6a42ce9.webp",
        "group_limit": "Безлимит",
        "price": 25,
        "category": "Плотоядные"
    },
    "Карнотавр": {
        "class_name": "BP_Carnotaurus_C",
        "weight": "1300 кг",
        "speed": "49,5-55,5 км/ч",
        "bite": "150 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/e2/Carnotaurus-e298026f.webp",
        "group_limit": "4 особи",
        "price": 200,
        "category": "Плотоядные"
    },
    "Бэйпяозавр": {
        "class_name": "BP_Beipiaosaurus_C",
        "weight": "90 кг",
        "speed": "32 км/ч",
        "bite": "20 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/07/Beipiaosaurus-0768af1f.webp",
        "group_limit": "Безлимит",
        "price": 40,
        "category": "Всеядные"
    },
    "Галлимимус": {
        "class_name": "BP_Gallimimus_C",
        "weight": "425 кг",
        "speed": "46,8-55,4 км/ч",
        "bite": "25 Ньютон",
        "image": "https://www.theisle-game.com/templates/yootheme/cache/1b/galli-the-isle-1bd708a6.webp",
        "group_limit": "10 особей",
        "price": 90,
        "category": "Всеядные"
    },
}

CATEGORY_EMOJIS: Dict[str, str] = {
    "Плотоядные": "🍖",
    "Травоядные": "🌿",
    "Всеядные": "🍒",
}

def find_name_by_class(class_name: str) -> str:
    for dino, data in DINOSAURS.items():
        if data.get("class_name", "") == class_name:
            return dino
    return ""
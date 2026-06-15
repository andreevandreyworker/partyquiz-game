CATEGORIES = [
    {"id": "friends", "ru": "Друзья", "en": "Friends", "premium": False},
    {"id": "awkward", "ru": "Неловкие моменты", "en": "Awkward",
     "premium": False},
    {"id": "love", "ru": "Отношения", "en": "Relationships",
     "premium": False},
    {"id": "deep", "ru": "Глубокие вопросы", "en": "Deep",
     "premium": False},
    {"id": "wouldyou", "ru": "Что бы ты выбрал", "en": "Would you",
     "premium": False},
    {"id": "childhood", "ru": "Детство", "en": "Childhood",
     "premium": False},
    {"id": "hot", "ru": "18+", "en": "18+", "premium": True},
    {"id": "random", "ru": "Рандом", "en": "Random", "premium": False},
]

CATEGORY_IDS = {c["id"] for c in CATEGORIES}
PREMIUM_CATEGORY_IDS = {c["id"] for c in CATEGORIES if c["premium"]}

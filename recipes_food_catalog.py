"""Catalogue nutritionnel générique utilisé par Recettes.

Les valeurs sont des moyennes indicatives par 100 g. Elles servent uniquement
à produire des estimations cohérentes dans JF Apps; elles ne remplacent pas
l'étiquette nutritionnelle du produit réellement utilisé.
"""
from __future__ import annotations

import re
import unicodedata


def _fold(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("œ", "oe")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _food(label, aliases, *, density=None, piece_g=None, calories=0,
          protein=0, carbs=0, sugars=0, fiber=0, fat=0, saturated=0,
          sodium=0, cholesterol=0):
    return {
        "label": label,
        "aliases": tuple(aliases),
        "density_g_ml": density,
        "piece_g": piece_g,
        "nutrition": {
            "calories_kcal": float(calories),
            "protein_g": float(protein),
            "carbohydrates_g": float(carbs),
            "sugars_g": float(sugars),
            "fiber_g": float(fiber),
            "fat_g": float(fat),
            "saturated_fat_g": float(saturated),
            "sodium_mg": float(sodium),
            "cholesterol_mg": float(cholesterol),
        },
    }


FOODS = {
    "flour_all_purpose": _food("Farine tout usage", ["farine", "farine tout usage", "farine blanche"], density=0.507, calories=364, protein=10.3, carbs=76.3, sugars=0.3, fiber=2.7, fat=1.0, saturated=0.2, sodium=2),
    "flour_whole_wheat": _food("Farine de blé entier", ["farine de blé entier", "farine integrale", "farine intégrale"], density=0.51, calories=340, protein=13.2, carbs=72.0, sugars=0.4, fiber=10.7, fat=2.5, saturated=0.4, sodium=5),
    "oats": _food("Flocons d’avoine", ["avoine", "flocons d avoine", "flocons avoine"], density=0.34, calories=379, protein=13.2, carbs=67.7, sugars=1.0, fiber=10.1, fat=6.5, saturated=1.2, sodium=6),
    "sugar": _food("Sucre blanc", ["sucre", "sucre blanc", "sucre granulé", "sucre granule"], density=0.845, calories=387, carbs=100, sugars=100, sodium=1),
    "brown_sugar": _food("Cassonade", ["cassonade", "sucre brun"], density=0.93, calories=380, protein=0.1, carbs=98.1, sugars=97.0, sodium=28),
    "date_sugar": _food("Poudre de dattes", ["poudre de dattes", "sucre de dattes"], density=0.62, calories=360, protein=2.5, carbs=90, sugars=65, fiber=8, fat=0.5, saturated=0.1, sodium=5),
    "maple_syrup": _food("Sirop d’érable", ["sirop d érable", "sirop erable"], density=1.33, calories=260, carbs=67, sugars=60.5, fat=0.1, sodium=12),
    "honey": _food("Miel", ["miel"], density=1.42, calories=304, protein=0.3, carbs=82.4, sugars=82.1, fiber=0.2, sodium=4),
    "butter": _food("Beurre", ["beurre"], density=0.96, calories=717, protein=0.9, carbs=0.1, sugars=0.1, fat=81.1, saturated=51.4, sodium=11, cholesterol=215),
    "olive_oil": _food("Huile d’olive", ["huile d olive", "huile olive"], density=0.91, calories=884, fat=100, saturated=13.8, sodium=2),
    "canola_oil": _food("Huile de canola / végétale", ["huile de canola", "huile vegetale", "huile végétale", "huile neutre"], density=0.92, calories=884, fat=100, saturated=7.4),
    "egg": _food("Œuf entier", ["oeuf", "œuf", "oeufs", "œufs"], piece_g=50, calories=143, protein=12.6, carbs=0.7, sugars=0.4, fat=9.5, saturated=3.1, sodium=142, cholesterol=372),
    "milk_2": _food("Lait 2 %", ["lait", "lait 2", "lait 2 %"], density=1.03, calories=50, protein=3.4, carbs=4.8, sugars=4.8, fat=2.0, saturated=1.3, sodium=44, cholesterol=8),
    "cream_35": _food("Crème 35 %", ["crème", "creme", "crème épaisse", "creme epaisse", "crème 35"], density=1.0, calories=340, protein=2.1, carbs=2.8, sugars=2.9, fat=36.1, saturated=22.9, sodium=27, cholesterol=137),
    "greek_yogurt_plain": _food("Yogourt grec nature", ["yogourt grec", "yaourt grec", "yogourt grec nature"], density=1.03, calories=73, protein=9.9, carbs=3.9, sugars=3.6, fat=1.9, saturated=1.2, sodium=36, cholesterol=10),
    "cream_cheese": _food("Fromage à la crème", ["fromage a la creme", "fromage à la crème", "cream cheese"], density=1.0, calories=342, protein=5.9, carbs=4.1, sugars=3.2, fat=34.2, saturated=19.3, sodium=321, cholesterol=110),
    "cheddar": _food("Cheddar", ["cheddar", "fromage cheddar"], density=0.48, calories=403, protein=24.9, carbs=1.3, sugars=0.5, fat=33.1, saturated=21.1, sodium=621, cholesterol=105),
    "gruyere": _food("Gruyère", ["gruyère", "gruyere"], density=0.47, calories=413, protein=29.8, carbs=0.4, sugars=0.4, fat=32.3, saturated=18.9, sodium=714, cholesterol=110),
    "parmesan": _food("Parmesan", ["parmesan", "fromage parmesan"], density=0.38, calories=431, protein=38, carbs=4.1, sugars=0.9, fat=29, saturated=18, sodium=1529, cholesterol=88),
    "silken_tofu": _food("Tofu soyeux", ["tofu soyeux"], density=1.0, calories=55, protein=4.8, carbs=2.9, sugars=0.5, fiber=0.3, fat=2.7, saturated=0.4, sodium=5),
    "firm_tofu": _food("Tofu ferme", ["tofu", "tofu ferme", "tofu extra ferme"], density=1.0, calories=144, protein=17.3, carbs=2.8, sugars=0.6, fiber=2.3, fat=8.7, saturated=1.3, sodium=14),
    "banana": _food("Banane", ["banane", "bananes"], piece_g=118, calories=89, protein=1.1, carbs=22.8, sugars=12.2, fiber=2.6, fat=0.3, saturated=0.1, sodium=1),
    "apple": _food("Pomme", ["pomme", "pommes"], piece_g=182, calories=52, protein=0.3, carbs=13.8, sugars=10.4, fiber=2.4, fat=0.2, sodium=1),
    "applesauce": _food("Compote de pommes non sucrée", ["compote de pommes", "compote pommes"], density=1.02, calories=42, protein=0.2, carbs=11.3, sugars=9.4, fiber=1.1, fat=0.1, sodium=2),
    "carrot": _food("Carotte", ["carotte", "carottes"], piece_g=61, calories=41, protein=0.9, carbs=9.6, sugars=4.7, fiber=2.8, fat=0.2, sodium=69),
    "onion": _food("Oignon", ["oignon", "oignons", "oignon jaune", "oignon rouge", "oignon blanc"], piece_g=110, calories=40, protein=1.1, carbs=9.3, sugars=4.2, fiber=1.7, fat=0.1, sodium=4),
    "garlic": _food("Ail", ["ail", "gousse d ail", "gousses d ail"], piece_g=3, calories=149, protein=6.4, carbs=33.1, sugars=1.0, fiber=2.1, fat=0.5, saturated=0.1, sodium=17),
    "tomato": _food("Tomate", ["tomate", "tomates"], piece_g=123, calories=18, protein=0.9, carbs=3.9, sugars=2.6, fiber=1.2, fat=0.2, sodium=5),
    "canned_tomato": _food("Tomates en conserve", ["tomates en conserve", "tomates en boite", "tomates en boîte"], density=1.02, calories=32, protein=1.6, carbs=7.3, sugars=4.4, fiber=1.9, fat=0.3, sodium=198),
    "potato": _food("Pomme de terre", ["pomme de terre", "pommes de terre", "patate", "patates"], piece_g=173, calories=77, protein=2.1, carbs=17.5, sugars=0.8, fiber=2.1, fat=0.1, sodium=6),
    "mushroom": _food("Champignon blanc", ["champignon", "champignons", "champignon blanc", "champignons blancs"], piece_g=18, calories=22, protein=3.1, carbs=3.3, sugars=2.0, fiber=1.0, fat=0.3, saturated=0.1, sodium=5),
    "broccoli": _food("Brocoli", ["brocoli"], density=0.38, calories=34, protein=2.8, carbs=6.6, sugars=1.7, fiber=2.6, fat=0.4, saturated=0.1, sodium=33),
    "strawberry": _food("Fraises", ["fraise", "fraises"], density=0.64, calories=32, protein=0.7, carbs=7.7, sugars=4.9, fiber=2.0, fat=0.3, sodium=1),
    "chicken_breast": _food("Poulet, poitrine cuite", ["poulet", "poitrine de poulet", "poulet cuit"], calories=165, protein=31.0, fat=3.6, saturated=1.0, sodium=74, cholesterol=85),
    "ground_beef": _food("Bœuf haché cuit", ["boeuf hache", "bœuf haché", "boeuf", "bœuf"], calories=250, protein=26.0, fat=15.0, saturated=6.0, sodium=72, cholesterol=88),
    "pork": _food("Porc cuit", ["porc", "roti de porc", "rôti de porc", "epaule de porc", "épaule de porc"], calories=242, protein=27.3, fat=14.0, saturated=5.0, sodium=62, cholesterol=80),
    "bacon": _food("Bacon cuit", ["bacon"], piece_g=8, calories=541, protein=37.0, carbs=1.4, fat=42.0, saturated=14.0, sodium=1717, cholesterol=110),
    "salmon": _food("Saumon cuit", ["saumon"], calories=206, protein=22.1, fat=12.4, saturated=2.5, sodium=59, cholesterol=63),
    "rice_dry": _food("Riz blanc sec", ["riz", "riz blanc", "riz sec"], density=0.78, calories=365, protein=7.1, carbs=80.0, sugars=0.1, fiber=1.3, fat=0.7, saturated=0.2, sodium=5),
    "pasta_dry": _food("Pâtes sèches", ["pates", "pâtes", "pates seches", "pâtes sèches"], density=0.42, calories=371, protein=13.0, carbs=75.0, sugars=2.7, fiber=3.2, fat=1.5, saturated=0.3, sodium=6),
    "breadcrumbs": _food("Chapelure", ["chapelure", "chapelure panko", "panko"], density=0.45, calories=395, protein=13.4, carbs=71.9, sugars=6.2, fiber=4.5, fat=5.3, saturated=1.2, sodium=732),
    "cocoa": _food("Cacao non sucré", ["cacao", "poudre de cacao", "cacao non sucre", "cacao non sucré"], density=0.36, calories=228, protein=19.6, carbs=57.9, sugars=1.8, fiber=37.0, fat=13.7, saturated=8.1, sodium=21),
    "dark_chocolate": _food("Chocolat noir", ["chocolat noir", "chocolat mi sucre", "chocolat mi-sucré", "chocolat"], density=0.78, calories=546, protein=4.9, carbs=61.2, sugars=47.9, fiber=7.0, fat=31.3, saturated=18.5, sodium=24, cholesterol=8),
    "peanut_butter": _food("Beurre d’arachide", ["beurre d arachide", "beurre arachide"], density=1.08, calories=588, protein=25.0, carbs=20.0, sugars=9.2, fiber=6.0, fat=50.0, saturated=10.0, sodium=426),
    "almonds": _food("Amandes", ["amande", "amandes"], density=0.60, calories=579, protein=21.2, carbs=21.6, sugars=4.4, fiber=12.5, fat=49.9, saturated=3.8, sodium=1),
    "walnuts": _food("Noix de Grenoble", ["noix", "noix de grenoble"], density=0.48, calories=654, protein=15.2, carbs=13.7, sugars=2.6, fiber=6.7, fat=65.2, saturated=6.1, sodium=2),
    "chia": _food("Graines de chia", ["chia", "graines de chia"], density=0.70, calories=486, protein=16.5, carbs=42.1, fiber=34.4, fat=30.7, saturated=3.3, sodium=16),
    "flax": _food("Graines de lin moulues", ["lin", "graines de lin", "graines de lin moulues"], density=0.56, calories=534, protein=18.3, carbs=28.9, sugars=1.6, fiber=27.3, fat=42.2, saturated=3.7, sodium=30),
    "beef_broth": _food("Bouillon de bœuf préparé", ["bouillon de boeuf", "bouillon de bœuf"], density=1.0, calories=7, protein=1.1, carbs=0.4, sugars=0.2, fat=0.2, saturated=0.1, sodium=450),
    "chicken_broth": _food("Bouillon de poulet préparé", ["bouillon de poulet"], density=1.0, calories=6, protein=0.6, carbs=0.4, sugars=0.2, fat=0.2, saturated=0.1, sodium=450),
    "soy_sauce": _food("Sauce soya", ["sauce soya", "sauce soja"], density=1.16, calories=53, protein=8.1, carbs=4.9, sugars=0.4, fiber=0.8, fat=0.6, saturated=0.1, sodium=5493),
    "vinegar": _food("Vinaigre", ["vinaigre", "vinaigre de cidre", "vinaigre balsamique", "vinaigre blanc"], density=1.0, calories=18, carbs=0.6, sugars=0.4, sodium=5),
    "red_wine": _food("Vin rouge", ["vin rouge"], density=0.99, calories=85, protein=0.1, carbs=2.6, sugars=0.6, sodium=4),
    "salt": _food("Sel de table", ["sel", "sel de table"], density=1.22, sodium=39340),
    "baking_powder": _food("Poudre à pâte", ["poudre a pate", "poudre à pâte", "levure chimique"], density=0.96, calories=53, carbs=28.1, fiber=0.2, sodium=10600),
    "baking_soda": _food("Bicarbonate de soude", ["bicarbonate", "bicarbonate de soude"], density=0.92, sodium=27360),
    "oat_flour": _food("Farine d’avoine", ["farine d avoine", "farine d’avoine"], density=0.51, calories=404, protein=14.7, carbs=65.7, sugars=0.8, fiber=6.5, fat=9.1, saturated=1.6, sodium=19),
    "cornstarch": _food("Fécule de maïs", ["fecule de mais", "fécule de maïs", "maizena", "cornstarch"], density=0.54, calories=381, protein=0.3, carbs=91.3, sugars=0, fiber=0.9, fat=0.1, sodium=9),
    "molasses": _food("Mélasse", ["melasse", "mélasse"], density=1.40, calories=290, carbs=74.7, sugars=74.7, sodium=37),
    "vanilla": _food("Extrait de vanille", ["vanille", "extrait de vanille"], density=0.88, calories=288, protein=0.1, carbs=12.7, sugars=12.7, sodium=9),
    "dates": _food("Dattes", ["datte", "dattes"], piece_g=24, calories=282, protein=2.5, carbs=75.0, sugars=63.4, fiber=8.0, fat=0.4, sodium=2),
    "raisins": _food("Raisins secs", ["raisins secs", "raisin sec"], density=0.67, calories=299, protein=3.1, carbs=79.2, sugars=59.2, fiber=3.7, fat=0.5, sodium=11),
    "jam": _food("Confiture", ["confiture", "confiture de fraises"], density=1.33, calories=250, protein=0.4, carbs=65.0, sugars=48.0, fiber=1.0, fat=0.1, sodium=20),
    "ketchup": _food("Ketchup", ["ketchup"], density=1.15, calories=112, protein=1.3, carbs=25.8, sugars=22.8, fat=0.2, sodium=907),
    "chili_sauce": _food("Sauce chili", ["sauce chili", "chili sauce"], density=1.10, calories=110, protein=1.5, carbs=25.0, sugars=20.0, fat=0.3, sodium=1100),
    "worcestershire": _food("Sauce Worcestershire", ["sauce worcestershire", "sauce w", "worcestershire"], density=1.12, calories=78, protein=0, carbs=19.5, sugars=10.0, fat=0, sodium=980),
    "mozzarella": _food("Mozzarella", ["mozzarella", "fromage mozzarella"], density=0.45, calories=280, protein=28.0, carbs=3.1, sugars=1.2, fat=17.0, saturated=11.0, sodium=627, cholesterol=54),
    "burrata": _food("Burrata", ["burrata"], density=0.95, calories=300, protein=12.0, carbs=2.0, sugars=1.0, fat=28.0, saturated=18.0, sodium=300, cholesterol=75),
    "prosciutto": _food("Prosciutto", ["prosciutto"], calories=275, protein=25.0, carbs=0.5, sugars=0, fat=18.0, saturated=6.0, sodium=1900, cholesterol=70),
    "ham": _food("Jambon", ["jambon"], calories=145, protein=21.0, carbs=1.5, sugars=1.2, fat=5.5, saturated=1.9, sodium=1200, cholesterol=53),
    "quinoa_dry": _food("Quinoa sec", ["quinoa", "quinoa sec"], density=0.72, calories=368, protein=14.1, carbs=64.2, sugars=0, fiber=7.0, fat=6.1, saturated=0.7, sodium=5),
    "lentils_dry": _food("Lentilles sèches", ["lentilles", "lentilles seches", "lentilles sèches"], density=0.80, calories=353, protein=25.8, carbs=60.1, sugars=2.0, fiber=10.7, fat=1.1, saturated=0.2, sodium=6),
    "chickpeas": _food("Pois chiches cuits", ["pois chiches", "pois chiche"], density=0.72, calories=164, protein=8.9, carbs=27.4, sugars=4.8, fiber=7.6, fat=2.6, saturated=0.3, sodium=240),
    "spinach": _food("Épinards", ["epinards", "épinards"], density=0.13, calories=23, protein=2.9, carbs=3.6, sugars=0.4, fiber=2.2, fat=0.4, sodium=79),
    "zucchini": _food("Courgette", ["courgette", "zucchini"], piece_g=196, calories=17, protein=1.2, carbs=3.1, sugars=2.5, fiber=1.0, fat=0.3, sodium=8),
    "bell_pepper": _food("Poivron", ["poivron", "poivrons"], piece_g=119, calories=31, protein=1.0, carbs=6.0, sugars=4.2, fiber=2.1, fat=0.3, sodium=4),
    "water": _food("Eau", ["eau"], density=1.0),
}

_ALIAS_TO_KEY = {}
for _key, _profile in FOODS.items():
    for _alias in (_profile["label"], *_profile["aliases"]):
        _ALIAS_TO_KEY[_fold(_alias)] = _key


def food_options():
    return {
        key: profile["label"]
        for key, profile in sorted(
            FOODS.items(),
            key=lambda item: item[1]["label"].casefold(),
        )
    }


def get_food(key):
    return FOODS.get(str(key or "").strip())


def match_food(name):
    folded = _fold(name)
    if not folded:
        return None
    if folded in _ALIAS_TO_KEY:
        return _ALIAS_TO_KEY[folded]

    candidates = []
    for alias, key in _ALIAS_TO_KEY.items():
        if len(alias) >= 3 and (
            folded.startswith(alias + " ")
            or folded.endswith(" " + alias)
            or f" {alias} " in f" {folded} "
        ):
            candidates.append((len(alias), key))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]

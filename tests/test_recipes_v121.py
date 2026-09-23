from __future__ import annotations

import unittest

from recipes_site_import import (
    item_name_from_ingredient_line,
    parse_recipe_html,
)


PORC_HTML = """
<html>
<head>
<title>Porc effiloché à la mijoteuse - Recettes de l'Ours</title>
</head>
<body>
<h1>Porc effiloché à la mijoteuse</h1>
<p>Recette tirée du site les Mordu de Radio Canada</p>
<p>https://ici.radio-canada.ca/mordu/recettes/7444/porc-effiloche-bbq-mijoteuse</p>
<p>Peu aussi se faire au four !</p>
<div>Ingrédients</div>
<ul>
<li>Pièce de porc (roti, épaule, etc...)</li>
<li>1 oignon</li>
<li>Poudre oignon 1, c à soupe</li>
<li>Poudre d'ail, 1 c à soupe</li>
<li>Paprika fumé, 1 c à soupe</li>
<li>Poudre de chili, 1 c à soupe</li>
<li>Pincée de cayenne</li>
<li>1 boite de pate de tomates (156 ml)</li>
<li>Cassonnade, 1/2 tasse</li>
<li>Vinaigre de cidre, 1/2 tasse</li>
<li>Sauce W, 1 c à soupe</li>
</ul>
<ol>
<li>Déposer l'oignon que vous aurez haché au fond de la mijoteuse</li>
<li>Mélanger toutes les épices (poudre oignon, ail, paprika, chili, cayenne)</li>
<li>Frotter toute la pièce de porc avec les épices</li>
<li>Bien mélanger la pate de tomates avec la cassonade, le vinaigre et la sauce W.</li>
<li>Répartir la sauce autour du morceau de porc</li>
<li>Cuire 6 à 8 heures</li>
<li>Effilocher la viande à l'aide de 2 fourchettes</li>
</ol>
<p>Perso, j'effiloche la viande environ 1 hre avant la fin.</p>
</body>
</html>
"""


class RecipesV121ImportTests(unittest.TestCase):
    def test_porc_page_uses_real_ingredients_and_numbered_steps(self):
        recipe = parse_recipe_html(
            PORC_HTML,
            "https://sites.google.com/view/recettes-de-lours/"
            "plats-principaux/porc",
        )
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "Porc effiloché à la mijoteuse")
        self.assertEqual(recipe["source_category"], "Plats principaux")
        self.assertEqual(recipe["source_subcategory"], "")
        self.assertEqual(len(recipe["ingredients"]), 11)

        names = [row["item_name"] for row in recipe["ingredients"]]
        self.assertIn("Pièce de porc", names)
        self.assertIn("oignon", [name.casefold() for name in names])
        self.assertIn("Poudre oignon", names)
        self.assertIn("Poudre d'ail", names)
        self.assertIn("Paprika fumé", names)
        self.assertIn("Poudre de chili", names)
        self.assertIn("cayenne", [name.casefold() for name in names])

        self.assertNotIn(
            "Recette tirée du site les Mordu de Radio Canada",
            names,
        )
        self.assertFalse(any(name.startswith("http") for name in names))
        self.assertNotIn("Peu aussi se faire au four !", names)

        self.assertTrue(
            recipe["instructions"].startswith(
                "Déposer l'oignon que vous aurez haché"
            )
        )
        self.assertIn("Cuire 6 à 8 heures", recipe["instructions"])
        self.assertNotIn("Pièce de porc", recipe["instructions"])
        self.assertNotIn("Poudre oignon 1, c à soupe", recipe["instructions"])

        self.assertIn(
            "Recette tirée du site les Mordu de Radio Canada",
            recipe["description"],
        )
        self.assertIn(
            "Peu aussi se faire au four !",
            recipe["description"],
        )
        self.assertNotIn("https://", recipe["description"])

    def test_trailing_measure_with_comma_is_removed_from_item_name(self):
        self.assertEqual(
            item_name_from_ingredient_line(
                "Poudre oignon 1, c à soupe"
            ),
            "Poudre oignon",
        )


if __name__ == "__main__":
    unittest.main()

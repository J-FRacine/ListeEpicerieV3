from __future__ import annotations

import unittest

from recipes_site_import import (
    DEFAULT_SITE_URL,
    _internal_links,
    item_name_from_ingredient_line,
    normalize_site_url,
    parse_recipe_html,
    preview_recipe_matches,
)


SAMPLE_HTML = """
<html>
<head><title>Poulet crémeux - Recettes de l'Ours</title></head>
<body>
<nav><a href="/view/recettes-de-lours/accueil">Accueil</a></nav>
<h1>Poulet crémeux</h1>
<p>Préparation: 15 min. Cuisson: 30 min. Pour 4 personnes.</p>
<h2>Ingrédients</h2>
<ul>
<li>2 poitrines de poulet</li>
<li>1 tasse de crème</li>
<li>3 gousses d'ail, hachées</li>
</ul>
<h2>Préparation</h2>
<ol>
<li>Faire dorer le poulet.</li>
<li>Ajouter la crème et mijoter 20 minutes.</li>
</ol>
<a href="/view/recettes-de-lours/plats/pates">Pâtes</a>
<a href="https://example.com/externe">Externe</a>
</body>
</html>
"""


BEAR_STYLE_HTML = """
<html>
<head><title>Burrata et tomates sur plaque - Recettes de l'Ours</title></head>
<body>
<nav><a href="/view/recettes-de-lours/accueil">Accueil</a></nav>
<h1>Burrata et tomates sur plaque</h1>
<div>Huile olive 60% 1/3 tasse (approx selon la quantité de tomates)</div>
<div>Vinaigre balsamique 40% 1/4 t (selon la quantité de tomates)</div>
<div>Tomates</div>
<div>Prosciutto</div>
<div>Parmesan</div>
<div>2 c a soupe de sucre</div>
<div>Ail au goût</div>
<div>Sel et poivre</div>
<div>Sucre au gout</div>
<div>Pincée de Fines herbes au goût (une pincée de paprika fumé fort et de poudre de Chili)</div>
<ul>
<li>Couper les tomates en tranches</li>
<li>Avec des Oignons au goût (rouges ou jaunes)</li>
<li>Mélanger les tomates et le mélange d’huile-épices et laisser quelques minutes</li>
<li>Étendre les tomates sur une plaque</li>
<li>Mettre au Four 425F, 25 minutes</li>
</ul>
<p>Déguster avec pain et biscottes</p>
<p>On peut ajouter quelques feuilles de basilic frais sur les tomates au moment de servir</p>
</body>
</html>
"""


class RecipesSiteImportTests(unittest.TestCase):
    def test_site_url_is_restricted_to_user_site(self):
        self.assertEqual(
            normalize_site_url(DEFAULT_SITE_URL + "?authuser=0"),
            DEFAULT_SITE_URL,
        )
        with self.assertRaises(ValueError):
            normalize_site_url("https://sites.google.com/view/autre-site/accueil")

    def test_parser_recognizes_recipe_sections(self):
        recipe = parse_recipe_html(SAMPLE_HTML, DEFAULT_SITE_URL)
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "Poulet crémeux")
        self.assertEqual(recipe["servings"], 4)
        self.assertEqual(len(recipe["ingredients"]), 3)
        self.assertIn("Faire dorer le poulet.", recipe["instructions"])

    def test_parser_recognizes_recettes_de_lours_without_section_headings(self):
        recipe = parse_recipe_html(
            BEAR_STYLE_HTML,
            "https://sites.google.com/view/recettes-de-lours/entrées/tomates-burrata",
        )
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "Burrata et tomates sur plaque")
        self.assertEqual(len(recipe["ingredients"]), 10)
        self.assertIn("Couper les tomates en tranches", recipe["instructions"])
        self.assertIn("Déguster avec pain et biscottes", recipe["instructions"])
        self.assertNotIn("Tomates\nProsciutto", recipe["instructions"])

    def test_ingredient_name_removes_common_quantity_and_unit(self):
        self.assertEqual(item_name_from_ingredient_line("1 tasse de crème"), "crème")
        self.assertEqual(
            item_name_from_ingredient_line("3 gousses d'ail, hachées"),
            "ail",
        )
        self.assertEqual(
            item_name_from_ingredient_line("2 c a soupe de sucre"),
            "sucre",
        )

    def test_ingredient_name_supports_measure_after_name(self):
        self.assertEqual(
            item_name_from_ingredient_line(
                "Huile olive 60% 1/3 tasse (approx selon la quantité de tomates)"
            ),
            "Huile olive 60%",
        )
        self.assertEqual(item_name_from_ingredient_line("Ail au goût"), "Ail")
        self.assertEqual(item_name_from_ingredient_line("Sucre au gout"), "Sucre")

    def test_internal_link_discovery_stays_inside_site(self):
        links = _internal_links(SAMPLE_HTML, DEFAULT_SITE_URL)
        self.assertIn(
            "https://sites.google.com/view/recettes-de-lours/plats/pates",
            links,
        )
        self.assertTrue(all("example.com" not in link for link in links))

    def test_preview_marks_duplicates_and_missing_items(self):
        recipe = parse_recipe_html(SAMPLE_HTML, DEFAULT_SITE_URL)
        preview = preview_recipe_matches(
            [recipe],
            existing_items=[{"name": "crème"}, {"name": "ail"}],
            existing_recipes=[{"name": "Poulet crémeux"}],
        )[0]
        self.assertTrue(preview["duplicate"])
        self.assertEqual(preview["matched_ingredients"], 2)
        self.assertIn("poitrines de poulet", preview["missing_ingredients"])

    def test_page_without_recipe_structure_is_not_imported(self):
        self.assertIsNone(
            parse_recipe_html("<h1>Accueil</h1><p>Bienvenue sur mon site.</p>", DEFAULT_SITE_URL)
        )


if __name__ == "__main__":
    unittest.main()

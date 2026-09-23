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

    def test_ingredient_name_removes_common_quantity_and_unit(self):
        self.assertEqual(item_name_from_ingredient_line("1 tasse de crème"), "crème")
        self.assertEqual(
            item_name_from_ingredient_line("3 gousses d'ail, hachées"),
            "ail",
        )

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

    def test_page_without_both_sections_is_not_imported(self):
        self.assertIsNone(
            parse_recipe_html("<h1>Accueil</h1><p>Bienvenue sur mon site.</p>", DEFAULT_SITE_URL)
        )


if __name__ == "__main__":
    unittest.main()

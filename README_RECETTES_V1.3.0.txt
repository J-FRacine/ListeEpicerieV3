Recettes V1.3.0 — Import ChatGPT et valeurs nutritives

Base attendue
- Recettes V1.2.1
- GitHub main vérifié au commit :
  6ba8ce57ccfdbd08af8a376309454848714a1313

Nouveautés
- Import JSON ChatGPT : jf_apps_recipe_import version 1.
- JSON collé ou fichier .json avec aperçu avant import.
- Détection des doublons; aucune recette existante n'est écrasée.
- Réutilisation des items existants et création contrôlée des items manquants.
- Catégorie/sous-catégorie de recette importable.
- Étiquettes, temps de préparation/cuisson et source facultative.
- Tableau nutritionnel facultatif et modifiable.
- Affichage par portion et pour la recette complète.
- Marqueur Estimation pour les valeurs approximatives.
- Sauvegarde/restauration des nouvelles métadonnées.

Base de données
- Une migration automatique ajoute grocery_recipes.recipe_extra JSONB.
- Migration idempotente.
- Aucun SQL manuel.
- Aucune nouvelle dépendance Python.

Installation
1. Extraire ce ZIP à la racine de ListeEpicerieV3-main.
2. Lancer INSTALLER_RECETTES_V1.3.0.bat.
3. Si tous les tests réussissent, publier :
   A_PUBLIER_GITHUB_RECETTES_V1.3.0_CHATGPT_NUTRITION.zip
4. Après déploiement Canner :
   - modifier une recette et saisir des valeurs nutritives;
   - vérifier l'affichage dans Consulter;
   - demander à ChatGPT une recette au format jf_apps_recipe_import v1;
   - tester l'import avec son tableau nutritionnel.

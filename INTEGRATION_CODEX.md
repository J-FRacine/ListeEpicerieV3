# Préparation JDR V1.4.0 — assistant de création

Ces fichiers sont préparés pour réduire au minimum le travail restant.

## Fichier prêt

- `rpg_character_creation.py` : assistant complet et autonome par injection de dépendances.
- `tests/test_rpg_character_creation.py` : tests des contrats purs et de l'architecture.

Le module ne touche pas directement NiceGUI, PostgreSQL ou les modules JDR existants. Il peut donc être ajouté au dépôt sans modifier le comportement actuel tant qu'il n'est pas raccordé.

## Raccordement restant dans `rpg_character.py`

1. Importer `open_new_character_dialog` et `build_character_creation_panel` depuis `rpg_character_creation`.
2. Remplacer l'implémentation de `_create_character_dialog` par un wrapper vers `open_new_character_dialog`, en injectant `ui`, `create_rpg_character`, `_character_url` et `_safe_notify_error`.
3. Ajouter un onglet `Création` après `Progression` (ou selon l'ordre retenu par le propriétaire), reconnaître `section=creation`, puis appeler `build_character_creation_panel(...)` avec les services/règles déjà importés dans `rpg_character.py`.
4. Ne pas dupliquer les calculs. Injecter les fonctions existantes déjà importées par `rpg_character.py`.
5. Mettre JDR à 1.4.0 dans `app_versions.py`, notes de version, `manual.py`, `PROJECT_STATUS.md`.
6. Ajouter des tests UI d'intégration avec NiceGUI simulée et conserver toute la suite existante.
7. Compiler et lancer toute la suite du dépôt.

## Garanties déjà encodées

- création guidée et création rapide;
- persistance immédiate du personnage avant le guide;
- aucune table de brouillon;
- race sans modification silencieuse des caractéristiques;
- conservation des champs non édités lors des appels `update_rpg_character_identity`, `update_rpg_character_combat` et `update_rpg_skills`;
- compteur facultatif de rangs de compétences;
- réutilisation des écrans Équipement et Attaques;
- résumé avec calculs et audit injectés;
- aucun import direct NiceGUI/DB dans le nouveau module.

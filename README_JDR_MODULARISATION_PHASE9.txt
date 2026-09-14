JDR V1.4.1 — Phase 9 : nettoyage final de la modularisation
================================================================

Base réellement utilisée
-------------------------
Dépôt : J-FRacine/ListeEpicerieV3
Branche : main
Commit observé : f9d54a399da3e119e0e2956316fa86bb3fa43340

La phase 8 Combat était déjà déployée et validée avant ce nettoyage.

Objectif
--------
Retirer de rpg_character_ui.py les anciens corps de panneaux qui étaient
devenus morts après les phases 2 à 8, sans modifier le comportement visible.

Ce qui change
-------------
- rpg_character_ui.py devient une coquille compacte :
  structure générale, sélection/création/suppression de personnage,
  bannière, onglets et Combat rapide.
- les styles passent dans rpg_character_styles.py;
- les dialogues Équipement passent dans
  rpg_character_equipment_dialogs.py;
- le petit dialogue et les formats Compétences passent dans
  rpg_character_skill_dialogs.py;
- le dialogue « Règles de calcul » passe dans
  rpg_character_rules_dialog.py;
- rpg_character.py raccorde désormais explicitement données, règles,
  dialogues et panneaux;
- le diagnostic temporaire Canner (traceback) est retiré.

Les panneaux déjà extraits restent inchangés :
Identité, Progression, Combat, Équipement, Sauvegardes, Compétences,
Attaques.

Installation
------------
À la racine :
1. REMPLACER rpg_character.py
2. REMPLACER rpg_character_ui.py
3. AJOUTER rpg_character_styles.py
4. AJOUTER rpg_character_equipment_dialogs.py
5. AJOUTER rpg_character_skill_dialogs.py
6. AJOUTER rpg_character_rules_dialog.py

Dans tests/ :
7. AJOUTER test_rpg_character_cleanup.py
8. AJOUTER test_rpg_character_skill_helpers.py

Le test d'intégration existant de la phase 8 peut rester en place pendant
la validation. Une prochaine finalisation pourra le regrouper avec les
tests de nettoyage.

Base de données
---------------
Aucune nouvelle migration.
Aucun SQL manuel.
La migration automatique d'équipement de la phase 7 reste raccordée.

Version
-------
JDR reste en V1.4.1 pendant cette validation, car il s'agit d'un refactor
interne sans nouvelle fonction utilisateur.

Validation réalisée ici
------------------------
- py_compile : OK pour tous les fichiers livrés;
- tests de nettoyage/architecture : OK;
- tests des helpers Compétences : OK;
- total ciblé : 7/7 OK.

Non testé ici
-------------
- PostgreSQL de production;
- Canner;
- navigateur NiceGUI réel;
- suite complète du dépôt.

Tests manuels après déploiement
-------------------------------
Vérifier rapidement les 8 onglets :
Création guidée, Identité, Progression, Combat, Équipement,
Sauvegardes, Compétences, Attaques.

Tester surtout :
- ouvrir et fermer Règles de calcul;
- ajouter/modifier une armure;
- ajouter une compétence personnalisée;
- sauvegarder Compétences;
- ouvrir Combat rapide;
- changer de personnage.

Après validation
----------------
La modularisation structurelle JDR pourra être considérée terminée.
La prochaine phase pourra enfin commencer les nouvelles fonctions,
dans l'ordre prévu : dons structurés, foi/divinité/domaines, portrait,
armes détaillées liées aux attaques, puis sorts.

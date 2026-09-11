JDR V1.4.1 — Modularisation, phase 4
========================================

Base réelle vérifiée
--------------------
GitHub main : 35ffb83eddce108671dc51542710bf97702546dd

La phase 3 est présente sur main et validée par l'utilisateur.

Objectif
--------
Extraire un troisième panneau réel : Attaques.

Nouveau module :
- rpg_character_attacks.py

Le module reprend le dialogue d'ajout/modification et la liste des attaques :
nom, caractéristique, magie/divers, dégâts, critique, portée, type, notes,
munitions, ajout, modification, suppression et bonus total.

Fichiers à téléverser
---------------------
Racine :
- rpg_character.py                  (remplacer)
- rpg_character_attacks.py          (nouveau)

tests/ :
- test_rpg_character_integration.py (remplacer)
- test_rpg_character_attacks.py     (nouveau)

Ne pas modifier
---------------
- rpg_character_ui.py
- rpg_character_saves.py
- rpg_character_progression.py
- app_versions.py
- requirements.txt
- PostgreSQL

Version
-------
JDR reste V1.4.1 : refactor interne.

Validation locale
-----------------
- py_compile : OK pour les 4 fichiers livrés;
- 3 tests spécifiques Attaques : OK;
- test d'intégration mis à jour;
- suite complète du dépôt, Canner et PostgreSQL de production non testés ici.

Vérification après déploiement
------------------------------
1. Ouvrir JDR > Attaques.
2. Vérifier les attaques existantes.
3. Ajouter une attaque simple.
4. La modifier.
5. Vérifier le bonus total.
6. Supprimer l'attaque de test si désiré.

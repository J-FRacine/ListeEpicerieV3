JDR V1.4.1 — Modularisation, phase 3
========================================

Base réelle vérifiée
--------------------
GitHub main : c83f607deb57673b539d22cf8ab549eb61464eed

La phase 2 est présente et validée par l'utilisateur :
- rpg_character_saves.py est actif;
- rpg_character.py raccorde déjà le panneau Sauvegardes;
- l'application fonctionne après déploiement.

Objectif
--------
Extraire un deuxième panneau réel : Progression.

Nouveau module :
- rpg_character_progression.py

Ce module contient l'assistant de montée de niveau et l'historique, avec les
mêmes champs, textes et actions que le panneau historique.

Architecture
------------
Les dépendances sont injectées par rpg_character.py :
- aucune importation directe de NiceGUI dans le nouveau module;
- aucune importation de db;
- aucune dépendance inverse vers rpg_character ou rpg_character_ui.

Comme pour Sauvegardes, le corps historique de _progression_panel reste encore
physiquement dans rpg_character_ui.py pendant la période de validation, mais
la façade le remplace à l'exécution par le nouveau module.

Cela permet de valider plusieurs extractions avant de faire un seul nettoyage
mécanique du gros fichier, ce qui réduit le risque.

Fichiers à téléverser
---------------------
Racine :
- rpg_character.py                  (remplacer)
- rpg_character_progression.py      (nouveau)

tests/ :
- test_rpg_character_integration.py (remplacer)
- test_rpg_character_progression.py (nouveau)

Ne pas modifier :
- rpg_character_ui.py
- rpg_character_saves.py
- app_versions.py
- requirements.txt
- PostgreSQL

Version
-------
JDR reste V1.4.1 : refactor interne, aucune nouvelle fonction utilisateur.

Validation locale
-----------------
- py_compile : OK pour les 4 fichiers livrés;
- 2 tests spécifiques Progression : OK;
- contrôles statiques de modularisation ajoutés au test d'intégration;
- suite complète du dépôt et Canner non exécutés ici.

Vérification après déploiement
------------------------------
1. Ouvrir JDR > Progression.
2. Vérifier le niveau, la classe et le BBA affichés.
3. Ouvrir « Monter au niveau suivant » sans nécessairement appliquer.
4. Vérifier que les 4 sections apparaissent.
5. Fermer/annuler.
6. Vérifier que l'historique existant, s'il y en a un, reste visible.

Si tout fonctionne, la phase 3 est validée.

JDR V1.4.1 — Modularisation, phase 2
========================================

Base réelle vérifiée
--------------------
GitHub main : 18dc85731d4109a60e4bcdf0c4199feaeec48018

La phase 1 est présente sur main :
- rpg_character.py est maintenant une façade courte;
- rpg_character_ui.py contient l'implémentation NiceGUI existante;
- l'utilisateur a confirmé le fonctionnement après déploiement.

Objectif de la phase 2
----------------------
Extraire un premier panneau réel : « Sauvegardes ».

Nouveau module :
- rpg_character_saves.py

Le module reçoit toutes ses dépendances par injection :
- aucune importation de NiceGUI;
- aucune importation de db;
- aucune dépendance inverse vers rpg_character ou rpg_character_ui.

La façade rpg_character.py raccorde le nouveau panneau au code historique.
Le point d'entrée public reste :
    from rpg_character import rpg_character_panel

Important
---------
Cette phase utilise un raccord de transition :
le vieux corps de _saves_panel reste encore physiquement dans
rpg_character_ui.py, mais il est remplacé à l'exécution par le nouveau module.

Ce choix réduit fortement le risque : après validation Canner, une phase de
nettoyage pourra supprimer le code devenu mort de rpg_character_ui.py.
Aucun comportement utilisateur volontaire n'est changé.

Fichiers à téléverser
---------------------
Racine :
- rpg_character.py          (remplacer)
- rpg_character_saves.py    (nouveau)

tests/ :
- test_rpg_character_integration.py  (remplacer)
- test_rpg_character_saves.py        (nouveau)

Aucune modification de :
- rpg_character_ui.py
- base PostgreSQL
- requirements.txt
- app_versions.py

Version
-------
JDR reste V1.4.1 : il s'agit d'un refactor interne sans nouvelle fonction.

Validation locale
-----------------
- py_compile : OK sur les 4 fichiers livrés.
- tests/test_rpg_character_saves.py : 2 tests réussis.
- contrôles statiques du raccord de façade inclus dans le test d'intégration.
- suite complète du dépôt, Canner et PostgreSQL de production non testés ici.

Vérification après déploiement
------------------------------
1. Ouvrir JDR.
2. Ouvrir l'onglet Sauvegardes.
3. Modifier une valeur (ex. Divers ou Temporaire).
4. Cliquer « Enregistrer les sauvegardes ».
5. Changer d'onglet puis revenir pour confirmer la persistance.
6. Ouvrir « Règles de calcul » depuis Sauvegardes.

Si ces points passent, la phase 2 est validée.

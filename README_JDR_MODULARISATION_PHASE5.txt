JDR V1.4.1 — Modularisation, phase 5
========================================

Base réelle vérifiée
--------------------
GitHub main : 36fc8b734d5820b4ed30bda45c790ea6d156f780

La phase 4 est présente et l'utilisateur a confirmé son fonctionnement.

Objectif
--------
Extraire le panneau Identité et profil racial.

Nouveau module :
- rpg_character_identity.py

Le module conserve notamment :
- identité générale;
- classe / sous-classe / niveau;
- race et héritage;
- profil racial;
- taille et vitesse de base;
- vision, langues et sous-types;
- capacité de charge;
- exceptions de vitesse;
- traits raciaux alternatifs;
- prévisualisation d'un changement de race;
- possibilité de conserver les valeurs actuelles;
- règle importante : le changement de race ne modifie jamais silencieusement
  les six scores de caractéristiques.

Fichiers à téléverser
---------------------
Racine :
- rpg_character.py                  (remplacer)
- rpg_character_identity.py         (nouveau)

tests/ :
- test_rpg_character_integration.py (remplacer)
- test_rpg_character_identity.py    (nouveau)

Ne pas modifier
---------------
- rpg_character_ui.py
- rpg_character_attacks.py
- rpg_character_progression.py
- rpg_character_saves.py
- app_versions.py
- requirements.txt
- PostgreSQL

Version
-------
JDR reste V1.4.1 : refactor interne, sans nouvelle fonction utilisateur.

Validation locale
-----------------
- py_compile : OK pour les 4 fichiers livrés;
- 3 tests spécifiques Identité : OK;
- test d'intégration mis à jour pour le quatrième module extrait;
- aucune connexion à PostgreSQL/Canner de production réalisée ici.

Vérification après déploiement
------------------------------
1. Ouvrir JDR > Identité.
2. Vérifier les valeurs existantes.
3. Modifier un champ simple puis enregistrer.
4. Tester le choix d'une autre race et ouvrir la prévisualisation.
5. Annuler ou choisir « Conserver mes valeurs » pour confirmer que les scores
   de caractéristiques ne changent pas.
6. Revenir à la race d'origine si le test l'a modifiée.

Si tout fonctionne, la phase 5 est validée.

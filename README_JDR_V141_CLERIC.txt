JDR — Fighter + Clerc niveaux 1 à 4 — candidat V1.4.1
================================================================

Base réelle utilisée
--------------------
GitHub main vérifié avant développement :
6a0c75b32dd5e42c8b2204d5278c561344a626a9

Le fichier rpg_character_creation.py de cette base correspond exactement au
correctif Identité -> Race déjà installé.

Fichiers applicatifs
--------------------
- rpg_character_guides.py
- rpg_character_creation.py

Fichiers de tests
-----------------
- tests/test_rpg_character_guides.py
- tests/test_rpg_character_creation_fighter.py
- tests/test_rpg_character_cleric.py

Ajouts Clerc / Cleric
---------------------
- Reconnaissance des libellés Clerc, Cleric et variantes simples.
- Repères niveaux 1 à 4 : d8, BBA, sauvegardes, canalisation et sorts/jour.
- Clerc niveau 4 : BBA +3, Vig +4, Réf +1, Vol +4, canalisation 2d6,
  4 oraisons, 3+1 sorts niveau 1, 2+1 sorts niveau 2.
- Aide pour dons, rangs de compétences, Skilled humain, canalisation selon CHA
  et DD indicatifs des sorts selon SAG.
- Compétences de classe Clerc identifiées et applicables en une action.
- Aide Humain pour Clerc : +2 flexible, SAG, don racial et Skilled.
- Rappel des deux domaines, divinité/concept divin et énergie canalisée.
- Aide armure adaptée : légère/intermédiaire, boucliers sauf pavois;
  l'échec des sorts profanes ne s'applique normalement pas aux sorts divins.
- Résumé Clerc enrichi.

Conservation
------------
- Toute l'aide Fighter reste présente.
- Le correctif Identité -> Race est conservé.
- Les 7 étapes restent identiques.
- Aucun changement de schéma PostgreSQL.
- Aucun nouveau paquet Python.
- Aucun choix de domaine, sort ou caractéristique n'est imposé automatiquement.

Validation effectuée ici
-------------------------
- py_compile : OK.
- 24 tests JDR ciblés : OK.
- Valeurs Clerc niveaux 1 à 4 vérifiées contre Pathfinder 1e Core Rulebook.

Non testé ici
-------------
- PostgreSQL de production;
- Canner;
- navigateur réel;
- suite complète de tous les tests du dépôt.

Version
-------
L'étiquette officielle reste V1.4.0 pendant le test navigateur.
Après validation, app_versions.py, manual.py et PROJECT_STATUS.md seront mis à jour
pour officialiser JDR V1.4.1.

Correctif JDR V1.4.1 candidat — passage Identité -> Race

Problème corrigé
----------------
Un nouveau personnage commence avec une race encore non choisie.
La couche de données refuse à juste titre d'enregistrer une race personnalisée sans nom,
ce qui bloquait le bouton « Enregistrer et suivant » dès l'étape Identité.

Correction
----------
- L'Identité reste dans l'état de l'assistant tant que la race n'est pas choisie.
- À l'étape Race, Identité + Race sont enregistrées ensemble.
- Aucune race temporaire ou inventée n'est écrite.
- Le champ « Sous-classe » devient « Sous-classe / archétype (facultatif) » avec
  l'indication de le laisser vide pour un Fighter standard.
- Aucun changement de schéma PostgreSQL.

Installation
------------
1. Remplacer à la racine : rpg_character_creation.py
2. Remplacer dans tests/ : test_rpg_character_creation_fighter.py

Validation locale
-----------------
- py_compile : OK
- 26 tests JDR ciblés : OK
- Canner / navigateur / PostgreSQL de production : non testés ici

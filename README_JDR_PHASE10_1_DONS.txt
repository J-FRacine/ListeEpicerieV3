JDR — Phase 10.1 : deux dons supplémentaires
================================================

Base utilisée
-------------
Dépôt : J-FRacine/ListeEpicerieV3
Branche : main
Commit observé : ca1f6d927e368f29fa2c6b4080e51849c30d4189

Modification
------------
Deux modèles sont ajoutés dans la liste « Modèle facultatif » de l’onglet Dons :

- Incantation en combat — Combat Casting
- Canalisation sélective — Selective Channeling

Les deux sont classés « Activable » parce qu’ils sont situationnels.

Combat Casting
--------------
Le modèle rappelle le bonus de +4 aux tests de concentration pour lancer un sort
ou utiliser un pouvoir magique en lançant sur la défensive ou en étant agrippé.
La feuille ne possède pas encore de calcul de concentration : aucun bonus
numérique n’est donc appliqué automatiquement aux statistiques existantes.

Selective Channeling
--------------------
Le modèle conserve les prérequis CHA 13 + Canalisation d’énergie et rappelle que
le nombre de cibles pouvant être exclues peut aller jusqu’au modificateur de
Charisme. Le don ne modifie pas automatiquement les dés ni le DD de canalisation.

Installation
------------
À la racine :
- REMPLACER uniquement rpg_character_feats_catalog.py

Facultatif, dans tests/ :
- AJOUTER tests/test_rpg_character_feats_catalog_phase10_1.py

Aucun changement de base de données.
Aucun SQL manuel.
Aucune nouvelle dépendance.

Validation locale
-----------------
- py_compile : OK
- tests ciblés catalogue : 2/2 OK

Non testé ici
-------------
- PostgreSQL de production
- Canner
- navigateur NiceGUI réel

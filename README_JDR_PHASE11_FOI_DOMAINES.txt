JDR — Phase 11 : Foi, divinité et domaines
==============================================

Base réellement utilisée
-------------------------
Dépôt : J-FRacine/ListeEpicerieV3
Branche : main
Commit observé : ac5fcaf886e76aafd27c200e991847acfc24ddbc

La phase 10 Dons et la phase 10.1 (Combat Casting / Selective Channeling)
étaient déjà installées et validées dans l'application avant cette livraison.

Objectif
--------
Structurer la foi du personnage sans inventer de domaines propres à une
divinité ou à Ravenloft.

Fonctions ajoutées
------------------
- nouvel onglet « Foi »;
- Divinité;
- Domaine 1;
- Sous-domaine 1 facultatif;
- Domaine 2;
- Sous-domaine 2 facultatif;
- notes de foi / campagne;
- rappel non bloquant pour les personnages Clerc / Cleric;
- aucune modification automatique des caractéristiques, sorts, canalisation,
  DD ou pouvoirs de domaine.

Décision importante
--------------------
La divinité n'est PAS dupliquée : le nouvel onglet utilise toujours la colonne
historique rpg_characters.deity, déjà utilisée dans Identité. Une modification
dans Foi est donc visible dans Identité au prochain rechargement, et inversement.

Les domaines restent en saisie libre. Aucun domaine d'Ezra ou d'une autre
divinité n'est présumé automatiquement.

Migration automatique
----------------------
À la première ouverture de la section, l'application ajoute si nécessaire :
- domain_1
- subdomain_1
- domain_2
- subdomain_2
- faith_notes

Les colonnes sont ajoutées avec ADD COLUMN IF NOT EXISTS.
Aucun SQL manuel.
Aucune donnée existante supprimée.

Fichiers à installer
--------------------
À la racine :
- REMPLACER rpg_character.py
- REMPLACER rpg_character_ui.py
- AJOUTER rpg_character_faith.py
- AJOUTER rpg_character_faith_data.py

Dans tests/ :
- REMPLACER test_rpg_character_integration.py
- AJOUTER test_rpg_character_faith_architecture.py
- AJOUTER test_rpg_character_faith_ui.py

Ne pas remplacer rpg_character_feats_catalog.py : la version Phase 10.1
actuellement sur main contient déjà Combat Casting et Selective Channeling.

Version
-------
L'affichage reste temporairement en V1.4.1 pendant cette validation.
Après validation navigateur/Canner de Foi, la finalisation V1.5.0 pourra
officialiser ensemble Dons + Foi/Domaines et mettre à jour versions, notes,
manuel et PROJECT_STATUS.

Validation locale réalisée
---------------------------
- py_compile : OK sur tous les fichiers Python livrés;
- tests Foi / migration / architecture : 6 tests;
- tests d'intégration structurelle : 5 tests;
- total ciblé : 11/11 OK.

Non testé ici
-------------
- PostgreSQL de production;
- Canner;
- navigateur NiceGUI réel;
- migration sur la base de production.

Test manuel recommandé
----------------------
1. Ouvrir un personnage Clerc et l'onglet Foi.
2. Vérifier que la divinité existante apparaît déjà.
3. Saisir les deux domaines et, si nécessaire, les sous-domaines.
4. Enregistrer puis recharger.
5. Retourner dans Identité et confirmer que la même divinité est affichée.
6. Modifier la divinité dans Identité, enregistrer, puis revenir dans Foi.
7. Vérifier qu'aucun score, sort, don ou calcul de combat n'a été modifié.

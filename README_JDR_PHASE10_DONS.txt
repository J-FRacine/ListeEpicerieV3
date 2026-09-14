JDR — Phase 10 : Dons structurés et Combat rapide
==================================================

Base réellement utilisée
-------------------------
Dépôt : J-FRacine/ListeEpicerieV3
Branche : main
Commit observé : 2e82e7e151830afd52ceeb73e31c3682de5378e7

La phase 9 de nettoyage avait déjà été déployée et validée.

Objectif
--------
Ajouter une vraie section Dons par personnage, sans perdre les anciennes notes
de progression, et permettre aux dons passifs/activables d'alimenter Combat
rapide de façon contrôlée.

Fonctions ajoutées
------------------
- nouvel onglet Dons;
- ajout, modification, suppression et fiche de détails;
- catégories Passif / Activable / Informatif;
- nom français + anglais;
- source, prérequis, résumé, effets et notes personnelles;
- lien facultatif vers une attaque précise;
- modificateurs structurés de Combat rapide :
  attaque, initiative, BMO/CMB, DMD/CMD et sauvegarde ciblée;
- note textuelle pour les dégâts, sans tenter de réécrire une formule de dés;
- dons passifs appliqués automatiquement dans Combat rapide;
- dons activables avec case « Utiliser » uniquement pour la session;
- les dons informatifs n'altèrent jamais les chiffres;
- les modificateurs ne réécrivent pas les valeurs permanentes du personnage.

Catalogue de départ
--------------------
Quelques modèles servent à préremplir le formulaire :
- Attaque en puissance / Power Attack;
- Arme de prédilection / Weapon Focus;
- Science de l'initiative / Improved Initiative;
- Vigueur surhumaine / Great Fortitude;
- Réflexes surhumains / Lightning Reflexes;
- Volonté de fer / Iron Will;
- Robustesse / Toughness.

Les modèles restent éditables. Pour Attaque en puissance, les valeurs numériques
ne sont PAS inventées automatiquement : elles doivent être adaptées au BBA et à
la manière de manier l'arme du personnage.

Base de données
---------------
La nouvelle table rpg_character_feats est créée automatiquement à la première
utilisation. Aucun SQL manuel.

Supprimer un personnage supprime ses dons par CASCADE. Si une attaque liée est
supprimée, le don est conservé et son lien d'attaque devient NULL.

Fichiers à installer
--------------------
À la racine :
- REMPLACER rpg_character.py
- REMPLACER rpg_character_ui.py
- REMPLACER rpg_combat_session.py
- AJOUTER rpg_character_feats.py
- AJOUTER rpg_character_feats_catalog.py
- AJOUTER rpg_character_feats_data.py
- AJOUTER rpg_character_feats_rules.py

Dans tests/ :
- REMPLACER test_rpg_character_integration.py
- AJOUTER test_rpg_character_feats_rules.py
- AJOUTER test_rpg_character_feats_architecture.py
- AJOUTER test_rpg_combat_session_feats.py

Aucun autre fichier applicatif n'est requis pour cette phase de validation.

Version pendant validation
--------------------------
JDR reste temporairement affiché en V1.4.1 pendant le test Canner, comme pour les
phases précédentes de validation. Après confirmation que la phase 10 fonctionne,
la finalisation courte passera JDR à V1.5.0 et mettra à jour :
- app_versions.py;
- les notes de version;
- le manuel;
- PROJECT_STATUS.

Ce choix évite d'officialiser une version utilisateur avant le test réel dans
le navigateur et PostgreSQL de production.

Validation réalisée ici
------------------------
- py_compile : OK pour tous les fichiers livrés;
- tests purs des effets de dons : 4/4 OK;
- test Combat rapide avec dons : 1/1 OK;
- tests d'architecture Phase 10 : 4/4 OK;
- tests d'intégration structurelle : 4/4 OK;
- total ciblé : 13/13 OK.

Non testé ici
-------------
- PostgreSQL de production;
- Canner;
- navigateur NiceGUI réel;
- suite complète historique du dépôt.

Test manuel recommandé après déploiement
----------------------------------------
1. Ouvrir Dons.
2. Ajouter « Science de l'initiative » depuis le modèle.
3. Ajouter « Arme de prédilection » et la lier à une attaque existante.
4. Ajouter « Attaque en puissance » comme Activable et saisir les valeurs
   correspondant au personnage.
5. Ouvrir Combat rapide.
6. Vérifier que Science de l'initiative apparaît comme Passif.
7. Changer d'attaque et confirmer qu'Arme de prédilection ne modifie que
   l'attaque liée.
8. Cocher/décocher « Utiliser » pour Attaque en puissance et vérifier que le
   bonus d'attaque change immédiatement.
9. Fermer sans enregistrer : l'état activé/désactivé du don ne doit pas rester
   actif lors du prochain combat.
10. Vérifier que les anciennes notes de Dons dans Progression sont toujours là.

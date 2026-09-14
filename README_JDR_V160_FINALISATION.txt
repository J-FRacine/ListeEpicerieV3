JDR V1.6.0 — FINALISATION AUTOMATIQUE
======================================

But
---
Officialiser le portrait / photo du personnage que vous venez de valider
dans le navigateur/Canner.

Cette finalisation ne change PAS le fonctionnement du portrait.
Elle met seulement à jour :
- le numéro de version;
- les notes de version;
- le manuel;
- PROJECT_STATUS;
- le test d'intégration.

Base observée
-------------
Dépôt : J-FRacine/ListeEpicerieV3
Branche : main
Commit observé : eb1d83b396d596319134be87a0e9b9d611a202d3

La phase Portrait est déjà présente dans ce commit et l'utilisateur a confirmé :
« parfait ca fonctionne ».

Utilisation
-----------
1. Sur GitHub, téléchargez le dépôt actuel avec « Download ZIP ».
2. Décompressez le dépôt.
3. Copiez les 3 fichiers de ce paquet à la RACINE du dossier décompressé :
   - finalize_jdr_v160.py
   - APPLIQUER_JDR_V160.bat
   - README_JDR_V160_FINALISATION.txt
4. Double-cliquez APPLIQUER_JDR_V160.bat.
5. Le script crée :
   JDR_V160_FINAL_FICHIERS_A_UPLOADER.zip
6. Téléversez le contenu de ce nouveau ZIP dans GitHub en conservant les chemins.

Fichiers produits
-----------------
- app_versions.py
- manual.py
- PROJECT_STATUS.md
- tests/test_rpg_character_integration.py

Le script crée aussi :
_backup_avant_JDR_V160

Ce dossier contient les quatre fichiers originaux avant modification.

Ce qui devient officiel
-----------------------
- JDR passe de V1.5.0 à V1.6.0.
- Le portrait est documenté dans les Nouveautés et le manuel.
- PROJECT_STATUS consigne la validation réelle de l'utilisateur.
- La prochaine phase devient :
  armes détaillées et lien Équipement <-> Attaques.

Contrôles automatiques
----------------------
Le script :
- vérifie que les trois modules Portrait sont présents;
- vérifie le raccordement du portrait dans rpg_character.py;
- vérifie l'affichage du portrait dans rpg_character_ui.py;
- vérifie que Pillow est dans requirements.txt;
- crée une sauvegarde avant modification;
- met à jour les quatre fichiers;
- compile les fichiers Python touchés;
- charge app_versions.py et vérifie JDR 1.6.0;
- vérifie la présence des nouvelles sections Manuel et PROJECT_STATUS;
- vérifie le raccordement Portrait dans le test d'intégration;
- restaure les originaux en cas d'échec;
- crée le ZIP final seulement si tous les contrôles réussissent.

Base de données
---------------
Cette finalisation n'ajoute aucune migration supplémentaire et n'exécute
aucun SQL.

La table rpg_character_portraits a déjà été ajoutée automatiquement par la
phase fonctionnelle Portrait.

Non testé indépendamment par ChatGPT
------------------------------------
- PostgreSQL de production;
- Canner / Render;
- navigateur après le simple changement de numéro de version.

La fonction elle-même a toutefois été validée en déploiement par l'utilisateur.

Après V1.6.0
------------
Prochaine phase :
armes détaillées et lien Équipement <-> Attaques.

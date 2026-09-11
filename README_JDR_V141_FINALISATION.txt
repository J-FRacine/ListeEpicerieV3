JF Apps — finalisation JDR V1.4.1
=================================

Base GitHub vérifiée avant préparation :
fde33144220983233e351f0c4a4dbf53a57e1a2a

But
---
Ce petit utilitaire applique automatiquement la finalisation documentaire et de version
JDR V1.4.1 sur une copie LOCALE actuelle du dépôt, puis fabrique un ZIP contenant les
4 fichiers complets prêts à téléverser dans GitHub.

Il modifie uniquement :
- app_versions.py
- manual.py
- PROJECT_STATUS.md
- tests/test_rpg_character_integration.py

Il ne modifie pas rpg_character.py, rpg_character_creation.py, rpg_character_guides.py,
Finances ni la base PostgreSQL.

Utilisation la plus simple sous Windows
---------------------------------------
1. Dans GitHub, télécharger le dépôt ListeEpicerieV3 en ZIP puis l'extraire.
2. Copier dans le dossier racine extrait :
   - finalize_jdr_v141.py
   - APPLIQUER_JDR_V141.bat
3. Double-cliquer APPLIQUER_JDR_V141.bat.
4. Le script crée JDR_V141_FINAL_FICHIERS_A_UPLOADER.zip dans ce même dossier.
5. Téléverser dans GitHub les 4 fichiers contenus dans ce ZIP en conservant leurs chemins.

Sécurité
--------
- Le script exige des repères précis correspondant à l'état actuel attendu.
- Si un repère important est absent ou ambigu, il s'arrête au lieu de deviner.
- Une copie des 4 fichiers d'origine est conservée dans _backup_avant_JDR_V141.
- Les fichiers Python modifiés sont compilés avant que le ZIP final soit annoncé.
- Aucune connexion PostgreSQL n'est faite.
- Aucun test Canner/Render n'est prétendu par cet utilitaire.

Après téléversement
-------------------
Vérifier que Canner redémarre, puis ouvrir JDR. La version affichée doit être 1.4.1.
Les fonctions existantes (création guidée, Combat rapide, Fighter et Clerc) ne sont pas
modifiées par cette finalisation.

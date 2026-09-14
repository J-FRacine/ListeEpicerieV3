JDR — Phase 12 : Portrait / photo du personnage
=================================================

Base réellement utilisée
-------------------------
Dépôt : J-FRacine/ListeEpicerieV3
Branche : main
Commit observé : 0baa0dd77c33c1528b6eb6414ba3aa8fbc305996
Version JDR actuelle : 1.5.0

Fonctions ajoutées
------------------
- emplacement portrait directement à gauche du nom;
- ajout d'une photo;
- remplacement;
- suppression avec confirmation;
- clic sur le portrait pour l'agrandir;
- persistance dans PostgreSQL.

Stockage
--------
Le portrait est stocké dans une table dédiée :
rpg_character_portraits

Cela évite de dépendre du disque local de Canner, dont la persistance entre
déploiements n'a pas été vérifiée.

Une seule photo existe par personnage. La suppression du personnage supprime
son portrait par ON DELETE CASCADE. Les accès vérifient user_id + character_id.

Traitement des images
---------------------
Formats : JPEG, PNG et WEBP.
Maximum : 8 Mo et 25 mégapixels.

Avant stockage :
- orientation EXIF;
- maximum 1000 x 1000 px;
- transparence sur fond blanc;
- conversion JPEG qualité 86;
- pas de recopie des métadonnées du fichier original.

Dépendance
----------
Pillow est ajoutée à requirements.txt.

Migration automatique
----------------------
CREATE TABLE IF NOT EXISTS rpg_character_portraits.
Aucun SQL manuel.

Installation
------------
À la racine, REMPLACER :
- rpg_character.py
- rpg_character_ui.py
- requirements.txt

À la racine, AJOUTER :
- rpg_character_portrait.py
- rpg_character_portrait_data.py
- rpg_character_portrait_images.py

Dans tests/, AJOUTER :
- test_rpg_character_portrait_images.py
- test_rpg_character_portrait_architecture.py

Version
-------
JDR reste V1.5.0 pendant cette validation.
Après validation navigateur/Canner, finalisation prévue en V1.6.0.

Validation locale
-----------------
- bases rpg_character.py et rpg_character_ui.py vérifiées contre les SHA GitHub
  du main actuel;
- py_compile : OK sur tous les fichiers Python livrés;
- traitement d'image : 8/8 tests;
- architecture : 5/5 tests;
- total ciblé : 13/13 OK.

Non testé ici
-------------
- PostgreSQL de production;
- migration réelle de production;
- Canner / Render;
- navigateur NiceGUI réel;
- upload réel depuis téléphone;
- inclusion du portrait dans la sauvegarde globale.

Test manuel recommandé
----------------------
1. Ouvrir un personnage.
2. Cliquer Photo à gauche du nom.
3. Ajouter un JPEG ou PNG.
4. Vérifier l'affichage dans la bannière.
5. Cliquer la photo pour l'agrandir.
6. Recharger la page : la photo doit rester présente.
7. Remplacer la photo.
8. Supprimer la photo et confirmer que le personnage reste intact.
9. Tester depuis un téléphone si possible.

Après validation
----------------
Finalisation V1.6.0, puis armes détaillées et lien Équipement <-> Attaques.

JDR — Phase 11.1 : préconfiguration Iomedae
============================================

Cette livraison remplace la Phase 11 précédente si elle n'est pas encore
installée. Elle contient toujours Foi / Divinité / Domaines et ajoute un profil
de référence Iomedae.

Préconfiguration Iomedae
------------------------
La section Foi affiche maintenant :
- alignement LG;
- domaines Glory, Good, Law, Sun, War;
- sous-domaines de référence regroupés par domaine;
- arme favorite : épée longue;
- symbole : épée et soleil;
- couleurs sacrées : rouge et blanc;
- animal sacré : lion;
- sorts particuliers Clerc / Warpriest indiqués comme référence future.

Le bouton « Préconfigurer Iomedae + Guerre / Soleil » remplit :
- Divinité : Iomedae;
- Domaine 1 : War (Guerre);
- Domaine 2 : Sun (Soleil).

Ce duo War/Sun est un préréglage personnel pour le personnage actuel, pas
une règle générale d'Iomedae. Les deux champs restent entièrement modifiables.

Fichiers
--------
À la racine :
- REMPLACER rpg_character.py
- REMPLACER rpg_character_ui.py
- REMPLACER rpg_character_faith.py
- AJOUTER rpg_character_faith_data.py
- AJOUTER rpg_character_deities_catalog.py

Dans tests/ :
- REMPLACER test_rpg_character_integration.py
- AJOUTER test_rpg_character_faith_architecture.py
- AJOUTER test_rpg_character_faith_ui.py
- AJOUTER test_rpg_character_iomedae_catalog.py
- AJOUTER test_rpg_character_faith_iomedae.py
- AJOUTER test_rpg_character_faith_iomedae_preset.py

Base de données
---------------
Même migration automatique que Phase 11 :
domain_1, subdomain_1, domain_2, subdomain_2 et faith_notes.
Aucun SQL manuel.

Validation locale
-----------------
Compilation Python : OK.
Tests ciblés Foi + Iomedae + intégration : OK.

Non testé ici
-------------
PostgreSQL de production, Canner et navigateur réel.

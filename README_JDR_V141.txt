JDR — évolution Fighter / équipement — candidat V1.4.1
========================================================

Base utilisée
-------------
GitHub main : bc3769a63aa34d2a408a8560035ed8a5484546cf
JDR officiel avant installation : V1.4.0

Fichiers applicatifs à placer à la RACINE du dépôt
--------------------------------------------------
- rpg_character_guides.py       (nouveau)
- rpg_character_creation.py     (remplacement complet)

Fichiers de tests à placer dans tests/
---------------------------------------
- test_rpg_character_guides.py
- test_rpg_character_creation_fighter.py

Fonctions ajoutées
------------------
- Repères Fighter / Guerrier niveaux 1 à 4 dans la création guidée.
- Rappels BBA, sauvegardes de base, dons, Bravoure et Entraînement aux armures.
- Aide au calcul des rangs de compétences Fighter et marquage des compétences de classe.
- Comparatif Humain / Elfe pour un Fighter qui envisage une orientation magique.
- Rappel clair qu'un Fighter pur ne reçoit pas de sorts simplement parce qu'il est Elfe.
- Catalogue de référence d'armes et armures courantes :
  chemise de mailles, cuirasse, cotte de mailles, harnois complet,
  bouclier lourd en acier, épée longue, rapière, épée à deux mains et arc long.
- Les valeurs du catalogue indiquent directement quoi saisir dans Équipement et Attaques.
- Rappels sur l'échec des sorts profanes et Entraînement aux armures 1.
- Résumé de création enrichi pour Fighter et équipement actif.

Important sur l'équipement
--------------------------
L'application JDR actuelle possédait déjà le moteur nécessaire :
- une armure/bouclier marqué Équipé influence la CA, le bonus DEX maximal,
  la pénalité d'armure, le poids et la vitesse;
- une arme est conservée dans Équipement pour son poids/possession et dans Attaques
  pour son jet d'attaque, ses dégâts, son critique et sa portée;
- Combat rapide réutilise les attaques enregistrées.

Cette évolution rend ces mécanismes beaucoup plus faciles à remplir, mais ne crée
pas de nouvelle logique Pathfinder automatique risquée et ne modifie pas le schéma SQL.

Validation effectuée ici
------------------------
- py_compile : OK pour les deux modules et les nouveaux tests.
- 16 nouveaux tests : OK.
- Les 8 tests purs existants de rpg_character_creation.py ont également été rejoués
  sur la nouvelle version : OK.
- Total local ciblé exécuté : 24 tests, tous réussis.

Non testé ici
-------------
- Suite complète du dépôt (environnement complet non disponible dans cette session).
- PostgreSQL de production.
- Navigateur réel / Canner.

Version
-------
Ce paquet est volontairement livré comme CANDIDAT V1.4.1 sans modifier app_versions.py
ni le manuel avant validation sur Canner. Après validation utilisateur, la version et
les notes de version pourront être finalisées dans un très petit passage séparé.

Références de règles
--------------------
Pathfinder RPG Core Rulebook : Fighter, races Human/Elf, armes et armures standards.

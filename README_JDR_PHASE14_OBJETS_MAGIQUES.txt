JDR — Phase 14 : Objets magiques
================================

Base requise
-------------
JDR V1.7.0 finalisée et validée localement :
- 26 tests ciblés OK;
- 152 tests JDR OK;
- 450 tests JF Apps OK;
- validation Canner/navigateur de la Phase 13 réussie.

Version
-------
Phase 14 finalisée officiellement en JDR V1.8.0 après validation locale et
validation fonctionnelle Canner/navigateur par l’utilisateur.

Objectif
--------
Objectif
--------
Ajouter des objets magiques à l'Équipement existant sans créer un second
inventaire et sans réécrire les valeurs permanentes de la fiche.

Architecture
------------
Nouveaux modules spécialisés :
- rpg_character_magic_catalog.py
- rpg_character_magic_schema.py
- rpg_character_magic_data.py
- rpg_character_magic_rules.py
- rpg_character_magic_dialog.py

Nouvelles tables PostgreSQL créées automatiquement et de façon non destructive :
- rpg_character_magic_item_details
- rpg_character_equipment_containment

Aucun SQL manuel.

Modèles de référence
--------------------
1. Cloak of Resistance
   - modèle +1 par défaut;
   - bonus configurable;
   - le meilleur bonus de résistance actif est appliqué à Vigueur, Réflexes et
     Volonté;
   - le bonus exige que le cloak soit équipé/porté;
   - les bonus de résistance ne sont pas additionnés entre eux;
   - aucune valeur permanente de Sauvegarde n'est réécrite.

2. Wand of Cure Light Wounds
   - 50 charges par défaut;
   - NLS/CL 1 par défaut;
   - sort contenu : Cure Light Wounds;
   - bouton Utiliser 1 charge;
   - chaque utilisation décrémente le compteur en base;
   - l'application n'applique pas automatiquement les soins à une cible pendant
     cette phase; cette intégration sera faite avec Sorts/Combat rapide;
   - au CL 1, l'effet de référence est 1d8+1 PV.

3. Handy Haversack
   - poids propre : 5 lb;
   - capacité totale suivie : 120 lb;
   - depuis la fiche du sac, « Contenu du conteneur » permet de cocher directement les équipements rangés dedans;
   - les objets déjà contenus sont présélectionnés et décocher un objet le retire du sac;
   - un objet déjà rangé dans un autre conteneur est déplacé vers le haversack lorsqu’il est sélectionné;
   - le champ individuel « Rangé dans » reste disponible sur chaque équipement;
   - le contenu ne rajoute pas son poids normal à l'encombrement du personnage;
   - le poids du sac reste 5 lb;
   - la capacité est contrôlée avant le rangement;
   - un conteneur magique ne peut pas être rangé dans un autre conteneur magique
     dans cette phase;
   - la suppression du sac retire les liens de rangement mais conserve les objets.

Sources de règles vérifiées
---------------------------
- Pathfinder RPG / Archives of Nethys / Ultimate Equipment : Cloak of Resistance
  donne un bonus de résistance de +1 à +5 à tous les jets de sauvegarde et pèse
  1 lb.
- Pathfinder RPG Core Rulebook : une baguette est créée avec 50 charges.
- Cure Light Wounds : 1d8 + 1 par niveau de lanceur, maximum +5.
- Handy Haversack : 5 lb; deux poches de 20 lb et compartiment central de 80 lb,
  donc 120 lb au total; le sac reste à 5 lb; récupérer un objet précis est une
  action de mouvement qui ne provoque pas normalement d'attaque d'opportunité.

Validation navigateur/Canner réalisée
--------------------------------------
La validation fonctionnelle a été effectuée avec succès par l’utilisateur pour le
dialogue Objet magique et la gestion directe du contenu du Handy Haversack.

Après validation
----------------
Validation finale V1.8.0
------------------------
- tests ciblés Phase 14 + non-régression : 47/47 OK;
- tous les tests JDR : 174/174 OK;
- suite complète JF Apps : 472/472 OK;
- validation fonctionnelle Canner / navigateur : réussie par l’utilisateur;
- dialogue Objet magique : validé;
- contenu direct du Handy Haversack : validé;
- PostgreSQL de production n’a pas été testé indépendamment par ChatGPT.

Phase 14 finalisée officiellement en JDR V1.8.0.
Prochaine grande fonction JDR : Sorts.

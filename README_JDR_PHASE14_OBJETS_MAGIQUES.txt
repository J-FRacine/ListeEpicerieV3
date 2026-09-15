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
La version officielle reste JDR V1.7.0 pendant la validation de cette phase.
Après validation fonctionnelle Canner/navigateur, finalisation prévue en V1.8.0.

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
   - un objet peut être configuré comme « Rangé dans » le haversack;
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

Validation navigateur/Canner recommandée
-----------------------------------------
A. Cloak of Resistance
1. Ouvrir Équipement > Objet magique.
2. Choisir le modèle Cloak of Resistance.
3. Enregistrer avec +1 et Équipé/porté activé.
4. Ouvrir Sauvegardes : Vigueur, Réflexes et Volonté doivent gagner +1.
5. Peur, Horreur et Folie ne doivent pas recevoir ce bonus automatique.
6. Déséquiper le cloak : le +1 doit disparaître après rafraîchissement.
7. Rééquiper : le +1 doit revenir.
8. Vérifier que les champs Magie/Divers/Temporaire existants n'ont pas été
   réécrits automatiquement.

B. Wand of Cure Light Wounds
1. Ajouter le modèle Wand of Cure Light Wounds.
2. Régler temporairement les charges à 3 / 50 pour faciliter le test.
3. Vérifier l'affichage du sort et des charges.
4. Cliquer Utiliser 1 charge : le compteur doit passer à 2.
5. Vérifier qu'aucun PV n'est modifié automatiquement.

C. Handy Haversack
1. Ajouter le modèle Handy Haversack.
2. Vérifier 5 lb et capacité 120 lb.
3. Ajouter ou choisir un objet existant de poids connu, par exemple 10 lb.
4. Utiliser l'icône magique/rangement sur cet objet et choisir Handy Haversack
   dans Rangé dans, sans devoir cocher Objet magique.
5. Vérifier que l'objet indique son rangement dans le sac.
6. Vérifier que l'encombrement total compte le sac à 5 lb mais pas les 10 lb du
   contenu.
7. Retirer l'objet du champ Rangé dans : ses 10 lb doivent revenir dans
   l'encombrement.
8. Essayer de dépasser 120 lb : l'enregistrement doit être refusé.

Après validation
----------------
Finalisation officielle JDR V1.8.0 : version, notes de version, manuel et
PROJECT_STATUS.md finalisés, puis prochaine grande fonction : Sorts.

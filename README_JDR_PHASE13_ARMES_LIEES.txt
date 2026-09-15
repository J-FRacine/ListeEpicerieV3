JDR — Phase 13 : Armes détaillées et lien Équipement <-> Attaques
===================================================================

Base réellement utilisée
-------------------------
Dépôt : J-FRacine/ListeEpicerieV3
Branche : main
Commit observé : 3208b25228bce2b9603daf0e0261d5cbe83f9e6c
Version JDR officielle au début de la phase : 1.6.0
Version JDR officielle après validation : 1.7.0

Objectif
--------
Conserver une seule arme physique dans Équipement et permettre aux Attaques
d'utiliser cette arme sans dupliquer ses caractéristiques.

Équipement = l'objet physique.
Attaques = la façon dont le personnage l'utilise.

Nouveaux détails d'une arme
---------------------------
- dégâts de base;
- critique;
- type de dégâts;
- portée;
- catégorie légère / une main / deux mains / distance / autre;
- arme de maître;
- bonus magique / altération;
- type de munitions;
- munitions actuelles et maximums;
- maîtrise requise;
- modèle d'arme facultatif.

Lien vers Attaques
------------------
Une attaque peut sélectionner une arme existante dans Équipement.

Lorsqu'elle est liée :
- le bonus propre à l'arme alimente automatiquement le bonus d'attaque;
- une arme de maître apporte +1 à l'attaque;
- un bonus magique supérieur remplace ce +1 au lieu de s'y additionner;
- dégâts, critique, portée et type peuvent être hérités de l'arme si les champs
  propres à l'attaque sont laissés vides;
- les munitions de l'arme physique deviennent la source affichée;
- l'attaque peut préciser une utilisation à une main ou à deux mains;
- une même arme peut servir à plusieurs attaques différentes.

Les dégâts propres à l'attaque restent un champ texte afin de laisser le
personnage intégrer Force, dons, effets temporaires et autres règles sans que
l'application invente une formule.

Combat rapide
-------------
Combat rapide reçoit maintenant la liste d'attaques enrichie par la façade.
Le bonus d'attaque lié à l'arme ainsi que les valeurs héritées sont donc
disponibles sans remplacer rpg_combat_session.py.

Équipement -> création d'attaque
--------------------------------
Une arme sans attaque liée affiche une action permettant de créer son attaque.
Avant de créer, l'application re-vérifie qu'aucune attaque n'est déjà liée afin
d'éviter les doublons évidents.

Iomedae
-------
Pour un personnage dont la divinité est Iomedae, Équipement propose :
« Épée longue d'Iomedae ».

Le modèle préremplit pour une taille Moyenne :
- Épée longue;
- 1d8;
- 19-20/x2;
- Tranchant;
- une main;
- 4 lb;
- 15 po;
- maîtrise : Armes de guerre.

Pour une taille Petite, le modèle propose 1d6.
Pour les autres tailles, les dégâts restent volontairement vides.

Migration automatique
----------------------
Deux tables sont créées automatiquement :
- rpg_character_weapon_details;
- rpg_character_attack_weapon_links.

Aucun SQL manuel.

La suppression d'une arme retire automatiquement ses détails et ses liens.
Les Attaques elles-mêmes sont conservées : elles deviennent indépendantes.

Compatibilité
-------------
- anciennes armes conservées;
- anciennes Attaques conservées;
- aucune conversion forcée;
- une Attaque non liée fonctionne comme avant;
- le Bonus magique historique est conservé pour une attaque indépendante;
- lorsqu'une arme est liée, son bonus devient la source réelle du bonus d'arme.

Stabilisation incluse
---------------------
La façade contourne aussi l'ancien cas PostgreSQL où une nouvelle armure ou un
nouveau bouclier coché « Équipé » dès sa création pouvait transmettre un NULL
non typé. L'objet est d'abord créé puis équipé avec son vrai identifiant.

Fichiers à installer
--------------------
REMPLACER à la racine :
- rpg_character.py
- rpg_character_equipment.py
- rpg_character_equipment_dialogs.py
- rpg_character_attacks.py

AJOUTER à la racine :
- rpg_character_weapon_catalog.py
- rpg_character_weapon_schema.py
- rpg_character_weapon_data.py
- rpg_character_weapon_rules.py

Dans tests/, AJOUTER :
- test_rpg_character_weapon_rules.py
- test_rpg_character_weapon_catalog.py
- test_rpg_character_weapon_architecture.py

Ne pas remplacer :
- rpg_character_data.py
- rpg_character_ui.py
- rpg_combat_session.py

Version
-------
La validation navigateur/Canner est terminée avec succès.
La phase est finalisée officiellement en JDR V1.7.0.

Validation locale
-----------------
- py_compile : OK sur tous les fichiers Python livrés;
- tests ciblés : 14/14 OK.

Non testé ici
-------------
- PostgreSQL de production;
- migration réelle de production;
- Canner / Render;
- navigateur NiceGUI réel;
- création d'une vraie attaque liée dans PostgreSQL.

Test manuel recommandé
----------------------
1. Ouvrir Équipement.
2. Pour Iomedae, cliquer Épée longue d'Iomedae.
3. Enregistrer puis cliquer l'icône de lien sur l'arme.
4. Ouvrir Attaques et vérifier le lien avec l'Équipement.
5. Tester la prise Une main / Deux mains.
6. Mettre l'arme de maître : le bonus total doit gagner +1.
7. Ajouter un bonus magique +2 : il doit remplacer le +1 de maître.
8. Ouvrir Combat rapide et vérifier le même bonus.
9. Supprimer le lien : l'attaque doit rester présente.
10. Supprimer l'arme : l'attaque doit rester présente mais non liée.

Après validation
----------------
Finalisation JDR V1.7.0 terminée.
Prochaine grande fonction : Sorts.

Validation finale V1.7.0
------------------------
- tests ciblés Phase 13 et panneaux : 20/20 OK;
- tous les tests JDR : 152/152 OK;
- suite complète JF Apps : 450/450 OK;
- validation fonctionnelle Canner / navigateur : réussie par l’utilisateur;
- PostgreSQL de production n’a pas été testé indépendamment par ChatGPT.

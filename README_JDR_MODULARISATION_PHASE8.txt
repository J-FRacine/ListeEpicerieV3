JDR V1.4.1 — Modularisation phase 8 : Combat
================================================

Base réellement utilisée
-------------------------
Dépôt : J-FRacine/ListeEpicerieV3
Branche : main
Commit observé : d942bdd83fdebdb077795ab76c67aa23386734f8

Cette base contient déjà :
- phases 1 à 7 de modularisation;
- migration automatique de l'équipement;
- Compétences extraites;
- diagnostic Canner temporaire dans rpg_character.py.

But
---
Extraire l'onglet Combat de rpg_character_ui.py sans changer son comportement.

Fichiers
--------
Racine :
- REMPLACER rpg_character.py
- AJOUTER rpg_character_combat.py

Tests :
- REMPLACER tests/test_rpg_character_integration.py
- AJOUTER tests/test_rpg_character_combat.py

Ne pas modifier
---------------
- rpg_character_ui.py
- rpg_character_data.py
- rpg_character_equipment.py
- rpg_character_equipment_schema.py
- les autres modules JDR déjà extraits
- app_versions.py / manual.py pour cette phase de refactor

Comportement conservé
---------------------
- six caractéristiques et scores temporaires;
- calcul des modificateurs;
- PV max / actuels / non létaux;
- vitesse finale calculée depuis race + armure + charge;
- réduction de dégâts et résistance à la magie;
- BBA, CA manuelle, bouclier manuel, armure naturelle, déviation;
- modificateurs CA, initiative, BMO/CMB et DMD/CMD;
- prévisualisation CA / contact / pris au dépourvu / initiative / BMO / DMD;
- résumé de l'armure, du bouclier, de la charge et de la pénalité;
- bouton Règles de calcul;
- sauvegarde vers l'API existante update_rpg_character_combat.

Architecture
------------
Le nouveau rpg_character_combat.py n'importe ni NiceGUI, ni db,
ni rpg_character, ni rpg_character_ui. Toutes ses dépendances sont injectées.

rpg_character.py raccorde ensuite :
    _impl._combat_panel = _combat_panel

L'ancien corps _combat_panel reste volontairement dans rpg_character_ui.py
pendant la validation, comme dans les phases précédentes.

Diagnostic
----------
Le diagnostic temporaire d'erreurs Canner est conservé dans cette phase
parce qu'il fait partie de la version réellement déployée actuellement.
Il pourra être retiré lors de la phase de nettoyage final, une fois la
modularisation terminée et validée.

Base de données
---------------
Aucune migration supplémentaire.
Aucun SQL manuel.
Le raccordement Combat appelle toujours la migration équipement existante
avant de lire l'équipement.

Version
-------
JDR reste en V1.4.1 : cette phase est un refactor sans nouvelle fonction
utilisateur.

Validation locale réalisée
---------------------------
- py_compile : OK
- tests ciblés Combat : 3/3 OK
- test statique de la façade / architecture : inclus pour le dépôt

Non testé ici
-------------
- PostgreSQL de production
- Canner
- navigateur NiceGUI réel

Test après déploiement
----------------------
1. Ouvrir JDR > Combat.
2. Vérifier que les six caractéristiques et leurs modificateurs s'affichent.
3. Vérifier que la Breastplate + Bouclier apparaissent dans le résumé.
4. Modifier temporairement un champ (par ex. PV actuels ou Divers initiative).
5. Vérifier que la prévisualisation se met à jour.
6. Enregistrer, recharger et confirmer que la valeur est conservée.
7. Ouvrir « Règles de calcul ».

Après validation
----------------
La prochaine étape recommandée est le nettoyage final de rpg_character_ui.py :
suppression des anciens corps devenus morts et éventuellement du diagnostic
temporaire. Ensuite, les nouvelles fonctions JDR pourront commencer.

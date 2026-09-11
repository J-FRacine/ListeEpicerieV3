JDR V1.4.1 — Modularisation, phase 6
========================================

Base réelle vérifiée
--------------------
GitHub main : ebf0a65a61583ffcc6ad1afa228901af1447bb09

La phase 5 est présente sur main et l'utilisateur a confirmé son fonctionnement.

Objectif
--------
Extraire le panneau Équipement et encombrement.

Nouveau module :
- rpg_character_equipment.py

Le module conserve :
- poids transporté;
- seuils de charge;
- vitesse finale;
- armure et bouclier retenus;
- DEX maximale;
- pénalité aux tests;
- échec des sorts profanes;
- état Transporté / Équipé;
- catégories d'équipement;
- délégation vers les dialogues existants Ajouter/Modifier/Supprimer.

Pour réduire le risque, les dialogues détaillés d'équipement restent encore
dans rpg_character_ui.py. Le panneau principal est maintenant séparé et les
dialogues pourront être extraits dans une phase ultérieure.

Fichiers à téléverser
---------------------
Racine :
- rpg_character.py                  (remplacer)
- rpg_character_equipment.py        (nouveau)

tests/ :
- test_rpg_character_integration.py (remplacer)
- test_rpg_character_equipment.py   (nouveau)

Ne pas modifier
---------------
- rpg_character_ui.py
- rpg_character_identity.py
- rpg_character_attacks.py
- rpg_character_progression.py
- rpg_character_saves.py
- app_versions.py
- requirements.txt
- PostgreSQL

Version
-------
JDR reste V1.4.1 : refactor interne sans changement fonctionnel volontaire.

Validation locale
-----------------
- py_compile : OK pour les 4 fichiers livrés;
- 3 tests spécifiques Équipement : OK;
- test d'intégration mis à jour pour le cinquième module extrait;
- Canner et PostgreSQL de production non testés ici.

Vérification après déploiement
------------------------------
1. Ouvrir JDR > Équipement.
2. Vérifier le résumé poids / charge / vitesse.
3. Vérifier une armure ou un bouclier existant.
4. Basculer Transporté ou Équipé sur un objet de test puis revenir à l'état voulu.
5. Ouvrir Modifier sur un objet sans forcément enregistrer.
6. Ouvrir Ajouter puis annuler.

Si tout fonctionne, la phase 6 est validée.

JDR V1.4.1 — Modularisation phase 7 : Compétences + correctifs
================================================================

Base réellement utilisée
-------------------------
Dépôt : J-FRacine/ListeEpicerieV3
Branche : main
Commit vérifié avant développement :
97b1f7d641dabca284fe7adff1500ab5a2cf4c44

La phase 6 est déjà présente dans cette base :
- rpg_character_equipment.py
- façade rpg_character.py raccordée à Identité, Équipement, Sauvegardes,
  Progression et Attaques.

But de la phase 7
-----------------
1. Extraire le panneau Compétences du gros rpg_character_ui.py.
2. Garder « Afficher les points à vérifier » fermé par défaut, y compris après
   une sauvegarde/rechargement.
3. Ajouter une migration automatique non destructive pour les anciennes tables
   rpg_character_equipment qui pourraient ne pas avoir tous les champs
   détaillés d'armure/bouclier.

Fichiers à téléverser
---------------------
À la racine :
- rpg_character.py                       REMPLACER
- rpg_character_skills.py                AJOUTER
- rpg_character_equipment_schema.py      AJOUTER

Dans tests/ :
- test_rpg_character_integration.py      REMPLACER
- test_rpg_character_skills.py           AJOUTER
- test_rpg_character_equipment_schema.py AJOUTER

Ne pas modifier
---------------
- rpg_character_ui.py
- rpg_character_data.py
- les modules des phases 2 à 6
- app_versions.py / manual.py pour l'instant
- les fichiers Recettes

Architecture
------------
Le nouveau rpg_character_skills.py ne dépend ni de NiceGUI, ni de db, ni de
rpg_character/rpg_character_ui. Les dépendances sont injectées par la façade.

Le vieux corps _skills_panel reste physiquement dans rpg_character_ui.py pour
cette phase de validation, mais il n'est plus utilisé : la façade remplace
_impl._skills_panel par le nouveau builder au chargement.

Les dialogues/assistants suivants restent volontairement dans
rpg_character_ui.py et sont injectés :
- _skill_dialog
- _skill_display_name
- _skill_breakdown_text
- _calculation_rules_dialog

Correctif « Vérification des calculs »
--------------------------------------
Dans le nouveau panneau, l'expansion :
    Afficher les points à vérifier
est créée avec value=False.

Donc elle revient fermée après :
- Enregistrer les compétences;
- rechargement de la page;
- retour dans l'onglet Compétences.

Migration Équipement
---------------------
Aucun SQL manuel.

rpg_character_equipment_schema.py utilise uniquement :
    ALTER TABLE ... ADD COLUMN IF NOT EXISTS
et recrée l'index avec IF NOT EXISTS.

Aucune suppression, aucun DROP, aucun TRUNCATE, aucun DELETE.
La migration est exécutée avant la lecture du personnage sélectionné, car la
fiche calcule l'équipement avant même d'afficher l'onglet Équipement.
Elle ne s'exécute qu'une fois par processus après un succès.

Version
-------
JDR reste V1.4.1 pendant la validation de cette phase de modularisation.
Une finalisation/version officielle pourra être faite après validation dans
le navigateur/Canner.

Tests locaux réalisés
---------------------
- py_compile des nouveaux/remplacés : voir livraison ChatGPT.
- tests unitaires Compétences : voir livraison ChatGPT.
- tests migration Équipement : voir livraison ChatGPT.

Ce qui n'est PAS prétendu testé
-------------------------------
- PostgreSQL de production;
- Canner en production;
- navigation NiceGUI réelle dans le navigateur.

Test manuel recommandé après déploiement
----------------------------------------
1. Ouvrir JDR > Compétences.
2. Vérifier que les compétences, filtres, recherche, badges et calculs sont là.
3. Si des points sont signalés, vérifier que « Afficher les points à vérifier »
   est FERMÉ par défaut.
4. Ouvrir cette section, puis cliquer « Enregistrer les compétences ».
5. Après le rechargement, vérifier qu'elle est de nouveau FERMÉE.
6. Modifier un rang puis enregistrer et confirmer que le changement persiste.
7. Ouvrir Équipement et modifier l'armure qui produisait l'erreur; enregistrer.
8. Vérifier que poids, charge, vitesse et CA restent cohérents.

Si tout est bon, prochaine étape recommandée : modularisation du panneau
Combat, puis nettoyage des anciennes implémentations mortes dans
rpg_character_ui.py.

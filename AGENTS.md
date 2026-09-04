# JF Apps — Instructions pour Codex

JF Apps est une suite d'applications personnelles développée avec Python, NiceGUI et PostgreSQL.

Le propriétaire du projet n'est pas programmeur. Les changements doivent donc être livrés de façon complète, claire et sans exiger de modifications manuelles de code.

## Référence du projet

- Dépôt principal : `J-FRacine/ListeEpicerieV3`
- Branche de référence : `main`
- Toujours partir de la version réellement actuelle des fichiers du dépôt.
- Ne pas supposer qu'un ancien fichier fourni dans une conversation est encore la version courante.
- Avant toute modification importante, inspecter les fichiers concernés et leurs dépendances directes.

## Principes de modification

- Préserver les fonctionnalités existantes sauf demande explicite contraire.
- Modifier uniquement ce qui est nécessaire à la tâche.
- Ne pas modifier une autre application sans justification claire.
- Éviter les changements massifs de style, de formatage ou de renommage non demandés.
- Préférer les correctifs simples et réversibles.
- Ne jamais demander au propriétaire de modifier du code manuellement si Codex peut faire la modification lui-même.
- Lorsqu'une migration de base de données est nécessaire, l'automatiser dans le code au démarrage lorsque c'est raisonnablement possible.
- Éviter le SQL manuel pour l'utilisateur.
- Ne jamais supprimer ou transformer des données existantes sans demande explicite et sans stratégie de migration sûre.

## Architecture et taille des fichiers

- Privilégier progressivement des modules fonctionnels de taille raisonnable.
- Éviter de recréer de très gros fichiers monolithiques.
- Le découpage temporaire actuel de Finances utilise :
  - `finances.py` comme petit chargeur;
  - `finances_part_XX.pyfrag` pour l'interface;
  - `finances_data.py` comme petit chargeur;
  - `finances_data_part_XX.pyfrag` pour la couche de données.
- Cette structure existe pour faciliter les modifications après la croissance des anciens monolithes.
- Pour les nouveaux développements importants de Finances, privilégier progressivement de vrais modules Python cohérents plutôt que d'agrandir indéfiniment les fragments.
- Ne pas effectuer un gros refactor fonctionnel en même temps qu'une petite correction utilisateur, sauf demande explicite.

## Règles métier Finances

- Budget = revenus et dépenses fixes.
- Tableau = dépenses variables.
- Éviter tout double comptage entre Budget, Tableau, Financements et groupes associés.
- Préserver les optimisations de navigation Budget introduites dans la série V1.13.
- Les marges de crédit ont une logique distincte des comptes bancaires; ne pas appliquer automatiquement à l'une les règles de présentation de l'autre.
- Toute modification des soldes ou projections doit réutiliser les fonctions/calculs existants lorsque possible afin d'éviter deux sources de vérité.

## Versions et documentation

Pour toute nouvelle version d'une application :

- Mettre à jour `app_versions.py`.
- Ajouter une note de version claire.
- Mettre à jour `manual.py` lorsque le comportement utilisateur change.
- Conserver le numéro de version demandé par le propriétaire.
- Utiliser la date réelle de la livraison.
- Ne pas modifier les versions des autres applications sans nécessité.

## Validation avant livraison

Toujours effectuer les vérifications raisonnablement disponibles après les changements :

1. Compiler les fichiers Python modifiés avec `python -m py_compile`.
2. Si Finances utilise encore les fragments, reconstruire en mémoire ou dans un fichier temporaire :
   - `finances.py` à partir de tous les `finances_part_*.pyfrag`;
   - `finances_data.py` à partir de tous les `finances_data_part_*.pyfrag`;
   puis compiler ces sources reconstruites.
3. Rechercher et exécuter les tests existants pertinents.
4. Si aucune suite de tests n'est disponible, l'indiquer explicitement au lieu de prétendre qu'elle a été exécutée.
5. Vérifier les appels, imports et références directement touchés par la modification.
6. Vérifier `git diff` et `git status` avant de déclarer la tâche terminée.

Ne jamais prétendre avoir testé :
- PostgreSQL en production;
- Canner ou Render en production;
- les notifications réelles;
- un navigateur ou appareil réel;
si ces tests n'ont pas réellement été exécutés.

## Livraison et compte rendu

À la fin d'une tâche, fournir un résumé simple comprenant :

- la version produite;
- ce qui a changé;
- la liste des fichiers modifiés;
- les migrations automatiques éventuelles;
- les commandes/tests exécutés et leurs résultats;
- ce qui reste à vérifier sur Canner/Render ou PostgreSQL.

Si le travail est effectué directement dans le dépôt, laisser les changements dans un état propre et facilement révisable. Si un ZIP est explicitement demandé, produire un ZIP contenant les fichiers complets nécessaires au remplacement.

## Style de travail avec le propriétaire

- Répondre en français lorsque du texte destiné au propriétaire est demandé.
- Utiliser des explications simples et orientées vers l'action.
- Éviter le jargon lorsqu'il n'est pas nécessaire.
- Signaler clairement toute incertitude ou limite réelle.

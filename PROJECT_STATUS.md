# JF Apps — État du projet

Dernière mise à jour : 2026-09-04

Ce fichier sert de point de reprise pour ChatGPT, Codex et les futures conversations. Le dépôt GitHub `J-FRacine/ListeEpicerieV3` sur `main` est la référence technique.

## Versions actuellement déclarées dans `main`

| Application | Version |
|---|---:|
| Portail JF Apps | 1.4.0 |
| Liste d'épicerie | 1.1.2 |
| Journal de pression | 1.2.1 |
| Finances | 1.13.2 |
| Personnages JDR | 1.3.0 |
| Commentaires et suggestions | 1.0.0 |

Important : ces versions sont celles présentes dans GitHub `main`. Leur validation réelle sur Canner/Render ou PostgreSQL de production doit être confirmée séparément après déploiement.

## Finances — état actuel

Version actuelle dans `main` : **V1.13.2**

### Changements récents terminés

- Navigation Budget optimisée dans V1.13.1.
- Le changement de mois du Budget évite les recalculs inutiles du Tableau.
- Un indicateur de calcul est affiché pendant les prévisions plus longues.
- Correctif de compatibilité `text_value()` pour l'ajout et la modification de transactions.
- Dans Compte bancaire, le Solde de départ est maintenant la première ligne du tableau.
- Le Solde de départ est informatif seulement : aucune case Vu, aucune transaction et aucune édition.
- Le résumé supérieur du compte bancaire affiche maintenant :
  - Solde actuel;
  - Plus bas prévu;
  - Solde fin de mois.
- Les marges de crédit conservent leur présentation distincte.
- Aucun changement de schéma PostgreSQL pour V1.13.2.

### Structure technique Finances

Les anciens gros monolithes ont été scindés pour faciliter la maintenance :

- `finances.py` : petit chargeur.
- `finances_part_01.pyfrag` à `finances_part_14.pyfrag` : interface et logique historique de Finances.
- `finances_data.py` : petit chargeur.
- `finances_data_part_01.pyfrag` à `finances_data_part_16.pyfrag` : couche de données historique.
- Modules déjà séparés :
  - `finances_calculations.py`
  - `finances_validation.py`
  - `finances_shared_loans.py`
  - `finances_shared_loans_data.py`
  - `finances_ui_state.py`

Le découpage en `.pyfrag` est une étape transitoire. Pour les futurs développements importants, privilégier progressivement de vrais modules Python fonctionnels.

## Décisions métier importantes

### Budget et Tableau

- Budget = capacité fixe, revenus fixes et dépenses fixes.
- Tableau = dépenses variables.
- Ne pas recompter dans Tableau ce qui est déjà absorbé dans Budget.
- Les groupes de financements doivent également éviter tout double comptage.

### Comptes bancaires et marges de crédit

- Compte bancaire : logique de solde positif/négatif classique.
- Marge de crédit : logique de dette distincte.
- Ne pas uniformiser les deux présentations sans demande explicite.

### Base de données

- Automatiser les migrations lorsqu'elles sont nécessaires.
- Éviter le SQL manuel pour le propriétaire.
- Préserver les données existantes.
- Ne jamais annoncer qu'une migration a été validée en production sans test réel.

## Travaux à développer / backlog

### Priorité technique

- Continuer à réduire la taille et les dépendances des gros fichiers.
- Transformer progressivement les fragments Finances en modules fonctionnels cohérents.
- Candidats naturels :
  - Compte;
  - Budget;
  - Financements;
  - Conciliation;
  - Organisation;
  - Historique / transactions.

Le refactor doit être progressif, écran par écran, afin de réduire le risque de régression.

### Validation / qualité

- Maintenir la compilation Python comme contrôle minimum.
- Ajouter ou consolider une vraie suite de tests automatisés pour Finances.
- Conserver des tests ciblés pour :
  - mois à trois paies;
  - projections Budget;
  - financements;
  - soldes de compte;
  - absence de double comptage.

## Workflow ChatGPT + Codex

Workflow recommandé :

1. Le propriétaire décrit le besoin dans ChatGPT.
2. ChatGPT aide à définir la fonctionnalité, les règles métier, le numéro de version et les critères d'acceptation.
3. Codex travaille directement sur le dépôt local ou le worktree :
   - lit `AGENTS.md`;
   - modifie les fichiers;
   - compile;
   - lance les tests pertinents;
   - résume les changements.
4. Le propriétaire peut ensuite demander à ChatGPT de relire le résultat dans GitHub.
5. La validation réelle sur Canner/Render et PostgreSQL reste une étape séparée.

## GitHub

Dépôt principal : `J-FRacine/ListeEpicerieV3`

`main` est la source de vérité.

ChatGPT peut actuellement lire correctement le dépôt et ses fragments. L'écriture GitHub directe depuis l'intégration ChatGPT peut rester limitée selon les permissions de l'intégration. Codex travaillant avec le dépôt local est donc le moyen recommandé pour les modifications directes.

## Règle de passation

À chaque changement important de version ou d'architecture, mettre ce fichier à jour avec :

- versions actuelles;
- changements terminés;
- éléments encore à tester;
- backlog;
- décisions métier ou techniques nouvelles.

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

### Extraction interne de Compte — 2026-09-04

Depuis le 2026-09-04, le noyau de données Compte est extrait dans `finances_account_data.py`. Finances reste en V1.13.2,
sans changement utilisateur, sans nouveau SQL et sans migration PostgreSQL.

- Le module contient la sélection des comptes, les mouvements effectifs, les
  signes banque/marge et les synthèses mensuelle et annuelle.
- Il n’importe ni `finances_data` ni `db` et ne se connecte pas à PostgreSQL.
- Les trois points d’entrée publics restent dans `finances_data_part_07.pyfrag`
  sous forme de délégations. Les lectures et la construction des projections
  sont injectées depuis les fonctions présentes au moment de chaque appel.
- Les deux fonctions privées, utilisées uniquement dans le bloc extrait,
  sont désormais internes au nouveau module.
- Cette première extraction ne déplaçait pas encore l’interface Compte ni la conciliation.
- Validation locale : 17 tests métier conservés, complétés par 3 tests
  d’architecture/compatibilité; compilation Python et des deux sources
  reconstruites. La validation réelle Canner/Render et PostgreSQL reste à faire.

### Préparation de l’interface Compte — 2026-09-04

- Cette étape a introduit `AccountPanelHandle` dans `finances_account.py`, sans import
  NiceGUI, `finances`, `finances_data` ou `db`.
- Le parent appelle `reload_options()` puis `refresh()`. Les callbacks fournis
  par le panneau sont résolus à l’appel et peuvent être remplacés; aucune
  référence au sélecteur ou au rendu interne n’est nécessaire à `refresh_all()`.
- Le rechargement conserve la sélection si elle existe, sinon choisit le premier
  compte disponible ou aucune sélection. Le mois reste géré dans le panneau.
- Lors de cette préparation, le panneau restait dans les fragments 05 et 06;
  les dialogues partagés conservaient leur résolution tardive.
- Six tests de contrat s’ajoutent aux 20 tests existants (26 au total), avec
  exécution des raccordements réels isolés et dépendances d’interface simulées.
- Finances reste en V1.13.2, sans migration. Le rendu réel NiceGUI, les
  notifications et PostgreSQL ne sont pas validés par ces tests.

### Extraction de l’interface Compte — 2026-09-04

- `build_account_panel()` dans `finances_account.py` contient désormais le
  panneau complet : banques et marges, mois, soldes, mouvements, conciliation
  « Vu », édition, vue annuelle et commandes de notifications Finances.
- Le bloc de 500 lignes des fragments 05/06 est remplacé par un appel de
  construction. Les textes, classes CSS et instructions du bloc sont conservés;
  les styles généraux et les dialogues partagés ne sont pas déplacés.
- `ui`, la navigation, le curseur mensuel, les lectures/calculs, le formatage,
  la conciliation et les services push sont injectés explicitement.
- Les services sont transmis par des lambdas; notamment `refresh_all`,
  `recurrence_dialog`, `_transaction_dialog` et `_card_payment_dialog` sont
  résolus au moment de leur utilisation, même après la construction.
- Le parent conserve seulement `AccountPanelHandle` et appelle ses opérations
  `reload_options()` et `refresh()`. Les widgets et fonctions internes restent
  locaux au constructeur. Aucun import de NiceGUI, `finances`, `finances_data`
  ou `db` dans le module du panneau.
- Les 26 tests précédents sont conservés/adaptés à la localisation du panneau;
  3 contrôles supplémentaires portent le total à 29. Construction simulée
  vérifiée pour une banque, une marge et l’absence de compte.
- Finances reste en V1.13.2, sans migration ni changement utilisateur prévu.
  Le navigateur, PostgreSQL et les notifications réelles restent à valider.

### Extraction du noyau de calcul Budget — 2026-09-04

- Le résumé, la capacité de base, la capacité avec report et les prévisions
  sont maintenant extraits dans `finances_budget_data.py`, sans changement
  fonctionnel, visuel ou de performance volontaire. Finances reste en V1.13.2.
- Les quatre façades historiques injectent les fonctions présentes dans
  `finances_data` au moment de chaque appel; les remplacements après import
  restent pris en compte. Le module importe seulement la bibliothèque standard
  et les calculs génériques de dates, sans connexion PostgreSQL directe.
- À cette première étape, les lectures détaillées et écritures Budget, les groupes
  de financement et `_variable_expense_total_for_month()` restaient dans les fragments.
- Aucune optimisation supplémentaire des KPI n’est réalisée; le chemin indirect
  par `_dashboard_month_projection_v190()` est conservé. Aucune migration.
- 48 tests : les 45 précédents et 3 contrôles d’import/délégation Budget.
  PostgreSQL, le navigateur et Canner/Render ne sont pas testés réellement.

### Extraction des lectures Budget — 2026-09-04

- `finances_budget_data.py` contient maintenant aussi `_list_budget_items_v111`,
  `_financing_group_amount_for_month`, `list_budget_items` et
  `list_financing_budget_groups`. Les corps et requêtes SQL sont conservés.
- Les accès reçoivent `get_connection` ou un curseur, sans importer `db`.
  Les façades historiques injectent les dépendances courantes à chaque appel.
- Les écritures et la synchronisation Budget/récurrences restent inchangées
  dans `finances_data`, tout comme `_variable_expense_total_for_month()` et les
  consommateurs Tableau, exports et restauration. L’interface Budget reste
  dans les fragments UI. Aucune optimisation KPI supplémentaire.
- 51 tests réussis : 48 précédents et 3 contrôles des lectures; les tests SQL
  simulés sont complétés pour les montants, périodes, overrides et groupes.
- Finances reste en V1.13.2, sans changement fonctionnel, SQL ou de performance
  volontaire et sans migration. PostgreSQL, navigateur et Canner/Render réels
  ne sont pas validés.

### Extraction des écritures Budget — 2026-09-04

- `finances_budget_writes.py` contient maintenant les six écritures spécifiques
  au Budget. Leurs corps, SQL, ordre de requêtes et commits sont conservés.
- Les connexions, validateurs, helpers, constantes et source de date sont injectés
  par les façades historiques à chaque appel. Le module n’importe ni `db`,
  `finances_data`, NiceGUI ou psycopg.
- `finances_budget_data.py` conserve les calculs et lectures Budget. L’interface
  reste dans les fragments UI et `_variable_expense_total_for_month()` reste
  historique. Aucune optimisation KPI supplémentaire et aucune migration.
- 83 tests réussis : les 80 précédents, dont les 29 tests SQL d’écriture sans
  changement, et 3 contrôles d’import/délégation. PostgreSQL, navigateur et
  Canner/Render réels ne sont pas validés.

### Préparation de l’interface Budget — 2026-09-04

- `finances_budget.py` contient le contrat minimal `BudgetPanelHandle`, sans
  dépendance NiceGUI, `finances`, `finances_data`, `db` ou psycopg.
- Le parent utilise `budget_panel.refresh()` pour le rafraîchissement global.
  Le handle est construit après la définition et l’appel initial de
  `render_budget`; son callback résout ce rendu au moment de l’appel.
- L’interface Budget reste dans les fragments 06/07. Navigation, sablier, tri,
  dialogues et rendu n’ont pas été déplacés. Budget conserve le même
  `month_state` que Tableau, sans second curseur.
- Les calculs/lectures restent dans `finances_budget_data.py` et les écritures
  dans `finances_budget_writes.py`. Aucun changement utilisateur ni migration.
- 88 tests réussis : les 83 précédents et 5 contrôles du contrat Budget.
  L’étape suivante prévue est `build_budget_panel(...) -> BudgetPanelHandle`.
  Navigateur, PostgreSQL et Canner/Render réels ne sont pas validés.

### Extraction de l’interface Budget — 2026-09-04

- `build_budget_panel()` dans `finances_budget.py` contient désormais le panneau
  complet et retourne `BudgetPanelHandle`. Le parent injecte les services par
  callbacks différés et conserve seulement le handle.
- Le builder reçoit le même `month_state` que Tableau. La navigation Tableau
  reste dans le parent; la navigation Budget, son sablier et son `finally` sont
  internes au panneau. Aucun second curseur.
- Tri, dialogues, textes, rendu, calcul unique de capacité, prévision avec
  `initial_capacity`, nouvelle période et génération des occurrences sont
  conservés. Aucun changement visuel, métier, SQL, KPI ou migration.
- Les fragments ne contiennent plus le bloc `# BUDGET GLOBAL` ni ses fonctions.
  89 tests réussis; NiceGUI/navigateur, PostgreSQL et Canner/Render réels ne sont
  pas validés.

### Caractérisation des Financements — 2026-09-04

- 18 tests dédiés protègent les lectures, enrichissements, résumés mensuels,
  validations et calculs des plans de financement.
- Les écritures sont exercées avec connexion et curseur simulés : création,
  modification, synchronisation des versements futurs, conservation de
  l'historique confirmé, activation et suppression.
- Les contrats UI actuels couvrent le curseur mensuel unique, la navigation
  ciblée, les services du rendu, l'aperçu des intérêts, l'avertissement
  d'incohérence et les actualisations globales après mutation.
- La suite compte 107 tests. Aucun code de production, comportement, SQL,
  migration ou numéro de version n'est modifié. NiceGUI, PostgreSQL et
  Canner/Render réels ne sont pas validés.

### Extraction des lectures et calculs Financements — 2026-09-04

- `finances_financing_data.py` contient désormais `_list_installment_plans_v111`,
  `list_installment_plans`, `get_installment_plan`, la projection mensuelle de
  secours et `financing_month_summary`, avec leurs comportements et SQL actuels.
- Le module ne dépend ni de `db`, `finances_data`, `finances`, NiceGUI ou psycopg.
  La connexion et les autres dépendances sont injectées par les façades
  historiques à chaque appel afin de préserver les remplacements dans les tests.
- Les écritures et l'interface Financements restent dans les fragments. La
  prochaine étape prévue est l'extraction des écritures.
- Trois contrôles d'architecture portent la suite à 110 tests. Finances reste en
  V1.13.2, sans changement fonctionnel, migration ou modification d'interface.
  PostgreSQL, NiceGUI, navigateur et Canner/Render réels ne sont pas validés.

### Structure technique Finances

Les anciens gros monolithes ont été scindés pour faciliter la maintenance :

- `finances.py` : petit chargeur.
- `finances_part_01.pyfrag` à `finances_part_14.pyfrag` : interface et logique historique de Finances.
- `finances_data.py` : petit chargeur.
- `finances_data_part_01.pyfrag` à `finances_data_part_16.pyfrag` : couche de données historique.
- Modules déjà séparés :
  - `finances_account.py` : panneau Compte et contrat `AccountPanelHandle`.
  - `finances_account_data.py` : noyau de données Compte (banques et marges).
  - `finances_budget.py` : panneau Budget et contrat `BudgetPanelHandle`.
  - `finances_budget_data.py` : résumé, capacités, prévisions et lectures Budget.
  - `finances_budget_writes.py` : écritures spécifiques au Budget.
  - `finances_financing_data.py` : lectures et calculs Financements.
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
- Maintenir les 110 tests automatisés de calcul et de compatibilité; compléter
  progressivement les protections de l’interface et des écritures SQL.
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

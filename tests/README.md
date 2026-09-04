# Tests Finances

Depuis la racine du dépôt, avec Python 3.10 ou plus récent :

```sh
python -m unittest discover -s tests -v
python -m py_compile tests/test_finances.py tests/test_finances_account.py tests/test_finances_account_ui.py tests/test_finances_budget.py tests/test_finances_budget_ui.py tests/test_finances_budget_writes.py finances_account.py finances_budget_data.py finances_calculations.py finances_account_data.py finances_data.py finances.py finances_ui_state.py finances_validation.py finances_shared_loans_data.py
```

Les tests utilisent `unittest`, inclus dans Python. Ils chargent les vrais
fragments de `finances_data.py`. Le module `db` est remplacé pendant cet import
par un objet qui refuse toute connexion; les lectures de données sont simulées.
Aucune installation de NiceGUI ou de psycopg, ni base de données, n'est requise.

Couverture : capacité Budget d’octobre 2026 (paies les 2, 16 et 30) et de
novembre 2026 (paies les 13 et 27), retrouvées depuis un ancrage au 11 décembre,
financement avec intérêts ou frais et financement terminé, solde actuel
et prévisionnel bancaire (y compris une dépense prévue en retard), sens de la
dette d'une marge, exclusion des dépenses fixes et financements du Tableau.

Ces tests valident les calculs Python, pas les requêtes SQL, l'interface ou un
déploiement sur Canner/Render. Les montants attendus sont fixés dans les tests.

## Caractérisation de Compte avant extraction

`test_finances_account.py` ajoute 10 tests métier aux 7 tests existants :

- continuité du solde avec mouvements antérieurs au mois affiché;
- mois sans mouvement et maintien du solde reporté;
- continuité décembre → janvier dans la synthèse annuelle;
- déduplication des occurrences, avec date explicite ou repli sur la date de transaction;
- absence de projection des récurrences inactives;
- respect de la date de fin d’une récurrence, borne incluse;
- isolation des transactions du compte sélectionné;
- ordre déterministe des mouvements le même jour;
- dépassement de limite d’une marge et crédit disponible négatif;
- effet sur le solde d’un mouvement exclu du Budget.

Les calculs mensuels et annuels et la construction des projections restent ceux
de `finances_data`. Les lectures sont simulées. Pour l’isolation des comptes,
la vraie `list_transactions()` est exécutée avec un curseur simulé : le test
vérifie le filtre SQL et ses paramètres, puis fournit les lignes correspondantes.
Cela protège le contrat de lecture, sans valider l’exécution SQL par PostgreSQL.

Toutes les dates et tous les montants attendus sont fixes. Aucun test NiceGUI,
de notifications ou de PostgreSQL réel n’est ajouté.

## Extraction des données de Compte

La suite comprend maintenant 80 tests : les 29 tests précédents (17 tests métier,
3 contrôles d’architecture des données et 9 tests du panneau Compte),
plus 10 tests Budget, 6 tests de navigation/structure Budget et 3 contrôles
d’architecture Budget, 3 contrôles des lectures Budget et 29 tests des écritures.
Les 3 contrôles d’architecture des données vérifient l’import de
`finances_account_data` dans un processus neuf interdisant `db`, `finances_data`,
`psycopg` et `nicegui`, ainsi que la résolution des dépendances à chaque appel
des trois points d’entrée historiques. Les contrôles de délégation complètent
les tests métier, qui continuent à exécuter les vrais calculs extraits.

## Contrat du panneau Compte

`tests/test_finances_account_ui.py` couvre 9 aspects du contrat `AccountPanelHandle` :

- import sans NiceGUI, `finances`, `finances_data` ou `db`;
- callbacks différés et remplaçables;
- actualisation par le vrai `refresh_all()`, via le handle, dans l’ordre options puis rendu;
- résolution des fonctions cibles après la construction du handle;
- maintien de la sélection ou choix du premier compte disponible lors du rechargement;
- résolution tardive des callbacks partagés utilisés par l’édition des mouvements;
- retrait des définitions du panneau des fragments et confidentialité des fonctions internes;
- construction par le parent via des callbacks différés et remplaçables;
- construction du panneau complet retournant un handle, pour banque, marge et absence de compte.

Ces tests simulent l’interface sans lancer réellement NiceGUI. Les raccordements
du parent sont exécutés depuis les fragments; ceux du panneau depuis
`finances_account.py`. Le constructeur complet est aussi exécuté avec des
composants simulés. Les contrôles d’import interdisent NiceGUI et les modules
historiques dans un processus neuf.
Ils ne valident ni le rendu dans un navigateur ni les notifications réelles.

## Caractérisation Budget avant extraction

`tests/test_finances_budget.py` ajoute 10 tests des vrais calculs : choix du revenu
principal, détection d’un ancrage bihebdomadaire, repli à deux paies, arrondis et
montant personnalisé, bornes des périodes, contrat de filtrage des postes actifs,
réutilisation de `initial_capacity`, propagation du report sur trois mois et date
d’activation, exclusion des fixes/financements et montant dynamique des groupes.
Le calcul des dépenses variables conserve une seule lecture des postes Budget.
Les requêtes de lecture sont vérifiées avec un curseur simulé fournissant les
résultats filtrés : cela ne valide pas leur exécution par PostgreSQL.
Le cas réel octobre/novembre 2026 reste couvert dans `test_finances.py`;
l’effet bancaire d’un mouvement exclu du Budget reste couvert dans
`test_finances_account.py`, sans duplication de ces scénarios.

`tests/test_finances_budget_ui.py` ajoute 6 tests : navigation Budget/Tableau
ciblée avec le même `MonthCursor`, remise au mois courant, ordre indicateur →
attente du navigateur → rendu → masquage, masquage même après une exception,
absence de curseur Budget indépendant et réutilisation du résumé de capacité
comme résumé affiché et comme capacité initiale des prévisions.
Le vrai `change_month()` est isolé depuis les fragments et exécuté avec des
composants simulés; les raccordements du rendu sont contrôlés par leur AST.
Ces tests simulent NiceGUI sans le lancer et ne valident aucun navigateur réel.

Les optimisations V1.13.1 couvertes concernent le rafraîchissement ciblé et la
réutilisation des calculs existants. Aucun test n’exige zéro calcul KPI :
`_variable_expense_total_for_month()` appelle encore
`_dashboard_month_projection_v190()`, qui calcule catégories/étiquettes/KPI.
Cette optimisation éventuelle reste une tâche séparée; aucun code de production
n’est modifié. PostgreSQL, les notifications et Canner/Render ne sont pas validés.

## Extraction du noyau de calcul Budget

Trois contrôles supplémentaires dans `test_finances_budget.py` vérifient :
import indépendant de `finances_budget_data` dans un processus neuf interdisant
`db`, `finances_data`, `nicegui` et `psycopg`; délégation des quatre façades avec
remplacements successifs de leurs dépendances; utilisation effective par les
prévisions des services remplacés après import. Les 45 tests précédents sont
conservés sans modification de leurs résultats attendus.

Le résumé, les capacités et les prévisions résident dans `finances_budget_data.py`.
Les lectures détaillées, écritures et `_variable_expense_total_for_month()` restent
dans `finances_data`. Aucune optimisation supplémentaire des KPI ni migration.

## Extraction des lectures Budget

Les lectures et enrichissements sont maintenant dans `finances_budget_data.py`,
avec le noyau de calcul déjà extrait. Trois nouveaux tests protègent les quatre
façades de lecture après remplacements successifs, le filtrage des seuls groupes
et la liaison du résumé vers la lecture courante. L’import indépendant déjà testé
reste vérifié après cette extraction. Les tests SQL existants vérifient aussi
les jointures, le tri, les montants, les indicateurs de période/override et les noms
des plans, sans changer leurs résultats métier attendus.

Les écritures et la synchronisation restent historiques, ainsi que
`_variable_expense_total_for_month()`; l’interface Budget reste dans les fragments.
Les requêtes SQL et leurs paramètres sont conservés. Les accès reçoivent une
connexion ou un curseur injecté; les tests utilisent uniquement des simulations.
Aucune migration ni optimisation KPI, aucune validation PostgreSQL/Canner/Render
ou navigateur réel.

## Caractérisation des écritures Budget

`tests/test_finances_budget_writes.py` ajoute 29 tests (avec plusieurs sous-cas)
sans modifier les 51 tests existants. Les six fonctions historiques sont exécutées
avec une connexion/curseur déterministe qui vérifie l’ordre du SQL, les filtres,
les paramètres et les réponses. Le SQL est comparé sans dépendre des espaces.

- Activation/désactivation, poste absent, date de mise à jour et commit.
- Tri verrouillé, même type de poste, déplacements haut/bas, limites sans commit,
  poste absent et ordre identique remplacé par les positions relatives actuelles.
- Création de récurrence : replis, validations, intervalle 1–365, zéro traité comme
  valeur absente, dates, catégorie/étiquettes et paiement via validateurs simulés,
  rappel normalisé, indicateurs et insertion des étiquettes.
- Sauvegarde : nettoyage, validations, création/modification, ordre et ID,
  appartenance et unicité de la récurrence, synchronisation et override,
  chevauchements inclusifs et exclusion du poste édité, autorisation explicite,
  nouvelle récurrence dans le même curseur, suppression limitée aux transactions
  prévues après la fin; conservation du chemin sans synchronisation.
- Groupes : plans triés/dédupliqués, appartenance, conflits avec exclusion du
  groupe courant, montant dynamique de repli et minimum 0.01, création/modification,
  dépense mensuelle imposée, retrait du lien récurrent, upsert et remplacement des
  liens, suppression réservée au groupe de l’utilisateur et retour de rowcount.

Les tests protègent l’appel unique au commit final et son absence sur les chemins
d’erreur ou de tri sans déplacement. Les transactions PostgreSQL sont simulées :
leur atomicité réelle et le rollback ne sont pas validés. Aucun PostgreSQL,
NiceGUI, navigateur, Canner/Render réel n’est lancé. Finances reste en V1.13.2;
aucun fichier de production ni migration n’est modifié.

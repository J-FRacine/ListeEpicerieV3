# Tests Finances

Depuis la racine du dépôt, avec Python 3.10 ou plus récent :

```sh
python -m unittest discover -s tests -v
python -m py_compile tests/test_finances.py tests/test_finances_account.py finances_calculations.py finances_data.py finances.py
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

`test_finances_account.py` ajoute 10 tests aux 7 tests existants (17 au total) :

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

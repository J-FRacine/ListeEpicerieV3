# Tests Finances

Depuis la racine du dépôt, avec Python 3.10 ou plus récent :

```sh
python -m unittest discover -s tests -v
python -m py_compile tests/test_finances.py finances_calculations.py finances_data.py finances.py
```

Les tests utilisent `unittest`, inclus dans Python. Ils chargent les vrais
fragments de `finances_data.py`. Le module `db` est remplacé pendant cet import
par un objet qui refuse toute connexion; les lectures de données sont simulées.
Aucune installation de NiceGUI ou de psycopg, ni base de données, n'est requise.

Couverture : capacité Budget d'un mois à trois paies et du mois suivant à deux
paies, financement avec intérêts ou frais et financement terminé, solde actuel
et prévisionnel bancaire (y compris une dépense prévue en retard), sens de la
dette d'une marge, exclusion des dépenses fixes et financements du Tableau.

Ces tests valident les calculs Python, pas les requêtes SQL, l'interface ou un
déploiement sur Canner/Render. Les montants attendus sont fixés dans les tests.

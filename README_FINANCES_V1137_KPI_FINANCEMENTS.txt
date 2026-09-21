FINANCES — V1.13.7 — KPI DES FINANCEMENTS
=================================================================

Base GitHub validée avant finalisation : 0603ded25ca79b4a8eff0f10fa83c2ecad30ac07
Version officielle : Finances V1.13.7

Fonctionnement
--------------
- Les cartes Dépenses variables du mois et Reste disponible conservent la logique
  actuelle : un financement déjà inclus dans un groupe du Budget n'est pas ajouté
  une seconde fois aux dépenses variables.
- Les KPI par catégorie et par étiquette incluent maintenant toutes les dépenses du
  mois qui ne sont pas Hors budget, y compris ces versements de financement.
- Le détail d'un KPI suit la même règle et affiche le versement concerné.
- Chaque dépense du détail affiche maintenant un badge Variable ou Budget :
  Variable entre dans les dépenses variables du Tableau; Budget indique qu'elle
  est déjà absorbée dans le Budget et n'est pas recomptée dans ces totaux.
- Les montants Hors budget restent exclus.

Base de données
---------------
Aucune table, colonne ou migration PostgreSQL. Aucun SQL manuel.

Validation locale
-----------------
- compilation Python complète : OK;
- 27 tests ciblés Tableau/KPI : OK;
- 307 tests Finances : OK;
- 531 tests JF Apps : OK.

Validation navigateur
---------------------
- Mois futur avec versement de financement : réussi.
- Catégorie / étiquette visible dans le KPI : réussi.
- Versement visible dans le détail : réussi.
- Badges Variable / Budget : réussi.
- Absence de double comptage dans les totaux variables : réussi.

PostgreSQL de production / Canner ne sont pas testés par ce script.

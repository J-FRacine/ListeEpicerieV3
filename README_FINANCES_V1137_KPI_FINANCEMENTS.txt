FINANCES — CORRECTIF V1.13.7 EN VALIDATION — KPI DES FINANCEMENTS
=================================================================

Base GitHub : 52fd3b89ec67ee1421806f31c61c10b50bb41c64
Version officielle pendant validation : Finances V1.13.6
Version cible après validation navigateur : Finances V1.13.7

Fonctionnement
--------------
- Les cartes Dépenses variables du mois et Reste disponible conservent la logique
  actuelle : un financement déjà inclus dans un groupe du Budget n'est pas ajouté
  une seconde fois aux dépenses variables.
- Les KPI par catégorie et par étiquette incluent maintenant toutes les dépenses du
  mois qui ne sont pas Hors budget, y compris ces versements de financement.
- Le détail d'un KPI suit la même règle et affiche le versement concerné.
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

Validation navigateur à faire
-----------------------------
1. Choisir dans Tableau un mois futur avec un versement de financement.
2. Vérifier la catégorie et l'étiquette dans les KPI.
3. Ouvrir le détail du KPI et vérifier le versement.
4. Vérifier que Dépenses variables du mois et Reste disponible ne montent pas une
   seconde fois lorsque le financement est déjà inclus au Budget.
5. Vérifier qu'un financement Hors budget n'apparaît pas dans le KPI.

PostgreSQL de production / Canner ne sont pas testés par ce script.

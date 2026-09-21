LISTE D'ÉPICERIE — V1.2.1 EN VALIDATION — SOUVENT AJOUTÉS
==========================================================

Version officielle pendant validation : Liste d'épicerie V1.2.0
Version cible après validation navigateur : V1.2.1
Base GitHub de départ : 766c390684ec973bf901561b1d5e45a3c8ca50c4

Fonctionnement
--------------
- La fenêtre Modifier l'item affiche maintenant deux cases sur la même ligne :
  Présent dans les besoins et Dans « Souvent ajoutés ».
- La seconde case contrôle explicitement l'appartenance à la section Souvent ajoutés.
- Maximum : 10 items sélectionnés par famille.
- Un item sélectionné qui est déjà dans les besoins n'est pas répété dans les
  raccourcis; il réapparaît lorsqu'il quitte les besoins.
- Les raccourcis sélectionnés restent ordonnés selon leur historique d'utilisation.

Migration
---------
Une colonne frequent_selected est ajoutée automatiquement au démarrage.
Lors de la première migration seulement, jusqu'à 10 items déjà fréquemment utilisés
et actuellement hors des besoins sont sélectionnés comme point de départ.
Aucun SQL manuel n'est requis.

Sauvegardes
-----------
Le choix Souvent ajoutés est exporté et restauré avec les données de la famille.
Les anciennes sauvegardes sans ce champ restent compatibles et ne suppriment pas
une sélection existante lors d'une fusion.

Validation navigateur à faire
-----------------------------
1. Ouvrir Modifier l'item et vérifier les deux cases côte à côte sur grand écran.
2. Cocher Dans « Souvent ajoutés », enregistrer et vérifier le raccourci.
3. Décocher puis enregistrer : le raccourci doit disparaître.
4. Vérifier qu'un item sélectionné déjà dans les besoins n'est pas dupliqué.
5. Vérifier la limite : le 11e item doit être refusé avec un message clair.
6. Vérifier l'affichage sur téléphone : les cases peuvent se replier proprement.

PostgreSQL de production / Canner ne sont pas testés indépendamment par ce script.

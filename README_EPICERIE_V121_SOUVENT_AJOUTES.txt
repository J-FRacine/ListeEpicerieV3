LISTE D'ÉPICERIE — V1.2.1 — SOUVENT AJOUTÉS
==========================================================

Version officielle : Liste d'épicerie V1.2.1
Base GitHub validée avant finalisation : 0603ded25ca79b4a8eff0f10fa83c2ecad30ac07

Fonctionnement
--------------
- Les items sélectionnés restent visibles même lorsqu'ils sont déjà dans les besoins.
  Un crochet vert indique alors qu'ils sont déjà présents; ils ne disparaissent plus de la section.
- La fenêtre Modifier l'item affiche maintenant deux cases sur la même ligne :
  Présent dans les besoins et Dans « Souvent ajoutés ».
- La seconde case contrôle explicitement l'appartenance à la section Souvent ajoutés.
- Maximum : 10 items sélectionnés par famille.
- Un item sélectionné reste visible même lorsqu'il est déjà dans les besoins;
  un crochet vert indique alors qu'il est déjà présent.
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

Validation
----------
- Validation locale initiale : 10 tests ciblés Épicerie et 541 tests JF Apps réussis.
- Validation navigateur réussie : sélection et désélection fonctionnent.
- La correction de visibilité a été validée : un item sélectionné reste visible
  lorsqu'il est déjà dans les besoins et affiche un crochet vert.
- La limite de 10 est protégée par les tests automatisés.

PostgreSQL de production / Canner ne sont pas testés indépendamment par ce script.

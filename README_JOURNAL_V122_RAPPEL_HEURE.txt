JOURNAL DE PRESSION — CORRECTIF V1.2.2 EN VALIDATION
=====================================================

Version officielle pendant validation : Journal de pression V1.2.1
Version visée après validation navigateur : V1.2.2

Correctifs
----------
- Le rappel du Portail relit la date et l’heure dans le contexte réel du navigateur.
- La saisie rapide « Saisir maintenant » réactualise la date et l’heure de l’appareil à l’ouverture.
- L’aperçu de l’onglet Rappel utilise la même lecture locale fiable.
- Les mesures du jour restent comptées chronologiquement : 0, 1 ou 2 prises complétées selon les lignes réellement enregistrées pour la date locale demandée.
- Une mesure faite hors de la plage Matin/Soir compte toujours comme une prise de la journée.
- Le changement de journée utilise la date locale du navigateur au lieu de dépendre de l’heure du serveur lorsque le JavaScript est disponible.

Cause corrigée dans le code
---------------------------
Les lectures initiales de date/heure étaient lancées dans des tâches asyncio détachées. Dans ce contexte, NiceGUI pouvait ne plus disposer du client navigateur pour exécuter le JavaScript et retomber sur l’heure du serveur. Les trois initialisations passent maintenant par des ui.timer(..., once=True), liés au client NiceGUI.

Base de données
---------------
Aucune table, colonne ou migration PostgreSQL supplémentaire.

Validation automatisée prévue
-----------------------------
- 9 tests ciblés Journal V1.2.2;
- suite complète JF Apps;
- compilation Python complète.

La version officielle reste V1.2.1 jusqu’à la validation réelle dans le navigateur.

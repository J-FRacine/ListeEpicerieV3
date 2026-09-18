JOURNAL DE PRESSION — V1.2.2 — RAPPEL DU PORTAIL ET HEURE LOCALE
===================================================================

Version officielle : Journal de pression V1.2.2
Validation navigateur : réussie par l’utilisateur le 2026-09-18

Correctifs finalisés
--------------------
- Le rappel du Portail relit la date et l’heure dans le contexte réel du navigateur.
- La saisie rapide « Saisir maintenant » réactualise la date et l’heure de l’appareil à l’ouverture.
- L’aperçu de l’onglet Rappel utilise la même lecture locale fiable.
- Les mesures du jour sont comptées selon la date locale demandée : 0, 1 ou 2 prises complétées selon les lignes réellement enregistrées.
- Une mesure faite hors de la plage Matin/Soir compte toujours comme une prise de la journée.
- Le changement de journée utilise la date locale du navigateur lorsque JavaScript est disponible.

Cause corrigée
--------------
Les lectures initiales de date/heure étaient lancées dans des tâches asyncio détachées. Dans ce contexte, NiceGUI pouvait perdre le client navigateur pour exécuter le JavaScript et retomber sur l’heure du serveur. Les trois initialisations utilisent maintenant des ui.timer(..., once=True) liés au client NiceGUI.

Base de données
---------------
Aucune table, colonne ou migration PostgreSQL supplémentaire.

Validation
----------
- compilation Python complète : OK;
- 9 tests ciblés Journal V1.2.2 : OK;
- 528 tests JF Apps : OK;
- validation fonctionnelle réelle dans le navigateur : réussie par l’utilisateur;
- PostgreSQL de production / Canner : non testés indépendamment par le script.

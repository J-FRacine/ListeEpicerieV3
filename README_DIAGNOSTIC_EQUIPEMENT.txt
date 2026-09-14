JDR V1.4.1 — Diagnostic équipement après Phase 7
=================================================

IMPORTANT
---------
Ne pas installer le paquet Phase 7.1 précédent basé sur l'hypothèse
« nouvel équipement coché Équipé ». Le test avec « Équipé » décoché reproduit
la même erreur, donc cette hypothèse est écartée.

But
---
Le code actuel masque les exceptions PostgreSQL inattendues derrière :
    « L’équipement n’a pas pu être enregistré. »

Ce correctif temporaire conserve le même message dans l'interface, mais écrit
maintenant le type exact de l'exception et sa trace dans le journal Canner.

Installation
------------
À la racine du dépôt, remplacer uniquement :
    rpg_character.py

Aucun autre fichier applicatif à changer.
Le test fourni est facultatif :
    tests/test_rpg_character_diagnostic.py

Test à faire
------------
1. Déployer/recharger Canner.
2. Ouvrir JDR > Équipement.
3. Refaire l'enregistrement de la Breastplate, avec ou sans « Équipé ».
4. Ouvrir immédiatement le journal Canner.
5. Chercher une ligne commençant par :
       [JDR] ERREUR TECHNIQUE NON GÉRÉE
6. Envoyer la capture ou copier les lignes de cette erreur.

Sécurité
--------
Aucun SQL manuel.
Aucune modification de données.
Aucune migration supplémentaire.
Ce fichier ne change pas la logique d'enregistrement; il révèle seulement
l'erreur technique qui était auparavant masquée.

Validation locale
-----------------
- py_compile : OK.
- 2 tests statiques du raccordement diagnostic : OK.
- PostgreSQL de production et Canner : non testés ici.

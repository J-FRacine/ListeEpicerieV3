JDR — PHASE 15B — LANCEMENT GUIDÉ DES SORTS
=============================================

Version officielle pendant validation : JDR V1.9.0
Version visée après validation navigateur : JDR V1.10.0

Objectif
--------
Permettre de lancer réellement un sort préparé depuis l’onglet Sorts ou Combat
rapide, en consommant le même emplacement quotidien et en affichant les repères
utiles avant confirmation.

Fonctions
---------
- bouton Lancer sur chaque sort préparé;
- dialogue de confirmation avec niveau du sort, niveau de lanceur, DD, portée,
  cible/zone, durée, formule de référence, résumé, source et notes lorsqu’ils
  sont disponibles;
- consommation atomique d’un emplacement de niveau 1+ dans PostgreSQL;
- les oraisons restent réutilisables et ne sont jamais dépensées;
- le nombre restant est rafraîchi immédiatement après le lancement;
- les anciens boutons +/- restent disponibles pour corriger manuellement le
  suivi lorsqu’une erreur de table doit être rectifiée;
- conversion spontanée Cure ou Inflict à partir d’un sort normal préparé de
  niveau suffisant;
- les oraisons et les sorts de domaine ne peuvent pas servir à la conversion
  spontanée;
- intégration à Combat rapide avec sélection d’un sort disponible et bouton
  Lancer le sort;
- résumé dynamique directement sous le sélecteur de Combat rapide : école,
  résumé, DD, niveau de lanceur, portée, cible/zone, durée et formule/jet lorsque
  ces informations sont connues;
- l’utilisation enregistrée depuis Combat rapide est la même que celle visible
  dans l’onglet Sorts;
- certains sorts courants disposent de repères courts de durée/cible/formule;
  lorsqu’un détail n’est pas intégré, l’interface indique À vérifier plutôt que
  d’inventer une règle.

Limites volontaires
-------------------
- aucun dégât, soin, état, bonus ou malus n’est appliqué automatiquement à une
  cible dans cette phase;
- aucun historique séparé de lancements n’est créé;
- aucun dé ni jet d’attaque de sort n’est lancé automatiquement;
- les sorts personnalisés utilisent les informations saisies dans leur fiche;
- les détails de tous les sorts Pathfinder ne sont pas recopiés dans le
  catalogue initial.

Règles Clerc utilisées
----------------------
- les oraisons préparées ne sont pas dépensées lorsqu’elles sont lancées;
- un sort de domaine utilise son créneau de domaine et ne peut pas être converti
  spontanément;
- un Clerc configuré Cure/Inflict peut sacrifier un sort normal préparé de
  niveau suffisant pour lancer un sort Cure/Inflict approprié;
- le DD de référence reste 10 + niveau réel du sort + modificateur de la
  caractéristique de lancement.

Base de données
---------------
Aucune nouvelle table ni colonne. La Phase 15B réutilise :
- rpg_character_spellcasting_profiles
- rpg_character_prepared_spells

La nouvelle action de lancement verrouille la préparation avant d’incrémenter
used_count afin d’éviter qu’un même emplacement soit consommé deux fois depuis
deux écrans concurrents.

Validation attendue
-------------------
- lancement depuis Sorts;
- lancement depuis Combat rapide;
- compteur restant synchronisé dans les deux écrans;
- oraison réutilisable;
- sort normal épuisé non relançable;
- conversion spontanée Cure/Inflict;
- refus de conversion spontanée d’un sort de domaine;
- Nouvelle prière / repos remet ensuite les utilisations à zéro.

Validation locale avant livraison
--------------------------------
- 52 tests ciblés Phase 15B : OK
- 212 tests JDR : OK
- 516 tests JF Apps : OK
- compilation Python complète : OK
- PostgreSQL de production / Canner / navigateur : non testés localement

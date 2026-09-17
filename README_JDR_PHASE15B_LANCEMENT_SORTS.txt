JDR — PHASE 15B — LANCEMENT GUIDÉ DES SORTS
=============================================

Version officielle : JDR V1.10.0
Phase 15B validée dans le navigateur le 2026-09-17

Objectif
--------
Permettre de lancer réellement un sort préparé depuis l’onglet Sorts ou Combat
rapide, en consommant le même emplacement quotidien et en affichant les repères
utiles avant confirmation.

Fonctions
---------
- bouton Lancer sur chaque sort préparé;
- dialogue de confirmation avec niveau du sort, niveau de lanceur, difficulté du jet, portée,
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
  résumé, difficulté du jet, niveau de lanceur, portée, cible/zone, durée et dégâts/effet lorsque
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
- la difficulté du jet reste 10 + niveau réel du sort + modificateur de la
  caractéristique de lancement.

Correctif clarté combat / dégâts
--------------------------------
- « DD » est remplacé par « Difficulté du jet » dans les résumés de lancement;
- lorsqu’un sort n’accorde aucun jet de sauvegarde, l’interface l’indique au lieu
  d’afficher une difficulté trompeuse;
- une ligne « Dégâts / effet » rend la formule ou l’effet principal visible avant
  de lancer le sort;
- les formules simples déjà connues sont résolues avec le niveau de lanceur actuel
  (portée standard, durée par niveau et bonus de soins/dégâts);
- Spiritual Weapon affiche sa portée calculée, sa durée calculée, ses dégâts de
  force, son jet d’attaque BBA + Sagesse, l’absence de jet de sauvegarde et la
  résistance à la magie.

Base de données
---------------
Aucune nouvelle table ni colonne. La Phase 15B réutilise :
- rpg_character_spellcasting_profiles
- rpg_character_prepared_spells

La nouvelle action de lancement verrouille la préparation avant d’incrémenter
used_count afin d’éviter qu’un même emplacement soit consommé deux fois depuis
deux écrans concurrents.

Validation navigateur réalisée
------------------------------
Validation fonctionnelle réussie par l’utilisateur : lancement depuis Sorts et Combat rapide,
compteur partagé, oraisons réutilisables, résumé dynamique sous le sélecteur,
Difficulté du jet / Dégâts explicites et valeurs calculées de Spiritual Weapon.

Validation locale avant livraison
--------------------------------
- 54 tests ciblés Phase 15B : OK
- 214 tests JDR : OK
- 518 tests JF Apps : OK
- compilation Python complète : OK
- validation navigateur/Canner : réussie par l’utilisateur
- PostgreSQL de production : non testé indépendamment par ChatGPT

Phase 15B finalisée officiellement en JDR V1.10.0.

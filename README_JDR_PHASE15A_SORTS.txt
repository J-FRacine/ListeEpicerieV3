JDR — PHASE 15A — SORTS PRÉPARÉS ET EMPLACEMENTS
=================================================

Version officielle : JDR V1.9.0
Phase 15A validée dans le navigateur le 2026-09-15

Objectif
--------
Ajouter la préparation quotidienne des sorts du Clerc sans automatiser encore
les effets de combat. La Phase 15B prendra ensuite en charge le lancement guidé.

Fonctions
---------
- nouvel onglet Sorts;
- profil de lancement : niveau de Clerc, niveau de lanceur, caractéristique;
- progression des emplacements du Clerc niveaux 1 à 20;
- sorts bonus de caractéristique;
- DD : 10 + niveau du sort + modificateur de caractéristique;
- oraisons préparées mais non dépensées;
- un créneau de domaine par niveau de sort accessible à partir du niveau 1;
- domaines War/Guerre et Sun/Soleil reliés à la section Foi;
- catalogue initial de Clerc niveaux 0 à 4 + listes War/Sun 1 à 9;
- niveau 1 complété avec Protection from Chaos / Evil / Good / Law;
- ajout possible de sorts personnalisés;
- badges visibles Préparé / Utilisé / Restant sur chaque sort;
- résumé utilisé/restant par niveau de sort, incluant le créneau de domaine;
- Nouvelle prière / repos remet les utilisations à zéro;
- conversion spontanée Cure / Inflict conservée comme configuration de référence.

Base de règles
--------------
Pathfinder RPG Core Rulebook / Archives of Nethys :
- le Clerc prépare ses sorts à l'avance;
- Sagesse minimale : 10 + niveau du sort;
- DD : 10 + niveau du sort + modificateur de Sagesse;
- emplacements de base selon la table du Clerc, avec sorts bonus de Sagesse;
- « +1 » de la table = créneau de domaine;
- les oraisons ne sont pas dépensées lorsqu'elles sont lancées;
- War : Magic Weapon, Spiritual Weapon, Magic Vestment, Divine Power, etc.;
- Sun : Endure Elements, Heat Metal, Searing Light, Fire Shield, etc.

Base de données
---------------
Migration automatique et idempotente, sans SQL manuel :
- rpg_character_spellcasting_profiles
- rpg_character_prepared_spells

Les deux tables utilisent ON DELETE CASCADE depuis rpg_characters.

Limites volontaires de la Phase 15A
-----------------------------------
- pas d'application automatique des dégâts ou soins;
- pas encore d'intégration directe dans Combat rapide;
- catalogue général initial limité aux sorts courants du Core niveau 0 à 4;
- autres classes de lanceurs à ajouter plus tard;
- pouvoirs de domaine et canalisation non automatisés ici.

Correctif lisibilité / catalogue
--------------------------------
- ajout des quatre variantes Protection from... de niveau 1;
- statut Préparé / Utilisé / Restant déplacé sur la ligne de titre avec badges;
- Restant est mis en évidence (vert si disponible, rouge à zéro);
- résumé utilisé/restant affiché au niveau de chaque groupe de sorts.

Validation navigateur réalisée
------------------------------
Validation fonctionnelle réussie par l'utilisateur : onglet Sorts, emplacements,
préparation, suivi utilisé/restant, domaines, repos, persistance, variantes
Protection from... et nouveaux indicateurs visuels.

Validation locale avant livraison
--------------------------------
- 29 tests ciblés Phase 15A : OK
- 197 tests JDR : OK
- 501 tests JF Apps : OK
- compilation Python complète : OK

Phase 15A finalisée officiellement en JDR V1.9.0. Prochaine étape : Phase 15B.

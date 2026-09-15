JDR — PHASE 15A — SORTS PRÉPARÉS ET EMPLACEMENTS
=================================================

Version officielle pendant validation : JDR V1.8.0
Finalisation prévue après validation navigateur : JDR V1.9.0

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
- ajout possible de sorts personnalisés;
- nombre préparé, utilisé et disponible;
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

Validation navigateur recommandée
---------------------------------
1. Ouvrir un personnage Clerc puis l'onglet Sorts.
2. Vérifier le niveau de Clerc et le niveau de lanceur dans Configurer.
3. Vérifier les emplacements et le DD avec la Sagesse actuelle.
4. Préparer une oraison et confirmer qu'elle est indiquée réutilisable.
5. Préparer un sort normal puis le marquer utilisé et le rendre disponible.
6. Avec War / Sun dans Foi, préparer un sort de domaine.
7. Vérifier qu'un deuxième sort de domaine au même niveau est refusé.
8. Utiliser Nouvelle prière / repos et vérifier que les utilisations reviennent à zéro.
9. Recharger la page et confirmer que la préparation est persistante.

Validation locale avant livraison
--------------------------------
- 28 tests ciblés Phase 15A : OK
- 196 tests JDR : OK
- 500 tests JF Apps : OK
- compilation Python complète : OK

Après validation réelle, finaliser officiellement JDR V1.9.0.

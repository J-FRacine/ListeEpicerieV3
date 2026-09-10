# Préparation JDR — Combat rapide

Paquet additif. Il peut être ajouté au dépôt sans changer le comportement actuel.

## Contenu
- `rpg_combat_session.py`
- `tests/test_rpg_combat_session.py`

## Fonction prévue
Le futur bouton **Combat rapide** ouvre une fenêtre avec :
- PV actuels / maximums;
- CA, contact, pris au dépourvu;
- initiative;
- BMO/CMB et DMD/CMD;
- Vigueur, Réflexes, Volonté;
- sélection d'une attaque déjà enregistrée;
- bonus total, dégâts et critique;
- bonus/malus temporaire;
- zone temporaire pour dons/tactique/modificateurs;
- dégâts, soins et dégâts non létaux rapides.

Les seules écritures persistantes sont les PV actuels et dégâts non létaux,
via `update_rpg_character_combat`. Aucun nouveau schéma n'est requis.

## Intégration future
Dans `rpg_character.py` :
1. importer `build_combat_session`;
2. construire le handle avec les services/règles déjà présents;
3. ajouter un bouton **Combat rapide** dans la bannière ou l'onglet Combat;
4. raccorder `on_click=combat_session.open`.

Faire ce raccordement à partir de la version réellement actuelle du fichier,
après ou en même temps que l'intégration de l'assistant de création.

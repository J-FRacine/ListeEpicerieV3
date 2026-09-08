# JF Apps — Liste d’épicerie V1.2.0

## But

Déplacer la navigation principale **Items | Besoins | Catégories/Magasins** de la barre fixe du bas vers la partie haute de la Liste d’épicerie, sans changer les trois écrans ni leurs données.

## Base utilisée

Paquet préparé à partir de `main` au SHA :

`98ca73988fdcd037ce80d5ffb80dc201f3dcc881`

Les fichiers de départ ont été vérifiés contre les blobs GitHub actuels :

- `app.py` : `ce2b01178fa5cde27163253e12b4b97c26d91925`
- `app_versions.py` : `fb6b9e4c73dd3ef6a8039e40780e0f0d160c5e81`
- `manual.py` : `272ef66d1bfb9332bb2519bcf97f9b5a28a1f3c2`

## Fichiers à déposer dans le dépôt

À la racine :

- `app.py`
- `app_versions.py`
- `manual.py`
- `grocery_navigation.py` — nouveau fichier

Dans `tests/` :

- `test_grocery_navigation.py` — nouveau fichier

Le présent README est seulement un guide de livraison et n’a pas besoin d’être ajouté au dépôt.

## Changements visibles

- navigation principale en haut, sous l’en-tête commun;
- `Items`, `Besoins` et `Catégories/Magasins` sur une seule rangée;
- compteur conservé, par exemple `Besoins 14`;
- section active mise en évidence;
- présentation compacte sur téléphone;
- suppression du rendu de la barre fixe inférieure;
- `Planification`, `Activité` et `Données` restent dans la barre secondaire;
- Mode courses inchangé.

## Version

Liste d’épicerie : **V1.2.0**.

Les versions des autres applications restent inchangées.

## Base de données

Aucun changement de schéma PostgreSQL et aucune migration.

## Vérifications effectuées ici

- 10 tests ciblés de navigation : réussis;
- `py_compile` de `app.py`, `app_versions.py`, `manual.py`, `grocery_navigation.py` et du nouveau test : réussi;
- analyse syntaxique AST : réussie;
- vérification structurelle : l’ancien `bottom_navigation()` et le `ui.footer()` associé ne sont plus utilisés;
- vérification que le compteur Besoins et le libellé dynamique Catégories/Magasins sont conservés.

NiceGUI n’est pas installé dans l’environnement de préparation, donc le rendu réel navigateur/téléphone n’a pas été exécuté ici. PostgreSQL, Canner et Render réels n’ont pas été testés.

## Après import

Tester principalement sur téléphone :

1. Items actif;
2. Besoins actif avec et sans compteur;
3. Catégories actif lorsque les catégories sont activées;
4. Magasins actif lorsqu’elles sont désactivées;
5. Planification / Activité / Données toujours accessibles;
6. aucune barre de navigation fixe au bas de l’écran;
7. Mode courses inchangé.

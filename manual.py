from nicegui import ui

from auth import get_current_user
from onboarding import organization_diagram


MANUAL_SECTIONS = [
    {
        "title": "Premiers pas",
        "icon": "rocket_launch",
        "caption": "Connexion, portail et installation",
        "keywords": (
            "connexion portail pwa installation écran accueil "
            "déconnexion démarrage"
        ),
        "content": """
### Se connecter

1. Ouvrez **JF Apps** dans le navigateur ou depuis son icône installée.
2. Entrez votre adresse courriel et votre mot de passe.
3. Après la connexion, le **Portail** présente les applications et les outils auxquels vous avez accès.

### Première connexion : commencez par créer votre famille

Une **famille** est l’espace où sont conservés vos items, besoins, magasins, catégories, listes modèles et recettes. Même lorsque vous utilisez l’application seul, vous devez obligatoirement créer une famille avant de commencer.

Depuis le Portail :

1. ouvrez **Commencer ici** pour voir le parcours visuel;
2. utilisez **Créer ma famille**;
3. ajoutez ensuite vos magasins et vos catégories;
4. créez enfin vos premiers items.

La page **Commencer ici** indique automatiquement les étapes déjà terminées.

### Repères visuels dans Commencer ici

La page **Commencer ici** contient aussi un guide visuel rapide des principaux boutons :

- **Items** : le catalogue de base;
- **Besoins** : la liste active d’achats;
- **Catégories** : l’organisation des catégories et des magasins;
- **Portail** : le retour à l’accueil général;
- **Planification** : les listes modèles, les recettes et la bibliothèque partagée;
- **Activité et corbeille** : l’historique récent et les suppressions récupérables;
- **Données** : importation, exportation et sauvegarde;
- **Manuel** : l’aide détaillée.

Ce repère est conçu pour qu’un nouvel utilisateur comprenne rapidement où cliquer, sans devoir fouiller dans toute l’application.

### Installer JF Apps sur un appareil

- Dans le Portail, utilisez **Installer JF Apps**.
- Sur Android et Chrome, acceptez l'installation proposée.
- Sur iPhone ou iPad, ouvrez le site dans Safari, puis utilisez **Partager → Sur l'écran d'accueil**.
- L'application a besoin d'une connexion Internet pour consulter et modifier les données partagées.

### Se déconnecter

Utilisez l'icône de déconnexion située dans l'en-tête du Portail ou de certaines pages administratives.
""",
    },
    {
        "title": "Portail et navigation",
        "icon": "apps",
        "caption": "Accéder aux différentes fonctions",
        "keywords": (
            "portail navigation applications icônes bas écran "
            "items besoins catégories modèles recettes"
        ),
        "content": """
### Portail

Le Portail est le point central de **JF Apps**. Sa grille **Applications** contient seulement les grandes applications :

- Liste d’épicerie;
- Journal de pression;
- Finances;
- Personnages JDR.

Les applications 2, 3 et 4 apparaissent comme **Bientôt** tant qu’elles ne sont pas développées.

Les fonctions propres à la liste d’épicerie — modèles, recettes, bibliothèque, activité, corbeille et sauvegardes — se trouvent maintenant à l’intérieur de cette application.

Le Portail contient aussi :

- **Mon espace** : familles et compte;
- **Aide et démarrage** : Commencer ici et Manuel;
- **Administration** : utilisateurs et maintenance, pour les administrateurs.

### Barre de navigation de la liste d'épicerie

La barre située au bas de l'écran permet d'ouvrir rapidement :

- **Items** : le catalogue privé de la famille;
- **Besoins** : les produits actuellement à acheter;
- **Catégories** : l'organisation des produits;
- **Portail** : le retour à l'accueil général.

Le nombre affiché près de **Besoins** indique combien d'articles restent dans la liste.

### Outils dans l'en-tête de l’épicerie

- **Livre / Planification** : listes modèles, recettes et bibliothèque partagée;
- **Horloge** : activité et corbeille;
- **Roue dentée** : données, importation et exportation;
- **Point d'interrogation** : manuel d'utilisation;
- **Grille** : retour au Portail.

Le bouton **Planification** est souvent le moins évident au départ. Retenez qu’il ouvre tout ce qui sert à préparer des achats à l’avance : vos modèles réutilisables, vos recettes et la bibliothèque publique de partage.

Sur téléphone, ces outils sont présentés sous forme d’icônes afin de conserver assez d’espace pour le contenu.
""",
    },
    {
        "title": "Journal de pression",
        "icon": "monitor_heart",
        "caption": "Saisir, consulter et imprimer les mesures",
        "keywords": (
            "pression artérielle systolique diastolique pouls "
            "date heure appareil privé note historique pdf rapport "
            "aucune donnée courriel"
        ),
        "content": """
### Données privées

Le **Journal de pression** appartient uniquement à l’utilisateur connecté. Les mesures ne sont jamais partagées avec une famille ni avec un autre compte.

### Ajouter une mesure

Dans l’onglet **Saisie** :

1. la date et l’heure de l’appareil sont proposées automatiquement;
2. vérifiez-les ou modifiez-les au besoin;
3. inscrivez la pression systolique, la pression diastolique et le pouls;
4. ajoutez éventuellement une note;
5. utilisez **Enregistrer**.

Il est possible d’enregistrer plus de deux mesures dans une même journée. La phase 1 ne calcule aucune moyenne et ne présente aucun graphique.

### Historique

L’onglet **Historique** permet de choisir une plage de dates, puis de consulter, modifier ou supprimer les mesures du compte connecté.

Chaque fiche affiche :

- l’heure;
- la pression systolique et diastolique;
- le pouls;
- la note facultative.

### Rapport PDF

Dans **Rapport PDF**, inscrivez le **nom complet à imprimer**, puis choisissez la date de début et la date de fin.

Le rapport contient :

- le nom indiqué;
- l’intervalle choisi;
- une ligne pour chaque date de l’intervalle;
- les deux premières mesures de la journée sur la même ligne;
- les mesures supplémentaires sur une ligne marquée **suite**;
- les notes associées;
- la mention **Aucune donnée pour ce jour** lorsqu’aucune mesure n’existe à une date donnée.

### Préparer le courriel

Le bouton **Préparer le courriel** ouvre l’application de messagerie avec un sujet et un texte proposés. Le PDF doit généralement être joint manuellement, car les navigateurs ne permettent pas d’ajouter automatiquement une pièce jointe à un courriel.
""",
    },
    {
        "title": "Familles et partage",
        "icon": "groups",
        "caption": "Espaces de données partagés",
        "keywords": (
            "famille partage membres propriétaire accès changer "
            "famille active"
        ),
        "content": """
### Principe

Chaque famille possède ses propres items, besoins, magasins, catégories, modèles et recettes. Les membres autorisés voient les mêmes données et peuvent collaborer.

### Choisir la famille active

Plusieurs pages affichent un sélecteur **Famille**. Le changement de famille recharge la page avec les données de l'espace choisi.

### Gestion des familles

Dans le Portail, ouvrez **Familles** pour :

- créer une famille;
- choisir la famille active;
- renommer une famille lorsque votre rôle le permet;
- gérer les accès partagés;
- consulter des statistiques;
- supprimer une famille avec confirmation.

La création des comptes et l'attribution des familles sont réservées aux utilisateurs autorisés.
""",
    },
    {
        "title": "Items",
        "icon": "inventory_2",
        "caption": "Créer et gérer le catalogue familial",
        "keywords": (
            "item ajouter modifier supprimer recherche quantité note "
            "magasin catégorie besoin fréquent"
        ),
        "content": """
### Ajouter un item

Dans **Items**, inscrivez le nom, la quantité, le magasin et la catégorie, puis touchez **Ajouter**. Une note facultative peut préciser le format, la marque ou une préférence.

### Rechercher et trier

Le champ **Rechercher un item** filtre instantanément par nom ou catégorie. Le menu de tri permet un classement alphabétique, par ordre d'ajout ou par catégorie.

### Ajouter ou retirer des besoins

Touchez la partie principale d'une ligne pour changer son statut. Le cercle vert indique que l'item est déjà dans les besoins.

### Modifier ou supprimer

- Crayon : modifier le nom, la quantité, le magasin, la catégorie, la note ou le statut;
- Corbeille : placer l'item dans la corbeille.

Les items supprimés peuvent être restaurés depuis **Activité et corbeille** pendant leur période de conservation.

### Items fréquents

Les produits souvent ajoutés peuvent être proposés comme raccourcis. Un toucher les replace dans les besoins sans créer de doublon.
""",
    },
    {
        "title": "Besoins",
        "icon": "shopping_cart",
        "caption": "Préparer la liste d'achats",
        "keywords": (
            "besoins liste acheter catégories fermer ouvrir crochet "
            "annuler magasin"
        ),
        "content": """
### Consulter les besoins

Les articles sont regroupés selon leur magasin et leur catégorie. Les noms longs passent automatiquement sur plusieurs lignes.

### Ouvrir ou fermer les groupes

Touchez l'en-tête d'un groupe pour le déployer ou le replier. Les boutons avec flèches permettent d'ouvrir ou de fermer tous les groupes.

### Retirer un article

Touchez la ligne ou le crochet vert. L'article est retiré des besoins. Le bouton **Annuler** demeure disponible brièvement pour corriger une erreur.

### Commencer les courses

Le bouton **Commencer les courses** ouvre un écran simplifié conçu pour l'utilisation en magasin.
""",
    },
    {
        "title": "Mode courses",
        "icon": "shopping_cart_checkout",
        "caption": "Cocher les achats en magasin",
        "keywords": (
            "mode courses progression acheté panier synchronisation "
            "actualisation terminer reprendre"
        ),
        "content": """
### Démarrer ou reprendre

Depuis **Besoins**, utilisez **Commencer les courses**. Une session interrompue peut être reprise avec **Reprendre les courses**.

### Pendant les achats

- La progression indique le nombre d'articles achetés et restants.
- Touchez toute une ligne lorsque l'article est placé dans le panier.
- Le dernier article coché peut être restauré avec **Annuler**.
- Un groupe terminé disparaît automatiquement.
- La liste s'actualise régulièrement pour afficher les changements faits par un autre membre.
- Lorsqu’un nouvel item est ajouté aux besoins pendant que vous êtes en **Mode courses**, un avis apparaît avec son nom.
- Le magasin et la catégorie du nouvel item sont ouverts automatiquement afin qu’il soit facile à repérer.

L’avis est affiché seulement pour un véritable ajout détecté pendant la session. Restaurer vous-même un article avec **Annuler** ne produit pas un faux avis.

### Terminer

**Terminer les courses** ferme la session. Les articles non achetés demeurent dans les besoins.
""",
    },
    {
        "title": "Magasins et catégories",
        "icon": "category",
        "caption": "Organiser les produits et le trajet",
        "keywords": (
            "magasin catégorie créer renommer ordre fusion supprimer "
            "trier trajet"
        ),
        "content": """
### Différence

- **Magasin** : lieu où le produit est normalement acheté, par exemple IGA ou Costco;
- **Catégorie** : type ou rayon du produit, par exemple Produits laitiers ou Fruits et légumes.

### Gestion

La page **Catégories** permet de créer, renommer, réordonner, fusionner ou supprimer les éléments permis. L'onglet des magasins offre des fonctions comparables.

### Ordre personnalisé

Les flèches permettent de placer les magasins et catégories dans l'ordre rencontré pendant les courses. Cet ordre est repris dans **Besoins** et dans le **Mode courses**.

Avant une suppression, les items associés doivent être réattribués ou la fonction de fusion doit être utilisée.
""",
    },
    {
        "title": "Listes modèles",
        "icon": "checklist",
        "caption": "Réutiliser des listes préparées",
        "keywords": (
            "liste modèle créer depuis besoins ajouter item quantité "
            "réordonner déployer"
        ),
        "content": """
### Créer une liste modèle

Deux possibilités :

- **Nouvelle liste modèle** : crée une liste vide;
- **Créer depuis les besoins** : copie tous les besoins actuels.

### Ajouter et organiser les items

Déployez une liste modèle, choisissez un item existant, sa quantité, puis utilisez **Ajouter**. La liste demeure déployée pendant que vous la préparez.

Les flèches modifient l'ordre. Le crayon ajuste la quantité. Le X retire seulement la ligne de la liste modèle; l'item original demeure dans le catalogue familial.

### Utiliser une liste modèle

**Ajouter aux besoins** traite toute la liste en une opération. Les items déjà présents ne sont pas dupliqués. Leur quantité est augmentée seulement lorsque le modèle en demande davantage.

### Publier dans la bibliothèque partagée

Cochez **Publier dans la bibliothèque partagée** pour créer une version publique sécurisée. Utilisez **Mettre à jour la version publiée** après une modification que vous souhaitez rendre visible. Décochez la case pour retirer la publication; les copies déjà créées dans d’autres familles demeurent intactes.
""",
    },
    {
        "title": "Recettes",
        "icon": "restaurant_menu",
        "caption": "Associer les recettes aux items",
        "keywords": (
            "recette ingrédient portions préparation ajouter besoins "
            "quantité précision"
        ),
        "content": """
### Créer une recette

Une recette peut contenir :

- un nom;
- une description;
- un nombre de portions;
- des instructions de préparation.

### Ajouter des ingrédients

Déployez la recette, choisissez un item existant, indiquez une quantité et une précision facultative, puis utilisez **Ajouter**. La recette demeure déployée pendant la saisie.

Les flèches changent l'ordre des ingrédients. Le crayon modifie la quantité ou la précision. Le X retire l'ingrédient de la recette sans supprimer l'item familial.

### Ajouter aux besoins

**Ajouter les ingrédients** transfère tous les ingrédients vers les besoins sans créer de doublons.

### Publier dans la bibliothèque partagée

Cochez **Publier dans la bibliothèque partagée** pour publier une copie sécurisée de la recette. La publication n’inclut pas les magasins, notes privées, prix, besoins ou identifiants internes. Une famille qui copie la recette reçoit une version privée et indépendante.
""",
    },
    {
        "title": "Bibliothèque partagée",
        "icon": "public",
        "caption": "Consulter et copier les publications",
        "keywords": (
            "bibliothèque partagée publique publier recette liste modèle "
            "copier famille aperçu recherche"
        ),
        "content": """
### Consulter la bibliothèque

Ouvrez **Bibliothèque partagée** depuis le Portail, les Listes modèles ou les Recettes. Vous pouvez rechercher un nom, un item, un ingrédient ou une catégorie, puis filtrer les recettes et les listes modèles.

### Copier dans votre famille

Utilisez **Consulter et copier** pour voir le contenu avant de le copier. L’application réutilise les items portant exactement le même nom dans votre famille et crée les items manquants. La copie est privée et indépendante : vous pouvez la modifier sans affecter la publication originale.

### Retrait d’une publication

Lorsqu’un auteur décoche la publication, celle-ci disparaît de la bibliothèque. Les copies déjà importées dans les autres familles ne sont jamais supprimées.
""",
    },
    {
        "title": "Activité et corbeille",
        "icon": "history",
        "caption": "Consulter et restaurer",
        "keywords": (
            "activité historique corbeille restaurer supprimer définitivement "
            "actions utilisateurs"
        ),
        "content": """
### Historique

L'historique indique les actions importantes effectuées dans la famille, par exemple l'ajout d'un besoin, la modification d'un item ou la création d'un magasin.

### Corbeille

Les items, catégories ou magasins supprimés peuvent être conservés temporairement.

Selon le type d'élément, vous pouvez :

- le restaurer;
- examiner les dépendances;
- le supprimer définitivement.

La suppression définitive ne peut normalement pas être annulée.
""",
    },
    {
        "title": "Données, importation et exportation",
        "icon": "settings",
        "caption": "Sauvegarder et transférer les données",
        "keywords": (
            "données sauvegarde exporter json csv importer restauration "
            "version 3 famille"
        ),
        "content": """
### Exporter

La page **Données et sauvegarde** permet de choisir une famille et un format :

- **JSON** : sauvegarde complète restaurable;
- **CSV** : tableau lisible des items.

Les sauvegardes JSON actuelles incluent les magasins, catégories, notes, items, besoins, listes modèles et recettes. L’état de publication dans la bibliothèque n’est pas restauré automatiquement : après une importation, republiez volontairement les contenus désirés.

### Importer

L'importation utilise un fichier JSON. Elle agit sur la famille active et demande une confirmation avant de remplacer ou ajouter des données selon le fonctionnement affiché.

### Bonne pratique

Faites une exportation JSON avant :

- une migration importante;
- une requête SQL manuelle;
- une importation;
- un changement majeur de structure.
""",
    },
    {
        "title": "Compte et sécurité",
        "icon": "account_circle",
        "caption": "Profil, mot de passe et sessions",
        "keywords": (
            "compte nom courriel mot passe sécurité déconnexion profil"
        ),
        "content": """
### Mon compte

La page **Mon compte** permet de modifier :

- le nom affiché;
- l'adresse courriel;
- le mot de passe.

Utilisez un mot de passe unique et difficile à deviner. Déconnectez-vous sur un appareil partagé.

### Accès aux données

L'utilisateur ne voit que les familles auxquelles il a été associé. Les données propres à chaque famille demeurent séparées.
""",
    },
    {
        "title": "Administration des utilisateurs",
        "icon": "manage_accounts",
        "caption": "Fonctions réservées aux administrateurs",
        "keywords": (
            "administrateur utilisateurs créer compte activer désactiver "
            "rôle famille accès"
        ),
        "admin_only": True,
        "content": """
### Utilisateurs

Un administrateur peut notamment :

- créer un compte;
- attribuer ou retirer des accès aux familles;
- choisir les applications visibles et utilisables par chaque utilisateur;
- gérer les rôles autorisés;
- activer ou désactiver un utilisateur;
- consulter les informations nécessaires à l'administration.

### Applications accessibles

Le bouton **Applications** dans la fiche d’un compte permet d’autoriser :

- Liste d’épicerie;
- Journal de pression;
- Finances;
- Personnages JDR.

Une application non autorisée ne paraît pas dans le Portail et ses écrans sont bloqués. Les applications encore en développement peuvent être attribuées à l’avance; elles affichent alors **Bientôt**.

Un administrateur du portail possède automatiquement tous les accès.

Les mots de passe ne doivent jamais être communiqués ou conservés en clair.
""",
    },
    {
        "title": "Centre de maintenance",
        "icon": "health_and_safety",
        "caption": "Diagnostic de la base",
        "keywords": (
            "maintenance diagnostic doublons intégrité inutilisés "
            "taille base administrateur"
        ),
        "admin_only": True,
        "content": """
### Diagnostic

Le Centre de maintenance actuel travaille en lecture seule. Il peut signaler :

- références invalides;
- doublons exacts ou probables;
- catégories et magasins inutilisés;
- noms vides ou mal normalisés;
- éléments expirés dans la corbeille;
- familles sans propriétaire ou membre actif;
- taille approximative de la base et de ses tables.

Aucune correction automatique n'est effectuée dans cette première phase.
""",
    },
    {
        "title": "Dépannage",
        "icon": "support",
        "caption": "Problèmes courants",
        "keywords": (
            "dépannage actualiser cache erreur déploiement connexion "
            "pwa canner"
        ),
        "content": """
### Une modification n'apparaît pas

- Actualisez la page;
- sur ordinateur, utilisez une actualisation complète;
- dans la PWA, fermez puis rouvrez l'application.

### L'application ne répond plus

Vérifiez la connexion Internet. Une page hors connexion peut apparaître lorsque le serveur est inaccessible.

### Une liste partagée semble en retard

Dans le Mode courses, utilisez l'icône d'actualisation. Les autres pages peuvent être rechargées en changeant d'onglet ou en actualisant.

### Après un déploiement

Attendez la fin du déploiement Canner avant de tester. En cas d'échec, consultez les dernières lignes du journal d'exécution.
""",
    },
]


def manual_panel():
    user = get_current_user()
    is_admin = bool(
        user
        and user.get("is_admin")
    )

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label(
                "Manuel d’utilisation"
            ).classes(
                "text-2xl font-bold"
            )
            ui.label(
                "Guide du Portail JF Apps, de la liste d’épicerie "
                "et du journal de pression."
            ).classes(
                "text-sm text-gray-500"
            )

        ui.icon(
            "help_center"
        ).classes(
            "text-4xl text-primary"
        )

    with ui.card().classes(
        "w-full p-4 border-l-4 border-primary"
    ):
        ui.label(
            "Ce manuel couvre les fonctions actuellement disponibles."
        ).classes(
            "font-bold"
        )
        ui.label(
            "La liste d’épicerie et le Journal de pression "
            "sont documentés. Il sera complété lorsque "
            "les applications Finances et Personnages JDR "
            "seront ajoutées."
        ).classes(
            "text-sm text-gray-600"
        )

    organization_diagram(
        compact=True,
    )

    with ui.row().classes(
        "w-full justify-end"
    ):
        ui.button(
            "Ouvrir le parcours complet",
            icon="rocket_launch",
            on_click=lambda: ui.navigate.to(
                "/?tab=demarrage"
            ),
        ).props(
            "outline color=primary"
        )

    search_state = {
        "value": "",
    }

    search_input = ui.input(
        label="Rechercher dans le manuel",
        placeholder=(
            "Ex. modèles, sauvegarde, courses…"
        ),
    ).props(
        "clearable debounce=150 "
        "autocomplete=off"
    ).classes(
        "w-full"
    )

    with search_input.add_slot(
        "prepend"
    ):
        ui.icon("search")

    @ui.refreshable
    def render_sections():
        query = (
            search_state["value"]
            .strip()
            .casefold()
        )

        available_sections = [
            section
            for section in MANUAL_SECTIONS
            if (
                is_admin
                or not section.get(
                    "admin_only",
                    False,
                )
            )
        ]

        if query:
            visible_sections = [
                section
                for section in available_sections
                if query
                in (
                    section["title"]
                    + " "
                    + section["caption"]
                    + " "
                    + section["keywords"]
                    + " "
                    + section["content"]
                ).casefold()
            ]
        else:
            visible_sections = (
                available_sections
            )

        ui.label(
            (
                f"{len(visible_sections)} rubrique"
                if len(visible_sections) == 1
                else (
                    f"{len(visible_sections)} rubriques"
                )
            )
        ).classes(
            "text-sm text-gray-500"
        )

        if not visible_sections:
            with ui.card().classes(
                "w-full p-6 items-center text-center"
            ):
                ui.icon(
                    "search_off"
                ).classes(
                    "text-4xl text-gray-400"
                )
                ui.label(
                    "Aucune rubrique trouvée"
                ).classes(
                    "text-lg font-bold"
                )
                ui.label(
                    "Essayez un autre mot."
                ).classes(
                    "text-gray-500"
                )
            return

        for index, section in enumerate(
            visible_sections
        ):
            with ui.expansion(
                text=section["title"],
                caption=section["caption"],
                icon=section["icon"],
                value=(
                    not query
                    and index == 0
                ),
            ).props(
                "expand-separator"
            ).classes(
                "w-full bg-white rounded-xl "
                "shadow-sm border border-gray-200 "
                "overflow-hidden mt-2"
            ):
                ui.markdown(
                    section["content"]
                ).classes(
                    "w-full px-3 pb-3"
                )

    def search_changed(event):
        search_state["value"] = (
            event.value or ""
        )
        render_sections.refresh()

    search_input.on_value_change(
        search_changed
    )

    render_sections()

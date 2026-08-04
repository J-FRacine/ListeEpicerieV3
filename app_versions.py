from __future__ import annotations

PORTAL_VERSION = "1.2.1"

APP_LABELS = {
    "portal": "Portail JF Apps",
    "grocery": "Liste d’épicerie",
    "blood_pressure": "Journal de pression",
    "finances": "Finances",
    "rpg": "Personnages JDR",
    "feedback": "Commentaires et suggestions",
}

APP_VERSIONS = {
    "portal": PORTAL_VERSION,
    "grocery": "1.1.1",
    "blood_pressure": "1.1.1",
    "finances": "1.4.1",
    "rpg": "1.1.0",
    "feedback": "1.0.0",
}

RELEASE_NOTES = [
    {
        "app_key": "blood_pressure",
        "version": "1.1.0",
        "date": "2026-08-04",
        "title": "Journal de pression — sauvegarde privée et importation",
        "summary": (
            "Ajout des exportations CSV et JSON, de l’importation "
            "contrôlée et de la détection des doublons."
        ),
        "changes": [
            "Nouvel onglet Données pour importer et exporter les mesures.",
            "Export CSV compatible avec Excel.",
            "Sauvegarde JSON complète incluant les plages et réglages de rappel.",
            "Prévisualisation avant toute importation.",
            "Détection des mesures déjà présentes.",
            "Détection des mesures différentes à la même date et à la même heure.",
            "Importation facultative des plages de rappel depuis une sauvegarde JSON.",
            "Onglets horizontaux adaptés au téléphone.",
            "Remplacement des minuteries de montage par des tâches contrôlées.",
        ],
    },
    {
        "app_key": "rpg",
        "version": "1.1.0",
        "date": "2026-08-04",
        "title": "Personnages JDR — vérification des calculs Pathfinder",
        "summary": (
            "Ajout d’un audit visible de la feuille et de tests "
            "de référence pour les principaux calculs."
        ),
        "changes": [
            "Vérification automatique des compétences et des pénalités d’armure.",
            "Avertissement lorsqu’un bonus de classe +3 semble aussi inscrit dans Divers.",
            "Avertissement pour une compétence exigeant une formation sans rang.",
            "Contrôle du réglage ×2 de la pénalité d’armure.",
            "Tests de référence intégrés pour les caractéristiques, compétences, BMO/CMB et DMD/CMD.",
            "Exemple explicite Dressage — Handle Animal donnant un total de +2.",
            "Décomposition visible des calculs conservée dans l’interface compacte.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.4.1",
        "date": "2026-08-03",
        "title": "Finances — correction du menu sur téléphone",
        "summary": (
            "Les onglets du sous-menu Finances ne se chevauchent "
            "plus sur les écrans étroits."
        ),
        "changes": [
            "Onglets non compressibles avec largeur adaptée à leur libellé.",
            "Défilement horizontal tactile du sous-menu sur téléphone.",
            "Icône et texte placés sur une même ligne pour réduire la hauteur.",
            "Flèches de navigation affichées lorsque tous les onglets ne tiennent pas.",
            "Aucun changement aux transactions, récurrences ou conciliations.",
        ],
    },
    {
        "app_key": "portal",
        "version": "1.2.1",
        "date": "2026-08-03",
        "title": "Portail JF Apps — restauration de la page principale",
        "summary": (
            "Correction d’une route NiceGUI manquante qui provoquait "
            "une page 404 après le déploiement."
        ),
        "changes": [
            "Restauration de la route principale / du Portail.",
            "Les adresses / et /?tab=items sont de nouveau reconnues.",
            "Aucune donnée ni fonction d’application n’est modifiée.",
        ],
    },
    {
        "app_key": "grocery",
        "version": "1.1.1",
        "date": "2026-08-03",
        "title": "Liste d’épicerie — stabilité du Mode courses",
        "summary": (
            "Correction d’un arrêt du service causé par des minuteries "
            "NiceGUI dont la page avait déjà été fermée."
        ),
        "changes": [
            "Remplacement des minuteries liées à l’interface par des tâches contrôlées.",
            "Arrêt automatique de l’actualisation du Mode courses lorsque la page est quittée.",
            "Protection de la période d’annulation dans Besoins après navigation.",
            "Conservation du bouton d’actualisation manuelle dans le Mode courses.",
        ],
    },
    {
        "app_key": "portal",
        "version": "1.2.0",
        "date": "2026-08-03",
        "title": "JF Apps — correction mobile et navigation simplifiée",
        "summary": (
            "Refonte de l’en-tête sur téléphone et simplification "
            "de la navigation inférieure de la liste d’épicerie."
        ),
        "changes": [
            "En-tête mobile compact avec logo, nom de l’application, version, Portail et menu Plus.",
            "Commentaires, Aide, Compte, Nouveautés, Installer et Déconnexion regroupés dans le menu mobile.",
            "Indicateur de commentaires non lus conservé sur le menu Plus.",
            "Suppression du bouton Portail redondant dans la navigation inférieure de l’épicerie.",
            "Navigation inférieure de l’épicerie ramenée à une seule ligne.",
            "Versions et nouveautés des applications centralisées.",
        ],
    },
    {
        "app_key": "grocery",
        "version": "1.1.0",
        "date": "2026-08-03",
        "title": "Liste d’épicerie — tri naturel et catégories facultatives",
        "summary": (
            "Le tri ignore maintenant les accents et chaque famille "
            "peut choisir d’utiliser ou non les catégories."
        ),
        "changes": [
            "Tri alphabétique insensible aux accents et à la casse.",
            "Café, Céréales et leurs équivalents sans accents sont classés naturellement.",
            "Option Utiliser les catégories configurable par famille.",
            "Les catégories et associations existantes sont conservées lorsqu’elles sont masquées.",
            "Items, Besoins et Mode courses se regroupent uniquement par magasin lorsque les catégories sont désactivées.",
            "Le bouton Organisation devient Magasins dans la navigation lorsque les catégories sont désactivées.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.4.0",
        "date": "2026-08-03",
        "title": "Finances — réalisé, à venir et total prévu",
        "summary": (
            "Le Tableau projette les récurrences et présente les "
            "transactions postdatées du mois affiché."
        ),
        "changes": [
            "Projection des dépenses et revenus récurrents jusqu’à la fin du mois affiché.",
            "Transactions postdatées séparées des montants réalisés.",
            "Totaux Dépenses à venir, Revenus à venir et Effet net prévu.",
            "Liste des transactions à venir avec date, description et mode de paiement.",
            "KPI par catégorie et étiquette avec Réalisé, À venir et Total prévu.",
            "KPI distincts pour les dépenses et les revenus.",
            "Noms longs tronqués avec consultation du nom complet.",
            "Les objectifs mensuels excluent désormais les transactions postdatées du réalisé.",
        ],
    },
    {
        "app_key": "portal",
        "version": "1.1.0",
        "date": "2026-08-03",
        "title": "JF Apps — navigation et identité visuelle communes",
        "summary": (
            "Uniformisation du Portail et des applications avec un en-tête "
            "commun, un accès permanent au Portail et le logo comme icône."
        ),
        "changes": [
            "En-tête commun dans le Portail, l’épicerie, le Journal de pression, Finances et Personnages JDR.",
            "Bouton Portail toujours visible dans toutes les applications, y compris le mode Courses.",
            "Accès harmonisés à Commentaires, Manuel, Mon compte, Nouveautés et Déconnexion.",
            "Versions affichées de façon cohérente dans les en-têtes et les cartes du Portail.",
            "Onglets et menus internes harmonisés sur ordinateur et téléphone.",
            "Logo JF Apps utilisé comme favicon, icône PWA et repère visuel de navigation.",
            "Largeur et espacements communs pour mieux utiliser les écrans larges.",
            "Manuel et page Nouveautés mis à jour en même temps.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.3.0",
        "date": "2026-07-30",
        "title": "Finances — soldes prévus et conciliation par relevé",
        "summary": (
            "Ajout des soldes cumulatifs par mode de paiement, "
            "des séances de conciliation et de leur historique."
        ),
        "changes": [
            "Solde prévu cumulatif par mode de paiement, sans remise à zéro mensuelle.",
            "Sélection multiple des transactions à concilier par relevé.",
            "Solde du relevé, date de relevé, date de paiement et différence conservés.",
            "Historique des séances avec annulation complète ou retrait d’une transaction.",
            "Ajustement initial configurable par mode de paiement.",
            "Remboursements et revenus réduisant le solde prévu.",
            "Attribution en lot d’un mode aux transactions non classées.",
            "Type de mode, jours habituels de relevé et de paiement et notes.",
            "Export JSON enrichi de l’historique des conciliations.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.2.0",
        "date": "2026-07-30",
        "title": "Finances — paiements et conciliation",
        "summary": (
            "Ajout des modes de paiement, de la conciliation mensuelle, "
            "des KPI par catégorie et étiquette et d’un historique structuré."
        ),
        "changes": [
            "Modes de paiement configurables et réordonnables.",
            "Mode de paiement par transaction et par récurrence.",
            "Statut À concilier ou Conciliée avec date facultative.",
            "Filtres et résumé mensuel de conciliation.",
            "Revenus placés dans une colonne distincte sur grand écran.",
            "Montants alignés à droite dans l’historique et les KPI.",
            "KPI mensuels par catégorie et par étiquette.",
            "Importations et exportations enrichies des données de paiement.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.1.0",
        "date": "2026-07-29",
        "title": "Finances — importation contrôlée",
        "summary": (
            "Ajout de l’importation CSV et JSON avec prévisualisation, "
            "création des catégories et détection des doublons."
        ),
        "changes": [
            "Importation directe des fichiers CSV de Spendee.",
            "Importation des CSV et JSON exportés par JF Apps.",
            "Prévisualisation avant l’ajout des transactions.",
            "Création automatique des catégories et étiquettes manquantes.",
            "Détection des transactions déjà importées et des doublons possibles.",
            "Conservation de clés d’importation dans les futures exportations.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.0.0",
        "date": "2026-07-28",
        "title": "Finances V1",
        "summary": (
            "Première version du suivi privé des dépenses variables, "
            "revenus, récurrences et objectifs mensuels."
        ),
        "changes": [
            "Saisie rapide compacte pour téléphone.",
            "Catégories, sous-catégories et étiquettes multiples.",
            "Dépenses et revenus récurrents paramétrables.",
            "Objectifs mensuels avec reports configurables.",
            "Historique compact et filtres.",
            "Exportations CSV et JSON.",
        ],
    },
]


def get_app_version(app_key):
    return APP_VERSIONS.get(str(app_key or "").strip())


def get_app_label(app_key):
    key = str(app_key or "").strip()
    return APP_LABELS.get(key, key or "JF Apps")


def version_label(app_key):
    version = get_app_version(app_key)
    return f"V{version}" if version else None

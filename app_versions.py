from __future__ import annotations

PORTAL_VERSION = "1.1.0"

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
    "grocery": "1.0.0",
    "blood_pressure": "1.0.0",
    "finances": "1.3.0",
    "rpg": "1.0.0",
    "feedback": "1.0.0",
}

RELEASE_NOTES = [
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

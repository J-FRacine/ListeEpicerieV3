from __future__ import annotations

PORTAL_VERSION = "1.0.0"

APP_VERSIONS = {
    "finances": "1.2.0",
}

RELEASE_NOTES = [
    {
        "version": "1.2.0",
        "date": "2026-07-30",
        "title": "Finances — paiements et conciliation",
        "summary": (
            "Ajout des modes de paiement, de la conciliation mensuelle, "
            "des KPI par catégorie et étiquette et d’un historique "
            "plus structuré."
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
            "Nouvelle page Nouveautés et versions.",
        ],
    },
]


def get_app_version(app_key):
    return APP_VERSIONS.get(str(app_key or "").strip())


def version_label(app_key):
    version = get_app_version(app_key)
    return f"V{version}" if version else None

from __future__ import annotations

PORTAL_VERSION = "1.0.0"

APP_VERSIONS = {
    "finances": "1.0.0",
}

RELEASE_NOTES = [
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

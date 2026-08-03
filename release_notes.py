from __future__ import annotations

from nicegui import ui

from app_versions import (
    APP_LABELS,
    APP_VERSIONS,
    PORTAL_VERSION,
    RELEASE_NOTES,
)


RELEASE_CSS = r"""
.jf-version-grid {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));
    gap:.55rem;
    width:100%;
}
.jf-version-card {
    width:100%;
    padding:.65rem .75rem;
    border:1px solid var(--jf-border);
    border-radius:12px;
    background:var(--jf-surface);
}
.jf-release-card {
    width:100%;
    padding:.85rem .95rem;
    border:1px solid var(--jf-border);
    border-radius:13px;
    background:var(--jf-surface);
}
.jf-release-version {
    display:inline-flex;
    padding:.17rem .5rem;
    border-radius:999px;
    background:var(--jf-blue-soft);
    color:var(--jf-blue);
    font-size:.74rem;
    font-weight:800;
    white-space:nowrap;
}
.jf-release-app {
    display:inline-flex;
    padding:.14rem .48rem;
    border-radius:999px;
    color:var(--jf-navy);
    background:rgba(189,149,85,.14);
    font-size:.7rem;
    font-weight:800;
}
.body--dark .jf-release-app {
    color:#e2edf6;
}
"""

ui.add_css(RELEASE_CSS, shared=True)


def release_notes_panel(show_heading=True):
    if show_heading:
        with ui.row().classes(
            "w-full items-center justify-between gap-3 flex-wrap"
        ):
            with ui.column().classes("gap-0"):
                ui.label("Nouveautés et versions").classes(
                    "text-2xl font-bold"
                )
                ui.label(
                    "Les changements importants publiés dans JF Apps."
                ).classes("text-sm jf-muted")
            ui.label(f"Portail V{PORTAL_VERSION}").classes(
                "jf-release-version"
            )

    ui.label("Versions actuelles").classes("text-lg font-bold")
    with ui.element("div").classes("jf-version-grid"):
        for app_key, app_label in APP_LABELS.items():
            version = APP_VERSIONS.get(app_key)
            if not version:
                continue
            with ui.element("div").classes("jf-version-card"):
                with ui.row().classes(
                    "w-full items-center justify-between gap-2"
                ):
                    ui.label(app_label).classes(
                        "text-sm font-bold min-w-0 truncate"
                    ).tooltip(app_label)
                    ui.label(f"V{version}").classes(
                        "jf-release-version"
                    )

    ui.label("Historique").classes("text-lg font-bold mt-2")
    with ui.column().classes("w-full gap-3"):
        for release in RELEASE_NOTES:
            app_key = release.get("app_key", "portal")
            app_label = APP_LABELS.get(app_key, app_key)

            with ui.element("article").classes("jf-release-card"):
                with ui.row().classes(
                    "w-full items-start justify-between gap-2 flex-wrap"
                ):
                    with ui.column().classes("gap-1 min-w-0 grow"):
                        with ui.row().classes(
                            "items-center gap-2 flex-wrap"
                        ):
                            ui.label(app_label).classes(
                                "jf-release-app"
                            )
                            ui.label(release["title"]).classes(
                                "text-lg font-bold"
                            )
                        ui.label(release["summary"]).classes(
                            "text-sm jf-muted"
                        )

                    with ui.column().classes("items-end gap-1 shrink-0"):
                        ui.label(
                            f"V{release['version']}"
                        ).classes("jf-release-version")
                        ui.label(release["date"]).classes(
                            "text-xs jf-muted"
                        )

                with ui.column().classes("gap-1 mt-2"):
                    for change in release["changes"]:
                        with ui.row().classes(
                            "items-start gap-2 flex-nowrap"
                        ):
                            ui.icon("check_circle").classes(
                                "text-positive text-base shrink-0"
                            )
                            ui.label(change).classes("text-sm")

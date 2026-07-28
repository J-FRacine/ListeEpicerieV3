from __future__ import annotations

from nicegui import ui

from app_versions import PORTAL_VERSION, RELEASE_NOTES


RELEASE_CSS = r"""
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
}
"""

ui.add_css(RELEASE_CSS, shared=True)


def release_notes_panel():
    with ui.row().classes(
        "w-full items-center justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Nouveautés et versions").classes("text-2xl font-bold")
            ui.label(
                "Les changements importants publiés dans JF Apps."
            ).classes("text-sm jf-muted")
        ui.label(f"Portail V{PORTAL_VERSION}").classes("jf-release-version")

    with ui.column().classes("w-full gap-3 mt-2"):
        for release in RELEASE_NOTES:
            with ui.element("article").classes("jf-release-card"):
                with ui.row().classes(
                    "w-full items-start justify-between gap-2"
                ):
                    with ui.column().classes("gap-1"):
                        ui.label(release["title"]).classes(
                            "text-lg font-bold"
                        )
                        ui.label(release["summary"]).classes(
                            "text-sm jf-muted"
                        )
                    with ui.column().classes("items-end gap-1"):
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

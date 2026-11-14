"""Rappel quotidien de Mise en forme dans le Portail JF Apps."""
from datetime import date
import random

from nicegui import ui

from fitness_data import (
    settings,
    entries_between,
    week_number,
    daily_plan,
    day_progress,
)


ENCOURAGEMENTS = [
    "Tu es capable. Commence par un seul exercice, le reste suivra.",
    "Pas besoin d’être parfait aujourd’hui : juste de commencer.",
    "Quelques minutes maintenant, et tu pourras être fier de l’avoir fait.",
    "Ton futur toi va être content que tu t’y sois mis aujourd’hui.",
    "Allez, une petite séance et c’est réglé.",
    "Fais-en au moins un. Après, tu décideras si tu continues.",
    "Tu n’as pas besoin d’avoir envie. Tu as juste besoin de commencer.",
    "Même une petite séance compte. Vas-y à ton rythme.",
    "Un exercice à la fois. Pas besoin de sauver le monde aujourd’hui.",
    "Le plus difficile, c’est souvent juste de cliquer sur « Faire mes exercices ».",
    "Vas-y mon gros, on se bouge un peu.",
    "Allez hop, fais-en un dans les 15 prochaines minutes.",
    "Tu es capable d’au moins 2 ou 3. Après, on négociera.",
    "Bon. On arrête de regarder le bouton et on clique dessus.",
    "Un petit effort maintenant, pis après tu retournes à tes affaires.",
    "Go. Un exercice. Juste un. Et tu verras après.",
    "On se lève, on se dégourdit, et après tu peux recommencer à chialer.",
    "Fais-moi ça vite fait, bien fait, pis on n’en parle plus.",
    "Tu peux très bien faire ça aujourd’hui. Oui, toi.",
    "Allez, champion. Montre à la chaise qui commande.",
    "Breaking news : les exercices ne vont malheureusement pas se faire tout seuls.",
    "Étrangement, regarder le rappel depuis 20 minutes ne compte pas comme activité physique.",
    "La chaise commence à croire qu’elle a gagné. Tu vas vraiment la laisser faire ?",
    "J’ai vérifié : repousser à plus tard ne brûle presque aucune calorie.",
    "Ton corps a déposé une plainte officielle pour manque de mouvement.",
    "Oui oui, je sais, tu allais justement commencer. Quelle coïncidence.",
    "Magnifique stratégie : attendre que la motivation tombe du ciel. Sinon, on peut commencer.",
    "Le bouton « Faire mes exercices » fonctionne encore. Je dis ça comme ça.",
    "Tu peux continuer à négocier avec toi-même, ou faire un exercice et gagner du temps.",
    "La procrastination est très bien entraînée aujourd’hui. À ton tour.",
    "Allez mon gros, bouge tes fesses un peu.",
    "On décolle le cul de la chaise et on fait au moins un exercice.",
    "Tes fesses ont assez donné au fauteuil pour aujourd’hui. À toi de travailler.",
    "Hop hop hop, on se remue le popotin.",
    "Un peu de sueur, un peu de dignité, et après c’est fini.",
    "Tu veux des jambes qui coopèrent ? Faut leur donner un peu de boulot, bordel.",
    "Allez, fais-en deux. Trois si tu veux vraiment m’impressionner.",
    "Bouge-moi ça cinq minutes avant que le canapé demande une pension alimentaire.",
    "Le fauteuil t’aime beaucoup trop. Il est temps de mettre un peu de distance.",
    "Fais tes exercices, après tu pourras glander avec la conscience tranquille.",
    "Défi : commence dans les 5 prochaines minutes.",
    "Défi express : un exercice avant de faire autre chose.",
    "Mission du jour : en faire au moins 2 avant le prochain café.",
    "Objectif minimal : commence maintenant et fais-en juste un.",
    "Chrono imaginaire lancé : 15 minutes pour commencer.",
    "Fais-en un tout de suite. Si tu veux arrêter après, permission accordée.",
]


def _encouragement(remaining: int) -> str:
    if remaining <= 1:
        return random.choice([
            "Il n’en reste qu’un. Termine-moi ça et débarrasse-toi du rappel.",
            "Un seul restant. Là, tu n’as franchement plus d’excuse.",
            "Dernier effort. Après ça, liberté.",
            "Tu es à un exercice de pouvoir dire « c’est fait ».",
            "Un dernier et je te laisse tranquille.",
        ])

    if remaining == 2:
        return random.choice([
            "Plus que deux. Tu peux clairement régler ça maintenant.",
            "Deux petits efforts et c’est terminé.",
            "Il en reste deux. Même la procrastination commence à manquer d’arguments.",
            "Allez, deux et on ferme boutique.",
        ] + ENCOURAGEMENTS)

    return random.choice(ENCOURAGEMENTS)


def fitness_portal_reminder(user_id: int) -> None:
    today = date.today()
    try:
        config = settings(user_id)
        if (
            config.get("reminder_enabled") is False
            or config.get("reminder_snoozed_on") == today
        ):
            return

        week = week_number(
            config["started_on"],
            today,
            config["level_offset"],
        )
        plan = daily_plan(
            week,
            today,
            config.get("schedule_mode", "daily"),
            config.get("strength_weekdays"),
        )
        rows = entries_between(user_id, today, today)
        records = {
            (row["session_date"], row["exercise_key"]): row
            for row in rows
        }
        done, required = day_progress(plan, records, today)
    except Exception as exc:
        print(f"[Mise en forme] Rappel Portail indisponible: {exc}")
        return

    if done >= required:
        return

    remaining = required - done
    needs_strength = any(
        ex["key"] in ("chair", "wall", "calf")
        and not records.get((today, ex["key"]), {}).get("completed")
        for ex in plan
    )

    with ui.card().classes(
        "w-full p-4 border-l-4 border-teal-500"
    ) as reminder:
        with ui.row().classes(
            "items-start gap-3 w-full flex-wrap"
        ):
            ui.icon("directions_walk").classes(
                "text-3xl text-teal-700"
            )

            with ui.column().classes(
                "gap-1 flex-1 min-w-[210px]"
            ):
                ui.label("Tes exercices du jour").classes(
                    "text-lg font-semibold"
                )
                ui.label(
                    f"{done}/{required} objectifs réalisés · "
                    f"{remaining} restant(s)"
                ).classes("text-sm")
                ui.label(
                    "Marche et renforcement"
                    if needs_strength
                    else "Marche extérieure ou marche sur place"
                ).classes("text-sm text-gray-600")
                ui.label(
                    _encouragement(remaining)
                ).classes(
                    "text-sm font-medium text-teal-800 italic mt-1"
                )

                if (
                    records.get(
                        (today, "outdoor_walk"),
                        {},
                    ).get("skip_reason") == "meteo"
                ):
                    ui.label(
                        "Météo défavorable notée : "
                        "la marche sur place reste facultative."
                    ).classes("text-xs text-orange-700")

            with ui.row().classes(
                "gap-2 items-center flex-wrap"
            ):
                ui.button(
                    "Faire mes exercices",
                    icon="open_in_new",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=mise-en-forme"
                    ),
                ).props("color=primary")

                def refresh_reminder():
                    current = entries_between(
                        user_id,
                        today,
                        today,
                    )
                    current_records = {
                        (
                            row["session_date"],
                            row["exercise_key"],
                        ): row
                        for row in current
                    }
                    current_done, current_required = day_progress(
                        plan,
                        current_records,
                        today,
                    )
                    if current_done >= current_required:
                        reminder.delete()
                        ui.notify(
                            "Séance complétée : bravo !",
                            type="positive",
                        )
                    else:
                        current_remaining = (
                            current_required - current_done
                        )
                        ui.notify(
                            f"{current_done}/{current_required} "
                            "objectifs réalisés aujourd’hui. "
                            + _encouragement(current_remaining),
                            type="info",
                        )

                ui.button(
                    "Déjà fait",
                    icon="check",
                    on_click=refresh_reminder,
                ).props("flat")

                def snooze():
                    from fitness_data import (
                        update_reminder_preferences,
                    )
                    update_reminder_preferences(
                        user_id,
                        snooze_date=today,
                    )
                    ui.notify(
                        "Rappel masqué pour aujourd’hui.",
                        type="info",
                    )
                    reminder.delete()

                ui.button(
                    "Reporter à demain",
                    icon="event",
                    on_click=snooze,
                ).props("flat")

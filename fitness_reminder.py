"""Rappel quotidien de Mise en forme dans le Portail JF Apps."""
from datetime import date
from nicegui import ui
from fitness_data import settings, entries_between, week_number, daily_plan, day_progress


def fitness_portal_reminder(user_id: int) -> None:
    today = date.today()
    try:
        config = settings(user_id)
        if config.get('reminder_enabled') is False or config.get('reminder_snoozed_on') == today:
            return
        week = week_number(config['started_on'], today, config['level_offset'])
        plan = daily_plan(week, today)
        rows = entries_between(user_id, today, today)
        records = {(row['session_date'], row['exercise_key']): row for row in rows}
        done, required = day_progress(plan, records, today)
    except Exception as exc:
        # Un problème de rappel ne doit jamais empêcher l'ouverture du Portail.
        print(f'[Mise en forme] Rappel Portail indisponible: {exc}')
        return
    if done >= required:
        return
    remaining = required - done
    needs_strength = any(ex['key'] in ('chair', 'wall', 'calf') and not records.get((today, ex['key']), {}).get('completed') for ex in plan)
    title = 'Tes exercices du jour'
    with ui.card().classes('w-full p-4 border-l-4 border-teal-500') as reminder:
        with ui.row().classes('items-start gap-3 w-full flex-wrap'):
            ui.icon('directions_walk').classes('text-3xl text-teal-700')
            with ui.column().classes('gap-1 flex-1 min-w-[210px]'):
                ui.label(title).classes('text-lg font-semibold')
                ui.label(f'{done}/{required} objectifs réalisés · {remaining} restant(s)').classes('text-sm')
                ui.label('Marche et renforcement' if needs_strength else 'Marche extérieure ou marche sur place').classes('text-sm text-gray-600')
                if records.get((today, 'outdoor_walk'), {}).get('skip_reason') == 'meteo':
                    ui.label('Météo défavorable notée : la marche sur place reste facultative.').classes('text-xs text-orange-700')
            with ui.row().classes('gap-2 items-center flex-wrap'):
                ui.button('Faire mes exercices', icon='open_in_new', on_click=lambda: ui.navigate.to('/?tab=mise-en-forme')).props('color=primary')
                def refresh_reminder():
                    current = entries_between(user_id, today, today)
                    current_records = {(row['session_date'], row['exercise_key']): row for row in current}
                    current_done, current_required = day_progress(plan, current_records, today)
                    if current_done >= current_required:
                        reminder.delete()
                        ui.notify('Séance complétée : bravo !', type='positive')
                    else:
                        ui.notify(f'{current_done}/{current_required} objectifs réalisés aujourd’hui.', type='info')
                ui.button('Déjà fait', icon='check', on_click=refresh_reminder).props('flat')
                def snooze():
                    from fitness_data import update_reminder_preferences
                    update_reminder_preferences(user_id, snooze_date=today)
                    ui.notify('Rappel masqué pour aujourd’hui.', type='info')
                    reminder.delete()
                ui.button('Reporter à demain', icon='event', on_click=snooze).props('flat')

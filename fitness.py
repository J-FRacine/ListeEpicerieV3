from __future__ import annotations
from datetime import date, timedelta
from nicegui import ui
from fitness_data import settings, week_number, daily_plan, entries_between, save_entry, change_level, day_progress


def fitness_panel(user, show_heading=False):
    uid=user['id']
    saved=settings(uid)
    today=date.today()
    selected={'day':today}
    base=ui.column().classes('w-full gap-4')

    def render():
        day=selected['day']
        week=week_number(saved['started_on'],day,saved['level_offset'])
        plan=daily_plan(week,day)
        rows=entries_between(uid,min(day,today-timedelta(days=27)),today)
        records={(r['session_date'],r['exercise_key']):r for r in rows}
        with base:
            base.clear()
            if show_heading: ui.label('Mise en forme').classes('text-2xl font-bold')
            ui.label('Marche extérieure quotidienne et exercices doux, sans appareil').classes('text-gray-500')
            with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
                ui.label(f'Semaine {week} sur 8').classes('text-xl font-semibold')
                with ui.row().classes('gap-2'):
                    ui.button('Plus doux',icon='remove',on_click=lambda: adjust(-1)).props('outline dense')
                    ui.button('Progresser',icon='add',on_click=lambda: adjust(1)).props('outline dense')
            ui.label('La progression est indicative : restez à une étape confortable. Les changements de niveau modifient les prochains objectifs, pas les séances enregistrées.').classes('text-xs text-gray-500')
            with ui.row().classes('items-center gap-2 flex-wrap'):
                ui.button(icon='chevron_left',on_click=lambda: go(-1)).props('flat round')
                ui.label(day.strftime('%d/%m/%Y')).classes('text-lg font-bold')
                ui.button(icon='chevron_right',on_click=lambda: go(1)).props('flat round')
                ui.button('Aujourd’hui',on_click=lambda: go(0)).props('outline dense')
            done,total=day_progress(plan,records,day)
            ui.linear_progress(done/max(total,1),show_value=False).classes('w-full')
            ui.label(f'{done} sur {total} objectifs réalisés (marche extérieure ou alternative intérieure)').classes('text-sm text-gray-600')
            for ex in plan:
                rec=records.get((day,ex['key']),{})
                with ui.card().classes('w-full'):
                    with ui.row().classes('items-center w-full gap-3'):
                        ui.icon('check_circle' if rec.get('completed') else ('cloud' if rec.get('skip_reason')=='meteo' else 'radio_button_unchecked'),size='md').classes('text-primary')
                        with ui.column().classes('gap-0 flex-1'):
                            ui.label(ex['name']).classes('font-semibold')
                            ui.label(f"Objectif : {ex['target']} {ex['unit']}" + (' · facultatif si marche extérieure effectuée' if ex.get('optional') else '')).classes('text-sm text-gray-600')
                        ui.button('Modifier' if rec.get('completed') or rec.get('skip_reason') else 'Faire',on_click=lambda ex=ex,rec=rec: edit(ex,rec)).props('outline')
                    if rec.get('skip_reason')=='meteo': ui.label('Météo défavorable : reporté, sans pénalité. Marche sur place possible.').classes('text-sm text-orange-700')
                    ui.label(ex['info']).classes('text-sm text-gray-500')
            with ui.card().classes('w-full'):
                ui.label('Historique des 28 derniers jours').classes('font-semibold')
                completed_days=0
                for i in range(27,-1,-1):
                    d=today-timedelta(days=i)
                    dp=daily_plan(week_number(saved['started_on'],d,saved['level_offset']),d)
                    n,required=day_progress(dp,records,d)
                    if n==required:completed_days+=1
                ui.label(f'{completed_days} journées entièrement réalisées sur 28').classes('text-sm')
                with ui.row().classes('gap-1 flex-wrap'):
                    for i in range(27,-1,-1):
                        d=today-timedelta(days=i)
                        dp=daily_plan(week_number(saved['started_on'],d,saved['level_offset']),d)
                        n,required=day_progress(dp,records,d)
                        status='check_circle' if n==required else ('timelapse' if n else 'radio_button_unchecked')
                        ui.button(icon=status,on_click=lambda d=d: choose(d)).props('flat dense round').tooltip(f'{d:%d/%m}: {n}/{required}')
            ui.label('La marche extérieure est proposée chaque jour; par forte pluie, verglas ou conditions dangereuses, choisissez « météo défavorable » et faites la marche sur place si vous le souhaitez.').classes('text-xs text-gray-500')
            ui.label('Sécurité : commencez doucement, respirez normalement et arrêtez en cas de douleur thoracique, malaise ou essoufflement inhabituel. La marche sur place peut être fractionnée.').classes('text-xs text-gray-500')

    def adjust(delta):
        change_level(uid,delta)
        saved['level_offset']=settings(uid)['level_offset']
        render()
    def go(delta):
        selected['day']=today if delta==0 else selected['day']+timedelta(days=delta)
        if selected['day']>today: selected['day']=today
        render()
    def choose(day):
        selected['day']=day
        render()
    def edit(ex,rec):
        with ui.dialog() as dialog,ui.card().classes('w-full max-w-lg'):
            ui.label(ex['name']).classes('text-lg font-bold')
            ui.label(ex['info']).classes('text-sm')
            done=ui.checkbox('Exercice effectué',value=bool(rec.get('completed')))
            weather=ui.checkbox('Reporté à cause de la météo (sans séance effectuée)',value=rec.get('skip_reason')=='meteo') if ex['key']=='outdoor_walk' else None
            amount=ui.number(ex['unit'].capitalize(),value=rec.get('actual_value') if rec.get('actual_value') is not None else ex['target'],min=0,max=999,precision=0)
            difficulty=ui.select({'facile':'Trop facile','correct':'Correct','difficile':'Trop difficile'},label='Ressenti (facultatif)',value=rec.get('difficulty'))
            note=ui.textarea('Note facultative',value=rec.get('notes') or '').classes('w-full')
            def save():
                try:
                    save_entry(uid,selected['day'],ex['key'],bool(done.value) and not (weather and weather.value),int(amount.value) if amount.value is not None and not (weather and weather.value) else None,difficulty.value,note.value,'meteo' if weather and weather.value else None)
                except (ValueError,TypeError) as err:
                    ui.notify(str(err),type='negative');return
                dialog.close();render();ui.notify('Séance enregistrée',type='positive')
            with ui.row().classes('justify-end w-full'):
                ui.button('Annuler',on_click=dialog.close).props('flat')
                ui.button('Enregistrer',on_click=save)
        dialog.open()
    render()

from __future__ import annotations
from datetime import date, timedelta
from urllib.parse import quote
from nicegui import ui
from fitness_data import settings, week_number, daily_plan, entries_between, save_entry, change_level, day_progress


EXERCISE_GUIDE = {
    'outdoor_walk': {
        'title': 'Marche extérieure',
        'summary': 'L’activité quotidienne principale pour améliorer doucement l’endurance.',
        'steps': [
            'Choisissez un trajet simple et sécuritaire près de la maison.',
            'Marchez à un rythme confortable qui vous permet de parler.',
            'Gardez les épaules détendues et regardez devant vous.',
            'Commencez avec le temps prévu, puis revenez calmement.',
        ],
        'tips': [
            'Portez des chaussures confortables.',
            'S’il pleut très fort, s’il y a du verglas ou des conditions dangereuses, utilisez l’option météo défavorable.',
            'Vous pouvez fractionner la marche en deux plus petites sorties si nécessaire.',
        ],
        'avoid': [
            'Partir trop vite dès le début.',
            'Continuer malgré un malaise important ou un essoufflement inhabituel.',
        ],
        'color': '#E8F5E9',
    },
    'walk': {
        'title': 'Marche sur place',
        'summary': 'Une bonne alternative intérieure quand la météo ne permet pas de sortir.',
        'steps': [
            'Tenez-vous debout près d’un comptoir ou d’une chaise stable au besoin.',
            'Levez un pied puis l’autre dans un mouvement régulier.',
            'Balancez doucement les bras si c’est confortable.',
            'Continuez jusqu’au nombre de minutes prévu, même en deux courtes périodes.',
        ],
        'tips': [
            'Regardez la télévision ou écoutez de la musique pour rendre l’exercice plus agréable.',
            'Gardez une respiration normale.',
        ],
        'avoid': [
            'Piétiner trop rapidement au point de perdre l’équilibre.',
        ],
        'color': '#E3F2FD',
    },
    'chair': {
        'title': 'Se lever d’une chaise',
        'summary': 'Excellent exercice pour les cuisses et les fessiers.',
        'steps': [
            'Assoyez-vous sur une chaise stable, les pieds bien à plat.',
            'Penchez légèrement le tronc vers l’avant.',
            'Levez-vous sans élan si possible.',
            'Rasseyez-vous lentement sans vous laisser tomber.',
        ],
        'tips': [
            'Utilisez les accoudoirs ou les mains au besoin au début.',
            'Gardez les genoux dans l’axe des pieds.',
        ],
        'avoid': [
            'Se laisser tomber sur la chaise.',
            'Retenir sa respiration en se levant.',
        ],
        'color': '#FFF3E0',
    },
    'wall': {
        'title': 'Pompes contre un mur',
        'summary': 'Renforce doucement les bras, les épaules et la poitrine.',
        'steps': [
            'Placez-vous face au mur, les mains à hauteur des épaules.',
            'Gardez le corps aligné, puis pliez lentement les coudes.',
            'Approchez la poitrine du mur sans forcer.',
            'Repoussez doucement pour revenir à la position de départ.',
        ],
        'tips': [
            'Plus vous êtes près du mur, plus c’est facile.',
            'Gardez les talons au sol si possible.',
        ],
        'avoid': [
            'Hausser les épaules vers les oreilles.',
            'Cambrer fortement le dos.',
        ],
        'color': '#F3E5F5',
    },
    'calf': {
        'title': 'Montées sur les pointes',
        'summary': 'Travaille les mollets et aide l’équilibre.',
        'steps': [
            'Tenez-vous derrière une chaise stable.',
            'Montez doucement sur la pointe des pieds.',
            'Redescendez lentement jusqu’à la position normale.',
            'Répétez le nombre de fois prévu.',
        ],
        'tips': [
            'Gardez un appui léger sur la chaise.',
            'Montez moins haut si vous manquez d’équilibre.',
        ],
        'avoid': [
            'Faire le mouvement trop vite.',
            'Lâcher complètement l’appui si vous n’êtes pas stable.',
        ],
        'color': '#FFFDE7',
    },
}


def _guide_svg(exercise_key: str) -> str:
    """Retourne un petit dessin SVG simple et local, consultable dans l'app sans dépendance externe."""
    if exercise_key == 'outdoor_walk':
        svg = """
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'>
          <rect width='240' height='180' rx='18' fill='#E8F5E9'/>
          <circle cx='175' cy='38' r='18' fill='#FFD54F'/>
          <path d='M15 135 Q70 110 125 130 T225 128' fill='none' stroke='#81C784' stroke-width='10' stroke-linecap='round'/>
          <path d='M30 138 Q90 118 160 139' fill='none' stroke='#A1887F' stroke-width='8' stroke-linecap='round'/>
          <circle cx='108' cy='58' r='12' fill='#37474F'/>
          <line x1='108' y1='70' x2='108' y2='102' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='108' y1='79' x2='88' y2='95' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='108' y1='80' x2='126' y2='89' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='108' y1='102' x2='89' y2='126' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='108' y1='102' x2='129' y2='119' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <path d='M58 126 L58 76' stroke='#6D4C41' stroke-width='6'/>
          <circle cx='58' cy='66' r='16' fill='#66BB6A'/>
          <circle cx='46' cy='79' r='13' fill='#66BB6A'/>
          <circle cx='70' cy='80' r='13' fill='#66BB6A'/>
        </svg>
        """
    elif exercise_key == 'walk':
        svg = """
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'>
          <rect width='240' height='180' rx='18' fill='#E3F2FD'/>
          <rect x='35' y='35' width='170' height='110' rx='8' fill='#FFF' stroke='#90CAF9' stroke-width='4'/>
          <circle cx='120' cy='62' r='12' fill='#455A64'/>
          <line x1='120' y1='74' x2='120' y2='106' stroke='#455A64' stroke-width='6' stroke-linecap='round'/>
          <line x1='120' y1='84' x2='100' y2='98' stroke='#455A64' stroke-width='6' stroke-linecap='round'/>
          <line x1='120' y1='84' x2='139' y2='94' stroke='#455A64' stroke-width='6' stroke-linecap='round'/>
          <line x1='120' y1='106' x2='101' y2='128' stroke='#455A64' stroke-width='6' stroke-linecap='round'/>
          <line x1='120' y1='106' x2='139' y2='125' stroke='#455A64' stroke-width='6' stroke-linecap='round'/>
          <path d='M72 130 h24 M144 130 h24' stroke='#90A4AE' stroke-width='5' stroke-linecap='round'/>
        </svg>
        """
    elif exercise_key == 'chair':
        svg = """
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'>
          <rect width='240' height='180' rx='18' fill='#FFF3E0'/>
          <rect x='55' y='95' width='48' height='12' rx='3' fill='#8D6E63'/>
          <rect x='57' y='60' width='10' height='35' fill='#8D6E63'/>
          <rect x='91' y='60' width='10' height='35' fill='#8D6E63'/>
          <rect x='60' y='106' width='8' height='32' fill='#8D6E63'/>
          <rect x='90' y='106' width='8' height='32' fill='#8D6E63'/>
          <circle cx='135' cy='53' r='12' fill='#37474F'/>
          <line x1='135' y1='65' x2='135' y2='96' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='135' y1='75' x2='116' y2='90' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='135' y1='75' x2='152' y2='83' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='135' y1='96' x2='112' y2='120' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='135' y1='96' x2='152' y2='120' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
        </svg>
        """
    elif exercise_key == 'wall':
        svg = """
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'>
          <rect width='240' height='180' rx='18' fill='#F3E5F5'/>
          <rect x='170' y='30' width='16' height='120' rx='4' fill='#B39DDB'/>
          <circle cx='115' cy='56' r='12' fill='#37474F'/>
          <line x1='115' y1='68' x2='130' y2='92' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='130' y1='92' x2='167' y2='84' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='130' y1='92' x2='166' y2='96' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='130' y1='92' x2='112' y2='120' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='130' y1='92' x2='144' y2='123' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
        </svg>
        """
    else:  # calf
        svg = """
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 180'>
          <rect width='240' height='180' rx='18' fill='#FFFDE7'/>
          <rect x='70' y='38' width='10' height='92' fill='#8D6E63'/>
          <rect x='70' y='38' width='48' height='8' fill='#8D6E63'/>
          <circle cx='142' cy='52' r='12' fill='#37474F'/>
          <line x1='142' y1='64' x2='142' y2='97' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='142' y1='74' x2='124' y2='86' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='142' y1='74' x2='161' y2='85' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='142' y1='97' x2='130' y2='124' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <line x1='142' y1='97' x2='156' y2='124' stroke='#37474F' stroke-width='6' stroke-linecap='round'/>
          <path d='M122 127 h16 M151 127 h16' stroke='#F9A825' stroke-width='5' stroke-linecap='round'/>
        </svg>
        """
    return 'data:image/svg+xml;utf8,' + quote(' '.join(svg.split()))


def _open_quick_help(exercise: dict) -> None:
    guide = EXERCISE_GUIDE.get(exercise['key'])
    if not guide:
        return
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl p-4 gap-3'):
        with ui.row().classes('w-full items-start gap-4 flex-wrap'):
            ui.image(_guide_svg(exercise['key'])).classes('w-56 rounded-lg border')
            with ui.column().classes('gap-1 flex-1 min-w-[240px]'):
                ui.label(guide['title']).classes('text-xl font-bold')
                ui.label(guide['summary']).classes('text-sm text-gray-600')
                ui.label(exercise['info']).classes('text-sm')
                ui.label(f"Objectif courant : {exercise['target']} {exercise['unit']}").classes('text-sm font-medium text-primary')
        with ui.expansion('Étapes à suivre', value=True).classes('w-full'):
            with ui.column().classes('gap-1 pl-2'):
                for idx, step in enumerate(guide['steps'], start=1):
                    ui.label(f'{idx}. {step}').classes('text-sm')
        with ui.expansion('Conseils utiles').classes('w-full'):
            with ui.column().classes('gap-1 pl-2'):
                for item in guide['tips']:
                    ui.label(f'• {item}').classes('text-sm')
        with ui.expansion('À éviter').classes('w-full'):
            with ui.column().classes('gap-1 pl-2'):
                for item in guide['avoid']:
                    ui.label(f'• {item}').classes('text-sm')
        ui.label('Respirez normalement pendant l’exercice. Arrêtez en cas de douleur thoracique, malaise ou essoufflement inhabituel.').classes('text-xs text-gray-500')
        with ui.row().classes('justify-end w-full'):
            ui.button('Fermer', on_click=dialog.close)
    dialog.open()


def _open_guide_sheet() -> None:
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-5xl p-4 gap-4'):
        ui.label('Feuille explicative des exercices').classes('text-2xl font-bold')
        ui.label('Cette feuille regroupe les exercices de ton programme Mise en forme. Elle est conçue pour être simple à consulter directement dans l’application.').classes('text-sm text-gray-600')
        with ui.row().classes('w-full items-start gap-4 flex-wrap'):
            with ui.card().classes('min-w-[260px] flex-1 bg-blue-50'):
                ui.label('Règles simples').classes('font-semibold')
                for rule in [
                    'Commence doucement et garde un rythme confortable.',
                    'Tu dois pouvoir parler pendant la marche.',
                    'Respire normalement; ne retiens pas ton souffle.',
                    'La régularité compte plus que la performance.',
                ]:
                    ui.label(f'• {rule}').classes('text-sm')
            with ui.card().classes('min-w-[260px] flex-1 bg-red-50'):
                ui.label('Quand arrêter').classes('font-semibold')
                for alert in [
                    'Douleur thoracique',
                    'Étourdissement ou malaise important',
                    'Essoufflement inhabituel',
                    'Douleur qui empire pendant l’exercice',
                ]:
                    ui.label(f'• {alert}').classes('text-sm')
        with ui.grid(columns=2).classes('w-full gap-4'):
            for key in ('outdoor_walk', 'walk', 'chair', 'wall', 'calf'):
                guide = EXERCISE_GUIDE[key]
                with ui.card().classes('w-full h-full'):
                    with ui.row().classes('w-full items-start gap-3 flex-wrap'):
                        ui.image(_guide_svg(key)).classes('w-44 rounded-lg border')
                        with ui.column().classes('gap-1 flex-1 min-w-[220px]'):
                            ui.label(guide['title']).classes('text-lg font-bold')
                            ui.label(guide['summary']).classes('text-sm text-gray-600')
                            ui.label('Étapes :').classes('text-sm font-semibold mt-1')
                            for idx, step in enumerate(guide['steps'], start=1):
                                ui.label(f'{idx}. {step}').classes('text-sm')
                            ui.label('Conseils :').classes('text-sm font-semibold mt-1')
                            for tip in guide['tips'][:2]:
                                ui.label(f'• {tip}').classes('text-sm')
        ui.separator()
        ui.label('Astuce : sur les cartes de la séance du jour, le bouton « ? » ouvre aussi l’explication rapide de l’exercice concerné.').classes('text-xs text-gray-500')
        with ui.row().classes('justify-end w-full'):
            ui.button('Fermer', on_click=dialog.close)
    dialog.open()


def fitness_panel(user, show_heading=False):
    uid = user['id']
    saved = settings(uid)
    today = date.today()
    selected = {'day': today}
    base = ui.column().classes('w-full gap-4')

    def render():
        day = selected['day']
        week = week_number(saved['started_on'], day, saved['level_offset'])
        plan = daily_plan(week, day)
        rows = entries_between(uid, min(day, today - timedelta(days=27)), today)
        records = {(r['session_date'], r['exercise_key']): r for r in rows}
        with base:
            base.clear()
            if show_heading:
                ui.label('Mise en forme').classes('text-2xl font-bold')
            ui.label('Marche extérieure quotidienne et exercices doux, sans appareil').classes('text-gray-500')
            with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
                ui.label(f'Semaine {week} sur 8').classes('text-xl font-semibold')
                with ui.row().classes('gap-2 flex-wrap'):
                    ui.button('Feuille explicative', icon='article', on_click=_open_guide_sheet).props('outline')
                    ui.button('Plus doux', icon='remove', on_click=lambda: adjust(-1)).props('outline dense')
                    ui.button('Progresser', icon='add', on_click=lambda: adjust(1)).props('outline dense')
            ui.label('La progression est indicative : restez à une étape confortable. Les changements de niveau modifient les prochains objectifs, pas les séances enregistrées.').classes('text-xs text-gray-500')
            with ui.row().classes('items-center gap-2 flex-wrap'):
                ui.button(icon='chevron_left', on_click=lambda: go(-1)).props('flat round')
                ui.label(day.strftime('%d/%m/%Y')).classes('text-lg font-bold')
                ui.button(icon='chevron_right', on_click=lambda: go(1)).props('flat round')
                ui.button('Aujourd’hui', on_click=lambda: go(0)).props('outline dense')
            done, total = day_progress(plan, records, day)
            ui.linear_progress(done / max(total, 1), show_value=False).classes('w-full')
            ui.label(f'{done} sur {total} objectifs réalisés (marche extérieure ou alternative intérieure)').classes('text-sm text-gray-600')
            for ex in plan:
                rec = records.get((day, ex['key']), {})
                with ui.card().classes('w-full'):
                    with ui.row().classes('items-center w-full gap-3'):
                        ui.icon('check_circle' if rec.get('completed') else ('cloud' if rec.get('skip_reason') == 'meteo' else 'radio_button_unchecked'), size='md').classes('text-primary')
                        with ui.column().classes('gap-0 flex-1'):
                            ui.label(ex['name']).classes('font-semibold')
                            ui.label(f"Objectif : {ex['target']} {ex['unit']}" + (' · facultatif si marche extérieure effectuée' if ex.get('optional') else '')).classes('text-sm text-gray-600')
                        ui.button(icon='help_outline', on_click=lambda ex=ex: _open_quick_help(ex)).props('flat round dense').tooltip('Voir l’explication')
                        ui.button('Modifier' if rec.get('completed') or rec.get('skip_reason') else 'Faire', on_click=lambda ex=ex, rec=rec: edit(ex, rec)).props('outline')
                    if rec.get('skip_reason') == 'meteo':
                        ui.label('Météo défavorable : reporté, sans pénalité. Marche sur place possible.').classes('text-sm text-orange-700')
                    ui.label(ex['info']).classes('text-sm text-gray-500')
            with ui.card().classes('w-full'):
                ui.label('Historique des 28 derniers jours').classes('font-semibold')
                completed_days = 0
                for i in range(27, -1, -1):
                    d = today - timedelta(days=i)
                    dp = daily_plan(week_number(saved['started_on'], d, saved['level_offset']), d)
                    n, required = day_progress(dp, records, d)
                    if n == required:
                        completed_days += 1
                ui.label(f'{completed_days} journées entièrement réalisées sur 28').classes('text-sm')
                with ui.row().classes('gap-1 flex-wrap'):
                    for i in range(27, -1, -1):
                        d = today - timedelta(days=i)
                        dp = daily_plan(week_number(saved['started_on'], d, saved['level_offset']), d)
                        n, required = day_progress(dp, records, d)
                        status = 'check_circle' if n == required else ('timelapse' if n else 'radio_button_unchecked')
                        ui.button(icon=status, on_click=lambda d=d: choose(d)).props('flat dense round').tooltip(f'{d:%d/%m}: {n}/{required}')
            ui.label('La marche extérieure est proposée chaque jour; par forte pluie, verglas ou conditions dangereuses, choisissez « météo défavorable » et faites la marche sur place si vous le souhaitez.').classes('text-xs text-gray-500')
            ui.label('Sécurité : commencez doucement, respirez normalement et arrêtez en cas de douleur thoracique, malaise ou essoufflement inhabituel. La marche sur place peut être fractionnée.').classes('text-xs text-gray-500')

    def adjust(delta):
        change_level(uid, delta)
        saved['level_offset'] = settings(uid)['level_offset']
        render()

    def go(delta):
        selected['day'] = today if delta == 0 else selected['day'] + timedelta(days=delta)
        if selected['day'] > today:
            selected['day'] = today
        render()

    def choose(day):
        selected['day'] = day
        render()

    def edit(ex, rec):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-lg'):
            ui.label(ex['name']).classes('text-lg font-bold')
            ui.label(ex['info']).classes('text-sm')
            done = ui.checkbox('Exercice effectué', value=bool(rec.get('completed')))
            weather = ui.checkbox('Reporté à cause de la météo (sans séance effectuée)', value=rec.get('skip_reason') == 'meteo') if ex['key'] == 'outdoor_walk' else None
            amount = ui.number(ex['unit'].capitalize(), value=rec.get('actual_value') if rec.get('actual_value') is not None else ex['target'], min=0, max=999, precision=0)
            difficulty = ui.select({'facile': 'Trop facile', 'correct': 'Correct', 'difficile': 'Trop difficile'}, label='Ressenti (facultatif)', value=rec.get('difficulty'))
            note = ui.textarea('Note facultative', value=rec.get('notes') or '').classes('w-full')

            def save():
                try:
                    save_entry(uid, selected['day'], ex['key'], bool(done.value) and not (weather and weather.value), int(amount.value) if amount.value is not None and not (weather and weather.value) else None, difficulty.value, note.value, 'meteo' if weather and weather.value else None)
                except (ValueError, TypeError) as err:
                    ui.notify(str(err), type='negative')
                    return
                # Notifier tant que le contexte du dialogue existe encore.
                # render() reconstruit base et supprime le parent du dialogue.
                ui.notify('Séance enregistrée', type='positive')
                dialog.close()
                render()

            with ui.row().classes('justify-between w-full items-center'):
                ui.button('Voir l’explication', icon='help_outline', on_click=lambda ex=ex: _open_quick_help(ex)).props('flat')
                with ui.row().classes('gap-2'):
                    ui.button('Annuler', on_click=dialog.close).props('flat')
                    ui.button('Enregistrer', on_click=save)
        dialog.open()

    render()

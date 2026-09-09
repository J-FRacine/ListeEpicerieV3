"""Caractérisation des Objectifs avec interface et services simulés."""
import ast
from datetime import date
from decimal import Decimal
import inspect
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock

from finances_goals import GoalsPanelHandle, build_goals_panel
from test_finances_financing_ui import SimulatedUi

ROOT = Path(__file__).resolve().parents[1]


def goal(**values):
    return dict(id=42, goal_type='category', category_id=3, tag_id=None, target_name='Maison',
                monthly_amount=Decimal('150'), start_month=date(2026, 9, 1),
                end_month=date(2027, 3, 1), carry_policy='positive', max_carry=Decimal('50'),
                is_active=True) | values


def build(rows=None):
    ui = SimulatedUi()
    deps = {name: Mock(name=name) for name in inspect.signature(build_goals_panel).parameters}
    deps.update(ui=ui, user_id=7, goals_tab=object(), _money=str,
                CARRY_POLICIES={'none': 'Aucun', 'positive': 'Positif'})
    deps['list_goals'].return_value = rows or []
    deps['_category_options'].return_value = {3: 'Maison'}
    deps['_tag_options'].return_value = {5: 'Voyage'}
    return build_goals_panel(**deps), ui, deps


def parent_tree():
    return ast.parse(''.join(p.read_text(encoding='utf-8') for p in sorted(ROOT.glob('finances_part_*.pyfrag'))))


class GoalsUiTests(unittest.TestCase):
    def test_handle_is_lazy_and_uses_current_callback(self):
        callback = Mock()
        handle = GoalsPanelHandle(callback)
        callback.assert_not_called()
        handle.refresh()
        callback.assert_called_once_with()
        replacement = Mock()
        handle.on_refresh = replacement
        handle.refresh()
        replacement.assert_called_once_with()

    def test_empty_panel_and_refresh(self):
        handle, ui, deps = build()
        self.assertIsInstance(handle, GoalsPanelHandle)
        ui.find('label', 'Aucun objectif.')
        ui.find('button', 'Ajouter')
        deps['list_goals'].assert_called_once_with(7)
        handle.refresh()
        self.assertEqual(deps['list_goals'].call_count, 2)
        deps['refresh_all'].assert_not_called()

    def test_list_and_toggle_both_directions_keep_global_refresh(self):
        for active in (True, False):
            with self.subTest(active=active):
                _, ui, deps = build([goal(is_active=active)])
                ui.find('label', 'Maison')
                ui.find('label', '150 / mois — Positif')
                switch = ui.find('switch')
                self.assertIs(switch[2]['value'], active)
                events = []
                deps['toggle_goal'].side_effect = lambda *args: events.append('toggle')
                deps['refresh_all'].side_effect = lambda: events.append('refresh')
                switch[2]['on_change'](SimpleNamespace(value=not active))
                deps['toggle_goal'].assert_called_once_with(7, 42, not active)
                self.assertEqual(events, ['toggle', 'refresh'])
                deps['toggle_goal'].side_effect = ValueError('refus')
                with self.assertRaisesRegex(ValueError, 'refus'):
                    switch[2]['on_change'](SimpleNamespace(value=active))
                deps['refresh_all'].assert_called_once_with()

    def test_creation_defaults_and_exact_save_order(self):
        _, ui, deps = build()
        ui.click('Ajouter')
        ui.find('label', 'Nouvel objectif')
        self.assertEqual(ui.find('toggle')[3].value, 'category')
        self.assertEqual(ui.find('select', 'Cible')[1][0], {3: 'Maison'})
        self.assertIsNone(ui.find('select', 'Cible')[3].value)
        self.assertIsNone(ui.find('number', 'Objectif mensuel')[3].value)
        self.assertIsNone(ui.find('number', 'Plafond de report facultatif')[3].value)
        self.assertEqual(ui.find('input', 'Début')[3].value, date.today().strftime('%Y-%m'))
        self.assertEqual(ui.find('input', 'Fin facultative')[3].value, '')
        self.assertEqual(ui.find('select', 'Report au mois suivant')[3].value, 'none')
        ui.find('select', 'Cible')[3].value = 3
        ui.find('number', 'Objectif mensuel')[3].value = 125
        ui.find('input', 'Début')[3].value = '2026-10'
        events = []
        deps['save_goal'].side_effect = lambda **kwargs: events.append('save')
        ui.find('dialog')[3].close.side_effect = lambda: events.append('close')
        ui.notify.side_effect = lambda *args, **kwargs: events.append('notify')
        deps['refresh_all'].side_effect = lambda: events.append('refresh')
        ui.click('Enregistrer')
        deps['save_goal'].assert_called_once_with(user_id=7, goal_id=None, goal_type='category',
            target_id=3, monthly_amount=125, carry_policy='none', start_month='2026-10', end_month=None, max_carry=None)
        self.assertEqual(events, ['save', 'close', 'notify', 'refresh'])
        ui.notify.assert_called_once_with('Objectif enregistré.', type='positive')

    def test_edit_category_and_tag_preserve_all_save_fields(self):
        for kind, target in [('category', 3), ('tag', 5)]:
            with self.subTest(kind=kind):
                _, ui, deps = build([goal(goal_type=kind, tag_id=5)])
                ui.click(icon='edit')
                ui.find('label', 'Modifier l’objectif')
                self.assertEqual(ui.find('select', 'Cible')[3].value, target)
                self.assertEqual(ui.find('select', 'Cible')[1][0], {3: 'Maison'} if kind == 'category' else {5: 'Voyage'})
                ui.click('Enregistrer')
                deps['save_goal'].assert_called_once_with(user_id=7, goal_id=42, goal_type=kind,
                    target_id=target, monthly_amount=Decimal('150'), carry_policy='positive',
                    start_month='2026-09', end_month='2027-03', max_carry=Decimal('50'))
                ui.find('dialog')[3].close.assert_called_once_with()
                deps['refresh_all'].assert_called_once_with()

    def test_target_options_reset_in_both_directions(self):
        _, ui, deps = build([goal()])
        ui.click(icon='edit')
        kind = ui.find('toggle')[3]
        target = ui.find('select', 'Cible')[3]
        callback = kind.on_value_change.call_args.args[0]
        for value, options in [('tag', {5: 'Voyage'}), ('category', {3: 'Maison'})]:
            target.value = 99
            kind.value = value
            callback(SimpleNamespace(value=value))
            self.assertEqual(target.options, options)
            self.assertIsNone(target.value)
        self.assertEqual(target.update.call_count, 2)
        deps['save_goal'].assert_not_called()

    def test_save_error_and_cancel_do_not_refresh(self):
        _, ui, deps = build([goal()])
        ui.click(icon='edit')
        deps['save_goal'].side_effect = ValueError('refus')
        ui.click('Enregistrer')
        ui.find('dialog')[3].close.assert_not_called()
        deps['refresh_all'].assert_not_called()
        ui.notify.assert_called_once_with('refus', type='warning')
        ui.click('Annuler')
        ui.find('dialog')[3].close.assert_called_once_with()
        deps['save_goal'].assert_called_once()
        deps['refresh_all'].assert_not_called()


class GoalsArchitectureTests(unittest.TestCase):
    def test_independent_import_and_standard_imports_only(self):
        script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'finances', 'finances_data', 'db', 'nicegui', 'psycopg'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_goals
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tree = ast.parse((ROOT / 'finances_goals.py').read_text(encoding='utf-8'))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertTrue(all(isinstance(n, ast.ImportFrom) for n in imports))
        self.assertEqual({n.module for n in imports}, {'dataclasses', 'datetime', 'typing'})

    def test_parent_injects_lazy_services_and_removes_internal_block(self):
        tree = parent_tree()
        assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'goals_panel' for t in n.targets))
        self.assertEqual(assignment.value.func.id, 'build_goals_panel')
        env = {name: Mock() for name in ('ui', 'user_id', 'goals_tab', 'CARRY_POLICIES', 'build_goals_panel')}
        exec(compile(ast.Module(body=[assignment], type_ignores=[]), '<parent>', 'exec'), env)
        kwargs = env['build_goals_panel'].call_args.kwargs
        for _ in range(2):
            for name in ('save_goal', 'toggle_goal', 'list_goals', 'refresh_all'):
                env[name] = Mock()
                kwargs[name](7, sample=True)
                env[name].assert_called_once_with(7, sample=True)
        internal = {'goals_box', 'goal_dialog', 'render_goals', 'change_goal_state'}
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        definitions = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertTrue(internal.isdisjoint(names | definitions))
        self.assertNotIn('with ui.tab_panel(goals_tab)', (ROOT / 'finances_part_10.pyfrag').read_text(encoding='utf-8'))

    def test_global_refresh_calls_handle(self):
        refresh = next(n for n in ast.walk(parent_tree()) if isinstance(n, ast.FunctionDef) and n.name == 'refresh_all')
        env = {n.id: MagicMock() for n in ast.walk(refresh) if isinstance(n, ast.Name)}
        exec(compile(ast.Module(body=[refresh], type_ignores=[]), '<refresh>', 'exec'), env)
        env['refresh_all']()
        env['goals_panel'].refresh.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()

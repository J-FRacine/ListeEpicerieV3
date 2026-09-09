"""Contrats et actions de Récurrences, sans NiceGUI ni base de données."""
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

from finances_recurrences import RecurrencesPanelHandle, build_recurrences_panel
from test_finances_financing_ui import SimulatedUi

ROOT = Path(__file__).resolve().parents[1]


def recurrence(**values):
    return dict(id=42, description='Assurance', amount=Decimal('75.50'), transaction_type='expense',
                frequency_interval=2, frequency_unit='week', start_date=date(2026, 9, 1),
                end_date=date(2027, 9, 1), next_date=date(2026, 9, 15), category_id=3,
                tag_ids=[5, 6], payment_method_id=4, payment_method_name='Banque',
                confirmation_mode='auto', budget_excluded=True, bank_programmed=True,
                reminder_enabled=True, reminder_time='08:30:00', note='Note existante',
                is_active=True) | values


def build(rows=None):
    ui = SimulatedUi()
    deps = {name: Mock(name=name) for name in inspect.signature(build_recurrences_panel).parameters}
    deps.update(ui=ui, user_id=7, recurring_tab=object(),
                TRANSACTION_TYPES={'expense': 'Dépense', 'income': 'Revenu'},
                FREQUENCY_UNITS={'month': 'Mois', 'week': 'Semaine'},
                CONFIRMATION_MODES={'confirm': 'À confirmer', 'auto': 'Automatique'},
                _signed=lambda amount, kind: f'{kind}:{amount}')
    deps['list_recurrences'].return_value = rows or []
    for name, options in [('_category_options', {3: 'Assurance'}),
                          ('_payment_options', {4: 'Banque'}), ('_tag_options', {5: 'Maison', 6: 'Fixe'})]:
        deps[name].return_value = options
    return build_recurrences_panel(**deps), ui, deps


def parent_tree():
    return ast.parse(''.join(p.read_text(encoding='utf-8') for p in sorted(ROOT.glob('finances_part_*.pyfrag'))))


class RecurrencesUiTests(unittest.TestCase):
    def test_handle_is_lazy_and_forwards_to_current_callbacks(self):
        refresh, dialog = Mock(), Mock()
        handle = RecurrencesPanelHandle(refresh, dialog)
        refresh.assert_not_called()
        dialog.assert_not_called()
        handle.refresh()
        refresh.assert_called_once_with()
        handle.open_dialog()
        dialog.assert_called_once_with()
        replacement = Mock()
        handle.on_open_dialog = replacement
        handle.open_dialog(row={'id': 42})
        replacement.assert_called_once_with(row={'id': 42})
        handle.on_refresh = replacement
        handle.refresh()
        self.assertEqual(replacement.call_count, 2)

    def test_empty_panel_and_refresh_use_existing_reader(self):
        handle, ui, deps = build()
        self.assertIsInstance(handle, RecurrencesPanelHandle)
        ui.find('label', 'Aucune récurrence.')
        ui.find('button', 'Ajouter')
        deps['list_recurrences'].assert_called_once_with(7)
        handle.refresh()
        self.assertEqual(deps['list_recurrences'].call_count, 2)
        deps['refresh_all'].assert_not_called()

    def test_list_preserves_labels_and_activation_in_both_directions(self):
        for active in (True, False):
            with self.subTest(active=active):
                _, ui, deps = build([recurrence(is_active=active)])
                ui.find('label', 'Assurance')
                ui.find('label', 'expense:75.50 — tous les 2 semaine(s)')
                ui.find('label', 'Prochaine : 15/09/2026 — Automatique — Banque — Hors budget — Programmée à la banque — Rappel 08:30')
                switch = ui.find('switch')
                self.assertIs(switch[2]['value'], active)
                switch[2]['on_change'](SimpleNamespace(value=not active))
                deps['toggle_recurrence'].assert_called_once_with(7, 42, not active)
                self.assertEqual(deps['list_recurrences'].call_count, 2)
                deps['refresh_all'].assert_not_called()

    def test_add_defaults_and_save_generate_without_force_planned(self):
        _, ui, deps = build()
        ui.click('Ajouter')
        ui.find('label', 'Nouvelle récurrence')
        expected_defaults = [('number', 'Montant', None), ('input', 'Description', ''),
            ('number', 'Tous les', 1), ('select', 'Unité', 'month'),
            ('input', 'Fin facultative', ''), ('select', 'Catégorie', None),
            ('select', 'Mode de paiement par défaut', None), ('select', 'Étiquettes', []),
            ('input', 'Heure du rappel', '09:00'), ('select', 'Création des occurrences', 'confirm')]
        for kind, label, value in expected_defaults:
            self.assertEqual(ui.find(kind, label)[3].value, value)
        self.assertTrue(all(w[3].value is False for w in ui.widgets if w[0] == 'checkbox'))
        ui.find('number', 'Montant')[3].value = 25
        ui.find('input', 'Description')[3].value = 'Nouvelle'
        ui.find('input', 'Début')[3].value = '2026-10-01'
        ui.click('Enregistrer')
        deps['save_recurrence'].assert_called_once_with(
            user_id=7, recurrence_id=None, transaction_type='expense', description='Nouvelle', amount=25,
            category_id=None, tag_ids=[], payment_method_id=None, note='', frequency_unit='month',
            frequency_interval=1, start_date='2026-10-01', end_date=None, confirmation_mode='confirm',
            budget_excluded=False, bank_programmed=False, reminder_enabled=False, reminder_time='09:00')
        deps['generate_due_recurrences'].assert_called_once_with(7, force_planned=False)
        deps['refresh_all'].assert_called_once_with()
        ui.find('dialog')[3].close.assert_called_once_with()

    def test_edit_preserves_every_field_and_generation_order(self):
        _, ui, deps = build([recurrence()])
        ui.click(icon='edit')
        ui.find('label', 'Modifier la récurrence')
        events = []
        deps['save_recurrence'].side_effect = lambda **kwargs: events.append('save')
        deps['generate_due_recurrences'].side_effect = lambda *args, **kwargs: events.append('generate')
        deps['refresh_all'].side_effect = lambda: events.append('refresh')
        ui.click('Enregistrer')
        self.assertEqual(events, ['save', 'generate', 'refresh'])
        deps['save_recurrence'].assert_called_once_with(
            user_id=7, recurrence_id=42, transaction_type='expense', description='Assurance',
            amount=Decimal('75.50'), category_id=3, tag_ids=[5, 6], payment_method_id=4,
            note='Note existante', frequency_unit='week', frequency_interval=2,
            start_date='2026-09-01', end_date='2027-09-01', confirmation_mode='auto',
            budget_excluded=True, bank_programmed=True, reminder_enabled=True, reminder_time='08:30')
        deps['generate_due_recurrences'].assert_called_once_with(7, force_planned=True)
        ui.find('dialog')[3].close.assert_called_once_with()

    def test_save_or_generation_error_keeps_dialog_open_without_refresh(self):
        for failing in ('save_recurrence', 'generate_due_recurrences'):
            with self.subTest(failing=failing):
                handle, ui, deps = build()
                handle.open_dialog(recurrence())
                deps[failing].side_effect = ValueError('refus')
                ui.click('Enregistrer')
                deps['refresh_all'].assert_not_called()
                ui.find('dialog')[3].close.assert_not_called()
                ui.notify.assert_called_once_with('refus', type='warning')
                if failing == 'save_recurrence':
                    deps['generate_due_recurrences'].assert_not_called()
                else:
                    deps['generate_due_recurrences'].assert_called_once_with(7, force_planned=True)

    def test_delete_both_planned_choices_and_errors(self):
        for delete_planned, label in [(True, 'Supprimer aussi les transactions prévues non confirmées'),
                                     (False, 'Conserver les transactions prévues comme transactions indépendantes')]:
            for fails in (False, True):
                with self.subTest(delete_planned=delete_planned, fails=fails):
                    _, ui, deps = build([recurrence()])
                    ui.click(icon='delete')
                    if fails:
                        deps['delete_recurrence'].side_effect = ValueError('refus')
                    ui.click(label)
                    deps['delete_recurrence'].assert_called_once_with(7, 42, delete_planned=delete_planned)
                    deps['generate_due_recurrences'].assert_not_called()
                    if fails:
                        deps['refresh_all'].assert_not_called()
                        ui.find('dialog')[3].close.assert_not_called()
                        ui.notify.assert_called_once_with('refus', type='warning')
                    else:
                        deps['refresh_all'].assert_called_once_with()
                        ui.find('dialog')[3].close.assert_called_once_with()

    def test_cancel_dialogs_does_not_write_or_refresh(self):
        for icon in ('edit', 'delete'):
            with self.subTest(icon=icon):
                _, ui, deps = build([recurrence()])
                ui.click(icon=icon)
                ui.click('Annuler')
                ui.find('dialog')[3].close.assert_called_once_with()
                for name in ('save_recurrence', 'delete_recurrence', 'generate_due_recurrences', 'refresh_all'):
                    deps[name].assert_not_called()


class RecurrencesArchitectureTests(unittest.TestCase):
    def test_independent_import_and_standard_imports_only(self):
        script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'finances', 'finances_data', 'db', 'nicegui', 'psycopg'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_recurrences
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tree = ast.parse((ROOT / 'finances_recurrences.py').read_text(encoding='utf-8'))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertTrue(all(isinstance(n, ast.ImportFrom) for n in imports))
        self.assertEqual({n.module for n in imports}, {'dataclasses', 'datetime', 'typing'})

    def test_parent_builder_is_lazy_and_internal_widgets_are_gone(self):
        tree = parent_tree()
        assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'recurrences_panel' for t in n.targets))
        self.assertEqual(assignment.value.func.id, 'build_recurrences_panel')
        env = {name: Mock() for name in ('ui', 'user_id', 'recurring_tab', 'TRANSACTION_TYPES',
                                        'FREQUENCY_UNITS', 'CONFIRMATION_MODES', 'build_recurrences_panel')}
        exec(compile(ast.Module(body=[assignment], type_ignores=[]), '<parent>', 'exec'), env)
        kwargs = env['build_recurrences_panel'].call_args.kwargs
        for _ in range(2):
            for name in ('save_recurrence', 'generate_due_recurrences', 'refresh_all'):
                env[name] = Mock()
                kwargs[name](7, sample=True)
                env[name].assert_called_once_with(7, sample=True)
        forbidden = {'recurrence_box', 'render_recurrences', 'recurrence_dialog', 'delete_recurrence_dialog', 'change_recurrence_state'}
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        definitions = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertTrue(forbidden.isdisjoint(names | definitions))
        fragment = (ROOT / 'finances_part_10.pyfrag').read_text(encoding='utf-8')
        self.assertNotIn('with ui.tab_panel(recurring_tab)', fragment)
        self.assertIn('# OBJECTIFS', fragment)

    def test_global_refresh_and_external_account_editor_use_current_handle(self):
        tree = parent_tree()
        refresh = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'refresh_all')
        env = {n.id: MagicMock() for n in ast.walk(refresh) if isinstance(n, ast.Name)}
        exec(compile(ast.Module(body=[refresh], type_ignores=[]), '<refresh>', 'exec'), env)
        env['refresh_all']()
        env['recurrences_panel'].refresh.assert_called_once_with()
        account = next(n for n in ast.walk(tree) if isinstance(n, ast.Call)
                       and isinstance(n.func, ast.Name) and n.func.id == 'build_account_panel')
        callback = next(k.value for k in account.keywords if k.arg == 'recurrence_dialog')
        env = {}
        forward = eval(compile(ast.Expression(body=callback), '<account callback>', 'eval'), env)
        for _ in range(2):
            handle, ui, deps = build()
            env['recurrences_panel'] = handle
            forward(recurrence())
            ui.find('label', 'Modifier la récurrence')
            ui.click('Enregistrer')
            deps['save_recurrence'].assert_called_once()
            self.assertEqual(deps['save_recurrence'].call_args.kwargs['recurrence_id'], 42)
            deps['generate_due_recurrences'].assert_called_once_with(7, force_planned=True)


if __name__ == '__main__':
    unittest.main()

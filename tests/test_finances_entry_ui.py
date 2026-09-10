"""Contrats de Saisie rapide, avec widgets et services simulés."""
import ast
from datetime import date
import inspect
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock

from finances_entry import EntryPanelHandle, build_entry_panel
from test_finances_financing_ui import SimulatedUi

ROOT = Path(__file__).resolve().parents[1]
ADD_CATEGORY = '__jf_add_category__'
ADD_TAG = '__jf_add_tag__'


def build():
    ui = SimulatedUi()
    deps = {name: Mock(name=name) for name in inspect.signature(build_entry_panel).parameters}
    deps.update(ui=ui, user_id=7, entry_tab=object(), ADD_CATEGORY_OPTION=ADD_CATEGORY, ADD_TAG_OPTION=ADD_TAG,
                TRANSACTION_TYPES={'expense': 'Dépense', 'income': 'Revenu'},
                TRANSACTION_STATUSES={'confirmed': 'Confirmée', 'planned': 'À confirmer'})
    deps['_quick_category_options'].return_value = {3: 'Maison', ADD_CATEGORY: 'Ajouter'}
    deps['_quick_tag_options'].return_value = {5: 'Fixe', ADD_TAG: 'Ajouter'}
    deps['_payment_options'].return_value = {4: 'Banque'}
    deps['list_categories'].return_value = [
        dict(id=3, name='Dépenses', parent_id=None, category_type='expense'),
        dict(id=4, name='Revenus', parent_id=None, category_type='income'),
        dict(id=6, name='Mixte', parent_id=None, category_type='both'),
        dict(id=8, name='Enfant', parent_id=3, category_type='expense')]
    deps['get_or_create_finance_category'].return_value = {'id': 9, 'created': True}
    deps['get_or_create_finance_tag'].return_value = {'id': 6, 'created': True}
    handle = build_entry_panel(**deps)
    fields = {'kind': ui.find('toggle')[3]}
    for name, widget, label in [
        ('amount', 'number', 'Montant'), ('when', 'input', 'Date'), ('description', 'input', 'Description'),
        ('category', 'select', 'Catégorie ou sous-catégorie'), ('payment_method', 'select', 'Mode de paiement'),
        ('tags', 'select', 'Étiquettes'), ('status', 'select', 'Statut de transaction'),
        ('budget_excluded', 'checkbox', 'Hors budget — transfert, paiement de carte ou déplacement d’épargne'),
        ('bank_programmed', 'checkbox', 'Programmée dans le compte bancaire'),
        ('reminder_enabled', 'checkbox', 'Me rappeler cette transaction le jour prévu'),
        ('reminder_time', 'input', 'Heure du rappel'), ('reconciled', 'checkbox', 'Transaction conciliée'),
        ('reconciliation_date', 'input', 'Date de conciliation (facultative)'), ('note', 'textarea', 'Note facultative')]:
        fields[name] = ui.find(widget, label)[3]
    return handle, ui, deps, fields


def fill(fields):
    values = dict(kind='income', amount=123.45, when='2026-10-12', description='Salaire', category=3,
                  payment_method=4, tags=[5, ADD_TAG], status='planned', budget_excluded=True,
                  bank_programmed=True, reminder_enabled=True, reminder_time='07:30', reconciled=True,
                  reconciliation_date='2026-10-13', note='Note test')
    for name, value in values.items():
        fields[name].value = value
    return values


def change(widget, value):
    widget.value = value
    widget.on_value_change.call_args.args[0](SimpleNamespace(value=value))


def parent_tree():
    return ast.parse(''.join(p.read_text(encoding='utf-8') for p in sorted(ROOT.glob('finances_part_*.pyfrag'))))


class EntryUiTests(unittest.TestCase):
    def test_handle_is_lazy_and_uses_current_callback(self):
        callback, replacement = Mock(), Mock()
        handle = EntryPanelHandle(callback)
        callback.assert_not_called()
        handle.reload_options()
        callback.assert_called_once_with()
        handle.on_reload_options = replacement
        handle.reload_options()
        replacement.assert_called_once_with()

    def test_construction_defaults_without_writes(self):
        handle, ui, deps, fields = build()
        self.assertIsInstance(handle, EntryPanelHandle)
        ui.find('label', 'Saisie rapide')
        ui.find('expansion', 'Note, statut, rappel, budget et conciliation')
        for name, expected in dict(kind='expense', when=date.today().isoformat(), status='confirmed',
                                   budget_excluded=False, bank_programmed=False, reminder_enabled=False,
                                   reminder_time='09:00', reconciled=False).items():
            self.assertEqual(fields[name].value, expected)
        for name in ('save_transaction', 'get_or_create_finance_category', 'get_or_create_finance_tag',
                     '_card_payment_dialog', 'refresh_all', 'refresh_dashboard', 'list_categories'):
            deps[name].assert_not_called()

    def test_reload_options_preserves_selections_and_updates_all_three_in_order(self):
        handle, _, deps, fields = build()
        values = dict(category=3, tags=[5], payment_method=4)
        events = []
        for name in values:
            fields[name].value = values[name]
            fields[name].update.side_effect = lambda name=name: events.append(name)
        for service, result in [('_quick_category_options', {9: 'Autre'}), ('_quick_tag_options', {6: 'Nouvelle'}),
                                ('_payment_options', {8: 'Carte'})]:
            deps[service].reset_mock()
            deps[service].return_value = result
        handle.reload_options()
        self.assertEqual(events, ['category', 'tags', 'payment_method'])
        for name, service in [('category', '_quick_category_options'), ('tags', '_quick_tag_options'), ('payment_method', '_payment_options')]:
            deps[service].assert_called_once_with(7)
            self.assertEqual(fields[name].options, deps[service].return_value)
            self.assertEqual(fields[name].value, values[name])
            fields[name].update.assert_called_once_with()

    def test_save_exact_parameters_and_only_existing_resets_before_notify_refresh(self):
        _, ui, deps, fields = build()
        values = fill(fields)
        reset = dict(amount=None, description='', note='', tags=[], reconciled=False, reconciliation_date='',
                     budget_excluded=False, bank_programmed=False, reminder_enabled=False, reminder_time='09:00')
        events = []
        deps['save_transaction'].side_effect = lambda **kwargs: events.append('save')
        def notify(*args, **kwargs):
            self.assertEqual({name: field.value for name, field in fields.items()}, values | reset)
            events.append('notify')
        ui.notify.side_effect = notify
        deps['refresh_all'].side_effect = lambda: events.append('refresh')
        ui.click('Enregistrer')
        deps['save_transaction'].assert_called_once_with(user_id=7, transaction_date='2026-10-12',
            transaction_type='income', amount=123.45, description='Salaire', category_id=3, tag_ids=[5],
            payment_method_id=4, note='Note test', status='planned', reconciliation_status='reconciled',
            reconciliation_date='2026-10-13', budget_excluded=True, bank_programmed=True,
            reminder_enabled=True, reminder_time='07:30')
        self.assertEqual(events, ['save', 'notify', 'refresh'])
        ui.notify.assert_called_once_with('Transaction enregistrée.', type='positive')
        deps['refresh_dashboard'].assert_not_called()

    def test_save_empty_optional_values_and_add_sentinel(self):
        for category in (None, ADD_CATEGORY):
            with self.subTest(category=category):
                _, ui, deps, fields = build()
                fill(fields)
                for name, value in dict(category=category, tags=None, reconciliation_date='',
                                        reminder_time='', reconciled=False).items():
                    fields[name].value = value
                ui.click('Enregistrer')
                kwargs = deps['save_transaction'].call_args.kwargs
                self.assertIsNone(kwargs['category_id'])
                self.assertEqual(kwargs['tag_ids'], [])
                self.assertEqual(kwargs['reconciliation_status'], 'unreconciled')
                self.assertIsNone(kwargs['reconciliation_date'])
                self.assertEqual(kwargs['reminder_time'], '09:00')

    def test_save_error_preserves_every_field_without_refresh(self):
        _, ui, deps, fields = build()
        before = fill(fields)
        deps['save_transaction'].side_effect = ValueError('refus')
        ui.click('Enregistrer')
        self.assertEqual({name: field.value for name, field in fields.items()}, before)
        ui.notify.assert_called_once_with('refus', type='warning')
        deps['refresh_all'].assert_not_called()
        deps['refresh_dashboard'].assert_not_called()

    def test_category_creation_and_reuse_keep_parent_type_selection_and_notification(self):
        for created, parent in [(True, 3), (False, None)]:
            with self.subTest(created=created):
                _, ui, deps, fields = build()
                deps['get_or_create_finance_category'].return_value = dict(id=9, created=created)
                change(fields['category'], ADD_CATEGORY)
                self.assertIsNone(fields['category'].value)
                ui.find('input', 'Nom de la catégorie')[3].value = 'Santé'
                ui.find('select', 'Sous-catégorie de (facultatif)')[3].value = parent
                ui.click('Ajouter')
                deps['get_or_create_finance_category'].assert_called_once_with(7, 'Santé', parent_id=parent, category_type='expense')
                self.assertEqual(fields['category'].value, 9)
                self.assertEqual(fields['category'].options, deps['_quick_category_options'].return_value)
                self.assertEqual(deps['_quick_category_options'].call_count, 2)
                ui.find('dialog')[3].close.assert_called_once_with()
                ui.notify.assert_called_once_with('Catégorie créée et sélectionnée.' if created else
                    'Cette catégorie existait déjà; elle a été sélectionnée.', type='positive' if created else 'info')
                deps['refresh_dashboard'].assert_called_once_with()
                deps['refresh_all'].assert_not_called()

    def test_parent_category_filter_expense_income_and_default(self):
        for kind, expected in [('expense', {3: 'Dépenses', 6: 'Mixte'}),
                               ('income', {4: 'Revenus', 6: 'Mixte'}),
                               (None, {3: 'Dépenses', 6: 'Mixte'})]:
            with self.subTest(kind=kind):
                _, ui, deps, fields = build()
                fields['kind'].value = kind
                change(fields['category'], ADD_CATEGORY)
                self.assertEqual(ui.find('select', 'Sous-catégorie de (facultatif)')[1][0],
                                 {None: 'Catégorie principale'} | expected)
                ui.find('input', 'Nom de la catégorie')[3].value = 'Nouvelle'
                ui.click('Ajouter')
                deps['get_or_create_finance_category'].assert_called_once_with(7, 'Nouvelle', parent_id=None, category_type=kind or 'expense')

    def test_tag_creation_and_reuse_preserve_previous_ids_without_add_sentinel(self):
        for created, identifier, expected in [(True, 6, [5, 6]), (False, 5, [5])]:
            with self.subTest(created=created):
                _, ui, deps, fields = build()
                deps['get_or_create_finance_tag'].return_value = dict(id=identifier, created=created)
                change(fields['tags'], ['5', None, ADD_TAG])
                self.assertEqual(fields['tags'].value, ['5', None])
                ui.find('input', 'Nom de l’étiquette')[3].value = 'Maison'
                ui.click('Ajouter')
                deps['get_or_create_finance_tag'].assert_called_once_with(7, 'Maison')
                self.assertEqual(fields['tags'].value, expected)
                self.assertEqual(fields['tags'].options, deps['_quick_tag_options'].return_value)
                self.assertEqual(deps['_quick_tag_options'].call_count, 2)
                ui.find('dialog')[3].close.assert_called_once_with()
                ui.notify.assert_called_once_with('Étiquette créée et sélectionnée.' if created else
                    'Cette étiquette existait déjà; elle a été sélectionnée.', type='positive' if created else 'info')
                deps['refresh_dashboard'].assert_called_once_with()
                deps['refresh_all'].assert_not_called()

    def test_quick_creation_errors_keep_dialog_open_and_cancel_does_not_write_again(self):
        for field, sentinel, service in [('category', ADD_CATEGORY, 'get_or_create_finance_category'),
                                         ('tags', [5, ADD_TAG], 'get_or_create_finance_tag')]:
            with self.subTest(field=field):
                _, ui, deps, fields = build()
                change(fields[field], sentinel)
                before = fields[field].value
                deps[service].side_effect = ValueError('refus')
                ui.click('Ajouter')
                self.assertEqual(fields[field].value, before)
                ui.find('dialog')[3].close.assert_not_called()
                deps['refresh_all'].assert_not_called()
                deps['refresh_dashboard'].assert_not_called()
                ui.notify.assert_called_once_with('refus', type='warning')
                ui.click('Annuler')
                ui.find('dialog')[3].close.assert_called_once_with()
                deps[service].assert_called_once()

    def test_ordinary_selections_do_not_open_quick_dialogs(self):
        _, ui, deps, fields = build()
        change(fields['category'], 3)
        change(fields['tags'], [5])
        self.assertFalse(any(kind == 'dialog' for kind, *_ in ui.widgets))
        deps['get_or_create_finance_category'].assert_not_called()
        deps['get_or_create_finance_tag'].assert_not_called()

    def test_card_payment_uses_existing_dialog_with_global_refresh(self):
        _, ui, deps, _ = build()
        ui.click('Paiement de carte')
        deps['_card_payment_dialog'].assert_called_once_with(7, deps['refresh_all'])
        deps['refresh_all'].assert_not_called()


class EntryArchitectureTests(unittest.TestCase):
    def test_independent_import_and_standard_imports_only(self):
        script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'finances', 'finances_data', 'db', 'nicegui', 'psycopg'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_entry
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tree = ast.parse((ROOT / 'finances_entry.py').read_text(encoding='utf-8'))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.ImportFrom, ast.Import))]
        self.assertTrue(all(isinstance(n, ast.ImportFrom) for n in imports))
        self.assertEqual({n.module for n in imports}, {'dataclasses', 'datetime', 'typing'})

    def test_parent_lazy_dependencies_and_no_internal_functions(self):
        tree = parent_tree()
        assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'entry_panel' for t in n.targets))
        self.assertEqual(assignment.value.func.id, 'build_entry_panel')
        env = {name: Mock() for name in ('ui', 'user_id', 'entry_tab', 'TRANSACTION_TYPES',
                                        'TRANSACTION_STATUSES', 'ADD_CATEGORY_OPTION', 'ADD_TAG_OPTION', 'build_entry_panel')}
        exec(compile(ast.Module(body=[assignment], type_ignores=[]), '<parent>', 'exec'), env)
        kwargs = env['build_entry_panel'].call_args.kwargs
        for _ in range(2):
            for name in ('save_transaction', '_card_payment_dialog', 'refresh_all'):
                env[name] = Mock()
                kwargs[name](7, sample=True)
                env[name].assert_called_once_with(7, sample=True)
            env['dashboard_panel'] = Mock()
            kwargs['refresh_dashboard']()
            env['dashboard_panel'].refresh.assert_called_once_with()
        internal = {'quick_parent_options', 'open_quick_category_dialog', 'category_quick_changed',
                    'open_quick_tag_dialog', 'tags_quick_changed', 'save_quick'}
        self.assertTrue(internal.isdisjoint({n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}))
        # Other global dialogs can legitimately use these names; inspect only the parent panel.
        parent = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'finances_panel')
        self.assertTrue({'category', 'tags', 'payment_method'}.isdisjoint(
            {n.id for n in ast.walk(parent) if isinstance(n, ast.Name)}))

    def test_parent_reload_precedes_history_filters_and_never_accesses_entry_widgets(self):
        refresh = next(n for n in ast.walk(parent_tree()) if isinstance(n, ast.FunctionDef) and n.name == 'refresh_all')
        names = {n.id for n in ast.walk(refresh) if isinstance(n, ast.Name)}
        self.assertTrue({'category', 'tags', 'payment_method'}.isdisjoint(names))
        self.assertEqual(ast.unparse(refresh.body[0]), 'entry_panel.reload_options()')
        env = {name: MagicMock() for name in names}
        events = []
        env['entry_panel'].reload_options.side_effect = lambda: events.append('entry')
        env['_category_options'].side_effect = lambda *args: events.append('history category') or {}
        env['_tag_options'].side_effect = lambda *args: events.append('history tags') or {}
        env['_payment_options'].side_effect = lambda *args, **kwargs: events.append('history payment') or {}
        exec(compile(ast.Module(body=[refresh], type_ignores=[]), '<refresh>', 'exec'), env)
        env['refresh_all']()
        self.assertEqual(events, ['entry', 'history category', 'history tags', 'history payment'])
        env['entry_panel'].reload_options.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()

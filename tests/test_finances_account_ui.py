"""Contrat du panneau Compte et raccordements réels, sans lancer NiceGUI."""
import ast
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock

from finances_account import AccountPanelHandle, build_account_panel

ROOT = Path(__file__).resolve().parents[1]


def ui_source():
    return ast.parse(''.join(p.read_text(encoding='utf-8')
                            for p in sorted(ROOT.glob('finances_part_*.pyfrag'))))


def account_source():
    return ast.parse((ROOT / 'finances_account.py').read_text(encoding='utf-8'))


def function_node(name):
    source = ui_source() if name == 'refresh_all' else account_source()
    return next(n for n in ast.walk(source)
                if isinstance(n, ast.FunctionDef) and n.name == name)


def load_function(name, namespace):
    # Exécuter le corps de production isolé de la construction de la page.
    node = function_node(name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / 'finances.py'), 'exec'), namespace)
    return namespace[name]


class AccountPanelContractTests(unittest.TestCase):
    def test_import_without_ui_or_database(self):
        script = """
import importlib.abc
import sys
class BlockImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'nicegui', 'finances', 'finances_data', 'db'}:
            raise AssertionError('Import interdit : ' + fullname)
sys.meta_path.insert(0, BlockImports())
from finances_account import AccountPanelHandle, build_account_panel
handle = AccountPanelHandle(lambda: None, lambda: None)
handle.reload_options()
handle.refresh()
"""
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_callbacks_are_lazy_and_replaceable(self):
        first = Mock()
        second = Mock()
        handle = AccountPanelHandle(first, first)
        first.assert_not_called()
        handle.refresh()
        first.assert_called_once_with()
        handle.on_refresh = second
        handle.on_reload_options = second
        handle.reload_options()
        handle.refresh()
        self.assertEqual(second.call_count, 2)
        self.assertEqual(first.call_count, 1)

    def test_parent_refresh_uses_only_handle_in_order(self):
        node = function_node('refresh_all')
        names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        self.assertTrue({'account_selector', 'render_account', '_bank_account_options'}.isdisjoint(names))
        # Les autres écrans sont simulés; le vrai refresh_all est exécuté.
        namespace = {name: MagicMock(name=name) for name in names}
        events = []
        namespace['account_panel'] = AccountPanelHandle(
            lambda: events.append('render'), lambda: events.append('options'))
        load_function('refresh_all', namespace)()
        self.assertEqual(events, ['options', 'render'])

    def test_panel_binding_resolves_functions_after_construction(self):
        assignment = next(n for n in ast.walk(account_source()) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'account_panel' for t in n.targets))
        namespace = {'AccountPanelHandle': AccountPanelHandle}
        # Les fonctions cibles sont volontairement absentes à la construction.
        exec(compile(ast.Module(body=[assignment], type_ignores=[]), '<binding>', 'exec'), namespace)
        for _ in range(2):
            render = Mock()
            reload = Mock()
            namespace.update(render_account=SimpleNamespace(refresh=render), reload_account_options=reload)
            namespace['account_panel'].reload_options()
            namespace['account_panel'].refresh()
            reload.assert_called_once_with()
            render.assert_called_once_with()

    def test_option_reload_preserves_selection_or_uses_first_available(self):
        selector = SimpleNamespace(value=2, options={}, update=Mock())
        reader = Mock()
        namespace = {'account_selector': selector, '_bank_account_options': reader, 'user_id': 7}
        reload = load_function('reload_account_options', namespace)
        for options, expected in (({1: 'Banque', 2: 'Marge'}, 2), ({3: 'Autre'}, 3), ({}, None)):
            with self.subTest(options=options):
                reader.return_value = options
                reload()
                self.assertEqual(selector.value, expected)
                self.assertEqual(selector.options, options)
        self.assertEqual(selector.update.call_count, 3)
        reader.assert_called_with(7)

    def test_editor_resolves_shared_callbacks_late(self):
        namespace = {'user_id': 7, 'ui': MagicMock(),
                     'list_recurrences': Mock(return_value=[{'id': 10}]),
                     'get_transaction': Mock(return_value={'id': 20}),
                     'get_card_payment_transfer': Mock(return_value={'id': 30})}
        editor = load_function('open_account_row_editor', namespace)
        # Définition et remplacement après création de la fonction d'édition.
        for _ in range(2):
            refresh = Mock()
            recurrence = Mock()
            transaction = Mock()
            card = Mock()
            namespace.update(refresh_all=refresh, recurrence_dialog=recurrence,
                             _transaction_dialog=transaction, _card_payment_dialog=card)
            editor({'projected': True, 'recurrence_id': 10})
            editor({'id': 20})
            editor({'id': 21, 'linked_transfer_id': 30})
            recurrence.assert_called_once_with({'id': 10})
            transaction.assert_called_once_with(7, refresh, transaction={'id': 20})
            card.assert_called_once_with(7, refresh, transfer={'id': 30})
        namespace['ui'].notify.assert_not_called()


    def test_panel_removed_from_fragments_and_internals_private(self):
        import finances_account as module
        internals = {'render_account', 'reload_account_options', 'open_account_row_editor',
                     'change_account_month', 'activate_finance_notifications',
                     'deactivate_finance_notifications', 'account_selector', 'account_box',
                     'account_month_state'}
        parent_names = {n.id for n in ast.walk(ui_source()) if isinstance(n, ast.Name)}
        parent_defs = {n.name for n in ast.walk(ui_source()) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue(internals.isdisjoint(parent_names | parent_defs))
        self.assertTrue(internals.isdisjoint(vars(module)))
        constructor = function_node('build_account_panel')
        defined = {n.name for n in ast.walk(constructor) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue({'render_account', 'open_account_row_editor',
                         'activate_finance_notifications', 'deactivate_finance_notifications'} <= defined)

    def test_parent_constructs_with_late_replaceable_callbacks(self):
        assignment = next(n for n in ast.walk(ui_source()) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'account_panel' for t in n.targets))
        self.assertIsInstance(assignment.value, ast.Call)
        self.assertEqual(assignment.value.func.id, 'build_account_panel')
        builder = Mock(return_value=AccountPanelHandle(Mock(), Mock()))
        namespace = dict(build_account_panel=builder, ui=Mock(), user_id=7,
                         account_tab=Mock(), tabs=Mock(), organization_tab=Mock())
        # Aucune fonction partagée n'existe encore à cet instant.
        exec(compile(ast.Module(body=[assignment], type_ignores=[]), '<parent>', 'exec'), namespace)
        self.assertIs(namespace['account_panel'], builder.return_value)
        callbacks = builder.call_args.kwargs
        for _ in range(2):
            for name in ('refresh_all', 'recurrence_dialog', '_transaction_dialog', '_card_payment_dialog'):
                target = Mock()
                namespace[name] = target
                callbacks[name](1, test=True)
                target.assert_called_once_with(1, test=True)

    def test_builder_returns_handle_and_renders_bank_and_credit_line(self):
        from datetime import date
        from decimal import Decimal
        from finances_ui_state import MonthCursor, month_label
        import inspect
        for kind in ('bank', 'credit_line', 'empty'):
            with self.subTest(kind=kind):
                ui = MagicMock()
                labels = []
                selectors = []
                def element(*args, **kwargs):
                    widget = MagicMock()
                    widget.__enter__.return_value = widget
                    for method in ('classes', 'props', 'tooltip', 'on', 'on_value_change'):
                        getattr(widget, method).return_value = widget
                    widget.value = kwargs.get('value')
                    return widget
                def label(text):
                    labels.append(text)
                    return element()
                def select(*args, **kwargs):
                    widget = element(*args, **kwargs)
                    selectors.append(widget)
                    return widget
                def refreshable(fn):
                    fn.refresh = Mock(side_effect=fn)
                    return fn
                for name in ('tab_panel', 'card', 'row', 'column', 'element', 'button', 'checkbox', 'dialog'):
                    getattr(ui, name).side_effect = element
                ui.label.side_effect = label
                ui.select.side_effect = select
                ui.refreshable.side_effect = refreshable
                deps = {name: Mock(name=name) for name in inspect.signature(build_account_panel).parameters}
                deps.update(ui=ui, user_id=7, MonthCursor=lambda: MonthCursor(date(2027, 1, 1)),
                            _month_label=month_label, _money=str, _balance_money=str)
                deps['list_bank_accounts'].return_value = [] if kind == 'empty' else [{'id': 1, 'name': 'Compte', 'method_type': kind}]
                deps['_bank_account_options'].return_value = {} if kind == 'empty' else {1: 'Compte'}
                month = dict(available=True, is_credit_line=kind == 'credit_line',
                             start_balance=Decimal('1000'), current_balance=Decimal('1000'),
                             minimum_balance=Decimal('1000'), maximum_balance=Decimal('1000'),
                             end_balance=Decimal('1000'), rows=[], credit_limit=Decimal('1500'),
                             end_available_credit=Decimal('500'))
                deps['bank_cashflow_month'].return_value = month
                deps['bank_cashflow_year_summary'].return_value = {'available': True, 'months': [
                    dict(month=date(2027, 1, 1), **{k: v for k, v in month.items() if k != 'rows'})]}
                deps['count_active_push_subscriptions'].return_value = 0
                handle = build_account_panel(**deps)
                self.assertIsInstance(handle, AccountPanelHandle)
                self.assertEqual(set(vars(handle)), {'on_refresh', 'on_reload_options'})
                self.assertEqual(len(selectors), 1)
                if kind == 'bank':
                    self.assertIn('Solde de départ', labels)
                    self.assertIn('Solde actuel', labels)
                    self.assertIn('Vue annuelle 2027', labels)
                elif kind == 'credit_line':
                    self.assertIn('Dette de départ', labels)
                    self.assertNotIn('Solde de départ', labels)
                    self.assertIn('Crédit disponible fin', labels)
                else:
                    deps['bank_cashflow_month'].assert_not_called()
                ui.notify.assert_not_called()
                handle.reload_options()
                handle.refresh()
                deps['_bank_account_options'].assert_called_once_with(7)
                selectors[0].update.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()

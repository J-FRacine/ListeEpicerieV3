"""Contrat du panneau Compte et raccordements réels, sans lancer NiceGUI."""
import ast
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock

from finances_account import AccountPanelHandle

ROOT = Path(__file__).resolve().parents[1]


def ui_source():
    return ast.parse(''.join(p.read_text(encoding='utf-8')
                            for p in sorted(ROOT.glob('finances_part_*.pyfrag'))))


def function_node(name):
    return next(n for n in ast.walk(ui_source())
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
from finances_account import AccountPanelHandle
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
        assignment = next(n for n in ast.walk(ui_source()) if isinstance(n, ast.Assign)
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


if __name__ == '__main__':
    unittest.main()

"""Structure finale de l'interface et identité des trois blocs CSS historiques."""
import ast
import hashlib
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock

from finances_styles import FINANCE_CSS, install_finance_styles

ROOT = Path(__file__).resolve().parents[1]
# Empreintes des trois chaînes transmises à ui.add_css au commit fa0c2c8.
CSS_SHA256 = (
    'c4c996f69fc06dc0637e39141a2ca20e7bd4fc58a0d5a40b69768df989b790e5',
    'b35ec71e95e1807a3842a7b833623b9f8d103bcb49a67b1ad902bc76b4a7212c',
    'e52637a7a105f7c10c5aa2afc34a11209482a103491765f255de29f2ebca0263',
)


def tree():
    return ast.parse((ROOT / 'finances.py').read_text(encoding='utf-8'))


class FinanceStructureTests(unittest.TestCase):
    def test_normal_module_without_ui_fragments_or_dynamic_loader(self):
        self.assertEqual(list(ROOT.glob('finances_part_*.pyfrag')), [])
        source = (ROOT / 'finances.py').read_text(encoding='utf-8')
        parsed = tree()
        self.assertNotIn('finances_part_', source)
        calls = [n for n in ast.walk(parsed) if isinstance(n, ast.Call)]
        self.assertFalse(any(isinstance(n.func, ast.Name) and n.func.id in {'exec', 'compile'} for n in calls))
        self.assertFalse(any(isinstance(n.func, ast.Attribute) and n.func.attr in {'glob', 'rglob'} for n in calls))
        functions = {n.name for n in parsed.body if isinstance(n, ast.FunctionDef)}
        self.assertTrue({'finances_panel', '_money', '_signed', '_payment_effect', '_balance_money',
                         '_category_options', '_tag_options', '_quick_category_options', '_quick_tag_options',
                         '_bank_account_options', '_payment_options', '_recurrence_options'} <= functions)
        assignments = {t.id for n in parsed.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
        self.assertTrue({'ADD_CATEGORY_OPTION', 'ADD_TAG_OPTION', 'CREATE_RECURRENCE_OPTION',
                         'BUDGET_SORT_FIELDS', 'BUDGET_SORT_DIRECTIONS'} <= assignments)

    def test_css_contents_order_and_shared_flag_match_reference(self):
        ui = Mock()
        install_finance_styles(ui)
        calls = ui.add_css.call_args_list
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0].args, (FINANCE_CSS,))
        self.assertEqual(tuple(hashlib.sha256(call.args[0].encode('utf-8')).hexdigest() for call in calls), CSS_SHA256)
        for call in calls:
            self.assertEqual(len(call.args), 1)
            self.assertEqual(call.kwargs, {'shared': True})

    def test_styles_independent_import_does_not_load_application_dependencies(self):
        script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'nicegui', 'finances', 'finances_data', 'db', 'psycopg'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_styles
assert callable(finances_styles.install_finance_styles)
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_finances_installs_styles_at_module_load_and_reexports_constant(self):
        parsed = tree()
        imported = next(n for n in parsed.body if isinstance(n, ast.ImportFrom) and n.module == 'finances_styles')
        self.assertEqual({n.name for n in imported.names}, {'FINANCE_CSS', 'install_finance_styles'})
        installs = [n for n in ast.walk(parsed) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name) and n.func.id == 'install_finance_styles']
        self.assertEqual(len(installs), 1)
        self.assertEqual(ast.unparse(installs[0]), 'install_finance_styles(ui)')
        self.assertTrue(any(isinstance(n, ast.Expr) and n.value is installs[0] for n in parsed.body))
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                             and n.func.attr == 'add_css' for n in ast.walk(parsed)))

    def test_panel_construction_and_global_refresh_order(self):
        panel = next(n for n in tree().body if isinstance(n, ast.FunctionDef) and n.name == 'finances_panel')
        panels = next(n for n in panel.body if isinstance(n, ast.With)
                      and any('ui.tab_panels(' in ast.unparse(item.context_expr) for item in n.items))
        order = []
        for node in panels.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                order.append(node.value.func.id)
            elif isinstance(node, ast.With):
                expression = ast.unparse(node.items[0].context_expr)
                if 'shared_loans_tab' in expression:
                    order.append('shared_loans')
                elif 'history_tab' in expression:
                    order.append('history')
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                order.append(node.value.func.id)
        self.assertEqual(order, ['build_dashboard_panel', 'build_account_panel', 'build_budget_panel',
            'build_financing_panel', 'shared_loans', 'build_entry_panel', 'history', 'build_recurrences_panel',
            'build_goals_panel', 'build_reconciliation_panel', 'build_organization_panel', 'build_import_export_panel'])
        refresh = panel.body[-1]
        self.assertIsInstance(refresh, ast.FunctionDef)
        self.assertEqual(refresh.name, 'refresh_all')
        self.assertEqual([ast.unparse(n.value.func) for n in refresh.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)],
            ['entry_panel.reload_options', 'history_category.update', 'history_tag.update', 'history_payment.update',
             'dashboard_panel.refresh', 'render_history.refresh', 'recurrences_panel.refresh', 'goals_panel.refresh',
             'organization_panel.refresh', 'account_panel.reload_options', 'account_panel.refresh', 'budget_panel.refresh',
             'financing_panel.refresh', 'reconciliation_panel.reload_options', 'reconciliation_panel.refresh'])


if __name__ == '__main__':
    unittest.main()

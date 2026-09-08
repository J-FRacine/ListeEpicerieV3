"""Contrats des dix façades de lecture Conciliation, sans base ni UI."""
import ast
from contextlib import ExitStack
import inspect
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_finances_budget_writes import data
from test_finances_financing import ROOT


SIGNATURES = {
    'payment_predicted_balance_summary': '(user_id)',
    'count_unassigned_confirmed_transactions': '(user_id)',
    'list_unreconciled_transactions': '(user_id, payment_method_id, start_date=None, end_date=None, query=None)',
    'list_unassigned_transactions': '(user_id, query=None, limit=500)',
    'list_reconciliation_sessions': '(user_id, payment_method_id=None, include_cancelled=True, limit=100)',
    'get_reconciliation_session': '(user_id, session_id)',
    'list_reconciliation_session_links': '(user_id)',
    'reconciliation_reference_summary': '(user_id, payment_method_id)',
    'list_reconciliation_drafts': '(user_id)',
    'get_reconciliation_draft': '(user_id, payment_method_id)',
}
DEPENDENCIES = {
    'payment_predicted_balance_summary': ['get_connection'],
    'count_unassigned_confirmed_transactions': ['get_connection'],
    'list_unreconciled_transactions': ['list_transactions'],
    'list_unassigned_transactions': ['list_transactions'],
    'list_reconciliation_sessions': ['get_connection'],
    'get_reconciliation_session': ['get_connection'],
    'list_reconciliation_session_links': ['get_connection'],
    'reconciliation_reference_summary': ['_validate_payment_method', 'get_connection'],
    'list_reconciliation_drafts': ['get_connection'],
    'get_reconciliation_draft': ['get_connection'],
}


class ReconciliationReadArchitectureTests(unittest.TestCase):
    def test_independent_import_without_database_ui_or_circular_dependency(self):
        script = '''
import builtins
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'db', 'finances_data', 'finances', 'nicegui', 'psycopg'}:
        raise AssertionError('import interdit: ' + name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_reconciliation_data
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tree = ast.parse((ROOT / 'finances_reconciliation_data.py').read_text(encoding='utf-8'))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertEqual(len(imports), 1)
        self.assertIsInstance(imports[0], ast.ImportFrom)
        self.assertEqual(imports[0].module, 'decimal')
        self.assertEqual([alias.name for alias in imports[0].names], ['Decimal'])

    def test_ten_historical_signatures_are_unchanged(self):
        for name, expected in SIGNATURES.items():
            with self.subTest(name=name):
                self.assertEqual(str(inspect.signature(getattr(data, name))), expected)

    def test_ten_facades_delegate_arguments_defaults_and_return_value(self):
        for name in SIGNATURES:
            facade = getattr(data, name)
            signature = inspect.signature(facade)
            for defaults in (False, True):
                with self.subTest(name=name, defaults=defaults):
                    kwargs = {p.name: object() for p in signature.parameters.values()
                              if not defaults or p.default == p.empty}
                    bound = signature.bind(**kwargs)
                    bound.apply_defaults()
                    with patch.object(data._reconciliation_data, name, return_value=object()) as target:
                        self.assertIs(facade(**kwargs), target.return_value)
                        target.assert_called_once_with(
                            *bound.args, **{dep: getattr(data, dep) for dep in DEPENDENCIES[name]})

    def test_all_dependencies_are_resolved_again_after_each_monkeypatch(self):
        for name, deps in DEPENDENCIES.items():
            facade = getattr(data, name)
            signature = inspect.signature(facade)
            args = [object() for p in signature.parameters.values() if p.default == p.empty]
            # Successive replacements catch any connection, reader or validator
            # cached at import. Existing business tests execute the actual bodies.
            for generation in range(2):
                with self.subTest(name=name, generation=generation), ExitStack() as stack:
                    replacements = {dep: object() for dep in deps}
                    for dep, value in replacements.items():
                        stack.enter_context(patch.object(data, dep, value))
                    target = stack.enter_context(patch.object(data._reconciliation_data, name))
                    facade(*args)
                    for dep, value in replacements.items():
                        self.assertIs(target.call_args.kwargs[dep], value)


if __name__ == '__main__':
    unittest.main()

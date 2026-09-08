"""Trois contrats d'architecture des écritures Conciliation extraites."""
import ast
from contextlib import ExitStack
import inspect
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_finances_budget_writes import data
from test_finances_financing import ROOT


CONTRACTS = {
    'bulk_assign_payment_method': ('(user_id, transaction_ids, payment_method_id)',
                                 ['_validate_payment_method', 'get_connection']),
    'create_reconciliation_session': (
        "(user_id, payment_method_id, transaction_ids, statement_date, statement_balance=None, due_date=None, reconciliation_date=None, note=None, include_opening_balance=False, difference_resolution='balanced', difference_explanation=None)",
        ['_decimal_value', '_text', '_validate_payment_method', 'get_connection']),
    'remove_transaction_from_reconciliation_session': (
        '(user_id, session_id, transaction_id)', ['_refresh_reconciliation_session_totals', 'get_connection']),
    'cancel_reconciliation_session': ('(user_id, session_id)', ['get_connection']),
    'save_reconciliation_draft': (
        "(user_id, payment_method_id, transaction_ids, *, statement_date=None, statement_balance=None, due_date=None, reconciliation_date=None, note=None, include_opening_balance=False, difference_explanation=None, filter_start=None, filter_end=None, filter_query=None, sort_direction='asc')",
        ['_decimal_value', '_optional_date_value', '_text', '_validate_payment_method', 'get_connection']),
    'delete_reconciliation_draft': ('(user_id, payment_method_id)', ['get_connection']),
}


class ReconciliationWritesArchitectureTests(unittest.TestCase):
    def test_independent_import_and_only_date_decimal_imports(self):
        script = '''
import builtins
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'db', 'finances_data', 'finances', 'nicegui', 'psycopg'}:
        raise AssertionError('import interdit: ' + name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_reconciliation_writes
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tree = ast.parse((ROOT / 'finances_reconciliation_writes.py').read_text(encoding='utf-8'))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertTrue(all(isinstance(n, ast.ImportFrom) for n in imports))
        self.assertEqual([(n.module, [a.name for a in n.names]) for n in imports],
                         [('datetime', ['date']), ('decimal', ['Decimal'])])

    def test_six_historical_signatures_and_delegation_with_defaults(self):
        for name, (expected, deps) in CONTRACTS.items():
            facade = getattr(data, name)
            signature = inspect.signature(facade)
            self.assertEqual(str(signature), expected)
            for defaults in (False, True):
                with self.subTest(name=name, defaults=defaults):
                    kwargs = {p.name: object() for p in signature.parameters.values()
                              if not defaults or p.default == p.empty}
                    bound = signature.bind(**kwargs)
                    bound.apply_defaults()
                    with patch.object(data._reconciliation_writes, name, return_value=object()) as target:
                        self.assertIs(facade(**kwargs), target.return_value)
                        target.assert_called_once_with(*bound.args, **bound.kwargs,
                                                       **{dep: getattr(data, dep) for dep in deps})

    def test_dependencies_are_resolved_after_each_monkeypatch(self):
        for name, (_, deps) in CONTRACTS.items():
            facade = getattr(data, name)
            signature = inspect.signature(facade)
            kwargs = {p.name: object() for p in signature.parameters.values() if p.default == p.empty}
            for generation in range(2):
                with self.subTest(name=name, generation=generation), ExitStack() as stack:
                    replacements = {dep: object() for dep in deps}
                    for dep, value in replacements.items():
                        stack.enter_context(patch.object(data, dep, value))
                    target = stack.enter_context(patch.object(data._reconciliation_writes, name))
                    facade(**kwargs)
                    for dep, value in replacements.items():
                        self.assertIs(target.call_args.kwargs[dep], value)


if __name__ == '__main__':
    unittest.main()

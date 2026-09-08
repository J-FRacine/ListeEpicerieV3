"""Contrats des écritures extraites, sans PostgreSQL ni interface réels."""
import ast
from contextlib import ExitStack
import inspect
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_finances_financing import ROOT, connection, data
import test_finances_financing as characterization

writes = data._financing_writes


SIGNATURES = {
    '_plan_transaction_note': '(plan, installment_number)',
    '_rebuild_installment_transactions': '(cur, user_id, plan_id)',
    '_save_installment_plan_v111': "(user_id, *, plan_type, provider_name, description, original_amount, total_installments, next_due_date, payment_method_id, category_id=None, tag_ids=None, purchase_date=None, completed_installments=0, remaining_balance=None, installment_amount=None, annual_interest_rate=0, fees_total=0, frequency_unit='month', frequency_interval=1, budget_excluded=False, note=None, plan_id=None)",
    'save_installment_plan': "(user_id, *, plan_type, provider_name, description, original_amount, total_installments, next_due_date, payment_method_id, plan_id=None, purchase_date=None, completed_installments=0, remaining_balance=None, installment_amount=None, annual_interest_rate=0, fees_total=0, frequency_unit='month', frequency_interval=1, category_id=None, tag_ids=None, budget_excluded=False, note=None, payment_includes_interest=True)",
    'toggle_installment_plan': '(user_id, plan_id, is_active)',
    'delete_installment_plan': '(user_id, plan_id)',
}
DEPENDENCIES = {
    '_plan_transaction_note': [],
    '_rebuild_installment_transactions': ['_next_date', '_plan_transaction_note'],
    '_save_installment_plan_v111': [
        'FREQUENCY_UNITS', 'INSTALLMENT_PLAN_TYPES', '_automatic_installment_amount',
        '_decimal_value', '_money', '_optional_date_value',
        '_rebuild_installment_transactions', '_text', '_validate_links',
        '_validate_payment_method', 'analyze_installment_progress', 'get_connection',
    ],
    'save_installment_plan': [
        '_automatic_installment_amount', '_decimal_value', '_money',
        '_save_installment_plan_v111', 'analyze_installment_progress', 'get_connection',
    ],
    'toggle_installment_plan': ['_rebuild_installment_transactions', 'get_connection'],
    'delete_installment_plan': ['get_connection'],
}


class FinancingWritesArchitectureTests(unittest.TestCase):
    def test_independent_import_and_no_circular_dependency(self):
        script = '''
import builtins
real_import = builtins.__import__
blocked = {'db', 'finances_data', 'finances', 'nicegui', 'psycopg'}
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in blocked:
        raise AssertionError('import interdit: ' + name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_financing_writes
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        tree = ast.parse((ROOT / 'finances_financing_writes.py').read_text(encoding='utf-8'))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertEqual(len(imports), 1)
        self.assertIsInstance(imports[0], ast.ImportFrom)
        self.assertEqual(imports[0].module, 'decimal')

    def test_historical_signatures_and_six_facades(self):
        for name, expected in SIGNATURES.items():
            with self.subTest(name=name):
                facade = getattr(data, name)
                signature = inspect.signature(facade)
                self.assertEqual(str(signature), expected)
                positional = [object() for p in signature.parameters.values()
                              if p.kind == p.POSITIONAL_OR_KEYWORD]
                keywords = {p.name: object() for p in signature.parameters.values()
                            if p.kind == p.KEYWORD_ONLY}
                with patch.object(writes, name, return_value=object()) as target:
                    self.assertIs(facade(*positional, **keywords), target.return_value)
                    target.assert_called_once_with(
                        *positional, **keywords,
                        **{dep: getattr(data, dep) for dep in DEPENDENCIES[name]})
                required = {p.name: object() for p in signature.parameters.values()
                            if p.kind == p.KEYWORD_ONLY and p.default == p.empty}
                bound = signature.bind(*positional, **required)
                bound.apply_defaults()
                with patch.object(writes, name) as target:
                    facade(*positional, **required)
                    for key, value in bound.kwargs.items():
                        self.assertEqual(target.call_args.kwargs[key], value)

    def test_all_dependencies_resolved_after_import_on_each_call(self):
        # Two successive replacements detect cached connections, constants and
        # nested facades as well as cached validators/calculations.
        for name, deps in DEPENDENCIES.items():
            facade = getattr(data, name)
            signature = inspect.signature(facade)
            args = [object() for p in signature.parameters.values()
                    if p.kind == p.POSITIONAL_OR_KEYWORD]
            kwargs = {p.name: object() for p in signature.parameters.values()
                      if p.kind == p.KEYWORD_ONLY and p.default == p.empty}
            for generation in range(2):
                with self.subTest(name=name, generation=generation), ExitStack() as stack:
                    replacements = {dep: object() for dep in deps}
                    for dep, replacement in replacements.items():
                        stack.enter_context(patch.object(data, dep, replacement))
                    target = stack.enter_context(patch.object(writes, name))
                    facade(*args, **kwargs)
                    for dep, replacement in replacements.items():
                        self.assertIs(target.call_args.kwargs[dep], replacement)

    def test_real_save_keeps_two_connections_and_commits_in_order(self):
        first, cur = connection()
        second, metadata_cur = connection()
        cur.fetchone.side_effect = [dict(method_type='bank'), dict(id=42)]
        events = []
        connections = iter([first.return_value, second.return_value])
        def connect():
            events.append('connect')
            return next(connections)
        first.return_value.__enter__.return_value.commit.side_effect = lambda: events.append('first commit')
        second.return_value.__enter__.return_value.commit.side_effect = lambda: events.append('second commit')
        def rebuild(cursor, user_id, plan_id):
            self.assertIs(cursor, cur)
            self.assertEqual((user_id, plan_id), (7, 42))
            events.append('rebuild')
        with patch.object(data, 'get_connection', side_effect=connect), \
             patch.object(data, '_validate_links', return_value=[5]), \
             patch.object(data, '_validate_payment_method', return_value=4), \
             patch.object(data, '_rebuild_installment_transactions', side_effect=rebuild):
            self.assertEqual(data.save_installment_plan(**characterization.FinancingSaveTests().base()), 42)
        self.assertEqual(events, ['connect', 'rebuild', 'first commit', 'connect', 'second commit'])
        self.assertIn('payment_includes_interest=%s', metadata_cur.execute.call_args.args[0])


if __name__ == '__main__':
    unittest.main()

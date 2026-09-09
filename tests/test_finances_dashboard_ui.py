"""Caractérisation du Tableau extrait, avec widgets et services simulés."""
import ast
import asyncio
import inspect
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock
from datetime import date
from decimal import Decimal as D

from finances_dashboard import DashboardPanelHandle, build_dashboard_panel
from finances_ui_state import MonthCursor
from test_finances_financing_ui import SimulatedUi

ROOT = Path(__file__).resolve().parents[1]
DAY = date(2026, 10, 1)


def parent_tree():
    return ast.parse(''.join(p.read_text(encoding='utf-8')
                            for p in sorted(ROOT.glob('finances_part_*.pyfrag'))))


def transaction(identifier=1, **values):
    return dict(id=identifier, transaction_type='expense', amount=D('12'),
                description=f'Transaction {identifier}', transaction_date=DAY,
                category_id=3, tag_ids=[5], tag_names=['Maison'],
                projection_bucket='realized', status='confirmed') | values


def build(**overrides):
    ui = SimulatedUi()
    capacity = dict(available_month=D('100'), remaining_per_pay=D('50'), pay_count=2)
    projection = dict(realized={'expenses': D('12')}, upcoming={'expenses': D('8'), 'count': 0},
                      total={'expenses': D('20')}, remaining_available=D('80'), capacity=capacity,
                      kpis={'expense': {'categories': [], 'tags': []}}, transactions=[], upcoming_transactions=[])
    deps = {name: Mock(name=name) for name in inspect.signature(build_dashboard_panel).parameters}
    deps.update(ui=ui, user_id=7, dashboard_tab=object(), account_tab=object(), reconciliation_tab=object(),
                month_state=MonthCursor(DAY), _money=str, _balance_money=str, _month_label=str,
                PAYMENT_METHOD_TYPES={'bank': 'Banque'})
    for name in ('goal_progress', 'payment_predicted_balance_summary', 'list_bank_accounts'):
        deps[name].return_value = []
    deps['count_unassigned_confirmed_transactions'].return_value = 0
    deps['dashboard_month_projection'].return_value = overrides.pop('projection', projection)
    deps['budget_capacity_summary'].return_value = capacity
    for name, value in overrides.items():
        deps[name].return_value = value
    handle = build_dashboard_panel(**deps)
    return handle, ui, deps


def labels(ui):
    return [args[0] for kind, args, _, _ in ui.widgets if kind == 'label' and args]


class DashboardPanelTests(unittest.TestCase):
    def test_handle_is_lazy_and_uses_current_callback(self):
        first, second = Mock(), Mock()
        handle = DashboardPanelHandle(first)
        first.assert_not_called()
        handle.refresh()
        first.assert_called_once_with()
        handle.on_refresh = second
        handle.refresh()
        second.assert_called_once_with()

    def test_build_and_refresh_use_current_shared_month(self):
        handle, ui, deps = build()
        self.assertIsInstance(handle, DashboardPanelHandle)
        deps['dashboard_month_projection'].assert_called_once_with(7, DAY)
        deps['budget_capacity_summary'].assert_not_called()
        self.assertIn('Dépenses variables du mois', labels(ui))
        deps['month_state'].shift(1)
        handle.refresh()
        deps['dashboard_month_projection'].assert_called_with(7, date(2026, 11, 1))
        deps['goal_progress'].assert_called_with(7, date(2026, 11, 1))
        deps['refresh_all'].assert_not_called()

    def test_previous_and_next_buttons_refresh_only_dashboard(self):
        _, ui, deps = build()
        asyncio.run(ui.find('button', icon='chevron_left')[2]['on_click']())
        self.assertEqual(deps['month_state'].value, date(2026, 9, 1))
        asyncio.run(ui.find('button', icon='chevron_right')[2]['on_click']())
        self.assertEqual(deps['month_state'].value, DAY)
        self.assertEqual(deps['dashboard_month_projection'].call_count, 3)
        deps['refresh_all'].assert_not_called()

    def test_without_bank_account_does_not_query_cashflow(self):
        _, ui, deps = build()
        deps['bank_cashflow_month'].assert_not_called()
        self.assertFalse(any(kind == 'button' and args == ('Voir le compte',)
                             for kind, args, _, _ in ui.widgets))

    def test_bank_and_credit_line_keep_distinct_summaries_and_account_link(self):
        for credit in (False, True):
            with self.subTest(credit=credit):
                cash = dict(available=True, is_credit_line=credit, account={'name': 'Principal'},
                            start_balance=D('10'), current_balance=D('20'), minimum_balance=D('5'),
                            maximum_balance=D('30'), end_balance=D('15'), end_available_credit=D('85'))
                _, ui, deps = build(list_bank_accounts=[{'id': 4, 'method_type': 'credit_line' if credit else 'bank'}],
                                    bank_cashflow_month=cash)
                deps['bank_cashflow_month'].assert_called_once_with(7, 4, DAY)
                self.assertIn('Dette actuelle' if credit else 'Solde actuel', labels(ui))
                self.assertIn('Crédit disponible fin' if credit else 'Plus bas prévu', labels(ui))
                ui.click('Voir le compte')
                deps['tabs'].set_value.assert_called_once_with(deps['account_tab'])

    def test_bank_is_preferred_over_credit_line_and_unavailable_projection_is_explained(self):
        _, ui, deps = build(list_bank_accounts=[{'id': 8, 'method_type': 'credit_line'}, {'id': 4, 'method_type': 'bank'}],
                            bank_cashflow_month={'available': False})
        deps['bank_cashflow_month'].assert_called_once_with(7, 4, DAY)
        self.assertTrue(any('solde de référence' in str(text) for text in labels(ui)))

    def test_cashflow_error_keeps_dashboard_available(self):
        handle, ui, deps = build(list_bank_accounts=[{'id': 4, 'method_type': 'bank'}], bank_cashflow_month=None)
        deps['bank_cashflow_month'].side_effect = ValueError('indisponible')
        handle.refresh()
        self.assertIn('Dépenses variables du mois', labels(ui))

    def test_carryover_uses_shared_month_and_refreshes_only_after_success(self):
        _, ui, deps = build()
        callback = ui.find('checkbox')[3].on_value_change.call_args.args[0]
        deps['month_state'].shift(1)
        callback(SimpleNamespace(value=True))
        deps['set_month_carryover'].assert_called_once_with(7, True, date(2026, 11, 1))
        deps['refresh_all'].assert_called_once_with()
        deps['set_month_carryover'].side_effect = ValueError('refus')
        callback(SimpleNamespace(value=False))
        deps['refresh_all'].assert_called_once_with()
        ui.notify.assert_called_once_with('refus', type='warning')

    def test_carry_values_and_capacity_fallback_are_preserved(self):
        handle, ui, deps = build()
        projection = deps['dashboard_month_projection'].return_value
        projection['capacity'] = None
        deps['budget_capacity_summary'].return_value.update(carry_enabled=True, carry_in=D('-9'),
                                                           available_month_base=D('109'), carry_start_month=DAY)
        handle.refresh()
        deps['budget_capacity_summary'].assert_called_once_with(7, DAY)
        for text in ('Report du mois précédent', '-9', 'Disponible ajusté ce mois'):
            self.assertIn(text, labels(ui))

    def test_upcoming_expenses_keep_metadata_and_income_is_not_displayed(self):
        handle, ui, deps = build()
        deps['dashboard_month_projection'].return_value['upcoming_transactions'] = [
            transaction(1, status='planned', bank_programmed=True, installment_number=2, budget_excluded=True),
            transaction(2, projected=True), transaction(3, transaction_type='income')]
        handle.refresh()
        expansion = ui.find('expansion', 'Voir les dépenses à venir — 2 dépense(s)')
        self.assertIs(expansion[2]['value'], False)
        self.assertIn('Transaction 1', labels(ui))
        self.assertIn('Transaction 2', labels(ui))
        self.assertNotIn('Transaction 3', labels(ui))
        self.assertIn('À confirmer — Hors budget — Programmé — Versement 2', labels(ui))
        self.assertIn('Récurrence projetée', labels(ui))

    def test_goals_keep_values_and_carry(self):
        _, ui, _ = build(goal_progress=[dict(percentage=120, target_name='Épargne', spent=D('12'),
                                           available=D('10'), remaining=D('-2'), carry_in=D('3'))])
        for text in ('Objectifs du mois', 'Épargne', '12 / 10', 'Reste : -2', 'Report : 3'):
            self.assertIn(text, labels(ui))

    def test_kpi_detail_filters_and_edit_existing_transaction(self):
        for dimension, key, name, identifier in [('category', 'categories', 'Achats', 3), ('tag', 'tags', 'Maison', 5)]:
            with self.subTest(dimension=dimension):
                handle, ui, deps = build()
                projection = deps['dashboard_month_projection'].return_value
                projection['kpis']['expense'][key] = [dict(id=identifier, name=name, realized=D('12'), upcoming=D('24'), total=D('36'))]
                projection['transactions'] = [transaction(), transaction(2, fixed_budget=True),
                    transaction(3, budget_excluded=True), transaction(4, transaction_type='income'),
                    transaction(5, category_id=99, tag_ids=[99]),
                    transaction(6, projected=True, projection_bucket='upcoming'),
                    transaction(7, status='planned', projection_bucket='upcoming')]
                handle.refresh()
                ui.click(name)
                text = labels(ui)
                for identifier in (1, 6, 7):
                    self.assertIn(f'Transaction {identifier}', text)
                for identifier in (2, 3, 4, 5):
                    self.assertNotIn(f'Transaction {identifier}', text)
                edits = [w for w in ui.widgets if w[0] == 'button' and w[2].get('icon') == 'edit']
                self.assertEqual(len(edits), 2)
                selected = transaction(7)
                deps['get_transaction'].return_value = selected
                edits[-1][2]['on_click']()
                deps['get_transaction'].assert_called_once_with(7, 7)
                deps['_transaction_dialog'].assert_called_once_with(7, deps['refresh_all'], selected)
                ui.find('dialog')[3].close.assert_called_once_with()

    def test_missing_kpi_transaction_does_not_open_editor(self):
        handle, ui, deps = build()
        projection = deps['dashboard_month_projection'].return_value
        projection['kpis']['expense']['categories'] = [dict(id=3, name='Achats', realized=D('12'), upcoming=D('0'), total=D('12'))]
        projection['transactions'] = [transaction()]
        handle.refresh()
        ui.click('Achats')
        deps['get_transaction'].return_value = None
        ui.click(icon='edit')
        deps['_transaction_dialog'].assert_not_called()
        ui.find('dialog')[3].close.assert_not_called()
        ui.notify.assert_called_once_with('Transaction introuvable.', type='warning')

    def test_unassigned_link_opens_reconciliation(self):
        _, ui, deps = build(count_unassigned_confirmed_transactions=2)
        ui.click('Classer')
        deps['tabs'].set_value.assert_called_once_with(deps['reconciliation_tab'])


class DashboardArchitectureTests(unittest.TestCase):
    def test_independent_import_and_only_standard_dependencies(self):
        script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'nicegui', 'finances', 'finances_data', 'db', 'psycopg'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_dashboard
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tree = ast.parse((ROOT / 'finances_dashboard.py').read_text(encoding='utf-8'))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertTrue(all(isinstance(n, ast.ImportFrom) for n in imports))
        self.assertEqual({n.module for n in imports}, {'dataclasses', 'decimal', 'typing'})

    def test_parent_passes_same_cursor_and_lazy_services_and_only_retains_handle(self):
        tree = parent_tree()
        calls = {n.func.id: n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id in {'build_dashboard_panel', 'build_budget_panel'}}
        dashboard = calls['build_dashboard_panel']
        for call in calls.values():
            self.assertEqual(ast.unparse(next(k.value for k in call.keywords if k.arg == 'month_state')), 'month_state')
        env = {k.arg: Mock(name=k.arg) for k in dashboard.keywords}
        env['build_dashboard_panel'] = Mock(return_value=DashboardPanelHandle(Mock()))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.Expr(value=dashboard)], type_ignores=[])), '<parent wiring>', 'exec'), env)
        kwargs = env['build_dashboard_panel'].call_args.kwargs
        self.assertIs(kwargs['month_state'], env['month_state'])
        replacement = Mock()
        env['dashboard_month_projection'] = replacement
        kwargs['dashboard_month_projection'](7, DAY)
        replacement.assert_called_once_with(7, DAY)
        names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue({'render_dashboard', 'change_month', 'open_kpi_detail', 'render_kpi_table'}.isdisjoint(names))
        self.assertNotIn('dashboard_box', {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})
        self.assertNotIn('render_dashboard', {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})

    def test_parent_global_refresh_and_organization_use_handle(self):
        tree = parent_tree()
        refresh = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'refresh_all')
        env = {n.id: MagicMock() for n in ast.walk(refresh) if isinstance(n, ast.Name)}
        exec(compile(ast.Module(body=[refresh], type_ignores=[]), '<refresh>', 'exec'), env)
        env['refresh_all']()
        env['dashboard_panel'].refresh.assert_called_once_with()
        organization = next(n for n in ast.walk(tree) if isinstance(n, ast.Call)
                            and isinstance(n.func, ast.Name) and n.func.id == 'build_organization_panel')
        self.assertEqual(ast.unparse(next(k.value for k in organization.keywords if k.arg == 'render_dashboard')), 'dashboard_panel')


if __name__ == '__main__':
    unittest.main()

"""Caractérisation de l'UI Conciliation existante, isolée par AST sans NiceGUI."""
import ast
from copy import deepcopy
from datetime import date
from decimal import Decimal as D
from functools import lru_cache
import unittest
import inspect
import subprocess
import sys
from unittest.mock import MagicMock, Mock

from test_finances_financing_ui import ROOT, SimulatedUi
from finances_reconciliation import ReconciliationPanelHandle, build_reconciliation_panel

DAY = date(2026, 9, 8)
RENDERS = ['render_reconciliation_draft', 'render_reconciliation_balance',
           'render_reconciliation_transactions', 'render_reconciliation_selection', 'render_sessions', 'render_unassigned']


@lru_cache(maxsize=1)
def source():
    return (ROOT / 'finances_reconciliation.py').read_text(encoding='utf-8')


def parent_source():
    return ''.join(p.read_text(encoding='utf-8') for p in sorted(ROOT.glob('finances_part_*.pyfrag')))


@lru_cache(maxsize=1)
def tree():
    return ast.parse(source())


def node(name):
    return next(n for n in ast.walk(tree()) if isinstance(n, ast.FunctionDef) and n.name == name)


def load(name, namespace):
    # Compile the actual function, including its nested callbacks and decorator.
    exec(compile(ast.Module(body=[deepcopy(node(name))], type_ignores=[]), '<conciliation UI>', 'exec'), namespace)
    return namespace[name]


def row(transaction_id=2, **values):
    return dict(id=transaction_id, transaction_date=DAY, transaction_type='expense', amount=D('80'),
                description=f'Achat {transaction_id}', category_full_name='Achats', tag_names=[]) | values


def environment():
    ui = SimulatedUi()
    values = dict(reconciliation_payment=4, reconciliation_start='2026-09-01', reconciliation_end='2026-09-30',
                  reconciliation_query='achat', reconciliation_sort='asc', statement_date=DAY.isoformat(),
                  statement_balance=D('150'), due_date='2026-09-20', reconciliation_date_input='2026-09-09',
                  reconciliation_note='note', difference_explanation='', include_opening_balance=True,
                  unassigned_search='achat', unassigned_target=4)
    env = {name: MagicMock(value=value) for name, value in values.items()}
    env.update({name: Mock() for name in RENDERS})
    for name in ('reconciliation_transactions_box', 'reconciliation_selection_box', 'reconciliation_balance_box',
                 'reconciliation_draft_box', 'opening_balance_label', 'sessions_box', 'unassigned_box'):
        env[name] = MagicMock()
    for name in ('save_current_reconciliation_draft', 'save_reconciliation_draft', 'delete_reconciliation_draft', 'get_reconciliation_draft',
                 'create_reconciliation_session', 'cancel_reconciliation_session',
                 'remove_transaction_from_reconciliation_session', 'bulk_assign_payment_method',
                 'refresh_reconciliation_screen', 'refresh_all', '_card_payment_dialog', '_transaction_dialog',
                 'toggle_reconciliation_selection', 'toggle_unassigned'):
        env[name] = Mock(name=name)
    env.update(ui=ui, user_id=7, date=date, Decimal=D, _money=str, _balance_money=str,
               _payment_effect=lambda amount, kind: str(amount), _signed=lambda amount, kind: str(amount),
               reconciliation_selected={2, 3}, reconciliation_rows_by_id={2: row(), 3: row(3, transaction_type='income', amount=D('30'))},
               unassigned_selected={2}, reconciliation_method_rows={4: {'method_type': 'credit_card'}},
               selected_reconciliation_total=Mock(return_value=D('50')),
               reconciliation_reference_summary=Mock(return_value={'reference_balance': D('100'), 'reference_date': DAY}),
               list_unreconciled_transactions=Mock(return_value=[row()]),
               list_unassigned_transactions=Mock(return_value=[row()]),
               payment_predicted_balance_summary=Mock(return_value=[]))
    env['create_reconciliation_session'].return_value = dict(transaction_count=2, statement_balance=D('150'), expected_balance=D('150'))
    return env, ui


class ReconciliationUiTests(unittest.TestCase):
    def test_block_location_and_filter_bindings_still_use_current_public_services(self):
        text = parent_source()
        start, end = text.index('        # CONCILIATION'), text.index('        # ORGANISATION')
        self.assertIn('reconciliation_panel = build_reconciliation_panel(', text[start:end])
        block = source()
        self.assertIn('with ui.tab_panel(reconciliation_tab)', block)
        self.assertNotIn('with ui.tab_panel(organization_tab)', block)
        for name in ('save_current_reconciliation_draft', 'render_reconciliation_transactions', 'session_detail_dialog', 'refresh_reconciliation_screen'):
            self.assertIn('def ' + name, block)
        names = {n.id for n in ast.walk(tree()) if isinstance(n, ast.Name)}
        self.assertTrue({'create_reconciliation_session', 'payment_predicted_balance_summary', 'list_unreconciled_transactions',
                         'list_unassigned_transactions', 'bulk_assign_payment_method', 'save_reconciliation_draft',
                         'get_reconciliation_draft', 'delete_reconciliation_draft', 'list_reconciliation_drafts',
                         'get_reconciliation_session', 'list_reconciliation_sessions', 'cancel_reconciliation_session',
                         'remove_transaction_from_reconciliation_session', 'reconciliation_reference_summary'}.issubset(names))
        bindings = [n for n in ast.walk(tree()) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'on_value_change' and isinstance(n.func.value, ast.Name)]
        for field in ('reconciliation_start', 'reconciliation_end', 'reconciliation_query', 'reconciliation_sort'):
            call = next(n for n in bindings if n.func.value.id == field)
            self.assertEqual(ast.unparse(call.args[0]), 'lambda event: render_reconciliation_transactions.refresh()')
        payment = next(n for n in bindings if n.func.value.id == 'reconciliation_payment')
        self.assertEqual(ast.unparse(payment.args[0]), 'change_reconciliation_payment')

    def test_filter_and_sort_preserve_hidden_selection_but_prune_ineligible_ids(self):
        env, ui = environment()
        env['reconciliation_selected'].add(99)
        all_rows = [row(), row(3), row(4)]
        env['list_unreconciled_transactions'].side_effect = lambda *args, **kwargs: [row(4), row()] if kwargs else all_rows
        render = load('render_reconciliation_transactions', env)
        for direction in ('asc', 'desc'):
            env['reconciliation_sort'].value = direction
            ui.widgets.clear()
            render()
            self.assertEqual(env['reconciliation_selected'], {2, 3})
            self.assertEqual(set(env['reconciliation_rows_by_id']), {2, 3, 4})
            labels = [args[0] for kind, args, _, _ in ui.widgets if kind == 'label' and args and str(args[0]).startswith('Achat ')]
            self.assertEqual(labels, ['Achat 2', 'Achat 4'] if direction == 'asc' else ['Achat 4', 'Achat 2'])
        env['list_unreconciled_transactions'].assert_called_with(7, 4, start_date='2026-09-01', end_date='2026-09-30', query='achat')
        self.assertEqual(ui.notify.call_count, 1)
        self.assertIn('plus admissibles', ui.notify.call_args.args[0])

    def test_all_adds_only_visible_ids_none_clears_entire_selection(self):
        env, ui = environment()
        env['reconciliation_selected'] = {3}
        env['list_unreconciled_transactions'].side_effect = lambda *args, **kwargs: [row()] if kwargs else [row(), row(3), row(4)]
        load('render_reconciliation_transactions', env)()
        ui.click('Tout')
        self.assertEqual(env['reconciliation_selected'], {2, 3})
        ui.click('Aucun')
        self.assertEqual(env['reconciliation_selected'], set())
        self.assertEqual(env['render_reconciliation_selection'].refresh.call_count, 2)

    def test_refresh_order_reset_flag_and_explicit_payment_change(self):
        env, _ = environment()
        events = []
        for name in RENDERS:
            env[name].refresh.side_effect = lambda name=name: events.append(name)
        refresh = load('refresh_reconciliation_screen', env)
        refresh()
        self.assertEqual(events, RENDERS)
        self.assertEqual(env['reconciliation_selected'], {2, 3})
        events.clear()
        load('change_reconciliation_payment', env)()
        self.assertEqual(events, RENDERS)
        self.assertEqual(env['reconciliation_selected'], set())
        env['refresh_all'].assert_not_called()

    def test_draft_save_transmits_all_current_fields_without_finalizing(self):
        env, _ = environment()
        save = load('save_current_reconciliation_draft', env)
        save()
        call = env['save_reconciliation_draft'].call_args
        self.assertEqual(call.args[:2], (7, 4))
        self.assertEqual(set(call.args[2]), {2, 3})
        self.assertEqual(call.kwargs, dict(statement_date='2026-09-08', statement_balance=D('150'), due_date='2026-09-20',
                        reconciliation_date='2026-09-09', note='note', include_opening_balance=True, difference_explanation=None,
                        filter_start='2026-09-01', filter_end='2026-09-30', filter_query='achat', sort_direction='asc'))
        env['render_reconciliation_draft'].refresh.assert_called_once_with()
        env['create_reconciliation_session'].assert_not_called()
        env['save_reconciliation_draft'].side_effect = ValueError('refus')
        save()
        env['render_reconciliation_draft'].refresh.assert_called_once_with()

    def test_draft_resume_restores_selection_statement_filters_sort_and_options(self):
        env, _ = environment()
        draft = dict(selected_transaction_ids=['5', 6], statement_date=DAY, statement_balance=D('210'), due_date=DAY,
                     reconciliation_date=DAY, note='repris', difference_explanation='frais', include_opening_balance=False,
                     filter_start=DAY, filter_end=DAY, filter_query='recherche', sort_direction='desc')
        load('resume_reconciliation_draft', env)(draft)
        self.assertEqual(env['reconciliation_selected'], {5, 6})
        expected = dict(statement_date='2026-09-08', statement_balance=D('210'), due_date='2026-09-08',
                        reconciliation_date_input='2026-09-08', reconciliation_note='repris', difference_explanation='frais',
                        include_opening_balance=False, reconciliation_start='2026-09-08', reconciliation_end='2026-09-08',
                        reconciliation_query='recherche', reconciliation_sort='desc')
        for name, value in expected.items():
            self.assertEqual(env[name].value, value, name)
        for name in ('render_reconciliation_transactions', 'render_reconciliation_selection', 'render_reconciliation_balance'):
            env[name].refresh.assert_called_once_with()
        env['create_reconciliation_session'].assert_not_called()

    def test_abandon_draft_only_deletes_draft_and_preserves_selection_and_sessions(self):
        env, _ = environment()
        load('abandon_reconciliation_draft', env)()
        env['delete_reconciliation_draft'].assert_called_once_with(7, 4)
        env['render_reconciliation_draft'].refresh.assert_called_once_with()
        self.assertEqual(env['reconciliation_selected'], {2, 3})
        for name in ('cancel_reconciliation_session', 'create_reconciliation_session', 'remove_transaction_from_reconciliation_session'):
            env[name].assert_not_called()

    def test_balance_reuses_summary_for_selected_method_and_opening_visibility(self):
        env, ui = environment()
        summary = dict(payment_method_id=4, current_balance=D('150'), predicted_balance=D('170'), confirmed_count=2, opening_balance_pending=D('100'))
        env['payment_predicted_balance_summary'].return_value = [summary | {'payment_method_id': 9, 'current_balance': D('999')}, summary]
        render = load('render_reconciliation_balance', env)
        render()
        env['payment_predicted_balance_summary'].assert_called_once_with(7)
        labels = [args[0] for kind, args, _, _ in ui.widgets if kind == 'label' and args]
        self.assertIn('150', labels)
        self.assertNotIn('999', labels)
        self.assertTrue(env['include_opening_balance'].visible)
        summary['opening_balance_pending'] = D('0')
        render()
        self.assertFalse(env['include_opening_balance'].visible)
        self.assertFalse(env['include_opening_balance'].value)

    def test_selected_total_uses_expense_positive_income_negative_ignores_missing(self):
        env, _ = environment()
        env['reconciliation_selected'].add(99)
        self.assertEqual(load('selected_reconciliation_total', env)(), D('50'))

    def test_balanced_finalization_transmits_values_then_resets_and_refreshes(self):
        env, ui = environment()
        events = []
        result = env['create_reconciliation_session'].return_value
        env['create_reconciliation_session'].side_effect = lambda **kwargs: events.append('create') or result
        env['refresh_reconciliation_screen'].side_effect = lambda: events.append('screen')
        env['refresh_all'].side_effect = lambda: events.append('parent')
        load('render_reconciliation_selection', env)()
        ui.click('Finaliser la conciliation')
        kwargs = dict(env['create_reconciliation_session'].call_args.kwargs)
        ids = kwargs.pop('transaction_ids')
        self.assertEqual(set(ids), {2, 3})
        self.assertEqual(kwargs, dict(user_id=7, payment_method_id=4, statement_date='2026-09-08', statement_balance=D('150'),
                         due_date='2026-09-20', reconciliation_date='2026-09-09', note='note', include_opening_balance=True,
                         difference_resolution='balanced', difference_explanation=None))
        self.assertEqual(events, ['create', 'screen', 'parent'])
        self.assertEqual(env['reconciliation_selected'], set())
        self.assertFalse(env['include_opening_balance'].value)
        self.assertEqual(env['reconciliation_note'].value, '')

    def test_unbalanced_dialog_requires_explanation_for_justified(self):
        env, ui = environment()
        env['statement_balance'].value = D('160')
        load('render_reconciliation_selection', env)()
        ui.click('Finaliser la conciliation')
        ui.find('label', 'La conciliation ne balance pas')
        for text in ('Clore comme écart justifié', 'Clore et programmer le paiement', 'Reporter l’écart', 'Retourner à la conciliation'):
            ui.find('button', text)
        ui.click('Clore comme écart justifié')
        env['create_reconciliation_session'].assert_not_called()
        ui.find('textarea', 'Explication de l’écart')[3].value = ' frais '
        ui.click('Clore comme écart justifié')
        self.assertEqual(env['create_reconciliation_session'].call_args.kwargs['difference_resolution'], 'justified')
        self.assertEqual(env['create_reconciliation_session'].call_args.kwargs['difference_explanation'], 'frais')
        env['_card_payment_dialog'].assert_not_called()

    def test_carry_choice_does_not_require_explanation_or_program_payment(self):
        env, ui = environment()
        env['statement_balance'].value = D('160')
        load('render_reconciliation_selection', env)()
        ui.click('Finaliser la conciliation')
        ui.click('Reporter l’écart')
        self.assertEqual(env['create_reconciliation_session'].call_args.kwargs['difference_resolution'], 'carry')
        self.assertIsNone(env['create_reconciliation_session'].call_args.kwargs['difference_explanation'])
        env['_card_payment_dialog'].assert_not_called()

    def test_credit_card_close_program_uses_statement_or_expected_and_due_date(self):
        for statement, expected, amount in [(D('-160'), D('150'), 160.0), (None, D('-150'), 150.0), (D('0'), D('150'), None)]:
            with self.subTest(statement=statement):
                env, ui = environment()
                env['statement_balance'].value = D('160')
                env['create_reconciliation_session'].return_value = dict(transaction_count=2, statement_balance=statement, expected_balance=expected)
                load('render_reconciliation_selection', env)()
                ui.click('Clore et programmer le paiement')
                ui.click('Clore et programmer le paiement')
                env['create_reconciliation_session'].assert_not_called()
                ui.find('textarea', 'Explication de l’écart')[3].value = 'écart accepté'
                ui.click('Clore et programmer le paiement')
                self.assertEqual(env['create_reconciliation_session'].call_args.kwargs['difference_resolution'], 'justified')
                env['_card_payment_dialog'].assert_called_once_with(7, env['refresh_all'], prefill={
                    'destination_payment_method_id': 4, 'amount': amount, 'payment_date': '2026-09-20',
                    'status': 'planned', 'bank_programmed': False, 'description': 'Paiement de carte — relevé du 08/09/2026'})

    def test_credit_card_programming_opens_before_parent_refresh(self):
        env, ui = environment()
        env['statement_balance'].value = D('160')
        result = dict(
            transaction_count=2,
            statement_balance=D('-160'),
            expected_balance=D('150'),
        )
        events = []
        env['create_reconciliation_session'].side_effect = (
            lambda **kwargs: events.append('create') or result
        )
        env['refresh_reconciliation_screen'].side_effect = (
            lambda: events.append('screen')
        )
        env['refresh_all'].side_effect = lambda: events.append('parent')
        env['_card_payment_dialog'].side_effect = (
            lambda *args, **kwargs: events.append('card')
        )

        load('render_reconciliation_selection', env)()
        ui.click('Clore et programmer le paiement')
        ui.find('textarea', 'Explication de l’écart')[3].value = 'écart accepté'
        ui.click('Clore et programmer le paiement')

        self.assertEqual(events, ['create', 'screen', 'card'])
        env['refresh_all'].assert_not_called()
        env['_card_payment_dialog'].assert_called_once()
        self.assertIs(
            env['_card_payment_dialog'].call_args.args[1],
            env['refresh_all'],
        )

    def test_empty_selection_or_failed_finalization_never_resets_or_refreshes(self):
        env, ui = environment()
        env['include_opening_balance'].value = False
        env['reconciliation_selected'].clear()
        load('render_reconciliation_selection', env)()
        ui.click('Finaliser la conciliation')
        env['create_reconciliation_session'].assert_not_called()
        env['reconciliation_selected'].add(2)
        env['create_reconciliation_session'].side_effect = ValueError('inadmissible')
        ui.click('Finaliser la conciliation')
        self.assertEqual(env['reconciliation_selected'], {2})
        env['refresh_reconciliation_screen'].assert_not_called()
        env['refresh_all'].assert_not_called()

    def test_unassigned_assignment_calls_bulk_then_refreshes_both(self):
        env, ui = environment()
        env['unassigned_selected'].add(99)
        env['bulk_assign_payment_method'].return_value = 1
        load('render_unassigned', env)()
        self.assertEqual(env['unassigned_selected'], {2})
        ui.click('Attribuer la sélection')
        env['bulk_assign_payment_method'].assert_called_once_with(7, [2], 4)
        self.assertEqual(env['unassigned_selected'], set())
        env['refresh_reconciliation_screen'].assert_called_once_with()
        env['refresh_all'].assert_called_once_with()

    def test_history_cancel_and_remove_refresh_screen_and_parent_after_success_only(self):
        for name, service, args in [('remove_one', 'remove_transaction_from_reconciliation_session', (7, 42, 2)),
                                    ('cancel_session_now', 'cancel_reconciliation_session', (7, 42))]:
            with self.subTest(name=name):
                env, _ = environment()
                env.update(session_id=42, transaction={'id': 2}, dialog=Mock())
                callback = load(name, env)
                callback()
                env[service].assert_called_once_with(*args)
                env['dialog'].close.assert_called_once_with()
                env['refresh_reconciliation_screen'].assert_called_once_with()
                env['refresh_all'].assert_called_once_with()
                env[service].side_effect = ValueError('refus')
                callback()
                env['refresh_all'].assert_called_once_with()
                env['refresh_reconciliation_screen'].assert_called_once_with()
        detail = ast.unparse(node('session_detail_dialog'))
        self.assertIn("transaction['is_active'] and session['status'] == 'completed'", detail)
        self.assertIn('on_click=remove_one', detail)
        self.assertIn('on_click=cancel_session_now', detail)


class ReconciliationPanelArchitectureTests(unittest.TestCase):
    def test_independent_import_and_only_allowed_standard_imports(self):
        script = '''
import builtins
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'nicegui', 'finances', 'finances_data', 'db', 'psycopg'}:
        raise AssertionError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_reconciliation
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        imports = [n for n in ast.walk(tree()) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertTrue(all(isinstance(n, ast.ImportFrom) for n in imports))
        self.assertEqual({(n.module, a.name) for n in imports for a in n.names},
                         {('dataclasses', 'dataclass'), ('typing', 'Callable'), ('datetime', 'date'), ('decimal', 'Decimal')})

    def test_handle_construction_is_lazy_and_callbacks_are_called_once(self):
        refresh, reload = Mock(), Mock()
        handle = ReconciliationPanelHandle(refresh, reload)
        refresh.assert_not_called()
        reload.assert_not_called()
        handle.refresh()
        refresh.assert_called_once_with()
        reload.assert_not_called()
        handle.reload_options()
        reload.assert_called_once_with()
        refresh.assert_called_once_with()

    def test_parent_uses_only_handle_and_extracted_builder_returns_it(self):
        parent = ast.parse(parent_source())
        internal = {n.name for n in ast.walk(node('build_reconciliation_panel')) if isinstance(n, ast.FunctionDef)} - {'build_reconciliation_panel'}
        self.assertTrue(internal.isdisjoint({n.name for n in ast.walk(parent) if isinstance(n, ast.FunctionDef)}))
        assignment = next(n for n in ast.walk(parent) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'reconciliation_panel' for t in n.targets))
        self.assertEqual(ast.unparse(assignment.value.func), 'build_reconciliation_panel')
        self.assertEqual(next(ast.unparse(k.value) for k in assignment.value.keywords if k.arg == 'refresh_all'), 'lambda: refresh_all()')
        refresh = next(n for n in ast.walk(parent) if isinstance(n, ast.FunctionDef) and n.name == 'refresh_all')
        names = {n.id for n in ast.walk(refresh) if isinstance(n, ast.Name)}
        self.assertTrue({'reconciliation_payment', 'unassigned_target', 'refresh_reconciliation_screen'}.isdisjoint(names))
        env = {name: MagicMock() for name in names}
        events = []
        env['reconciliation_panel'] = ReconciliationPanelHandle(lambda: events.append('refresh'), lambda: events.append('reload'))
        exec(compile(ast.Module(body=[refresh], type_ignores=[]), '<parent>', 'exec'), env)
        env['refresh_all']()
        self.assertEqual(events, ['reload', 'refresh'])
        # Build the entire extracted block with the same lightweight widgets
        # used by the characterization tests; no real NiceGUI is started.
        ui = SimulatedUi()
        deps = {name: Mock() for name in inspect.signature(build_reconciliation_panel).parameters}
        for name in ('list_payment_methods', 'list_reconciliation_drafts', 'list_unreconciled_transactions',
                     'list_unassigned_transactions', 'list_reconciliation_sessions', 'payment_predicted_balance_summary'):
            deps[name].return_value = []
        deps.update(ui=ui, user_id=7, reconciliation_tab=object(), _money=str, _balance_money=str,
                    _signed=lambda *args: '', _payment_effect=lambda *args: '', RECONCILIATION_SESSION_STATUSES={})
        deps['_payment_options'].return_value = {4: 'Visa'}
        deps['get_reconciliation_draft'].return_value = None
        deps['reconciliation_reference_summary'].return_value = {'reference_balance': D('0')}
        handle = build_reconciliation_panel(**deps)
        self.assertIsInstance(handle, ReconciliationPanelHandle)
        deps['_payment_options'].reset_mock()
        handle.reload_options()
        self.assertEqual(deps['_payment_options'].call_count, 2)
        deps['_payment_options'].assert_called_with(7, include_none=False)
        handle.refresh()
        deps['refresh_all'].assert_not_called()


if __name__ == '__main__':
    unittest.main()

"""Panneau Financements et raccordements réels avec une interface simulée."""
import ast
import inspect
import subprocess
import sys
import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from finances_financing import FinancingPanelHandle, build_financing_panel
from finances_ui_state import MonthCursor
from test_finances_financing import ROOT, plan


def parent_tree():
    return ast.parse((ROOT / "finances.py").read_text(encoding="utf-8"))


def panel_tree():
    return ast.parse((ROOT / 'finances_financing.py').read_text(encoding='utf-8'))


def function(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


class SimulatedUi:
    def __init__(self):
        self.widgets = []
        self.notify = Mock()
        self.renders = []

    def refreshable(self, fn):
        fn.refresh = Mock(side_effect=fn)
        self.renders.append(fn)
        return fn

    def __getattr__(self, kind):
        def create(*args, **kwargs):
            widget = MagicMock()
            widget.__enter__.return_value = widget
            for method in ('classes', 'props', 'tooltip', 'on_value_change'):
                getattr(widget, method).return_value = widget
            widget.value = kwargs.get('value')
            self.widgets.append((kind, args, kwargs, widget))
            return widget
        return create

    def find(self, kind, text=None, icon=None):
        return next(row for row in reversed(self.widgets)
                    if row[0] == kind and (text is None or row[2].get('label') == text or row[1][:1] == (text,))
                    and (icon is None or row[2].get('icon') == icon))

    def click(self, text=None, icon=None):
        self.find('button', text, icon)[2]['on_click']()


def build(plans=None):
    ui = SimulatedUi()
    deps = {name: Mock(name=name) for name in inspect.signature(build_financing_panel).parameters}
    deps.update(
        ui=ui, user_id=7, financing_tab=object(),
        financing_month_state=MonthCursor(date(2026, 10, 1)),
        INSTALLMENT_PLAN_TYPES={'merchant': 'Magasin', 'credit_card': 'Carte'},
        FREQUENCY_UNITS={'month': 'Mensuel'},
        list_installment_plans=Mock(return_value=plans or []),
        financing_month_summary=Mock(return_value={'payments': Decimal('100'), 'remaining_balances': Decimal('900')}),
        _payment_options=Mock(return_value={4: 'Visa'}),
        _category_options=Mock(return_value={3: 'Achats'}),
        _tag_options=Mock(return_value={5: 'Important'}),
        _money=str, _balance_money=str, _month_label=str,
    )
    return build_financing_panel(**deps), ui, deps


class FinancingPanelTests(unittest.TestCase):
    def test_handle_is_lazy_and_calls_current_callback_once(self):
        first, second = Mock(), Mock()
        handle = FinancingPanelHandle(first)
        first.assert_not_called()
        handle.refresh()
        first.assert_called_once_with()
        handle.on_refresh = second
        handle.refresh()
        second.assert_called_once_with()
        first.assert_called_once_with()

    def test_independent_import_and_no_circular_dependencies(self):
        script = '''
import builtins
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'nicegui', 'finances', 'finances_data', 'db', 'psycopg'}:
        raise AssertionError('Import interdit: ' + name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
from finances_financing import FinancingPanelHandle, build_financing_panel
assert callable(build_financing_panel)
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        imports = [n for n in ast.walk(panel_tree()) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertTrue(all(isinstance(n, ast.ImportFrom) for n in imports))
        self.assertEqual({n.module for n in imports}, {'dataclasses', 'datetime', 'decimal', 'typing'})

    def test_parent_passes_unique_cursor_and_late_services(self):
        tree = parent_tree()
        assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'financing_panel' for t in n.targets))
        self.assertEqual(ast.unparse(assignment.value.func), 'build_financing_panel')
        keywords = {k.arg: k.value for k in assignment.value.keywords}
        expected = {
            'ui', 'user_id', 'financing_tab', 'financing_month_state', 'INSTALLMENT_PLAN_TYPES',
            'FREQUENCY_UNITS', '_payment_options', '_category_options', '_tag_options',
            'list_installment_plans', 'financing_month_summary', 'save_installment_plan',
            'delete_installment_plan', 'toggle_installment_plan', 'calculate_installment_payment',
            'analyze_installment_progress', '_money', '_balance_money', '_month_label', 'refresh_all',
        }
        self.assertEqual(set(keywords), expected)
        self.assertEqual(set(inspect.signature(build_financing_panel).parameters), expected)
        self.assertEqual(ast.unparse(keywords['refresh_all']), 'lambda: refresh_all()')
        cursors = [n for tree_ in (tree, panel_tree()) for n in ast.walk(tree_)
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'financing_month_state' for t in n.targets)]
        self.assertEqual(len(cursors), 1)
        self.assertEqual(ast.unparse(cursors[0].value), 'MonthCursor()')
        self.assertNotIn('MonthCursor', ast.unparse(panel_tree()))
        direct = {key for key, value in keywords.items() if not isinstance(value, ast.Lambda)}
        namespace = {name: object() for name in direct}
        target = Mock()
        namespace['build_financing_panel'] = target
        # refresh_all deliberately does not exist during parent construction.
        exec(compile(ast.Module(body=[assignment], type_ignores=[]), '<binding>', 'exec'), namespace)
        injected = target.call_args.kwargs
        self.assertIs(injected['financing_month_state'], namespace['financing_month_state'])
        for generation in range(2):
            for name in expected - direct:
                service = Mock()
                namespace[name] = service
                if name == 'refresh_all':
                    injected[name]()
                    service.assert_called_once_with()
                else:
                    injected[name](7, sample=generation)
                    service.assert_called_once_with(7, sample=generation)

    def test_internal_definitions_removed_and_initial_render_precedes_handle(self):
        names = {'installment_plan_dialog', 'update_interest_preview', 'perform_plan_save',
                 'save_plan_now', 'remove_installment_plan', 'change_financing_month', 'render_financing'}
        self.assertTrue(names.isdisjoint({n.name for n in ast.walk(parent_tree()) if isinstance(n, ast.FunctionDef)}))
        self.assertTrue(names.issubset({n.name for n in ast.walk(panel_tree()) if isinstance(n, ast.FunctionDef)}))
        body = function(panel_tree(), 'build_financing_panel').body
        self.assertIsInstance(body[-1], ast.Return)
        self.assertEqual(ast.unparse(body[-2].body[-1]), 'render_financing()')
        self.assertIn('FinancingPanelHandle(on_refresh=lambda: render_financing.refresh())', ast.unparse(body[-1]))
        fragment = (ROOT / 'finances.py').read_text(encoding='utf-8')
        panels = next(n for n in ast.walk(parent_tree()) if isinstance(n, ast.With)
                      and any('ui.tab_panels(' in ast.unparse(item.context_expr) for item in n.items))
        index = next(i for i, n in enumerate(panels.body) if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'financing_panel' for t in n.targets))
        self.assertEqual(ast.unparse(panels.body[index - 1].targets[0]), 'budget_panel')
        self.assertEqual(ast.unparse(panels.body[index].value.func), 'build_financing_panel')
        self.assertEqual(ast.unparse(panels.body[index + 1].items[0].context_expr),
                         "ui.tab_panel(shared_loans_tab).classes('px-0')")
        self.assertIn('        )\n\n        # PRÊTS PARTAGÉS', fragment)

    def test_real_parent_refresh_uses_handle_once(self):
        node = function(parent_tree(), 'refresh_all')
        self.assertNotIn('render_financing', ast.unparse(node))
        names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        namespace = {name: MagicMock(name=name) for name in names}
        callback = Mock()
        namespace['financing_panel'] = FinancingPanelHandle(callback)
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<refresh>', 'exec'), namespace)
        namespace['refresh_all']()
        callback.assert_called_once_with()

    def test_builder_returns_handle_and_navigation_refreshes_only_financing(self):
        for plans in ([], [plan()]):
            with self.subTest(has_plan=bool(plans)):
                handle, ui, deps = build(plans)
                self.assertIsInstance(handle, FinancingPanelHandle)
                listing, summary = deps['list_installment_plans'], deps['financing_month_summary']
                listing.assert_called_once_with(7, include_inactive=True)
                summary.assert_called_once_with(7, date(2026, 10, 1))
                for icon, expected in [('chevron_left', date(2026, 9, 1)), ('chevron_right', date(2026, 10, 1))]:
                    before = listing.call_count
                    ui.click(icon=icon)
                    self.assertEqual(deps['financing_month_state'].value, expected)
                    self.assertEqual(listing.call_count, before + 1)
                    summary.assert_called_with(7, expected)
                with patch('finances_ui_state.month_start', return_value=date(2027, 2, 1)):
                    ui.click(text='2026-10-01')
                self.assertEqual(deps['financing_month_state'].value, date(2027, 2, 1))
                summary.assert_called_with(7, date(2027, 2, 1))
                self.assertEqual(ui.renders[0].refresh.call_count, 3)
                handle.refresh()
                self.assertEqual(ui.renders[0].refresh.call_count, 4)
                deps['refresh_all'].assert_not_called()

    def test_dialog_preview_inconsistency_and_save_callbacks(self):
        row = plan(annual_interest_rate=Decimal('12'), payment_includes_interest=False,
                   completed_installments_estimated=True, payment_method_id=4, category_id=3)
        _, ui, deps = build([row])
        analysis = deps['analyze_installment_progress']
        analysis.return_value = dict(estimated_completed_installments=4, is_inconsistent=True,
                                     expected_remaining_balance=Decimal('800'), balance_difference=Decimal('200'))
        calculate = deps['calculate_installment_payment']
        calculate.return_value = Decimal('150')
        ui.click(icon='edit')
        calculate.assert_called_once_with(Decimal('1000'), 8, Decimal('12'), 'month', 1, Decimal('0'))
        analysis.assert_called_once_with(original_amount=Decimal('1200'), remaining_balance=Decimal('1000'),
                                        installment_amount=Decimal('100'), total_installments=12, completed_installments=None)
        preview = ui.find('label', '')[3]
        self.assertIn('versement total calculé : 150', preview.set_text.call_args.args[0])
        completed = ui.find('number', 'Versements déjà effectués — facultatif')[3]
        completed.value = 2
        ui.click(text='Enregistrer')
        deps['save_installment_plan'].assert_not_called()
        ui.find('label', 'Les versements saisis semblent incohérents')
        ui.click(text='Conserver quand même')
        deps['save_installment_plan'].assert_called_once()
        self.assertEqual(deps['save_installment_plan'].call_args.kwargs['completed_installments'], 2)
        self.assertFalse(deps['save_installment_plan'].call_args.kwargs['payment_includes_interest'])
        deps['refresh_all'].assert_called_once_with()
        deps['save_installment_plan'].side_effect = ValueError('refus')
        deps['refresh_all'].reset_mock()
        analysis.return_value = {'is_inconsistent': False}
        ui.click(text='Enregistrer')
        ui.notify.assert_called_with('refus', type='warning')
        deps['refresh_all'].assert_not_called()

    def test_toggle_and_delete_keep_mutation_then_global_refresh(self):
        _, ui, deps = build([plan(id=42)])
        events = []
        deps['toggle_installment_plan'].side_effect = lambda *args: events.append(('toggle', args))
        deps['delete_installment_plan'].side_effect = lambda *args: events.append(('delete', args))
        deps['refresh_all'].side_effect = lambda: events.append('refresh')
        toggle = ui.find('switch')[2]['on_change']
        for value in (False, True):
            toggle(SimpleNamespace(value=value))
        self.assertEqual(events, [('toggle', (7, 42, False)), 'refresh', ('toggle', (7, 42, True)), 'refresh'])
        events.clear()
        ui.click(icon='delete')
        self.assertEqual(events, [])
        ui.click(text='Supprimer')
        self.assertEqual(events, [('delete', (7, 42)), 'refresh'])
        events.clear()
        deps['delete_installment_plan'].side_effect = ValueError('refus')
        ui.click(text='Supprimer')
        ui.notify.assert_called_with('refus', type='warning')
        self.assertEqual(events, [])


if __name__ == '__main__':
    unittest.main()

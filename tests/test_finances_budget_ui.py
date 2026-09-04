"""Contrat du panneau Budget et raccordements réels, sans lancer NiceGUI."""
import ast
import inspect
import subprocess
import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from finances_budget import BudgetPanelHandle, build_budget_panel
from finances_ui_state import MonthCursor

ROOT = Path(__file__).resolve().parents[1]


def ui_tree():
    return ast.parse("".join(p.read_text(encoding="utf-8") for p in sorted(ROOT.glob("finances_part_*.pyfrag"))))


def budget_tree():
    return ast.parse((ROOT / "finances_budget.py").read_text(encoding="utf-8"))


def function(name, tree=None):
    return next(n for n in ast.walk(tree or ui_tree())
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)


def load_function(name, namespace, tree=None):
    node = function(name, tree)
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<isolated>", "exec"), namespace)
    return namespace[name]


class BudgetNavigationTests(unittest.IsolatedAsyncioTestCase):
    async def test_dashboard_navigation_changes_shared_month_and_only_dashboard(self):
        cursor = MonthCursor(date(2026, 10, 1)); dashboard = Mock()
        change = load_function("change_month", dict(month_state=cursor, render_dashboard=dashboard))
        await change(-1)
        self.assertEqual(cursor.value, date(2026, 9, 1))
        dashboard.refresh.assert_called_once_with()

    async def test_dashboard_reset_uses_monthcursor_current_month(self):
        cursor = MonthCursor(date(2026, 10, 1)); dashboard = Mock()
        change = load_function("change_month", dict(month_state=cursor, render_dashboard=dashboard))
        with patch("finances_ui_state.month_start", return_value=date(2027, 2, 1)):
            await change(99, reset=True)
        self.assertEqual(cursor.value, date(2027, 2, 1))
        dashboard.refresh.assert_called_once_with()

    def budget_change(self, fail=False):
        cursor=MonthCursor(date(2026,10,1)); events=[]
        loading=Mock(); loading.set_visibility.side_effect=lambda value: events.append(value)
        ui=Mock(); ui.run_javascript=AsyncMock(side_effect=lambda script: events.append("browser"))
        render=Mock()
        if fail:
            def failure(): events.append("failed"); raise RuntimeError("test")
            render.refresh.side_effect=failure
        else: render.refresh.side_effect=lambda: events.append(("budget",cursor.value))
        change=load_function("change_budget_month",dict(month_state=cursor,budget_loading=loading,ui=ui,
                                                         render_budget=render),budget_tree())
        return change,cursor,events,ui

    async def test_budget_navigation_spinner_browser_budget_hidden(self):
        change,cursor,events,ui=self.budget_change()
        await change(1)
        self.assertEqual(events,[True,"browser",("budget",date(2026,11,1)),False])
        self.assertIn("requestAnimationFrame",ui.run_javascript.call_args.args[0])

    async def test_budget_navigation_hides_spinner_on_exception(self):
        change,_,events,_=self.budget_change(True)
        with self.assertRaisesRegex(RuntimeError,"test"): await change(1)
        self.assertEqual(events,[True,"browser","failed",False])


class BudgetPanelTests(unittest.TestCase):
    def test_handle_is_lazy_and_refreshes_callback(self):
        callback=Mock(); handle=BudgetPanelHandle(callback); callback.assert_not_called()
        handle.refresh(); callback.assert_called_once_with()

    def test_independent_import(self):
        script="""
import importlib.abc,sys
class B(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'nicegui','finances','finances_data','db','psycopg'}: raise AssertionError(fullname)
sys.meta_path.insert(0,B())
from finances_budget import BudgetPanelHandle,build_budget_panel
assert callable(build_budget_panel)
"""
        result=subprocess.run([sys.executable,"-B","-c",script],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_builder_returns_handle_with_simulated_ui(self):
        ui=MagicMock()
        def element(*args,**kwargs):
            widget=MagicMock(); widget.__enter__.return_value=widget
            for name in ("classes","props","tooltip","style","on_value_change"):
                getattr(widget,name).return_value=widget
            widget.value=kwargs.get("value")
            return widget
        for name in ("tab_panel","row","column","card","element","button","select","label","spinner",
                     "dialog","input","number","checkbox","switch","expansion","textarea","time"):
            getattr(ui,name).side_effect=element
        def refreshable(fn): fn.refresh=Mock(side_effect=fn); return fn
        ui.refreshable.side_effect=refreshable
        deps={name:Mock(name=name) for name in inspect.signature(build_budget_panel).parameters}
        summary=dict(monthly_income=Decimal(0),monthly_expense=Decimal(0),monthly_remaining=Decimal(0),
                     biweekly_income=Decimal(0),biweekly_expense=Decimal(0),biweekly_remaining=Decimal(0),
                     pay_count=0,available_month=Decimal(0),carry_in=Decimal(0),available_month_base=Decimal(0))
        deps.update(ui=ui,user_id=7,budget_tab=Mock(),month_state=MonthCursor(date(2026,10,1)),
                    budget_capacity_summary=Mock(return_value=summary),list_budget_items=Mock(return_value=[]),
                    budget_forecast=Mock(return_value=[]),list_installment_plans=Mock(return_value=[]),
                    _recurrence_options=Mock(return_value={}),_category_options=Mock(return_value={}),
                    _payment_options=Mock(return_value={}),_tag_options=Mock(return_value={}),
                    _money=str,_balance_money=str,_month_label=str,_shift_month=lambda value,n:value)
        handle=build_budget_panel(**deps)
        self.assertIsInstance(handle,BudgetPanelHandle)
        deps["budget_capacity_summary"].assert_called_once_with(7,date(2026,10,1))
        deps["budget_forecast"].assert_called_once_with(7,date(2026,10,1),months=6,initial_capacity=summary)

    def test_parent_injects_same_month_state_and_lazy_services(self):
        assignment=next(n for n in ast.walk(ui_tree()) if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=="budget_panel" for t in n.targets))
        self.assertEqual(assignment.value.func.id,"build_budget_panel")
        keywords={k.arg:k.value for k in assignment.value.keywords}
        self.assertEqual(ast.unparse(keywords["month_state"]),"month_state")
        for name in ("budget_capacity_summary","list_budget_items","save_budget_item","refresh_all"):
            self.assertIsInstance(keywords[name],ast.Lambda)

    def test_panel_definitions_removed_from_fragments(self):
        names={"sorted_budget_rows","budget_item_dialog","financing_budget_group_dialog","change_budget_state",
               "change_budget_order","render_budget","render_budget_rows_card","change_budget_sort","change_budget_month"}
        fragment_defs={n.name for n in ast.walk(ui_tree()) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        self.assertTrue(names.isdisjoint(fragment_defs))
        module_defs={n.name for n in ast.walk(budget_tree()) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        self.assertTrue(names.issubset(module_defs))
        self.assertNotIn("# BUDGET GLOBAL",(ROOT/"finances_part_06.pyfrag").read_text(encoding="utf-8"))

    def test_render_keeps_single_capacity_and_initial_forecast(self):
        render=function("render_budget",budget_tree()); calls=[n for n in ast.walk(render) if isinstance(n,ast.Call)]
        self.assertEqual(sum(ast.unparse(n.func)=="budget_capacity_summary" for n in calls),1)
        self.assertNotIn("budget_summary",ast.unparse(render))
        self.assertIn("summary_budget = capacity_budget",ast.unparse(render))
        forecast=next(n for n in calls if ast.unparse(n.func)=="budget_forecast")
        self.assertEqual(next(ast.unparse(k.value) for k in forecast.keywords if k.arg=="initial_capacity"),"capacity_budget")

    def test_period_clone_and_recurrence_generation_contracts(self):
        dialog=function("budget_item_dialog",budget_tree()); text=ast.unparse(dialog)
        saves=[n for n in ast.walk(dialog) if isinstance(n,ast.Call) and ast.unparse(n.func)=="save_budget_item"]
        self.assertGreaterEqual(len(saves),2)
        self.assertIn("if clone_period",text)
        self.assertIn("generate_due_recurrences(user_id)",text)
        self.assertIn("refresh_all()",text)

    def test_targeted_sort_move_and_global_refresh_contracts(self):
        module=ast.unparse(budget_tree())
        self.assertIn("move_budget_item(user_id, item_id, direction)",module)
        self.assertIn("render_budget.refresh()",module)
        sort=function("change_budget_sort",budget_tree())
        self.assertIn("render_budget.refresh()",ast.unparse(sort))
        refresh=function("refresh_all"); text=ast.unparse(refresh)
        self.assertIn("budget_panel.refresh()",text); self.assertNotIn("render_budget",text)
        self.assertEqual(len([n for n in ast.walk(ui_tree()) if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=="month_state" for t in n.targets)]),1)


if __name__=="__main__": unittest.main()

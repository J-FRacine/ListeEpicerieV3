"""Navigation réelle isolée des fragments, sans démarrer NiceGUI."""
import ast
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from finances_ui_state import MonthCursor

ROOT = Path(__file__).resolve().parents[1]


def source():
    return ast.parse("".join(p.read_text(encoding="utf-8")
                             for p in sorted(ROOT.glob("finances_part_*.pyfrag"))))


def function(name):
    return next(n for n in ast.walk(source())
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)


class BudgetNavigationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.events = []
        self.cursor = MonthCursor(date(2026, 10, 1))
        self.namespace = dict(month_state=self.cursor,
                              render_budget=Mock(), render_dashboard=Mock(),
                              budget_loading=Mock(), ui=Mock())
        self.namespace["budget_loading"].set_visibility.side_effect = lambda value: self.events.append(value)
        self.namespace["ui"].run_javascript = AsyncMock(side_effect=lambda script: self.events.append("browser"))
        self.namespace["render_budget"].refresh.side_effect = lambda: self.events.append(("budget", self.cursor.value))
        exec(compile(ast.Module(body=[function("change_month")], type_ignores=[]),
                     "<real change_month>", "exec"), self.namespace)

    async def test_budget_changes_shared_month_and_refreshes_only_budget_in_order(self):
        await self.namespace["change_month"](1, source="budget")
        self.assertIs(self.namespace["month_state"], self.cursor)
        self.assertEqual(self.events, [True, "browser", ("budget", date(2026, 11, 1)), False])
        self.namespace["render_dashboard"].refresh.assert_not_called()
        self.namespace["ui"].run_javascript.assert_awaited_once()
        self.assertIn("requestAnimationFrame", self.namespace["ui"].run_javascript.call_args.args[0])

    async def test_dashboard_uses_same_cursor_and_only_dashboard(self):
        await self.namespace["change_month"](-1, source="dashboard")
        self.assertIs(self.namespace["month_state"], self.cursor)
        self.assertEqual(self.cursor.value, date(2026, 9, 1))
        self.namespace["render_dashboard"].refresh.assert_called_once_with()
        self.namespace["render_budget"].refresh.assert_not_called()
        self.namespace["ui"].run_javascript.assert_not_awaited()
        self.assertEqual(self.events, [])

    async def test_reset_uses_monthcursor_current_month(self):
        with patch("finances_ui_state.month_start", return_value=date(2027, 2, 1)) as current:
            await self.namespace["change_month"](99, reset=True)
        current.assert_called_once_with()
        self.assertEqual(self.cursor.value, date(2027, 2, 1))

    async def test_render_exception_still_hides_loading(self):
        def fail():
            self.events.append("render failed")
            raise RuntimeError("test")
        self.namespace["render_budget"].refresh.side_effect = fail
        with self.assertRaisesRegex(RuntimeError, "test"):
            await self.namespace["change_month"](1)
        self.assertEqual(self.events, [True, "browser", "render failed", False])
        self.namespace["render_dashboard"].refresh.assert_not_called()


class BudgetStructureTests(unittest.TestCase):
    def test_render_reuses_capacity_as_summary_and_initial_forecast(self):
        node = function("render_budget")
        calls = [n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertEqual(sum(n.func.id == "budget_capacity_summary" for n in calls), 1)
        self.assertFalse(any(n.func.id == "budget_summary" for n in calls))
        assignment = next(n for n in node.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == "summary_budget" for t in n.targets))
        self.assertEqual(ast.unparse(assignment.value), "capacity_budget")
        capacity = next(n for n in node.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "capacity_budget" for t in n.targets))
        self.assertEqual(capacity.value.func.id, "budget_capacity_summary")
        forecast = [n for n in calls if n.func.id == "budget_forecast"]
        self.assertEqual(len(forecast), 1)
        self.assertEqual(next(ast.unparse(k.value) for k in forecast[0].keywords
                              if k.arg == "initial_capacity"), "capacity_budget")

    def test_budget_has_no_independent_cursor_or_dashboard_refresh(self):
        render = function("render_budget")
        change = function("change_month")
        self.assertNotIn("render_dashboard", ast.unparse(render))
        self.assertNotIn("MonthCursor", ast.unparse(render))
        self.assertNotIn("MonthCursor", ast.unparse(change))
        # Le curseur partagé est construit une fois dans le parent.
        assignments = [n for n in ast.walk(source()) if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == "month_state" for t in n.targets)]
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].value.func.id, "MonthCursor")
        self.assertIn("month_state.value", ast.unparse(render))


if __name__ == "__main__":
    unittest.main()

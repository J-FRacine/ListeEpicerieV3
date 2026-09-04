"""Écritures réelles avec contrat SQL simulé; aucun rollback réel testé."""
import importlib
import inspect
import subprocess
from pathlib import Path
import sys
import unittest
from contextlib import contextmanager, ExitStack
from datetime import date, time
from decimal import Decimal as D
from types import ModuleType
from unittest.mock import Mock, patch

stub = ModuleType("db")
stub.get_connection = Mock(side_effect=AssertionError("PostgreSQL interdit"))
with patch.dict(sys.modules, {"db": stub}):
    data = importlib.import_module("finances_data")

START = date(2026, 10, 1)
END = date(2026, 10, 31)


def step(sql, params=None, one=None, rows=None, count=1):
    return (sql, params, one, rows or [], count)


class ScriptedConnection:
    """Une connexion/curseur, réponses ordonnées; tout SQL imprévu échoue."""
    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []
        self.commits = 0
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self

    def execute(self, sql, params):
        assert not self.commits, "SQL après commit intermédiaire"
        assert self.steps, "SQL inattendu: " + sql
        expected, values, self.one, self.rows, self.rowcount = self.steps.pop(0)
        normalized = " ".join(sql.split())
        for fragment in ([expected] if isinstance(expected, str) else expected):
            assert fragment in normalized, (fragment, normalized)
        if values is not None:
            assert params == values, (params, values)
        self.calls.append((normalized, params))

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.rows

    def commit(self):
        assert not self.steps, "Commit avant la dernière écriture"
        self.commits += 1


class BudgetWritesTests(unittest.TestCase):
    @contextmanager
    def database(self, steps, commits=1):
        conn = ScriptedConnection(steps)
        with patch.object(data, "get_connection", return_value=conn) as connect:
            yield conn
        self.assertEqual(conn.steps, [])
        self.assertEqual(conn.commits, commits)
        connect.assert_called_once_with()

    def save(self, **values):
        args = dict(user_id=7, item_type="expense", description="  Loyer  ",
                    input_frequency="monthly", input_amount="100.125", note=" note ",
                    effective_start=START, effective_end=END, allow_overlap=True)
        args.update(values)
        return data.save_budget_item(**args)

    def insert_steps(self, **values):
        args = dict(kind="expense", frequency="monthly", amount=D("100.12"), override=None,
                    recurrence=None, sync=True, end=END)
        args.update(values)
        return [step(["COALESCE(MAX(sort_order),0)+1", "WHERE user_id=%s AND item_type=%s"],
                     (7, args["kind"]), one={"next_order": 9}),
                step(["INSERT INTO finance_budget_items", "RETURNING id"],
                     (7, args["kind"], "Loyer", args["frequency"], args["amount"], args["override"],
                      "note", 9, args["recurrence"], args["sync"], START, args["end"]), one={"id": 42})]

    def linked(self, **values):
        row = dict(id=12, transaction_type="income", amount=D("700"), frequency_unit="week",
                   frequency_interval=2, start_date=START, end_date=None)
        row.update(values)
        return row

    def link_steps(self, row, editing=None, duplicate=None):
        return [step(["FROM finance_recurrences", "WHERE id=%s AND user_id=%s"], (12, 7), one=row),
                step(["WHERE user_id=%s AND recurrence_id=%s", "AND id<>%s" if editing else "LIMIT 1"],
                     [7, 12] + ([editing] if editing else []), one=duplicate)]

    def test_toggle_activation_and_deactivation(self):
        for active in (True, False):
            with self.subTest(active=active), self.database([step(
                    ["SET is_active=%s, updated_at=NOW()", "WHERE id=%s AND user_id=%s"], (active, 42, 7))]):
                data.toggle_budget_item(7, 42, active)

    def test_toggle_missing(self):
        with self.database([step("UPDATE finance_budget_items", (True, 42, 7), count=0)], commits=0):
            with self.assertRaisesRegex(ValueError, "^Poste budgétaire introuvable[.]$"):
                data.toggle_budget_item(7, 42, True)

    def test_move_invalid_direction(self):
        with self.assertRaisesRegex(ValueError, "Direction invalide"):
            data.move_budget_item(7, 2, "left")

    def test_move_up_down_and_equal_order(self):
        for direction, orders, expected in [("up", [10, 20, 30], [(10, 2), (20, 1)]),
                                             ("down", [10, 20, 30], [(30, 2), (20, 3)]),
                                             ("up", [5, 5, 5], [(1, 2), (2, 1)]),
                                             ("down", [5, 5, 5], [(3, 2), (2, 3)])]:
            rows = [dict(id=i, item_type="expense", sort_order=o) for i, o in enumerate(orders, 1)]
            rows.insert(1, dict(id=99, item_type="income", sort_order=15))
            steps = [step(["WHERE user_id=%s", "ORDER BY item_type, sort_order, id", "FOR UPDATE"], (7,), rows=rows)]
            steps += [step("SET sort_order=%s,updated_at=NOW() WHERE id=%s", pair) for pair in expected]
            with self.subTest(direction=direction, orders=orders), self.database(steps):
                data.move_budget_item(7, 2, direction)

    def test_move_edges_and_missing_do_not_commit(self):
        rows = [dict(id=1, item_type="expense", sort_order=10), dict(id=2, item_type="expense", sort_order=20)]
        for identity, direction in [(1, "up"), (2, "down"), (3, "up")]:
            with self.subTest(id=identity), self.database([step("FOR UPDATE", (7,), rows=rows)], commits=0):
                if identity == 3:
                    with self.assertRaisesRegex(ValueError, "Poste budgétaire introuvable"):
                        data.move_budget_item(7, identity, direction)
                else:
                    data.move_budget_item(7, identity, direction)

    def create_recurrence(self, cursor, payload=None, **extra):
        args = dict(transaction_type="expense", fallback_description=" Loyer ", fallback_amount="100.125",
                    fallback_start=START, fallback_end=END, payload=payload)
        args.update(extra)
        return data._create_budget_recurrence_cursor(cursor, 7, **args)

    def test_recurrence_defaults_insert_and_return_id(self):
        cur = ScriptedConnection([step(["INSERT INTO finance_recurrences", "RETURNING id"],
            (7, "expense", "Loyer", D("100.12"), None, None, None, "month", 1, START, END, START,
             "confirm", False, False, False, time(9)), one={"id": 12})])
        with patch.object(data, "_validate_links", return_value=[]) as links, \
             patch.object(data, "_validate_payment_method", return_value=None) as payment:
            self.assertEqual(self.create_recurrence(cur), 12)
            links.assert_called_once_with(cur, 7, None, [])
            payment.assert_called_once_with(cur, 7, None)
        self.assertFalse(cur.steps)
        self.assertEqual(cur.commits, 0)

    def test_recurrence_payload_flags_tags_and_normalized_reminder(self):
        payload = dict(description=" Autre ", amount="20", start_date="2026-10-02", end_date="2026-10-30",
                       frequency_unit="week", frequency_interval=365, confirmation_mode="automatic",
                       category_id=3, tag_ids=[5, 4, 5], payment_method_id="8", note=" test ",
                       budget_excluded=True, bank_programmed=True, reminder_enabled=True, reminder_time=" 08:30:00 ")
        cur = ScriptedConnection([step("INSERT INTO finance_recurrences",
            (7, "expense", "Autre", D("20.00"), 3, 8, "test", "week", 365,
             date(2026, 10, 2), date(2026, 10, 30), date(2026, 10, 2), "automatic", True, True, True, time(8, 30)), one={"id": 12}),
            step("ON CONFLICT DO NOTHING", (12, 4)), step("ON CONFLICT DO NOTHING", (12, 5))])
        with patch.object(data, "_validate_links", return_value=[4, 5]) as links, \
             patch.object(data, "_validate_payment_method", return_value=8) as payment:
            self.assertEqual(self.create_recurrence(cur, payload), 12)
            links.assert_called_once_with(cur, 7, 3, [5, 4, 5])
            payment.assert_called_once_with(cur, 7, "8")
        self.assertFalse(cur.steps)
        self.assertEqual(cur.commits, 0)

    def test_recurrence_zero_interval_uses_default_and_today_fallback(self):
        # Zéro est traité comme une valeur absente dans le code actuel.
        cur = ScriptedConnection([step("INSERT INTO finance_recurrences",
            (7, "expense", "Loyer", D("100.12"), None, None, None, "month", 1, START, None, START,
             "confirm", False, False, False, time(9)), one={"id": 12})])
        class FixedDate(date):
            @classmethod
            def today(cls):
                return START
        with patch.object(data, "date", FixedDate), patch.object(data, "_validate_links", return_value=[]), \
             patch.object(data, "_validate_payment_method", return_value=None):
            self.assertEqual(self.create_recurrence(cur, dict(frequency_interval=0),
                             fallback_start=None, fallback_end=None), 12)
        self.assertFalse(cur.steps)
        self.assertEqual(cur.commits, 0)

    def test_new_recurrence_then_overlap_failure_has_no_explicit_commit(self):
        steps = self.link_steps(self.linked()) + [step("LOWER(TRIM(description))", [7, "income", "Loyer"],
            rows=[dict(id=99, effective_start=START, effective_end=END)])]
        with self.database(steps, commits=0) as conn, \
             patch.object(data, "_create_budget_recurrence_cursor", return_value=12) as create:
            with self.assertRaisesRegex(ValueError, "chevauche"):
                self.save(new_recurrence={"amount": "700"}, allow_overlap=False)
            self.assertIs(create.call_args.args[0], conn)
        # Aucun constat sur le rollback réel : la connexion n'est qu'une simulation.

    def test_recurrence_invalid_fields(self):
        for payload in [dict(frequency_unit="invalid"), dict(frequency_interval=-1),
                        dict(frequency_interval=366), dict(end_date="2026-09-30"),
                        dict(confirmation_mode="invalid"), dict(reminder_time="25:99")]:
            with self.subTest(payload=payload), patch.object(data, "_validate_links", return_value=[]), \
                 patch.object(data, "_validate_payment_method", return_value=None):
                cur = ScriptedConnection([])
                with self.assertRaises(ValueError):
                    self.create_recurrence(cur, payload)
                self.assertEqual(cur.calls, [])

    def test_recurrence_link_validation_errors_propagate(self):
        for helper in ("_validate_links", "_validate_payment_method"):
            with patch.object(data, "_validate_links", return_value=[]), \
                 patch.object(data, "_validate_payment_method", return_value=None), \
                 patch.object(data, helper, side_effect=ValueError("lien invalide")):
                with self.assertRaisesRegex(ValueError, "lien invalide"):
                    self.create_recurrence(ScriptedConnection([]), dict(category_id=3, tag_ids=[4], payment_method_id=8))

    def test_save_invalid_inputs_before_connection(self):
        for values in [dict(item_type="bad"), dict(input_frequency="bad"), dict(description=" "),
                       dict(input_amount="0"), dict(effective_end="2026-09-30"),
                       dict(recurrence_id=12, new_recurrence={"amount": "20"})]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.save(**values)

    def test_save_insert_cleaned_values_and_biweekly_ignores_override(self):
        for frequency in ("monthly", "biweekly"):
            override = D("55") if frequency == "monthly" else None
            with self.subTest(frequency=frequency), self.database(self.insert_steps(frequency=frequency, override=override)):
                self.assertEqual(self.save(input_frequency=frequency, biweekly_override="55"), 42)

    def test_save_update_existing_or_missing(self):
        for count in (1, 0):
            with self.subTest(count=count), self.database([step(
                ["UPDATE finance_budget_items", "is_active=TRUE", "updated_at=NOW()", "WHERE id=%s AND user_id=%s"],
                ("expense", "Loyer", "monthly", D("100.12"), None, "note", None, True, START, END, 42, 7), count=count)], commits=count):
                if count:
                    self.assertEqual(self.save(budget_item_id=42), 42)
                else:
                    with self.assertRaisesRegex(ValueError, "Poste budgétaire introuvable"):
                        self.save(budget_item_id=42)

    def test_save_missing_or_duplicate_recurrence(self):
        with self.database([step("WHERE id=%s AND user_id=%s", (12, 7), one=None)], commits=0):
            with self.assertRaises(ValueError):
                self.save(recurrence_id=12)
        with self.database(self.link_steps(self.linked(), duplicate={"id": 99}), commits=0):
            with self.assertRaisesRegex(ValueError, "déjà liée"):
                self.save(recurrence_id=12)

    def test_save_sync_types_amount_frequency_override_and_end_cleanup(self):
        for unit, interval, frequency, override in [("week", 2, "biweekly", None), ("month", 1, "monthly", D("55"))]:
            steps = self.link_steps(self.linked(frequency_unit=unit, frequency_interval=interval))
            steps += self.insert_steps(kind="income", frequency=frequency, amount=D("700"), override=override, recurrence=12)
            steps += [step(["UPDATE finance_recurrences", "SET end_date=%s", "WHERE id=%s AND user_id=%s"], (END, 12, 7)),
                      step(["DELETE FROM finance_transactions", "WHERE user_id=%s", "recurrence_id=%s",
                            "status='planned'", "transaction_date>%s"], (7, 12, END))]
            with self.subTest(unit=unit), self.database(steps):
                self.assertEqual(self.save(recurrence_id=12, biweekly_override="55"), 42)

    def test_save_sync_end_before_recurrence_rejected(self):
        with self.database([step("FROM finance_recurrences", (12, 7), one=self.linked(start_date=date(2026, 11, 1)))], commits=0):
            with self.assertRaisesRegex(ValueError, "précède le début"):
                self.save(recurrence_id=12)

    def test_save_without_sync_keeps_values_and_does_not_touch_recurrence(self):
        with self.database(self.link_steps(self.linked()) + self.insert_steps(recurrence=12, sync=False)):
            self.assertEqual(self.save(recurrence_id=12, sync_from_recurrence=False), 42)

    def test_save_sync_without_end_does_not_delete_transactions(self):
        steps = self.link_steps(self.linked()) + self.insert_steps(kind="income", frequency="biweekly", amount=D("700"), recurrence=12, end=None)
        steps += [step("UPDATE finance_recurrences", (None, 12, 7))]
        with self.database(steps):
            self.assertEqual(self.save(recurrence_id=12, effective_end=None), 42)

    def test_save_new_recurrence_uses_same_cursor_without_intermediate_commit(self):
        steps = self.link_steps(self.linked()) + self.insert_steps(kind="income", frequency="biweekly", amount=D("700"), recurrence=12)
        steps += [step("UPDATE finance_recurrences", (END, 12, 7)),
                  step("DELETE FROM finance_transactions", (7, 12, END))]
        with self.database(steps) as conn, patch.object(data, "_create_budget_recurrence_cursor", return_value=12) as create:
            self.assertEqual(self.save(new_recurrence={"amount": "700"}), 42)
            create.assert_called_once_with(conn, 7, transaction_type="expense", fallback_description="Loyer",
                                           fallback_amount=D("100.12"), fallback_start=START, fallback_end=END,
                                           payload={"amount": "700"})

    def test_save_overlap_inclusive_boundary_and_edit_exclusion(self):
        for editing in (None, 42):
            steps = [step(["LOWER(TRIM(description))=LOWER(TRIM(%s))", "AND id<>%s" if editing else "WHERE user_id=%s"],
                          [7, "expense", "Loyer"] + ([42] if editing else []),
                          rows=[dict(id=99, effective_start=END, effective_end=None)])]
            with self.subTest(editing=editing), self.database(steps, commits=0):
                with self.assertRaisesRegex(ValueError, "chevauche"):
                    self.save(budget_item_id=editing, allow_overlap=False)

    def test_save_nonoverlap_allows_insert(self):
        steps = [step("LOWER(TRIM(description))", [7, "expense", "Loyer"],
                      rows=[dict(id=99, effective_start=date(2026, 11, 1), effective_end=None)])]
        with self.database(steps + self.insert_steps()):
            self.assertEqual(self.save(allow_overlap=False), 42)

    def test_save_edit_excludes_own_recurrence_link(self):
        steps = self.link_steps(self.linked(), editing=42)
        steps += [step("UPDATE finance_budget_items",
                       ("expense", "Loyer", "monthly", D("100.12"), None, "note", 12, False, START, END, 42, 7))]
        with self.database(steps):
            self.assertEqual(self.save(budget_item_id=42, recurrence_id=12, sync_from_recurrence=False), 42)

    def group(self, **values):
        args = dict(description=" Groupe ", plan_ids=[3, 2, 3], effective_start=START, effective_end=END, note=" note ")
        args.update(values)
        return data.save_financing_budget_group(7, **args)

    def group_checks(self, editing=None, valid=None, conflicts=None):
        return [step(["FROM finance_installment_plans", "WHERE user_id=%s AND id=ANY(%s)"],
                     (7, [2, 3]), rows=valid if valid is not None else [{"id": 2}, {"id": 3}]),
                step(["WHERE group_row.user_id=%s", "link.plan_id=ANY(%s)",
                      "(%s::BIGINT IS NULL OR link.budget_item_id<>%s::BIGINT)"],
                     (7, [2, 3], editing, editing), rows=conflicts)]

    def group_links(self):
        return [step(["INSERT INTO finance_budget_financing_groups", "ON CONFLICT (budget_item_id) DO UPDATE", "updated_at=NOW()"], (42, 7)),
                step("DELETE FROM finance_budget_financing_group_plans WHERE budget_item_id=%s", (42,)),
                step("INSERT INTO finance_budget_financing_group_plans", (42, 2)),
                step("INSERT INTO finance_budget_financing_group_plans", (42, 3))]

    def test_group_empty_or_invalid_dates(self):
        for values in [dict(plan_ids=[]), dict(effective_end="2026-09-30"), dict(effective_start="bad")]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.group(**values)

    def test_group_plan_ownership_and_conflicts(self):
        with self.database(self.group_checks(valid=[{"id": 2}])[:1], commits=0):
            with self.assertRaisesRegex(ValueError, "introuvable"):
                self.group()
        with self.database(self.group_checks(conflicts=[{"description": "Autre"}]), commits=0):
            with self.assertRaisesRegex(ValueError, "Autre"):
                self.group()

    def test_group_create_sorted_unique_plans_and_fallback_minimum(self):
        for amount in (D("0"), D("-5"), D("123")):
            expected = amount if amount > 0 else D("0.01")
            steps = self.group_checks() + [step(["MAX(sort_order)", "item_type='expense'"], (7,), one={"next_order": 9}),
                step(["INSERT INTO finance_budget_items", "'expense'", "'monthly'", "RETURNING id"],
                     (7, "Groupe", expected, "note", 9, START, END), one={"id": 42})] + self.group_links()
            with self.subTest(amount=amount), self.database(steps) as conn, \
                 patch.object(data, "_financing_group_amount_for_month", return_value=amount) as fallback:
                self.assertEqual(self.group(), 42)
                fallback.assert_called_once_with(conn, 7, [2, 3], START)

    def test_group_update_forces_monthly_expense_and_removes_recurrence(self):
        steps = self.group_checks(editing=42) + [step(["UPDATE finance_budget_items", "item_type='expense'",
            "input_frequency='monthly'", "biweekly_override=NULL", "recurrence_id=NULL", "sync_from_recurrence=FALSE",
            "is_active=TRUE", "updated_at=NOW()", "WHERE id=%s AND user_id=%s", "RETURNING id"],
            ("Groupe", D("100"), "note", START, END, 42, 7), one={"id": 42})] + self.group_links()
        with self.database(steps), patch.object(data, "_financing_group_amount_for_month", return_value=D("100")):
            self.assertEqual(self.group(budget_item_id=42), 42)

    def test_group_update_missing(self):
        with self.database(self.group_checks(editing=42) + [step("UPDATE finance_budget_items", one=None)], commits=0), \
             patch.object(data, "_financing_group_amount_for_month", return_value=D("100")):
            with self.assertRaisesRegex(ValueError, "Groupe Budget introuvable"):
                self.group(budget_item_id=42)

    def test_group_delete_scoped_to_user_and_group_returns_rowcount(self):
        for count in (0, 1):
            with self.subTest(count=count), self.database([step(["DELETE FROM finance_budget_items",
                "WHERE id=%s AND user_id=%s", "AND EXISTS", "FROM finance_budget_financing_groups AS group_row",
                "group_row.budget_item_id=finance_budget_items.id"], (42, 7), count=count)]):
                self.assertEqual(data.delete_financing_budget_group(7, "42"), count)


class BudgetWritesArchitectureTests(unittest.TestCase):
    def test_independent_import(self):
        script = """
import importlib.abc
import sys
class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'db', 'finances_data', 'nicegui', 'psycopg'}:
            raise AssertionError(fullname)
sys.meta_path.insert(0, Blocker())
import finances_budget_writes
assert callable(finances_budget_writes.save_budget_item)
"""
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_six_facades_resolve_successively_replaced_dependencies(self):
        contracts = {
            "toggle_budget_item": ["get_connection"],
            "move_budget_item": ["get_connection"],
            "_create_budget_recurrence_cursor": ["_text", "_money", "_optional_date_value",
                "_normalize_reminder_time", "_validate_links", "_validate_payment_method",
                "FREQUENCY_UNITS", "CONFIRMATION_MODES", "date"],
            "save_budget_item": ["get_connection", "TRANSACTION_TYPES", "BUDGET_INPUT_FREQUENCIES",
                "_text", "_money", "_optional_date_value", "_create_budget_recurrence_cursor",
                "_budget_values_from_recurrence", "_periods_overlap"],
            "save_financing_budget_group": ["get_connection", "_text", "_optional_date_value",
                "_financing_group_amount_for_month", "date"],
            "delete_financing_budget_group": ["get_connection"],
        }
        for name, dependencies in contracts.items():
            facade = getattr(data, name)
            signature = inspect.signature(facade)
            values = {key: Mock(name=key) for key in signature.parameters}
            positional = [values[key] for key, value in signature.parameters.items()
                          if value.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD]
            keywords = {key: values[key] for key, value in signature.parameters.items()
                        if value.kind == inspect.Parameter.KEYWORD_ONLY}
            for iteration in range(2):
                with self.subTest(name=name, iteration=iteration), ExitStack() as stack:
                    replacements = {dep: stack.enter_context(patch.object(data, dep)) for dep in dependencies}
                    target = stack.enter_context(patch.object(data._budget_writes, name))
                    self.assertIs(facade(**values), target.return_value)
                    target.assert_called_once_with(*positional, **keywords, **replacements)

    def test_late_dates_validators_and_connection_are_executed(self):
        for day in (START, END):
            class FixedDate(date):
                @classmethod
                def today(cls):
                    return day
            cur = ScriptedConnection([step("INSERT INTO finance_recurrences",
                (7, "expense", "Test", D("20"), None, 8, None, "month", 1, day, None, day,
                 "confirm", False, False, False, time(9)), one={"id": 12}),
                step("ON CONFLICT DO NOTHING", (12, 4))])
            with patch.object(data, "date", FixedDate), \
                 patch.object(data, "_validate_links", return_value=[4]) as links, \
                 patch.object(data, "_validate_payment_method", return_value=8) as payment:
                self.assertEqual(data._create_budget_recurrence_cursor(cur, 7, transaction_type="expense",
                    fallback_description="Test", fallback_amount="20", fallback_start=None,
                    fallback_end=None, payload={}), 12)
                links.assert_called_once_with(cur, 7, None, [])
                payment.assert_called_once_with(cur, 7, None)
            self.assertEqual(cur.steps, [])
            conn = ScriptedConnection([step("UPDATE finance_budget_items", (True, 42, 7))])
            with patch.object(data, "get_connection", return_value=conn) as connect:
                data.toggle_budget_item(7, 42, True)
                connect.assert_called_once_with()
            self.assertEqual(conn.commits, 1)


if __name__ == "__main__":
    unittest.main()

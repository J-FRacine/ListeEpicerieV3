"""Caractérisation Financements sans PostgreSQL ni NiceGUI réels."""
import ast
import importlib
import inspect
import subprocess
import sys
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, Mock, patch

from finances_calculations import analyze_installment_progress
from finances_ui_state import MonthCursor

stub=ModuleType("db"); stub.get_connection=Mock(side_effect=AssertionError("PostgreSQL interdit"))
with patch.dict(sys.modules,{"db":stub}): data=importlib.import_module("finances_data")
ROOT=Path(__file__).resolve().parents[1]


def connection():
    conn=MagicMock();cur=conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
    return conn,cur


def plan(**values):
    row=dict(id=1,is_active=True,plan_type="merchant",provider_name="Marchand",description="Achat",
        original_amount=D("1200"),total_installments=12,completed_installments=2,
        completed_installments_estimated=False,remaining_balance=D("1000"),installment_amount=D("100"),
        annual_interest_rate=D("0"),fees_total=D("0"),frequency_unit="month",frequency_interval=1,
        next_due_date=date(2026,10,15),next_planned_date=None,confirmed_tracked_count=1,
        confirmed_tracked_amount=D("100"),payment_includes_interest=True,base_installment_amount=D("100"),
        calculated_installment_amount=None,payment_method_name="Visa",payment_method_type="credit_card",
        category_full_name="Maison • Achats",tag_ids=[2],tag_names=["Important"])
    row.update(values);return row


class FinancingDataArchitectureTests(unittest.TestCase):
    def test_independent_import_without_database_or_ui_modules(self):
        script = r'''
import builtins
real_import = builtins.__import__
blocked = {"db", "finances_data", "finances", "nicegui", "psycopg"}
def guarded(name, *args, **kwargs):
    if name.split(".")[0] in blocked:
        raise AssertionError("import interdit: " + name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_financing_data
'''
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_historical_signatures_and_five_facades(self):
        expected = {
            "_list_installment_plans_v111": "(user_id, include_inactive=True)",
            "list_installment_plans": "(user_id, include_inactive=True)",
            "get_installment_plan": "(user_id, plan_id)",
            "_project_installment_plan_payments_for_month": "(plan, month_value)",
            "financing_month_summary": "(user_id, month_value)",
        }
        for name, signature in expected.items():
            with self.subTest(name=name):
                self.assertEqual(str(inspect.signature(getattr(data, name))), signature)

        with patch.object(data._financing_data, "_list_installment_plans_v111", return_value="raw") as target:
            self.assertEqual(data._list_installment_plans_v111(7, False), "raw")
            self.assertIs(target.call_args.kwargs["get_connection"], data.get_connection)
            self.assertIs(target.call_args.kwargs["next_date"], data._next_date)
            self.assertIs(target.call_args.kwargs["FREQUENCY_UNITS"], data.FREQUENCY_UNITS)
        with patch.object(data._financing_data, "list_installment_plans", return_value="list") as target:
            self.assertEqual(data.list_installment_plans(7, False), "list")
            self.assertIs(target.call_args.kwargs["_list_installment_plans_v111"], data._list_installment_plans_v111)
        with patch.object(data._financing_data, "get_installment_plan", return_value="one") as target:
            self.assertEqual(data.get_installment_plan(7, 42), "one")
            self.assertIs(target.call_args.kwargs["list_installment_plans"], data.list_installment_plans)
        with patch.object(data._financing_data, "_project_installment_plan_payments_for_month", return_value=(D("1"), 1)) as target:
            self.assertEqual(data._project_installment_plan_payments_for_month({}, "2026-10"), (D("1"), 1))
            target.assert_called_once_with({}, "2026-10")
        with patch.object(data._financing_data, "financing_month_summary", return_value="summary") as target:
            self.assertEqual(data.financing_month_summary(7, "2026-10"), "summary")
            self.assertIs(target.call_args.kwargs["get_connection"], data.get_connection)
            self.assertIs(target.call_args.kwargs["list_installment_plans"], data.list_installment_plans)
            self.assertIs(target.call_args.kwargs["_project_installment_plan_payments_for_month"], data._project_installment_plan_payments_for_month)

    def test_facades_resolve_replaced_dependencies_at_call_time(self):
        first = Mock(return_value=[plan(id=1)])
        second = Mock(return_value=[plan(id=2)])
        with patch.object(data, "_list_installment_plans_v111", first):
            self.assertEqual(data.list_installment_plans(7)[0]["id"], 1)
        with patch.object(data, "_list_installment_plans_v111", second):
            self.assertEqual(data.list_installment_plans(7)[0]["id"], 2)

        current_list = Mock(return_value=[plan(id=42)])
        with patch.object(data, "list_installment_plans", current_list):
            self.assertEqual(data.get_installment_plan(7, 42)["id"], 42)

        conn, cur = connection()
        cur.fetchall.return_value = []
        plans = [plan(id=5)]
        current_project = Mock(return_value=(D("75"), 1))
        with patch.object(data, "get_connection", conn), \
             patch.object(data, "list_installment_plans", return_value=plans) as current_plans, \
             patch.object(data, "_project_installment_plan_payments_for_month", current_project):
            result = data.financing_month_summary(7, "2026-10")
        current_plans.assert_called_once_with(7, include_inactive=False)
        current_project.assert_called_once_with(plans[0], date(2026, 10, 1))
        self.assertEqual(result["payments"], D("75.00"))


class FinancingReadTests(unittest.TestCase):
    def test_real_list_reader_filters_user_and_enriches_progress_dates_balance(self):
        conn,cur=connection();cur.fetchall.return_value=[plan()]
        with patch.object(data,"get_connection",conn): rows=data.list_installment_plans(7,include_inactive=False)
        sql,params=cur.execute.call_args.args
        compact=" ".join(sql.split())
        self.assertIn("WHERE plan.user_id=%s",compact);self.assertIn("(%s OR plan.is_active=TRUE)",compact)
        self.assertEqual(params,(7,False));row=rows[0]
        self.assertEqual(row["display_completed_installments"],3)
        self.assertEqual(row["display_remaining_installments"],9)
        self.assertEqual(row["estimated_remaining_balance"],D("900"))
        self.assertEqual(row["display_next_due_date"],date(2026,10,15))
        self.assertEqual(row["estimated_end_date"],date(2027,6,15))
        self.assertEqual(row["payment_terms_label"],"Mensuel")
        self.assertEqual((row["payment_method_name"],row["category_full_name"],row["tag_names"]),("Visa","Maison • Achats",["Important"]))

    def test_list_interest_enrichment_and_inactive_option(self):
        raw=plan(is_active=False,annual_interest_rate=D("12"),fees_total=D("10"),remaining_balance=D("800"),
                 installment_amount=D("120"),base_installment_amount=D("100"),payment_includes_interest=False,
                 completed_installments_estimated=True,frequency_unit="week",frequency_interval=2)
        with patch.object(data,"_list_installment_plans_v111",return_value=[raw]) as reader:
            row=data.list_installment_plans(7,True)[0]
        reader.assert_called_once_with(7,True)
        self.assertEqual(row["remaining_balance"],D("800"))
        self.assertEqual(row["estimated_interest_per_payment"],D("20.00"))
        self.assertFalse(row["payment_includes_interest"])
        self.assertEqual(row["base_installment_amount"],D("100"))

    def test_get_plan_found_or_missing(self):
        with patch.object(data,"list_installment_plans",return_value=[plan(id=3)]) as reader:
            self.assertEqual(data.get_installment_plan(7,"3")["id"],3)
            with self.assertRaisesRegex(ValueError,"introuvable"):data.get_installment_plan(7,4)
        self.assertEqual(reader.call_count,2)
        reader.assert_called_with(7,include_inactive=True)

    def test_month_summary_materialized_projected_inactive_and_balances(self):
        conn,cur=connection();cur.fetchall.return_value=[dict(installment_plan_id=1,payments=D("100"),payment_count=1),
                                                         dict(installment_plan_id=99,payments=D("50"),payment_count=1)]
        plans=[plan(id=1,estimated_remaining_balance=D("900")),plan(id=2,estimated_remaining_balance=D("400"))]
        with patch.object(data,"get_connection",conn),patch.object(data,"list_installment_plans",return_value=plans) as listing,             patch.object(data,"_project_installment_plan_payments_for_month",return_value=(D("75"),1)) as projected:
            result=data.financing_month_summary(7,"2026-10")
        sql,params=cur.execute.call_args.args
        self.assertEqual(params,(7,date(2026,10,1),date(2026,10,31)))
        self.assertIn("status IN ('planned','confirmed')"," ".join(sql.split()))
        listing.assert_called_once_with(7,include_inactive=False);projected.assert_called_once_with(plans[1],date(2026,10,1))
        self.assertEqual(result,dict(month=date(2026,10,1),payments=D("225.00"),payment_count=3,
                                     remaining_balances=D("1300.00"),active_plan_count=2))

    def test_completed_plan_has_no_projected_payment(self):
        self.assertEqual(data._project_installment_plan_payments_for_month(plan(display_remaining_installments=0),"2026-10"),(D("0.00"),0))
        self.assertEqual(data._project_installment_plan_payments_for_month(plan(is_active=False,display_remaining_installments=2),"2026-10"),(D("0.00"),0))


class FinancingSaveTests(unittest.TestCase):
    def base(self,**values):
        args=dict(user_id=7,plan_type="merchant",provider_name=" Magasin ",description=" Achat ",
                  original_amount="1200",total_installments=12,next_due_date="2026-10-15",payment_method_id=4,
                  completed_installments=2,remaining_balance="1000",installment_amount="100",
                  annual_interest_rate="0",fees_total="0",frequency_unit="month",frequency_interval=1,
                  category_id=3,tag_ids=[5],budget_excluded=True,note=" note ",payment_includes_interest=True)
        args.update(values);return args

    def raw(self,**values):
        args=self.base(**values)
        args.pop("payment_includes_interest")
        return args

    def test_save_zero_interest_passes_fields_and_updates_metadata(self):
        conn,cur=connection();cur.rowcount=1
        with patch.object(data,"_save_installment_plan_v111",return_value=42) as save,patch.object(data,"get_connection",conn):
            self.assertEqual(data.save_installment_plan(**self.base()),42)
        kwargs=save.call_args.kwargs
        self.assertEqual((kwargs["provider_name"],kwargs["description"],kwargs["category_id"],kwargs["tag_ids"]),(" Magasin "," Achat ",3,[5]))
        self.assertTrue(kwargs["budget_excluded"]);self.assertEqual(kwargs["installment_amount"],D("100.00"))
        sql,params=cur.execute.call_args.args;self.assertIn("payment_includes_interest=%s"," ".join(sql.split()))
        self.assertEqual(params,(True,D("100.00"),None,False,42,7));conn.return_value.__enter__.return_value.commit.assert_called_once_with()

    def test_save_interest_excluded_calculates_total_with_fees_and_progress(self):
        progress=dict(estimated_completed_installments=4)
        with patch.object(data,"analyze_installment_progress",return_value=progress) as analysis,             patch.object(data,"_automatic_installment_amount",return_value=D("150")) as calculate,             patch.object(data,"_save_installment_plan_v111",return_value=42) as save,             patch.object(data,"get_connection",connection()[0]):
            data.save_installment_plan(**self.base(annual_interest_rate="12",fees_total="60",
                payment_includes_interest=False,completed_installments=None))
        analysis.assert_called_once();calculate.assert_called_once_with(D("1000.00"),8,D("12.00"),D("60.00"),"month",1)
        self.assertEqual(save.call_args.kwargs["completed_installments"],4)
        self.assertEqual(save.call_args.kwargs["installment_amount"],D("150"))

    def test_save_interest_included_keeps_entered_payment(self):
        with patch.object(data,"_automatic_installment_amount") as calculate,patch.object(data,"_save_installment_plan_v111",return_value=42) as save,             patch.object(data,"get_connection",connection()[0]):
            data.save_installment_plan(**self.base(annual_interest_rate="12",payment_includes_interest=True))
        calculate.assert_not_called();self.assertEqual(save.call_args.kwargs["installment_amount"],D("100.00"))

    def test_real_save_validation_paths(self):
        base=self.raw()
        for changes in [dict(plan_type="bad"),dict(total_installments=0),dict(annual_interest_rate=-1),dict(fees_total=-1),
                        dict(frequency_unit="bad"),dict(frequency_interval=366),dict(completed_installments=13),
                        dict(next_due_date=None,completed_installments=2)]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):data._save_installment_plan_v111(**(base|changes))

    def test_real_insert_validates_links_method_tags_rebuilds_and_commits(self):
        conn,cur=connection();cur.fetchone.side_effect=[dict(method_type="bank"),dict(id=42)]
        with patch.object(data,"get_connection",conn),patch.object(data,"_validate_links",return_value=[5]) as links,             patch.object(data,"_validate_payment_method",return_value=4) as method,             patch.object(data,"_rebuild_installment_transactions") as rebuild:
            result=data._save_installment_plan_v111(**self.raw())
        self.assertEqual(result,42);links.assert_called_once_with(cur,7,3,[5]);method.assert_called_once_with(cur,7,4)
        calls=[(" ".join(c.args[0].split()),c.args[1]) for c in cur.execute.call_args_list]
        self.assertTrue(any("INSERT INTO finance_installment_plans" in sql and params[-3:] == (True,"note",True) for sql,params in calls))
        self.assertTrue(any("INSERT INTO finance_installment_plan_tags" in sql and params==(42,5) for sql,params in calls))
        rebuild.assert_called_once_with(cur,7,42);conn.return_value.__enter__.return_value.commit.assert_called_once_with()

    def test_real_update_missing_plan(self):
        conn,cur=connection();cur.fetchone.return_value=dict(method_type="bank");cur.rowcount=0
        with patch.object(data,"get_connection",conn),patch.object(data,"_validate_links",return_value=[]),             patch.object(data,"_validate_payment_method",return_value=4):
            with self.assertRaisesRegex(ValueError,"introuvable"):data._save_installment_plan_v111(**self.raw(plan_id=42))

    def test_rebuild_preserves_confirmed_and_generates_only_remaining(self):
        conn,cur=connection();cur.fetchone.side_effect=[plan(id=42,total_installments=3,completed_installments=0,
            remaining_balance=D("300"),next_due_date=date(2026,10,1),category_id=3,payment_method_id=4,budget_excluded=True),
            dict(id=101),dict(id=102)];cur.fetchall.side_effect=[[dict(installment_number=1,amount=D("100"))],[dict(tag_id=5)]]
        data._rebuild_installment_transactions(cur,7,42)
        calls=[(" ".join(c.args[0].split()),c.args[1]) for c in cur.execute.call_args_list]
        self.assertTrue(any("status='confirmed'" in sql and sql.startswith("SELECT installment_number") for sql,_ in calls))
        self.assertTrue(any(sql.startswith("DELETE FROM finance_transactions") and "status='planned'" in sql for sql,_ in calls))
        inserts=[params for sql,params in calls if sql.startswith("INSERT INTO finance_transactions")]
        self.assertEqual([x[-1] for x in inserts],[2,3]);self.assertTrue(all(x[-3] is True for x in inserts))

    def test_progress_inconsistency_and_completed_case(self):
        result=analyze_installment_progress(original_amount="1200",remaining_balance="1000",installment_amount="100",
            total_installments=12,completed_installments=8)
        self.assertTrue(result["is_inconsistent"])
        done=analyze_installment_progress(original_amount="1200",remaining_balance="0",installment_amount="100",
            total_installments=12,completed_installments=12)
        self.assertEqual(done["estimated_remaining_installments"],0)


class FinancingMutationTests(unittest.TestCase):
    def test_toggle_active_rebuilds_inactive_deletes_planned(self):
        for active in (True,False):
            conn,cur=connection();cur.rowcount=1
            with patch.object(data,"get_connection",conn),patch.object(data,"_rebuild_installment_transactions") as rebuild:
                data.toggle_installment_plan(7,42,active)
            first=cur.execute.call_args_list[0];self.assertEqual(first.args[1],(active,42,7));self.assertIn("updated_at=NOW()"," ".join(first.args[0].split()))
            if active:rebuild.assert_called_once_with(cur,7,42)
            else:
                self.assertIn("status='planned'"," ".join(cur.execute.call_args_list[1].args[0].split()));rebuild.assert_not_called()

    def test_toggle_missing(self):
        conn,cur=connection();cur.rowcount=0
        with patch.object(data,"get_connection",conn),self.assertRaisesRegex(ValueError,"introuvable"):
            data.toggle_installment_plan(7,42,True)

    def test_delete_locks_removes_planned_detaches_confirmed_then_plan(self):
        conn,cur=connection();cur.fetchone.return_value={"id":42}
        with patch.object(data,"get_connection",conn):data.delete_installment_plan(7,42)
        calls=[(" ".join(c.args[0].split()),c.args[1]) for c in cur.execute.call_args_list]
        self.assertIn("FOR UPDATE",calls[0][0]);self.assertEqual(calls[0][1],(42,7))
        self.assertIn("status='planned'",calls[1][0]);self.assertIn("status='confirmed'",calls[2][0])
        self.assertIn("SET installment_plan_id=NULL",calls[2][0]);self.assertTrue(calls[3][0].startswith("DELETE FROM finance_installment_plans"))
        self.assertTrue(all(params in {(42,7),(7,42)} for _,params in calls));conn.return_value.__enter__.return_value.commit.assert_called_once_with()


class FinancingUiTests(unittest.TestCase):
    def tree(self):return ast.parse("".join(p.read_text(encoding="utf-8") for p in sorted(ROOT.glob("finances_part_*.pyfrag"))))
    def fn(self,name):return next(n for n in ast.walk(self.tree()) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)

    def test_single_cursor_and_targeted_navigation(self):
        tree=self.tree();assign=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="financing_month_state" for t in n.targets)]
        self.assertEqual(len(assign),1);self.assertEqual(ast.unparse(assign[0].value),"MonthCursor()")
        node=self.fn("change_financing_month");namespace=dict(financing_month_state=MonthCursor(date(2026,10,1)),render_financing=Mock())
        exec(compile(ast.Module(body=[node],type_ignores=[]),"<financing nav>","exec"),namespace)
        for offset,reset,expected in [(-1,False,date(2026,9,1)),(1,False,date(2026,10,1)),(0,True,date.today().replace(day=1))]:
            namespace["change_financing_month"](offset,reset);self.assertEqual(namespace["financing_month_state"].value,expected)
        namespace["render_financing"].refresh.assert_called_with()

    def test_ui_callbacks_and_render_contracts(self):
        dialog=ast.unparse(self.fn("installment_plan_dialog"));remove=ast.unparse(self.fn("remove_installment_plan"));render=ast.unparse(self.fn("render_financing"))
        self.assertIn("save_installment_plan",dialog);self.assertIn("delete_installment_plan",remove)
        self.assertIn("toggle_installment_plan",render);self.assertIn("refresh_all()",dialog);self.assertIn("refresh_all()",remove);self.assertIn("refresh_all()",render)
        self.assertIn("calculate_installment_payment",dialog);self.assertIn("analyze_installment_progress",dialog)
        self.assertIn("list_installment_plans(user_id, include_inactive=True)",render)
        self.assertIn("financing_month_summary(user_id, financing_month_state.value)",render)


if __name__=="__main__":unittest.main()

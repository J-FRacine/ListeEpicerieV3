"""Listes Organisation : contrats SQL simulés et vraie logique UI sans navigateur."""
from datetime import date
from decimal import Decimal as D
import inspect
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from finances_organization import build_organization_panel
from test_finances import data
from test_finances_budget_writes import ScriptedConnection, step
from test_finances_financing_ui import SimulatedUi


def categories():
    return [dict(id=9, name='Maison', parent_id=None, parent_name=None, full_name='Maison',
                 is_active=True, category_type='both', dashboard_visible=True),
            dict(id=12, name='Travaux', parent_id=9, parent_name='Maison', full_name='Maison › Travaux',
                 is_active=False, category_type='expense', dashboard_visible=False),
            dict(id=15, name='Salaire', parent_id=None, parent_name=None, full_name='Salaire',
                 is_active=True, category_type='income')]


def tags():
    return [dict(id=21, name='Annuel', is_active=False, dashboard_visible=None),
            dict(id=22, name='Famille', is_active=True, dashboard_visible=True)]


def methods():
    def row(identity, name, kind, **values):
        return dict(id=identity, name=name, method_type=kind, is_active=True, sort_order=identity,
                    statement_day=None, payment_day=None, opening_balance=D('0'),
                    opening_balance_date=None, opening_balance_reconciled=False,
                    credit_limit=None, note=None, transaction_count=0) | values
    return [row(31, 'Banque Z', 'bank', opening_balance=D('100'), opening_balance_reconciled=True),
            row(32, 'Banque A', 'bank', opening_balance=D('-20'), transaction_count=3),
            row(33, 'Marge', 'credit_line', opening_balance=D('40'), credit_limit=D('100'),
                opening_balance_date=date(2026, 9, 8), statement_day=15, payment_day=25),
            row(34, 'Marge inactive', 'credit_line', is_active=False, opening_balance=None),
            row(35, 'Carte inactive', 'credit_card', is_active=False)]


def build_lists():
    ui = SimulatedUi()
    deps = {name: Mock(name=name) for name in inspect.signature(build_organization_panel).parameters}
    deps.update(ui=ui, user_id=7, organization_tab=object(), _balance_money=str,
                PAYMENT_METHOD_TYPES={'bank': 'Compte bancaire', 'credit_line': 'Marge de crédit',
                                      'credit_card': 'Carte de crédit'},
                list_categories=Mock(return_value=categories()), list_tags=Mock(return_value=tags()),
                list_payment_methods=Mock(return_value=methods()))
    return build_organization_panel(**deps), ui, deps


class OrganizationListTests(unittest.TestCase):
    def check_reader(self, name, rows, clauses, order):
        # Résultats fournis par le curseur, pas une réimplémentation du moteur SQL.
        # Vérifier le SQL/paramétrage ET que Python ne retrie ni ne filtre les lignes.
        for inactive, returned in [(False, [r for r in rows if r['is_active']]), (True, rows), (True, [])]:
            with self.subTest(name=name, inactive=inactive, empty=not returned):
                connection = ScriptedConnection([step(clauses, (7, inactive), rows=returned)])
                with patch.object(data, 'get_connection', return_value=connection):
                    result = getattr(data, name)(7, include_inactive=inactive)
                self.assertEqual(result, returned)
                for actual, expected in zip(result, returned):
                    self.assertIs(actual, expected)
                self.assertEqual(connection.calls[0][0].split('ORDER BY', 1)[1].strip(), order)
                self.assertEqual(connection.commits, 0)
                self.assertEqual(connection.steps, [])

    def test_categories_multiple_hierarchy_visibility_empty_and_active_filter(self):
        self.check_reader('list_categories', categories(),
            ['LEFT JOIN finance_categories parent ON parent.id=child.parent_id',
             'parent.name AS parent_name', "ELSE parent.name || ' › ' || child.name",
             'WHERE child.user_id=%s AND (%s OR child.is_active=TRUE)'],
            'COALESCE(parent.name, child.name), CASE WHEN parent.id IS NULL THEN 0 ELSE 1 END, child.name;')

    def test_tags_multiple_optional_visibility_empty_and_active_filter(self):
        self.check_reader('list_tags', tags(),
            ['SELECT * FROM finance_tags', 'WHERE user_id=%s AND (%s OR is_active=TRUE)'], 'name;')

    def test_payment_methods_multiple_types_nulls_counts_and_sql_order(self):
        self.check_reader('list_payment_methods', methods(),
            ['COUNT(transaction.id) AS transaction_count',
             'transaction.payment_method_id = method.id AND transaction.user_id = method.user_id',
             'WHERE method.user_id = %s AND (%s OR method.is_active = TRUE)', 'GROUP BY method.id'],
            'method.is_active DESC, method.sort_order, LOWER(method.name), method.id;')

    def test_bank_reader_stays_in_account_module_and_keeps_banks_margins_order(self):
        for inactive, rows in [(False, methods()[:3]), (True, methods()), (True, [])]:
            with self.subTest(inactive=inactive, empty=not rows), \
                 patch.object(data, 'list_payment_methods', return_value=rows) as reader:
                result = data.list_bank_accounts(7, include_inactive=inactive)
                reader.assert_called_once_with(7, include_inactive=inactive)
                self.assertEqual([r['id'] for r in result], [r['id'] for r in rows if r['id'] != 35])
                self.assertEqual([r['method_type'] for r in result],
                                 ['bank', 'bank', 'credit_line', 'credit_line'][:len(result)])
                for row in result:
                    self.assertTrue(any(row is original for original in rows))

    def test_nonempty_category_tag_rows_preserve_order_flags_and_callback_ids(self):
        _, ui, deps = build_lists()
        labels = [w[1][0] for w in ui.widgets if w[0] == 'label' and w[1]]
        expected = ['Maison', 'Maison › Travaux', 'Salaire', 'Annuel', 'Famille']
        self.assertEqual([x for x in labels if x in expected], expected)
        boxes = [w for w in ui.widgets if w[0] == 'checkbox']
        self.assertEqual([w[2]['value'] for w in boxes], [True, False, True, False, True])
        for i, (service, identity) in enumerate([
            ('set_category_dashboard_visible', 9), ('set_category_dashboard_visible', 12),
            ('set_category_dashboard_visible', 15), ('set_tag_dashboard_visible', 21),
            ('set_tag_dashboard_visible', 22),
        ]):
            boxes[i][2]['on_change'](SimpleNamespace(value=False))
            deps[service].assert_called_with(7, identity, False)
        self.assertEqual(deps['render_dashboard'].refresh.call_count, 5)
        deps['refresh_all'].assert_not_called()

    def test_nonempty_payments_preserve_bank_margin_text_schedule_and_disabled_rows(self):
        _, ui, _ = build_lists()
        labels = [w[1][0] for w in ui.widgets if w[0] == 'label' and w[1]]
        names = [r['name'] for r in methods()]
        self.assertEqual([x for x in labels if x in names], names)
        for text in ['Compte bancaire — 3 transaction(s)', 'Carte de crédit — 0 transaction(s)',
                     'Solde initial : 100 — concilié', 'Solde initial : -20 — à concilier',
                     'Solde utilisé de référence : 40 — limite 100 — disponible 60',
                     'Solde utilisé de référence : 0', 'relevé vers le 15 — paiement vers le 25']:
            self.assertIn(text, labels)
        switches = [w for w in ui.widgets if w[0] == 'switch']
        self.assertEqual([w[2]['value'] for w in switches[-5:]], [True, True, True, False, False])

    def test_payment_edit_buttons_capture_each_row_and_initial_values(self):
        for index in (0, 2, 3):
            with self.subTest(index=index):
                _, ui, _ = build_lists()
                edits = [w for w in ui.widgets if w[0] == 'button' and w[2].get('icon') == 'edit']
                edits[5 + index][2]['on_click']()
                row = methods()[index]
                self.assertEqual(ui.find('input', 'Nom')[3].value, row['name'])
                self.assertEqual(ui.find('select', 'Type')[3].value, row['method_type'])
                self.assertEqual(ui.find('input', 'Date du solde initial')[3].value,
                                 '2026-09-08' if index == 2 else '')
                self.assertEqual(ui.find('number', 'Limite de crédit — facultative')[3].value, row['credit_limit'])
                self.assertEqual(ui.find('number', 'Limite de crédit — facultative')[3].visible,
                                 row['method_type'] == 'credit_line')

    def test_nonempty_mutation_buttons_bind_correct_ids_and_refresh_targets(self):
        _, ui, deps = build_lists()
        switches = [w for w in ui.widgets if w[0] == 'switch']
        for widget, service, identity in [(switches[1], 'toggle_category', 12),
                                           (switches[3], 'toggle_tag', 21),
                                           (switches[-2], 'toggle_payment_method', 34)]:
            widget[2]['on_change'](SimpleNamespace(value=True))
            deps[service].assert_called_once_with(7, identity, True)
        self.assertEqual(deps['refresh_all'].call_count, 3)
        arrows = [w for w in ui.widgets if w[0] == 'button' and w[2].get('icon') == 'keyboard_arrow_up']
        deps['list_payment_methods'].reset_mock()
        arrows[0][2]['on_click']()
        deps['move_payment_method'].assert_called_once_with(7, 31, 'up')
        deps['list_payment_methods'].assert_called_once_with(7, include_inactive=True)
        self.assertEqual(deps['refresh_all'].call_count, 3)

    def test_category_edit_options_keep_roots_exclude_self_and_preserve_parent(self):
        _, ui, deps = build_lists()
        # Le dialogue appelle le lecteur actif; résultats de cette lecture simulés.
        deps['list_categories'].return_value = [categories()[0], categories()[2]]
        edits = [w for w in ui.widgets if w[0] == 'button' and w[2].get('icon') == 'edit']
        edits[1][2]['on_click']()
        deps['list_categories'].assert_called_with(7)
        self.assertEqual(ui.find('select', 'Catégorie parente')[1][0],
                         {None: 'Aucune — catégorie principale', 9: 'Maison', 15: 'Salaire'})
        self.assertEqual(ui.find('select', 'Catégorie parente')[3].value, 9)
        self.assertEqual(ui.find('select', 'Utilisation')[3].value, 'expense')
        edits[0][2]['on_click']()
        self.assertNotIn(9, ui.find('select', 'Catégorie parente')[1][0])

    def test_refresh_nonempty_to_empty_clears_all_three_lists_without_mutation(self):
        handle, ui, deps = build_lists()
        for name in ('list_categories', 'list_tags', 'list_payment_methods'):
            deps[name].return_value = []
            deps[name].reset_mock()
        containers = [w[3] for w in ui.widgets if w[0] == 'column' and w[3].clear.call_count]
        self.assertEqual(len(containers), 3)
        for container in containers:
            container.clear.reset_mock()
        marker = len(ui.widgets)
        handle.refresh()
        for container in containers:
            container.clear.assert_called_once_with()
        self.assertFalse(any(w[0] in ('checkbox', 'switch') for w in ui.widgets[marker:]))
        for name in ('list_categories', 'list_tags', 'list_payment_methods'):
            deps[name].assert_called_once_with(7, include_inactive=True)
        deps['refresh_all'].assert_not_called()


if __name__ == '__main__':
    unittest.main()

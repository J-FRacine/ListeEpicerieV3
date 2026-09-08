"""Caractérisation des vrais corps Conciliation avec SQL et connexions simulés."""
from contextlib import contextmanager
from datetime import date
from decimal import Decimal as D
import unittest
from unittest.mock import patch

from test_finances_budget_writes import ScriptedConnection, data, step

DAY = date(2026, 9, 8)
OPEN = date(2026, 8, 1)
MOVEMENTS = [dict(id=2, transaction_type='expense', amount=D('80')),
             dict(id=3, transaction_type='income', amount=D('30'))]


def method(**values):
    return dict(id=4, name='Visa', method_type='credit_card', opening_balance=D('100'),
                opening_balance_date=OPEN, opening_balance_reconciled=False) | values


class ReconciliationDataTests(unittest.TestCase):
    @contextmanager
    def database(self, steps, commits=0):
        conn = ScriptedConnection(steps)
        with patch.object(data, 'get_connection', return_value=conn) as connect:
            yield conn
        self.assertEqual(conn.steps, [])
        self.assertEqual(conn.commits, commits)
        connect.assert_called_once_with()

    def save(self, **values):
        args = dict(user_id=7, payment_method_id=4, transaction_ids=[3, '2', 2],
                    statement_date=DAY.isoformat(), statement_balance='150',
                    reconciliation_date=DAY, due_date='2026-09-20', note=' note ')
        return data.create_reconciliation_session(**(args | values))

    def prefix(self, current=None, previous=None, rows=MOVEMENTS, ids=None):
        result = [step(['FROM finance_payment_methods', 'WHERE id = %s AND user_id = %s', 'FOR UPDATE'],
                       (4, 7), one=current if current is not None else method()),
                  step(["status = 'completed'", 'ORDER BY statement_date DESC, id DESC', 'LIMIT 1', 'FOR UPDATE'],
                       (7, 4), one=previous)]
        if rows is not None:
            result.append(step(['SELECT id, transaction_type, amount', 'user_id = %s', 'payment_method_id = %s',
                                'id = ANY(%s)', "status = 'confirmed'", "reconciliation_status = 'unreconciled'", 'FOR UPDATE'],
                               (7, 4, [2, 3] if ids is None else ids), rows=rows))
        return result

    def suffix(self, opening=True, ids=(2, 3)):
        result = [step('INSERT INTO finance_reconciliation_sessions', one={'id': 42})]
        result += [step('INSERT INTO finance_reconciliation_session_transactions', (42, i)) for i in ids]
        if ids:
            result.append(step(["reconciliation_status = 'reconciled'", 'reconciliation_date = %s',
                                'reconciliation_session_id = %s', 'WHERE user_id = %s', 'id = ANY(%s)'],
                               (DAY, 42, 7, list(ids))))
        if opening:
            result.append(step(['UPDATE finance_payment_methods', 'opening_balance_reconciled = TRUE',
                                'WHERE id = %s AND user_id = %s'], (4, 7)))
        result.append(step(['DELETE FROM finance_reconciliation_drafts', 'user_id=%s AND payment_method_id=%s'], (7, 4)))
        return result

    def test_predicted_balance_preserves_expense_income_signs_and_pending_opening(self):
        rows = [dict(payment_method_id=i, method_type=kind, opening_balance_pending=D(opening),
                     confirmed_expenses=D('80'), confirmed_incomes=D('30'),
                     planned_expenses=D('20'), planned_incomes=D('5'))
                for i, kind, opening in [(4, 'credit_card', '100'), (5, 'bank', '0')]]
        with self.database([step(['method.opening_balance_reconciled = FALSE',
                                  "transaction.reconciliation_status = 'unreconciled'",
                                  "transaction.status = 'confirmed'", "transaction.status = 'planned'",
                                  "transaction.transaction_type = 'expense'", "transaction.transaction_type = 'income'",
                                  'transaction.user_id = method.user_id', 'transaction.payment_method_id = method.id',
                                  'WHERE method.user_id = %s', "session.status = 'completed'", 'method.is_active DESC'],
                                 (7,), rows=rows)]):
            result = data.payment_predicted_balance_summary(7)
        self.assertEqual([(r['current_balance'], r['planned_impact'], r['predicted_balance']) for r in result],
                         [(D('150'), D('15'), D('165')), (D('50'), D('15'), D('65'))])
        self.assertEqual(result[0]['payment_method_id'], 4)

    def test_unassigned_count_keeps_confirmed_null_method_without_reconciliation_filter(self):
        with self.database([step(["status = 'confirmed'", 'payment_method_id IS NULL', 'user_id = %s'],
                                 (7,), one={'total': '3'})]) as conn:
            self.assertEqual(data.count_unassigned_confirmed_transactions(7), 3)
        self.assertNotIn('reconciliation_status', conn.calls[0][0])

    def test_unreconciled_reader_uses_real_query_with_all_filters(self):
        rows = [dict(id=2)]
        with self.database([step(['t.user_id = %s', 't.status = %s', 't.payment_method_id = %s',
                                  't.reconciliation_status = %s', 't.transaction_date >= %s', 't.transaction_date <= %s',
                                  'LOWER(t.description) LIKE LOWER(%s)', 'LIMIT %s'],
                                 [7, OPEN, DAY, 'confirmed', 4, 'unreconciled', '%achat%', '%achat%', '%achat%', 10000], rows=rows)]):
            self.assertEqual(data.list_unreconciled_transactions(7, 4, OPEN, DAY, ' achat '), rows)

    def test_unassigned_reader_filters_null_methods_then_limits(self):
        rows = [dict(id=1, payment_method_id=4), dict(id=2, payment_method_id=None),
                dict(id=3, payment_method_id=None), dict(id=4, payment_method_id=None)]
        for limit, read_limit in [(2, 1000), (500, 2500)]:
            with self.subTest(limit=limit), patch.object(data, 'list_transactions', return_value=rows) as reader:
                result = data.list_unassigned_transactions(7, 'achat', limit)
                self.assertEqual(result, rows[1:][:limit])
                reader.assert_called_once_with(7, status='confirmed', query='achat', limit=read_limit)

    def test_bulk_assignment_validates_deduplicates_and_commits_once(self):
        with self.database([step(['UPDATE finance_transactions', 'WHERE user_id = %s', 'id = ANY(%s)'],
                                 (9, 7, [2, 3]), count=2)], commits=1) as conn, \
             patch.object(data, '_validate_payment_method', return_value=9) as validate:
            self.assertEqual(data.bulk_assign_payment_method(7, ['3', 2, 3], 4), 2)
            validate.assert_called_once_with(conn, 7, 4)

    def test_bulk_assignment_empty_or_missing_transactions_has_no_commit(self):
        with patch.object(data, 'get_connection') as connect, self.assertRaisesRegex(ValueError, 'au moins'):
            data.bulk_assign_payment_method(7, [], 4)
        connect.assert_not_called()
        with self.database([step('UPDATE finance_transactions', (4, 7, [2, 3]), count=1)]), \
             patch.object(data, '_validate_payment_method', return_value=4), self.assertRaisesRegex(ValueError, 'introuvables'):
            data.bulk_assign_payment_method(7, [2, 3], 4)

    def test_first_session_uses_opening_automatically_and_preserves_net_total(self):
        with self.database(self.prefix() + self.suffix(), commits=1) as conn, \
             patch.object(data, '_validate_payment_method', return_value=4) as validate:
            result = self.save(include_opening_balance=False)
            validate.assert_called_once_with(conn, 7, 4)
        self.assertEqual(result, dict(session_id=42, selected_total=D('50'), reference_balance=D('100'),
                                     expected_balance=D('150'), statement_balance=D('150'), difference=D('0'),
                                     difference_resolution='balanced', closing_reference_balance=D('150'), transaction_count=2))
        self.assertEqual(conn.calls[3][1], (7, 4, DAY, D('150'), date(2026, 9, 20), DAY, 'note', D('50'),
                                           D('0'), True, D('100'), D('100'), OPEN, D('150'), D('150'), 'balanced', None))

    def test_next_session_reference_priority_and_historical_fallbacks(self):
        for previous, reference in [({'closing_reference_balance': D('70'), 'statement_balance': D('90'), 'expected_balance': D('80')}, D('70')),
                                    ({'closing_reference_balance': D('0'), 'statement_balance': D('90')}, D('0')),
                                    ({'closing_reference_balance': None, 'statement_balance': D('90')}, D('90')),
                                    ({'statement_balance': None, 'expected_balance': D('80')}, D('80')),
                                    ({'expected_balance': None}, D('0'))]:
            previous = previous | {'id': 10, 'statement_date': OPEN}
            with self.subTest(previous=previous), self.database(self.prefix(previous=previous) + self.suffix(opening=False), commits=1), \
                 patch.object(data, '_validate_payment_method', return_value=4):
                result = self.save(statement_balance=reference + D('50'))
            self.assertEqual(result['reference_balance'], reference)
            self.assertEqual(result['expected_balance'], reference + D('50'))

    def test_selection_becoming_ineligible_fails_before_insert(self):
        with self.database(self.prefix(rows=MOVEMENTS[:1])), patch.object(data, '_validate_payment_method', return_value=4), \
             self.assertRaisesRegex(ValueError, 'plus disponible'):
            self.save()

    def test_balanced_tolerance_and_blank_statement_force_balanced(self):
        # The public validator rounds the statement to cents; a sub-cent net
        # movement exercises the strict < .01 comparison without patching it.
        for amount, balance, difference in [('79.999', '150', D('.001')), ('80.001', '150', D('-.001')), ('80', None, None)]:
            rows = [MOVEMENTS[0] | {'amount': D(amount)}, MOVEMENTS[1]]
            with self.subTest(amount=amount), self.database(self.prefix(rows=rows) + self.suffix(), commits=1) as conn, \
                 patch.object(data, '_validate_payment_method', return_value=4):
                result = self.save(statement_balance=balance, difference_resolution='carry', difference_explanation=' effacé ')
            self.assertEqual(result['difference_resolution'], 'balanced')
            self.assertEqual(result['difference'], difference)
            self.assertIsNone(conn.calls[3][1][-1])

    def test_nonzero_balanced_and_unexplained_justified_are_rejected(self):
        for resolution, explanation, balance in [('balanced', None, '150.01'), ('balanced', None, '149.99'), ('justified', ' ', '160')]:
            with self.subTest(resolution=resolution, balance=balance), self.database(self.prefix()), \
                 patch.object(data, '_validate_payment_method', return_value=4), self.assertRaises(ValueError):
                self.save(statement_balance=balance, difference_resolution=resolution, difference_explanation=explanation)

    def test_justified_closes_on_statement_carry_on_expected(self):
        for resolution, closing in [('justified', D('160')), ('carry', D('150'))]:
            with self.subTest(resolution=resolution), self.database(self.prefix() + self.suffix(), commits=1) as conn, \
                 patch.object(data, '_validate_payment_method', return_value=4):
                result = self.save(statement_balance='160', difference_resolution=resolution, difference_explanation=' frais ')
            self.assertEqual(result['closing_reference_balance'], closing)
            self.assertEqual(result['difference'], D('10'))
            self.assertEqual(conn.calls[3][1][-3:], (closing, resolution, 'frais'))

    def test_opening_only_and_empty_or_already_reconciled_rejections(self):
        with self.database(self.prefix(rows=None) + self.suffix(ids=()), commits=1), \
             patch.object(data, '_validate_payment_method', return_value=4):
            result = self.save(transaction_ids=[], statement_balance='100')
        self.assertEqual(result['transaction_count'], 0)
        self.assertEqual(result['selected_total'], D('0'))
        for current, include in [(method(opening_balance=D('0')), True), (method(opening_balance_reconciled=True), True),
                                 (method(opening_balance_reconciled=True), False)]:
            with self.subTest(current=current, include=include), self.database(self.prefix(current=current, rows=None)), \
                 patch.object(data, '_validate_payment_method', return_value=4), self.assertRaises(ValueError):
                self.save(transaction_ids=[], include_opening_balance=include)

    def test_invalid_resolution_or_missing_method_cannot_commit(self):
        with patch.object(data, 'get_connection') as connect, self.assertRaisesRegex(ValueError, 'Traitement'):
            self.save(difference_resolution='bad')
        connect.assert_not_called()
        with self.database([step('FROM finance_payment_methods', (4, 7))]), \
             patch.object(data, '_validate_payment_method', return_value=4), self.assertRaisesRegex(ValueError, 'introuvable'):
            self.save()

    def test_session_list_filters_order_counts_and_limit(self):
        for selected, cancelled, params in [(None, True, [7, 100]), (4, False, [7, 4, 12])]:
            with self.subTest(selected=selected), self.database([step(['session.user_id = %s', 'link.is_active = TRUE',
                 'link.is_active = FALSE', 'ORDER BY session.statement_date DESC, session.id DESC', 'LIMIT %s'], params, rows=[{'id': 42}])]) as conn:
                self.assertEqual(data.list_reconciliation_sessions(7, selected, cancelled, params[-1]), [{'id': 42}])
            self.assertEqual("session.status = 'completed'" in conn.calls[0][0], not cancelled)
            self.assertEqual('session.payment_method_id = %s' in conn.calls[0][0], selected is not None)

    def test_session_detail_keeps_active_and_removed_links_and_missing_error(self):
        rows = [dict(id=2, is_active=True), dict(id=3, is_active=False)]
        with self.database([step(['session.id = %s', 'session.user_id = %s'], (42, 7), one={'id': 42}),
                            step(['link.is_active', 'link.removed_at', 'ORDER BY transaction.transaction_date, transaction.id'], (42,), rows=rows)]) as conn:
            self.assertEqual(data.get_reconciliation_session(7, 42), {'session': {'id': 42}, 'transactions': rows})
        self.assertNotIn('is_active = TRUE', conn.calls[1][0])
        with self.database([step('session.user_id = %s', (42, 7))]), self.assertRaisesRegex(ValueError, 'introuvable'):
            data.get_reconciliation_session(7, 42)

    def test_removal_deactivates_link_resets_transaction_and_recalculates_without_deletion(self):
        for reference, resolution, selected, expected, closing in [(D('100'), 'carry', D('20'), D('120'), D('120')),
                (D('100'), 'justified', D('20'), D('120'), D('150')), (None, 'legacy', D('120'), D('120'), D('150'))]:
            steps = [step(['FOR UPDATE', 'WHERE id = %s AND user_id = %s'], (42, 7), one={'status': 'completed'}),
                     step(['SET is_active = FALSE', 'removed_at = NOW()', 'AND is_active = TRUE'], (42, 2)),
                     step(["reconciliation_status = 'unreconciled'", 'reconciliation_date = NULL', 'reconciliation_session_id = NULL'], (2, 7)),
                     step(['FILTER (WHERE link.is_active = TRUE)', "WHEN transaction.transaction_type = 'expense'", 'ELSE -transaction.amount'], (42,),
                          one=dict(transaction_total=D('20'), statement_balance=D('150'), opening_balance_amount=D('100'), reference_balance=reference, difference_resolution=resolution)),
                     step('UPDATE finance_reconciliation_sessions', (selected, expected, D('30'), closing, 42))]
            with self.subTest(reference=reference, resolution=resolution), self.database(steps, commits=1) as conn:
                data.remove_transaction_from_reconciliation_session(7, 42, 2)
            self.assertFalse(any('DELETE' in sql for sql, _ in conn.calls))

    def test_removal_missing_cancelled_or_inactive_link_rejected(self):
        for session in (None, {'status': 'cancelled'}):
            with self.subTest(session=session), self.database([step('FOR UPDATE', (42, 7), one=session)]), self.assertRaises(ValueError):
                data.remove_transaction_from_reconciliation_session(7, 42, 2)
        with self.database([step('FOR UPDATE', (42, 7), one={'status': 'completed'}), step('is_active = TRUE', (42, 2), count=0)]), self.assertRaisesRegex(ValueError, 'plus partie'):
            data.remove_transaction_from_reconciliation_session(7, 42, 2)

    def test_cancel_resets_only_active_transactions_and_restores_opening_when_included(self):
        for included, ids in [(True, [2, 3]), (False, []), (False, [2])]:
            steps = [step('FOR UPDATE', (42, 7), one=dict(status='completed', included_opening_balance=included, payment_method_id=4)),
                     step(['SELECT transaction_id', 'AND is_active = TRUE'], (42,), rows=[{'transaction_id': i} for i in ids])]
            if ids:
                steps += [step(["reconciliation_status = 'unreconciled'", 'reconciliation_date = NULL', 'reconciliation_session_id = NULL'], (7, ids)),
                          step(['SET is_active = FALSE', 'AND is_active = TRUE'], (42,))]
            if included:
                steps.append(step('opening_balance_reconciled = FALSE', (4, 7)))
            steps.append(step(["status = 'cancelled'", 'cancelled_at = NOW()'], (42,)))
            with self.subTest(included=included, ids=ids), self.database(steps, commits=1):
                data.cancel_reconciliation_session(7, 42)

    def test_cancel_missing_or_already_cancelled_does_not_commit(self):
        for session in (None, {'status': 'cancelled'}):
            with self.subTest(session=session), self.database([step('FOR UPDATE', (42, 7), one=session)]), self.assertRaises(ValueError):
                data.cancel_reconciliation_session(7, 42)

    def test_links_reader_preserves_all_history_for_user(self):
        rows = [{'is_active': True}, {'is_active': False}]
        with self.database([step(['session.user_id = %s', 'ORDER BY link.session_id, link.transaction_id'], (7,), rows=rows)]) as conn:
            self.assertEqual(data.list_reconciliation_session_links(7), rows)
        self.assertNotIn('is_active =', conn.calls[0][0])

    def test_reference_summary_first_and_previous_fallbacks(self):
        for previous, expected, source in [(None, D('100'), 'opening_balance'),
                ({'closing_reference_balance': D('0'), 'statement_balance': D('90')}, D('0'), 'previous_statement'),
                ({'closing_reference_balance': D('70'), 'statement_balance': D('90')}, D('70'), 'previous_statement'),
                ({'statement_balance': D('90'), 'expected_balance': D('80')}, D('90'), 'previous_statement'),
                ({'expected_balance': D('80')}, D('80'), 'previous_statement'),
                ({'expected_balance': None}, D('0'), 'previous_statement')]:
            if previous is not None:
                previous |= dict(id=42, statement_date=DAY, difference=D('10'), difference_resolution='carry')
            with self.subTest(previous=previous), self.database([
                    step('WHERE id = %s AND user_id = %s', (4, 7), one=method()),
                    step(["status = 'completed'", 'ORDER BY statement_date DESC, id DESC', 'LIMIT 1'], (7, 4), one=previous)]), \
                 patch.object(data, '_validate_payment_method', return_value=4):
                result = data.reconciliation_reference_summary(7, 4)
            self.assertEqual(result['reference_balance'], expected)
            self.assertEqual(result['source'], source)
            self.assertEqual(result['reference_date'], DAY if previous else OPEN)
            self.assertEqual(result['previous_difference_resolution'], 'carry' if previous else None)

    def test_draft_upsert_preserves_every_field_and_deduplicated_ids(self):
        for sort, expected_sort in [(' DESC ', 'desc'), ('bad', 'asc')]:
            params = (7, 4, DAY, D('150.25'), date(2026, 9, 20), DAY, 'note', True, 'écart', OPEN, DAY, 'achat', expected_sort, [2, 3])
            fields = ['statement_date', 'statement_balance', 'due_date', 'reconciliation_date', 'note', 'include_opening_balance',
                      'difference_explanation', 'filter_start', 'filter_end', 'filter_query', 'sort_direction', 'selected_transaction_ids']
            with self.subTest(sort=sort), self.database([step(['ON CONFLICT (user_id, payment_method_id) DO UPDATE'] +
                    [f'{field}=EXCLUDED.{field}' for field in fields], params, one={'id': 51})], commits=1) as conn, \
                 patch.object(data, '_validate_payment_method', return_value=4) as validate:
                result = data.save_reconciliation_draft(7, 4, [3, '2', 3], statement_date=DAY.isoformat(), statement_balance='150.25',
                    due_date='2026-09-20', reconciliation_date=DAY, note=' note ', include_opening_balance=True,
                    difference_explanation=' écart ', filter_start=OPEN, filter_end=DAY, filter_query=' achat ', sort_direction=sort)
                validate.assert_called_once_with(conn, 7, 4)
            self.assertEqual(result, 51)
            self.assertEqual(len(conn.calls), 1)

    def test_draft_empty_selection_and_invalid_method_or_fields(self):
        with self.database([step('INSERT INTO finance_reconciliation_drafts',
                                (7, 4, None, None, None, None, None, False, None, None, None, None, 'asc', []), one={'id': 51})], commits=1), \
             patch.object(data, '_validate_payment_method', return_value=4):
            self.assertEqual(data.save_reconciliation_draft(7, 4, []), 51)
        with self.database([]), patch.object(data, '_validate_payment_method', return_value=None), self.assertRaisesRegex(ValueError, 'Choisissez'):
            data.save_reconciliation_draft(7, None, [])
        for kwargs in [dict(statement_date='bad'), dict(statement_balance='bad'), dict(note='x' * 1001)]:
            with self.subTest(kwargs=kwargs), patch.object(data, 'get_connection') as connect, self.assertRaises(ValueError):
                data.save_reconciliation_draft(7, 4, [], **kwargs)
            connect.assert_not_called()

    def test_draft_readers_and_delete_filter_by_user_and_method(self):
        row = dict(id=51, selected_transaction_ids=[2, 3], statement_date=DAY, note='note')
        with self.database([step(['draft.user_id=%s', 'ORDER BY draft.updated_at DESC, draft.id DESC'], (7,), rows=[row])]):
            self.assertEqual(data.list_reconciliation_drafts(7), [row])
        for value in (row, None):
            with self.subTest(row=value), self.database([step('draft.user_id=%s AND draft.payment_method_id=%s', (7, 4), one=value)]):
                self.assertEqual(data.get_reconciliation_draft(7, '4'), value)
        for count in (0, 1):
            with self.subTest(count=count), self.database([step(['DELETE FROM finance_reconciliation_drafts', 'user_id=%s AND payment_method_id=%s'], (7, 4), count=count)], commits=1):
                self.assertEqual(data.delete_reconciliation_draft(7, '4'), count)
        with patch.object(data, 'get_connection') as connect:
            for value in (None, ''):
                self.assertIsNone(data.get_reconciliation_draft(7, value))
                self.assertEqual(data.delete_reconciliation_draft(7, value), 0)
            connect.assert_not_called()


if __name__ == '__main__':
    unittest.main()

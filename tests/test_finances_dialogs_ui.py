"""Dialogues partagés : paramètres, erreurs, ordre des actions et raccordements."""
import ast
from datetime import date
from decimal import Decimal as D
import inspect
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock

from finances_dialogs import FinanceDialogsHandle, build_finance_dialogs
from test_finances_financing_ui import SimulatedUi

ROOT = Path(__file__).resolve().parents[1]


def build():
    ui = SimulatedUi()
    deps = {name: Mock(name=name) for name in inspect.signature(build_finance_dialogs).parameters}
    deps.update(ui=ui, TRANSACTION_TYPES={'expense': 'Dépense', 'income': 'Revenu'},
                TRANSACTION_STATUSES={'planned': 'À confirmer', 'confirmed': 'Confirmée'})
    deps['_category_options'].return_value = {8: 'Maison'}
    deps['_tag_options'].return_value = {9: 'Fixe'}
    deps['_payment_options'].return_value = {1: 'Banque', 2: 'Carte'}
    methods = [dict(id=1, name='Banque', method_type='bank', is_active=True),
               dict(id=2, name='Carte', method_type='credit_card', is_active=True),
               dict(id=3, name='Ancienne banque', method_type='bank', is_active=False),
               dict(id=4, name='Ancienne carte', method_type='credit_card', is_active=False),
               dict(id=5, name='Marge', method_type='credit_line', is_active=True)]
    deps['list_payment_methods'].side_effect = lambda user_id, include_inactive=False: [
        row for row in methods if include_inactive or row['is_active']]
    return build_finance_dialogs(**deps), ui, deps


def transaction():
    return dict(id=42, transaction_type='income', amount=D('123.45'), transaction_date=date(2026, 9, 1),
                description='Salaire', category_id=8, payment_method_id=2, tag_ids=[9],
                budget_excluded=True, status='planned', bank_programmed=True, reminder_enabled=True,
                reminder_time='07:30:00', reconciliation_status='reconciled',
                reconciliation_date=date(2026, 9, 2), note='Note transaction')


def transfer():
    return dict(id=43, source_payment_method_id=3, destination_payment_method_id=4, amount=D('75.25'),
                source_date=date(2026, 9, 3), destination_date=date(2026, 9, 5), description='Paiement modifié',
                status='confirmed', bank_programmed=True, reminder_enabled=True,
                reminder_time='08:15:00', note='Note paiement')


def value(ui, kind, label):
    return ui.find(kind, label)[3].value


def success_order(ui, deps, service, saved, button, message, test):
    events = []
    deps[service].side_effect = lambda **kwargs: events.append('save')
    ui.find('dialog')[3].close.side_effect = lambda: events.append('close')
    ui.notify.side_effect = lambda *args, **kwargs: events.append('notify')
    saved.side_effect = lambda: events.append('saved')
    ui.click(button)
    test.assertEqual(events, ['save', 'close', 'notify', 'saved'])
    ui.notify.assert_called_once_with(message, type='positive')


class DialogUiTests(unittest.TestCase):
    def test_handle_and_builder_are_lazy_and_signatures_forward_all_arguments(self):
        handle, ui, deps = build()
        self.assertIsInstance(handle, FinanceDialogsHandle)
        self.assertEqual(ui.widgets, [])
        for dep in deps.values():
            if isinstance(dep, Mock):
                dep.assert_not_called()
        on_transaction, on_card = Mock(), Mock()
        handle.on_transaction, handle.on_card_payment = on_transaction, on_card
        saved = Mock()
        handle.transaction(7, saved, transaction={'id': 42}, default_payment_method_id=1)
        on_transaction.assert_called_once_with(7, saved, {'id': 42}, 1)
        handle.card_payment(7, saved, transfer={'id': 43}, prefill={'amount': 20})
        on_card.assert_called_once_with(7, saved, {'id': 43}, {'amount': 20})
        saved.assert_not_called()
        self.assertEqual(list(inspect.signature(handle.transaction).parameters),
                         ['user_id', 'on_saved', 'transaction', 'default_payment_method_id'])
        self.assertEqual(list(inspect.signature(handle.card_payment).parameters),
                         ['user_id', 'on_saved', 'transfer', 'prefill'])

    def test_new_transaction_defaults_and_default_payment_method(self):
        for payment in (None, 1):
            with self.subTest(payment=payment):
                handle, ui, deps = build()
                saved = Mock()
                handle.transaction(7, saved, default_payment_method_id=payment)
                ui.find('label', 'Nouvelle transaction')
                self.assertEqual(ui.find('toggle')[3].value, 'expense')
                self.assertEqual(value(ui, 'input', 'Date'), date.today().isoformat())
                self.assertEqual(value(ui, 'select', 'Mode de paiement'), payment)
                self.assertEqual(value(ui, 'select', 'Statut de transaction'), 'confirmed')
                self.assertEqual(value(ui, 'select', 'Étiquettes'), [])
                self.assertEqual(value(ui, 'input', 'Heure du rappel'), '09:00')
                self.assertTrue(all(w[3].value is False for w in ui.widgets if w[0] == 'checkbox'))
                ui.find('number', 'Montant')[3].value = 25
                ui.find('input', 'Description')[3].value = 'Nouvelle'
                ui.find('input', 'Date')[3].value = '2026-09-10'
                success_order(ui, deps, 'save_transaction', saved, 'Enregistrer', 'Transaction enregistrée.', self)
                deps['save_transaction'].assert_called_once_with(user_id=7, transaction_id=None,
                    transaction_date='2026-09-10', transaction_type='expense', amount=25,
                    description='Nouvelle', category_id=None, tag_ids=[], payment_method_id=payment, note='',
                    status='confirmed', reconciliation_status='unreconciled', reconciliation_date=None,
                    budget_excluded=False, bank_programmed=False, reminder_enabled=False, reminder_time='09:00')

    def test_edit_transaction_preserves_exact_fields_over_payment_default(self):
        handle, ui, deps = build()
        saved = Mock()
        handle.transaction(7, saved, transaction(), default_payment_method_id=1)
        ui.find('label', 'Modifier la transaction')
        self.assertEqual(value(ui, 'select', 'Mode de paiement'), 2)
        success_order(ui, deps, 'save_transaction', saved, 'Enregistrer', 'Transaction enregistrée.', self)
        deps['save_transaction'].assert_called_once_with(user_id=7, transaction_id=42,
            transaction_date='2026-09-01', transaction_type='income', amount=D('123.45'), description='Salaire',
            category_id=8, tag_ids=[9], payment_method_id=2, note='Note transaction', status='planned',
            reconciliation_status='reconciled', reconciliation_date='2026-09-02', budget_excluded=True,
            bank_programmed=True, reminder_enabled=True, reminder_time='07:30')

    def test_transaction_error_keeps_dialog_open_without_on_saved(self):
        handle, ui, deps = build()
        saved = Mock()
        handle.transaction(7, saved, transaction())
        deps['save_transaction'].side_effect = ValueError('refus')
        ui.click('Enregistrer')
        ui.find('dialog')[3].close.assert_not_called()
        saved.assert_not_called()
        ui.notify.assert_called_once_with('refus', type='warning')

    def test_new_card_payment_defaults_and_save_fallbacks(self):
        handle, ui, deps = build()
        saved = Mock()
        handle.card_payment(7, saved)
        self.assertEqual(value(ui, 'select', 'Compte bancaire de départ'), 1)
        self.assertEqual(value(ui, 'select', 'Carte de crédit à payer'), 2)
        self.assertEqual(value(ui, 'select', 'Statut'), 'planned')
        self.assertEqual(value(ui, 'input', 'Date du débit bancaire'), date.today().isoformat())
        self.assertEqual(value(ui, 'input', 'Date de réception sur la carte'), date.today().isoformat())
        self.assertEqual(ui.find('select', 'Compte bancaire de départ')[1][0], {1: 'Banque'})
        self.assertEqual(ui.find('select', 'Carte de crédit à payer')[1][0], {2: 'Carte'})
        self.assertEqual(deps['list_payment_methods'].call_count, 2)
        deps['list_payment_methods'].assert_called_with(7, include_inactive=False)
        ui.find('number', 'Montant du paiement')[3].value = 50
        ui.find('input', 'Date du débit bancaire')[3].value = '2026-09-10'
        ui.find('input', 'Date de réception sur la carte')[3].value = ''
        ui.find('input', 'Heure du rappel')[3].value = ''
        success_order(ui, deps, 'save_card_payment_transfer', saved, 'Enregistrer le paiement', 'Paiement de carte enregistré.', self)
        deps['save_card_payment_transfer'].assert_called_once_with(user_id=7, transfer_id=None,
            source_payment_method_id=1, destination_payment_method_id=2, amount=50, source_date='2026-09-10',
            destination_date='2026-09-10', description='Paiement de carte', note='', status='planned',
            bank_programmed=False, reminder_enabled=False, reminder_time='09:00')

    def test_card_prefill_valid_and_unavailable_source_choices(self):
        for source, expected in [(1, 1), (99, None)]:
            with self.subTest(source=source):
                handle, ui, deps = build()
                saved = Mock()
                prefill = dict(source_payment_method_id=source, destination_payment_method_id=2, amount=84,
                               payment_date='2026-11-02', description='Relevé', note='Prérempli',
                               status='confirmed', bank_programmed=True)
                handle.card_payment(7, saved, prefill=prefill)
                self.assertEqual(value(ui, 'select', 'Compte bancaire de départ'), expected)
                ui.click('Enregistrer le paiement')
                deps['save_card_payment_transfer'].assert_called_once_with(user_id=7, transfer_id=None,
                    source_payment_method_id=expected, destination_payment_method_id=2, amount=84,
                    source_date='2026-11-02', destination_date='2026-11-02', description='Relevé', note='Prérempli',
                    status='confirmed', bank_programmed=True, reminder_enabled=False, reminder_time='09:00')

    def test_edit_card_includes_inactive_methods_and_transfer_overrides_prefill(self):
        handle, ui, deps = build()
        saved = Mock()
        handle.card_payment(7, saved, transfer(), prefill={'amount': 999, 'payment_date': '2020-01-01'})
        ui.find('label', 'Modifier le paiement de carte')
        self.assertEqual(ui.find('select', 'Compte bancaire de départ')[1][0], {1: 'Banque', 3: 'Ancienne banque — désactivé'})
        self.assertEqual(ui.find('select', 'Carte de crédit à payer')[1][0], {2: 'Carte', 4: 'Ancienne carte — désactivée'})
        deps['list_payment_methods'].assert_called_with(7, include_inactive=True)
        success_order(ui, deps, 'save_card_payment_transfer', saved, 'Enregistrer le paiement', 'Paiement de carte enregistré.', self)
        deps['save_card_payment_transfer'].assert_called_once_with(user_id=7, transfer_id=43,
            source_payment_method_id=3, destination_payment_method_id=4, amount=D('75.25'),
            source_date='2026-09-03', destination_date='2026-09-05', description='Paiement modifié',
            note='Note paiement', status='confirmed', bank_programmed=True, reminder_enabled=True, reminder_time='08:15')

    def test_missing_bank_or_card_only_allows_closing(self):
        for kind, missing in [('bank', 'une Carte de crédit'), ('credit_card', 'un Compte bancaire')]:
            with self.subTest(kind=kind):
                handle, ui, deps = build()
                deps['list_payment_methods'].side_effect = None
                deps['list_payment_methods'].return_value = [dict(id=1, name='Unique', method_type=kind, is_active=True)]
                saved = Mock()
                handle.card_payment(7, saved)
                ui.find('label', f'Configurez d’abord {missing} dans Organisation > Modes de paiement.')
                self.assertFalse(any(w[0] == 'button' and w[1] == ('Enregistrer le paiement',) for w in ui.widgets))
                ui.click('Fermer')
                ui.find('dialog')[3].close.assert_called_once_with()
                deps['save_card_payment_transfer'].assert_not_called()
                saved.assert_not_called()

    def test_card_error_does_not_close_or_call_on_saved(self):
        handle, ui, deps = build()
        saved = Mock()
        handle.card_payment(7, saved)
        deps['save_card_payment_transfer'].side_effect = ValueError('refus')
        ui.click('Enregistrer le paiement')
        ui.find('dialog')[3].close.assert_not_called()
        saved.assert_not_called()
        ui.notify.assert_called_once_with('refus', type='warning')

    def test_rounding_and_cancel_preserve_existing_behavior(self):
        handle, ui, deps = build()
        saved = Mock()
        handle.card_payment(7, saved)
        ui.click('Arrondir au dollar supérieur')
        ui.notify.assert_called_with('Indiquez d’abord un montant.', type='warning')
        ui.find('number', 'Montant du paiement')[3].value = 'invalide'
        ui.click('Arrondir au dollar supérieur')
        ui.notify.assert_called_with('Le montant est invalide.', type='warning')
        ui.find('number', 'Montant du paiement')[3].value = 75.25
        ui.click('Arrondir au dollar supérieur')
        self.assertEqual(value(ui, 'number', 'Montant du paiement'), 76.0)
        ui.click('Annuler')
        ui.find('dialog')[3].close.assert_called_once_with()
        deps['save_card_payment_transfer'].assert_not_called()
        saved.assert_not_called()


class DialogArchitectureTests(unittest.TestCase):
    def test_independent_import_and_standard_dependencies_only(self):
        script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'finances', 'finances_data', 'db', 'nicegui', 'psycopg'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_dialogs
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tree = ast.parse((ROOT / 'finances_dialogs.py').read_text(encoding='utf-8'))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.ImportFrom, ast.Import))]
        self.assertTrue(all(isinstance(n, ast.ImportFrom) for n in imports))
        self.assertEqual({n.module for n in imports}, {'dataclasses', 'datetime', 'decimal', 'typing'})

    def test_all_parent_consumers_forward_lazily_to_current_handle(self):
        tree = ast.parse(''.join(p.read_text(encoding='utf-8') for p in sorted(ROOT.glob('finances_part_*.pyfrag'))))
        definitions = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertTrue({'_transaction_dialog', '_card_payment_dialog', '_bank_payment_source_options', '_credit_card_options'}.isdisjoint(definitions | names))
        lambdas = [n for n in ast.walk(tree) if isinstance(n, ast.Lambda) and isinstance(n.body, ast.Call)
                   and isinstance(n.body.func, ast.Attribute) and isinstance(n.body.func.value, ast.Name)
                   and n.body.func.value.id == 'dialogs']
        self.assertEqual(len(lambdas), 12)
        for node in lambdas:
            env = {}
            callback = eval(compile(ast.Expression(body=node), '<callback>', 'eval'), env)
            for _ in range(2):
                env.update(dialogs=Mock(), user_id=7, refresh_all=Mock())
                target = getattr(env['dialogs'], node.body.func.attr)
                target.assert_not_called()
                if node.args.vararg:
                    callback(7, sample=True)
                    target.assert_called_once_with(7, sample=True)
                else:
                    callback()
                    target.assert_called_once_with(7, env['refresh_all'])
                env['refresh_all'].assert_not_called()

    def test_parent_builder_only_injects_late_services(self):
        tree = ast.parse(''.join(p.read_text(encoding='utf-8') for p in sorted(ROOT.glob('finances_part_*.pyfrag'))))
        assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'dialogs' for t in n.targets))
        env = {name: Mock() for name in ('ui', 'TRANSACTION_TYPES', 'TRANSACTION_STATUSES', 'build_finance_dialogs')}
        exec(compile(ast.Module(body=[assignment], type_ignores=[]), '<builder>', 'exec'), env)
        kwargs = env['build_finance_dialogs'].call_args.kwargs
        for name in ('save_transaction', 'save_card_payment_transfer', 'list_payment_methods'):
            env[name] = Mock()
            kwargs[name](7, example=True)
            env[name].assert_called_once_with(7, example=True)


if __name__ == '__main__':
    unittest.main()

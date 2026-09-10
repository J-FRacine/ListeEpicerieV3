"""Contrats de l'interface Importer/Exporter sans serveur ni base de données."""
import ast
import asyncio
from datetime import date
import inspect
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from finances_import_export import build_import_export_panel
from test_finances_financing_ui import SimulatedUi

ROOT = Path(__file__).resolve().parents[1]


def row(index=1, **values):
    return dict(description=f'Achat {index}', transaction_date=date(2026, 9, 1),
                transaction_type='expense', amount=25, category_name='Maison',
                tag_names=['Fixe'], payment_method_name='Banque') | values


def build():
    ui = SimulatedUi()
    deps = {name: Mock(name=name) for name in inspect.signature(build_import_export_panel).parameters}
    deps.update(ui=ui, user_id=7, export_tab=object(), _signed=lambda amount, kind: f'{kind}:{amount}')
    deps['prepare_finance_import'].return_value = dict(
        format='JF Apps', rows=[row()], valid_rows=1, already_imported=2, possible_duplicates=3,
        categories=['Maison'], tags=['Fixe'], payment_methods=['Banque'], errors=[], budget_items=[{'id': 8}])
    deps['import_finance_rows'].return_value = dict(imported=1, skipped=2, categories_created=3,
        tags_created=4, payment_methods_created=5, budget_items_imported=6, failures=[])
    result = build_import_export_panel(**deps)
    return result, ui, deps


def upload(ui, filename='import.csv'):
    event = SimpleNamespace(file=SimpleNamespace(name=filename, text=AsyncMock(return_value='contenu')))
    asyncio.run(ui.find('upload')[2]['on_upload'](event))
    return event


def labels(ui):
    return [args[0] for kind, args, _, _ in ui.widgets if kind == 'label' and args]


class ImportExportUiTests(unittest.TestCase):
    def test_build_is_lazy_and_keeps_upload_and_export_controls(self):
        result, ui, deps = build()
        self.assertIsNone(result)
        control = ui.find('upload')
        self.assertEqual(control[2]['label'], 'Choisir un fichier CSV ou JSON')
        self.assertIs(control[2]['auto_upload'], True)
        self.assertEqual(control[2]['max_files'], 1)
        control[3].props.assert_called_once_with('accept=.csv,.json,text/csv,application/json')
        ui.find('button', 'Exporter CSV')
        ui.find('button', 'Exporter JSON')
        for name in ('prepare_finance_import', 'import_finance_rows', 'export_finances', 'refresh_all'):
            deps[name].assert_not_called()

    def test_upload_formats_preview_counts_and_cancel_without_import(self):
        for filename, format_name in [('spendee.csv', 'Spendee'), ('jf.csv', 'JF Apps'), ('backup.json', 'JSON')]:
            with self.subTest(filename=filename):
                _, ui, deps = build()
                deps['prepare_finance_import'].return_value['format'] = format_name
                event = upload(ui, filename)
                event.file.text.assert_awaited_once_with()
                deps['prepare_finance_import'].assert_called_once_with(7, filename, 'contenu')
                for text in ('Prévisualisation de l’importation', f'Format reconnu : {format_name}',
                             'Valides', '1', 'Déjà importées', '2', 'Doublons possibles', '3',
                             'Catégories détectées : 1 — Étiquettes détectées : 1 — Modes de paiement détectés : 1 — Postes de budget détectés : 1',
                             'Achat 1', '01/09/2026 — Maison — Fixe — Banque', 'expense:25'):
                    self.assertIn(text, labels(ui))
                self.assertIs(ui.find('checkbox')[3].value, True)
                ui.find('dialog')[3].open.assert_called_once_with()
                deps['import_finance_rows'].assert_not_called()
                ui.click('Annuler')
                deps['import_finance_rows'].assert_not_called()
                deps['refresh_all'].assert_not_called()
                ui.find('dialog')[3].close.assert_called_once_with()

    def test_preview_limits_and_already_imported_filter(self):
        _, ui, deps = build()
        preview = deps['prepare_finance_import'].return_value
        preview['rows'] = [row(99, duplicate_reason='already_imported')] + [row(i) for i in range(10)]
        preview['errors'] = [f'Erreur {i}' for i in range(32)]
        upload(ui)
        ui.find('expansion', 'Erreurs ignorées (32)')
        text = labels(ui)
        for i in range(8):
            self.assertIn(f'Achat {i}', text)
        for i in (8, 9, 99):
            self.assertNotIn(f'Achat {i}', text)
        self.assertIn('Erreur 29', text)
        self.assertNotIn('Erreur 30', text)

    def test_read_or_preparation_error_does_not_open_dialog(self):
        for fails in ('read', 'prepare'):
            with self.subTest(fails=fails):
                _, ui, deps = build()
                event = SimpleNamespace(file=SimpleNamespace(name='test.csv', text=AsyncMock(return_value='texte')))
                if fails == 'read':
                    event.file.text.side_effect = ValueError('refus')
                else:
                    deps['prepare_finance_import'].side_effect = ValueError('refus')
                asyncio.run(ui.find('upload')[2]['on_upload'](event))
                self.assertFalse(any(kind == 'dialog' for kind, *_ in ui.widgets))
                ui.notify.assert_called_once_with('refus', type='negative')
                deps['import_finance_rows'].assert_not_called()
                deps['refresh_all'].assert_not_called()
                if fails == 'read':
                    deps['prepare_finance_import'].assert_not_called()

    def test_confirm_passes_duplicate_option_and_budget_items_then_refreshes(self):
        for skip, budgets in [(True, [{'id': 8}]), (False, None)]:
            with self.subTest(skip=skip):
                _, ui, deps = build()
                preview = deps['prepare_finance_import'].return_value
                if budgets is None:
                    preview.pop('budget_items')
                upload(ui)
                ui.find('checkbox')[3].value = skip
                events = []
                result = deps['import_finance_rows'].return_value
                deps['import_finance_rows'].side_effect = lambda *args, **kwargs: events.append('import') or result
                ui.find('dialog')[3].close.side_effect = lambda: events.append('close')
                ui.notify.side_effect = lambda *args, **kwargs: events.append('notify')
                deps['refresh_all'].side_effect = lambda: events.append('refresh')
                ui.click('Importer')
                deps['import_finance_rows'].assert_called_once_with(7, preview['rows'],
                    skip_possible_duplicates=skip, budget_items=budgets or [])
                self.assertEqual(events, ['import', 'close', 'notify', 'refresh'])
                ui.notify.assert_called_once_with('Importation terminée : 1 ajoutée(s), 2 ignorée(s), 3 catégorie(s) créée(s), 4 étiquette(s) créée(s), 5 mode(s) de paiement créé(s), 6 poste(s) de budget restauré(s).',
                                                  type='positive', timeout=10000)

    def test_import_error_keeps_dialog_open_without_refresh(self):
        _, ui, deps = build()
        upload(ui)
        deps['import_finance_rows'].side_effect = ValueError('refus')
        ui.click('Importer')
        ui.notify.assert_called_once_with('refus', type='negative')
        ui.find('dialog')[3].close.assert_not_called()
        deps['refresh_all'].assert_not_called()

    def test_partial_import_warns_and_refreshes(self):
        _, ui, deps = build()
        result = deps['import_finance_rows'].return_value
        result['failures'] = ['ligne 1', 'ligne 2']
        result.pop('budget_items_imported')
        upload(ui)
        ui.click('Importer')
        self.assertIn('0 poste(s) de budget restauré(s).', ui.notify.call_args_list[0].args[0])
        ui.notify.assert_called_with('2 ligne(s) n’ont pas pu être importées.', type='warning', timeout=10000)
        deps['refresh_all'].assert_called_once_with()

    def test_csv_and_json_export_bytes_names_and_download(self):
        for kind, content in [('csv', b'csv-data'), ('json', b'{"data": []}')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                _, ui, deps = build()
                deps['export_finances'].return_value = (b'csv-data', b'{"data": []}')
                with patch('finances_import_export.tempfile.gettempdir', return_value=folder):
                    ui.click(f'Exporter {kind.upper()}')
                filename = f'finances_{date.today().isoformat()}.{kind}'
                path = Path(folder) / f'7_{filename}'
                self.assertEqual(path.read_bytes(), content)
                download = ui.find('download')
                self.assertEqual(download[1], (str(path),))
                self.assertEqual(download[2], {'filename': filename})
                deps['export_finances'].assert_called_once_with(7)
                deps['refresh_all'].assert_not_called()

    def test_export_service_and_file_errors_are_reported(self):
        for fails in ('export', 'write'):
            with self.subTest(fails=fails):
                _, ui, deps = build()
                deps['export_finances'].return_value = (b'csv', b'json')
                if fails == 'export':
                    deps['export_finances'].side_effect = ValueError('refus')
                with patch('finances_import_export.Path.write_bytes', side_effect=OSError('refus')):
                    ui.click('Exporter CSV')
                ui.notify.assert_called_once_with('refus', type='negative')
                self.assertFalse(any(kind == 'download' for kind, *_ in ui.widgets))
                deps['refresh_all'].assert_not_called()


class ImportExportArchitectureTests(unittest.TestCase):
    def test_independent_import_and_standard_imports(self):
        script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'finances', 'finances_data', 'db', 'nicegui', 'psycopg'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_import_export
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tree = ast.parse((ROOT / 'finances_import_export.py').read_text(encoding='utf-8'))
        imports = {n.module if isinstance(n, ast.ImportFrom) else n.names[0].name
                   for n in ast.walk(tree) if isinstance(n, (ast.ImportFrom, ast.Import))}
        self.assertEqual(imports, {'datetime', 'pathlib', 'tempfile'})

    def test_parent_lazy_injection_and_full_block_removed(self):
        tree = ast.parse((ROOT / "finances.py").read_text(encoding="utf-8"))
        call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == 'build_import_export_panel')
        env = {name: Mock() for name in ('ui', 'user_id', 'export_tab', 'build_import_export_panel')}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.Expr(value=call)], type_ignores=[])), '<parent>', 'exec'), env)
        kwargs = env['build_import_export_panel'].call_args.kwargs
        self.assertEqual(set(kwargs), set(inspect.signature(build_import_export_panel).parameters))
        for _ in range(2):
            for name in ('prepare_finance_import', 'import_finance_rows', 'export_finances', '_signed', 'refresh_all'):
                env[name] = Mock()
                kwargs[name](7, sample=True)
                env[name].assert_called_once_with(7, sample=True)
        names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue({'receive_import', 'confirm_import', 'do_export'}.isdisjoint(names))
        self.assertTrue({'Path', 'tempfile'}.isdisjoint({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}))
        self.assertNotIn('with ui.tab_panel(export_tab)', (ROOT / 'finances.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()

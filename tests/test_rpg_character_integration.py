"""Raccordements JDR sans navigateur ni connexion à la base."""
import ast
import inspect
from pathlib import Path
import unittest
from unittest.mock import MagicMock, Mock

import app_versions
from rpg_character_creation import open_new_character_dialog, build_character_creation_panel
from rpg_combat_session import build_combat_session

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_PATH = ROOT / 'rpg_character_ui.py'
PUBLIC_PATH = ROOT / 'rpg_character.py'


def tree():
    return ast.parse(IMPLEMENTATION_PATH.read_text(encoding='utf-8'))


def public_tree():
    return ast.parse(PUBLIC_PATH.read_text(encoding='utf-8'))


class CharacterIntegrationTests(unittest.TestCase):
    def test_public_module_is_thin_compatibility_facade(self):
        parsed = public_tree()
        imported_modules = {
            alias.name
            for node in parsed.body
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        functions = {
            node.name
            for node in parsed.body
            if isinstance(node, ast.FunctionDef)
        }
        source = ast.unparse(parsed)

        self.assertIn('rpg_character_ui', imported_modules)
        self.assertIn('rpg_character_panel = _impl.rpg_character_panel', source)
        self.assertEqual(functions, {'__getattr__', '__dir__'})
        self.assertLess(len(PUBLIC_PATH.read_text(encoding='utf-8').splitlines()), 80)

    def test_builders_receive_complete_existing_dependencies(self):
        parsed = tree()
        available = {n.name for n in parsed.body if isinstance(n, ast.FunctionDef)}
        available |= {a.asname or a.name for n in parsed.body if isinstance(n, ast.ImportFrom) for a in n.names}
        available |= {'ui', 'user_id', 'character', 'player_default'}
        for builder in (open_new_character_dialog, build_character_creation_panel, build_combat_session):
            calls = [n for n in ast.walk(parsed) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Name) and n.func.id == builder.__name__]
            self.assertEqual(len(calls), 1)
            call = calls[0]
            values = {k.arg: object() for k in call.keywords}
            inspect.signature(builder).bind(**values)
            self.assertTrue(all(isinstance(k.value, ast.Name) and k.value.id in available for k in call.keywords))

    def test_both_modes_create_persistent_character_then_navigate(self):
        for mode, section in [('quick', None), ('guided', 'creation')]:
            with self.subTest(mode=mode):
                ui = MagicMock()
                ui.toggle.return_value.props.return_value.classes.return_value.value = mode
                inputs = [MagicMock(), MagicMock()]
                for widget, value in zip(inputs, ['Héros', 'Joueur']):
                    widget.props.return_value.classes.return_value.value = value
                ui.input.side_effect = inputs
                create = Mock(return_value=17)
                url = Mock(return_value='/selected')
                notify = Mock()
                open_new_character_dialog(ui=ui, user_id=3, player_default='Joueur',
                    create_rpg_character=create, character_url=url, notify_error=notify)
                self.assertEqual(set(ui.toggle.call_args.args[0].values()), {'Création rapide', 'Création guidée'})
                callback = next(c.kwargs['on_click'] for c in ui.button.call_args_list if c.args[0] == 'Créer')
                callback()
                create.assert_called_once_with(3, 'Héros', 'Joueur')
                url.assert_called_once_with(17, section)
                ui.navigate.to.assert_called_once_with('/selected')
                notify.assert_not_called()

    def test_creation_error_does_not_navigate(self):
        ui = MagicMock(); notify = Mock()
        open_new_character_dialog(ui=ui, user_id=3, player_default='Joueur',
            create_rpg_character=Mock(side_effect=ValueError('invalid')),
            character_url=Mock(), notify_error=notify)
        next(c.kwargs['on_click'] for c in ui.button.call_args_list if c.args[0] == 'Créer')()
        ui.navigate.to.assert_not_called()
        ui.dialog.return_value.__enter__.return_value.close.assert_not_called()
        notify.assert_called_once()

    def test_tabs_and_selected_creation_route_and_quick_combat(self):
        parsed = tree()
        panel = next(n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == 'rpg_character_panel')
        calls = [n for n in ast.walk(panel) if isinstance(n, ast.Call)]
        tabs = [n.args[0].value for n in calls if ast.unparse(n.func) == 'ui.tab']
        self.assertEqual(tabs, ['Création guidée', 'Identité', 'Progression', 'Combat', 'Équipement', 'Sauvegardes', 'Compétences', 'Attaques'])
        source = ast.unparse(panel)
        self.assertIn("'creation': creation_tab", source)
        self.assertIn('value=initial_tab', source)
        self.assertIn('ui.tab_panel(creation_tab)', source)
        button = next(n for n in calls if ast.unparse(n.func) == 'ui.button' and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == 'Combat rapide')
        self.assertEqual(ast.unparse(next(k.value for k in button.keywords if k.arg == 'on_click')), 'open_combat_session')
        self.assertEqual(sum(ast.unparse(n.func) == '_create_character_dialog' for n in calls), 2)

    def test_combat_reloads_latest_character_without_rebuilding_handle(self):
        callback = next(n for n in ast.walk(tree()) if isinstance(n, ast.FunctionDef) and n.name == 'open_combat_session')
        character = {'id': 17, 'current_hp': 4}
        fresh = {'id': 17, 'current_hp': 12, 'str_score': 16}
        handle = Mock()
        env = dict(character=character, current_id=17, user_id=3,
                   get_rpg_character=Mock(return_value=fresh), combat_session=handle, _safe_notify_error=Mock())
        exec(compile(ast.Module(body=[callback], type_ignores=[]), '<callback>', 'exec'), env)
        env['open_combat_session']()
        self.assertEqual(character, fresh)
        handle.open.assert_called_once_with()
        env['get_rpg_character'].assert_called_once_with(3, 17)
        handle.reset_mock()
        env['get_rpg_character'].side_effect = ValueError('missing')
        env['open_combat_session']()
        handle.open.assert_not_called()
        env['_safe_notify_error'].assert_called_once()

    def test_modules_imported_without_back_reference(self):
        modules = {n.module for n in tree().body if isinstance(n, ast.ImportFrom)}
        self.assertTrue({'rpg_character_creation', 'rpg_combat_session'} <= modules)
        for name in ('rpg_character_creation', 'rpg_combat_session'):
            parsed = ast.parse((ROOT / (name + '.py')).read_text(encoding='utf-8'))
            imports = {n.module for n in ast.walk(parsed) if isinstance(n, ast.ImportFrom)}
            imports |= {a.name for n in ast.walk(parsed) if isinstance(n, ast.Import) for a in n.names}
            self.assertTrue({'rpg_character', 'rpg_character_ui', 'nicegui', 'db'}.isdisjoint(imports))

    def test_jdr_version_and_release_note(self):
        self.assertEqual(app_versions.APP_VERSIONS['rpg'], '1.4.1')
        self.assertEqual(app_versions.APP_VERSIONS['finances'], '1.13.5')
        note = next(n for n in app_versions.RELEASE_NOTES if n['app_key'] == 'rpg')
        self.assertEqual(note['version'], '1.4.1')


if __name__ == '__main__':
    unittest.main()

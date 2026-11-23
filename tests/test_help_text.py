"""Every selector option has a description and the UI wires them up."""
import _testenv  # noqa: F401 - must precede the app imports (test log folder)
import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


class HelpTextTests(unittest.TestCase):
    def test_texts_cover_every_option(self):
        from app.ui.qt import help_text as h
        for key in ('Off', 'Dry run', 'Maxer', 'Rusher'):
            self.assertTrue(h.AUTO_UPGRADE[key])
        for key in ('Gold', 'Both', 'Elixir', 'Trophy'):
            self.assertTrue(h.BB_PRIORITISE[key])
        for key in ('Valkyries', 'Sneaky Goblins', 'Super Minions', 'Edrags'):
            self.assertTrue(h.STRATEGIES[key])

    def test_run_page_buttons_have_tooltips(self):
        from PySide6.QtWidgets import QApplication, QAbstractButton
        app = QApplication.instance() or QApplication([])
        from app.ui.qt.bot_controller import BotController
        from app.ui.qt.pages.run import RunPage
        page = RunPage(BotController(bot_version = 'test'), lambda *_: None)
        missing = [b.text() for b in page.findChildren(QAbstractButton) if b.text().strip() and not b.toolTip()]
        self.assertEqual(missing, [])
        self.assertTrue(page._auto_hint.text())


if __name__ == '__main__':
    unittest.main()

import os
import threading
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest

import main


class CleanTableInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = main.QApplication.instance() or main.QApplication([])

    def setUp(self):
        self.table = main.CleanRulesTableView()
        self.model = main.CleanRulesTableModel(self.table)
        self.table.setModel(self.model)
        self.model.set_rows(self.rows(6))
        self.table.resize(800, 450)
        self.table.show()
        self.app.processEvents()
        self.errors = []
        import sys
        self.previous_hook = sys.excepthook
        def capture_error(*error):
            self.errors.append(error)
            self.previous_hook(*error)
        sys.excepthook = capture_error
        self.addCleanup(setattr, sys, "excepthook", self.previous_hook)
        self.addCleanup(self.table.close)

    @staticmethod
    def rows(count):
        return [main.CleanRuleRow(i, f"Rule {i}", f"C:/test/{i}", "dir", False, "", False, "")
                for i in range(count)]

    def click(self, row, shift=False):
        index = self.model.index(row, 0)
        rect = self.table.visualRect(index)
        point = main.QPoint(rect.left() + 24, rect.center().y())
        QTest.mouseClick(self.table.viewport(), main.Qt.MouseButton.LeftButton,
                         main.Qt.KeyboardModifier.ShiftModifier if shift else main.Qt.KeyboardModifier.NoModifier,
                         point)
        self.app.processEvents()
        self.assertEqual(self.errors, [])

    def states(self):
        return [self.model.row_at(i).checked for i in range(self.model.rowCount())]

    def test_shift_checks_and_unchecks_visible_range(self):
        self.table.setRowHidden(2, True)
        self.click(0)
        self.click(4, shift=True)
        self.assertEqual(self.states(), [True, True, False, True, True, False])
        self.click(4)
        self.click(0, shift=True)
        self.assertEqual(self.states(), [False] * 6)

    def test_anchor_survives_row_move(self):
        self.click(0)
        self.model.moveRows(main.QModelIndex(), 0, 1, main.QModelIndex(), 6)
        self.click(3, shift=True)
        self.assertEqual(self.states(), [False, False, False, True, True, True])

    def test_anchor_survives_sort(self):
        self.click(4)
        for i, row in enumerate(self.model._rows):
            row.size = i
        self.model.sort_by_mode(3)
        self.click(3, shift=True)
        self.assertEqual(self.states(), [False, True, True, True, False, False])

    def test_reload_invalidates_removed_anchor(self):
        self.click(5)
        self.model.set_rows(self.rows(2))
        self.app.processEvents()
        self.click(0, shift=True)
        self.assertEqual(self.states(), [True, False])
        self.click(1, shift=True)
        self.assertEqual(self.states(), [True, True])

    def test_hidden_anchor_starts_a_new_range(self):
        self.click(0)
        self.table.setRowHidden(0, True)
        self.click(4, shift=True)
        self.assertEqual(self.states(), [True, False, False, False, True, False])

    def test_normal_row_press_still_arms_drag(self):
        point = self.table.visualRect(self.model.index(2, 1)).center()
        QTest.mousePress(self.table.viewport(), main.Qt.MouseButton.LeftButton,
                         main.Qt.KeyboardModifier.NoModifier, point)
        self.assertEqual(self.table._press_row, 2)
        QTest.mouseRelease(self.table.viewport(), main.Qt.MouseButton.LeftButton,
                           main.Qt.KeyboardModifier.NoModifier, point)
        self.assertEqual(self.table._press_row, -1)

    def test_columns_can_resize(self):
        page = main.CleanPage(main.Sig(), [], threading.Event(), threading.Lock())
        self.addCleanup(page.close)
        header = page.tbl.horizontalHeader()
        for column in range(5):
            self.assertEqual(header.sectionResizeMode(column), main.QHeaderView.ResizeMode.Interactive)
            header.resizeSection(column, 180 + column)
            self.assertEqual(header.sectionSize(column), 180 + column)


if __name__ == "__main__":
    unittest.main()

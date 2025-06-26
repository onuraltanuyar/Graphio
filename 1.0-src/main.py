"""
Graphio 1.0 – Onur Altan Uyar
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QAction, QColorDialog, QFileDialog, QToolBar,
    QDockWidget, QWidget, QVBoxLayout, QLabel, QSlider,
    QPushButton, QMessageBox, QUndoStack, QUndoCommand
)
from PyQt5.QtGui import QPen, QImage, QPainter, QColor, QPainterPath, QIcon
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtSvg import QSvgGenerator

APP_NAME = "Graphio"
APP_VERSION = "1.0"

STYLE = """
QMainWindow {
  background: #353535; font-family: "Segoe UI"; font-size: 10pt;
}
QToolBar {
  background: #2b2b2b; spacing: 6px; padding: 4px;
}
QToolButton {
  background: transparent; border: none; padding: 4px; color: #DDD;
}
QToolButton:hover { background: #3c3c3c; }
QDockWidget {
  background: #2b2b2b; font-weight: bold;
}
QSlider::handle:horizontal {
  background: #2A82DA; border: 1px solid #5c5c5c;
  width: 12px; margin: -2px 0; border-radius: 6px;
}
QLabel, QPushButton {
  color: #EEE; font-size: 9pt;
}
"""

def apply_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    p = app.palette()
    p.setColor(p.Window, QColor(53, 53, 53))
    p.setColor(p.WindowText, Qt.white)
    p.setColor(p.Base, QColor(25, 25, 25))
    p.setColor(p.AlternateBase, QColor(53, 53, 53))
    p.setColor(p.ToolTipBase, Qt.white)
    p.setColor(p.ToolTipText, Qt.white)
    p.setColor(p.Text, Qt.white)
    p.setColor(p.Button, QColor(53, 53, 53))
    p.setColor(p.ButtonText, Qt.white)
    p.setColor(p.Highlight, QColor(42, 130, 218))
    p.setColor(p.HighlightedText, Qt.black)
    app.setPalette(p)
    app.setStyleSheet(STYLE)


class AddCommand(QUndoCommand):
    def __init__(self, scene, item, description="Add Item"):
        super().__init__(description)
        self.scene = scene
        self.item = item

    def undo(self):
        self.scene.removeItem(self.item)

    def redo(self):
        self.scene.addItem(self.item)

class Canvas(QGraphicsView):
    def __init__(self, undo_stack: QUndoStack, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self); self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self._tool = 'brush'
        self._color = Qt.white
        self.pen_width = 3
        self._start = QPointF(); self._last = QPointF()
        self.current_path = None
        self.current_item = None
        self.undo_stack = undo_stack

    def set_tool(self, tool: str):
        self._tool = tool

    def set_color(self, col: QColor):
        self._color = col

    def mousePressEvent(self, e):
        pos = self.mapToScene(e.pos())
        self._start = self._last = pos
        if self._tool == 'brush':
            path = QPainterPath(pos)
            self.current_item = self.scene.addPath(
                path, QPen(self._color, self.pen_width,
                           Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            )
            self.current_path = path
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        pos = self.mapToScene(e.pos())
        if self._tool == 'brush' and e.buttons() & Qt.LeftButton:
            self.current_path.lineTo(pos)
            self.current_item.setPath(self.current_path)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        pos = self.mapToScene(e.pos())
        if self._tool in ('rect', 'ellipse'):
            pen = QPen(self._color, self.pen_width)
            rect = QRectF(self._start, pos)
            if self._tool == 'rect':
                item = self.scene.addRect(rect, pen)
            else:
                item = self.scene.addEllipse(rect, pen)
            self.undo_stack.push(AddCommand(self.scene, item))
        elif self._tool == 'brush':
            cmd = AddCommand(self.scene, self.current_item, "Brush Stroke")
            cmd.undo()
            self.undo_stack.push(cmd)
        super().mouseReleaseEvent(e)

class MainWindow(QMainWindow):
    def __init__(self, app: QApplication):
        super().__init__(); self.app = app
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(900, 600)

        self.undo_stack = QUndoStack(self)

        self.canvas = Canvas(self.undo_stack)
        self.setCentralWidget(self.canvas)

        self._create_toolbar()
        self._create_dock()
        self._create_menus()

    def _create_toolbar(self):
        tb = QToolBar("Araçlar", self); self.addToolBar(tb)
        for name, tool in [("Fırça", "brush"),
                           ("Dikdörtgen", "rect"),
                           ("Elips", "ellipse")]:
            act = QAction(name, self)
            act.triggered.connect(lambda _, t=tool: self.canvas.set_tool(t))
            tb.addAction(act)
        tb.addSeparator()
        self.act_toggle = QAction("Karanlık Tema", self, checkable=True)
        self.act_toggle.toggled.connect(self._toggle_theme)
        tb.addAction(self.act_toggle)

    def _create_dock(self):
        dock = QDockWidget("Araç Seçenekleri", self)
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(QLabel("Fırça Kalınlığı"))
        s = QSlider(Qt.Horizontal)
        s.setRange(1,50); s.setValue(self.canvas.pen_width)
        s.valueChanged.connect(lambda v: setattr(self.canvas,'pen_width',v))
        v.addWidget(s)
        btn = QPushButton("Renk Seç")
        btn.clicked.connect(self._pick_color)
        v.addWidget(btn)
        v.addStretch()
        dock.setWidget(w); self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _create_menus(self):
        mb = self.menuBar()
        m = mb.addMenu("Dosya")
        m.addAction(QAction("Kaydet PNG...", self,
                     triggered=self._save_png))
        m.addAction(QAction("Dışa Aktar SVG...", self,
                     triggered=self._export_svg))
        m = mb.addMenu("Düzen")
        m.addAction(QAction("Geri Al", self, shortcut="Ctrl+Z",
                     triggered=self.undo_stack.undo))
        m.addAction(QAction("İleri Al", self, shortcut="Ctrl+Y",
                     triggered=self.undo_stack.redo))
        m = mb.addMenu("Yardım")
        m.addAction(QAction("Hakkında", self,
                     triggered=self._show_about))

    def _toggle_theme(self, dark: bool):
        if dark:
            apply_dark_theme(self.app)
            self.act_toggle.setText("Aydınlık Tema")
        else:
            self.app.setPalette(self.app.style().standardPalette())
            self.app.setStyleSheet("")
            self.act_toggle.setText("Karanlık Tema")

    def _pick_color(self):
        c = QColorDialog.getColor(self.canvas._color, self)
        if c.isValid(): self.canvas.set_color(c)

    def _save_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "PNG Olarak Kaydet",
                                              "", "PNG Files (*.png)")
        if not path: return
        r = self.canvas.scene.itemsBoundingRect().toRect()
        img = QImage(r.size(), QImage.Format_ARGB32); img.fill(Qt.transparent)
        p = QPainter(img)
        self.canvas.scene.render(p, target=QRectF(img.rect()),
                                 source=QRectF(r))
        p.end(); img.save(path)

    def _export_svg(self):
        path, _ = QFileDialog.getSaveFileName(self, "SVG Olarak Dışa Aktar",
                                              "", "SVG Files (*.svg)")
        if not path: return
        gen = QSvgGenerator()
        gen.setFileName(path)
        gen.setSize(self.canvas.scene.itemsBoundingRect().size().toSize())
        p = QPainter(gen)
        self.canvas.scene.render(p)
        p.end()

    def _show_about(self):
        QMessageBox.about(self, f"Hakkında {APP_NAME}",
            f"<b>{APP_NAME} {APP_VERSION}</b><br>"
            "Tek dosya, Python + PyQt5 ile geliştirilmiş grafik uygulaması.<br>"
            "© 2025 Graphio 1.0 - Onur Altan Uyar"
        )

def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    w = MainWindow(app)
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

""""
Uygulama içerisinde modülleri pip install komutunu girerek kurulum gerçekleştirmelisiniz.
İletişim: onuraltanuyariletisim@gmail.com
""""

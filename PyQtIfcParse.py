from PyQt5 import QtWidgets
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QFileDialog, QProgressDialog, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import sys
import os
from collections.abc import Iterable
import ifcopenshell
from ifcopenshell import geom
from OCC.Display.backend import load_any_qt_backend, get_qt_modules
from OCC.Display.OCCViewer import rgb_color, Quantity_Color
from OCC.Extend.DataExchange import read_stl_file
from OCC.Extend.DataExchange import read_iges_file
from OCC.Extend.DataExchange import read_step_file
import images

load_any_qt_backend()

QtCore, QtGui, QtWidgets, QtOpenGL = get_qt_modules()

from OCC.Display.qtDisplay import qtViewer3d


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args) -> None:
        QtWidgets.QMainWindow.__init__(self, *args)
        self.canva = qtViewer3d(self)
        self.setWindowTitle("解析IFC")
        self.setWindowIcon(QIcon(":/Ifc.ico"))
        self.setCentralWidget(self.canva)
        if sys.platform != "darwin":
            self.menu_bar = self.menuBar()
        else:
            # create a parentless menubar
            # see: http://stackoverflow.com/questions/11375176/qmenubar-and-qmenu-doesnt-show-in-mac-os-x?lq=1
            # noticeable is that the menu ( alas ) is created in the
            # topleft of the screen, just
            # next to the apple icon
            # still does ugly things like showing the "Python" menu in
            # bold
            self.menu_bar = QtWidgets.QMenuBar()
        self.menuOpen = self.menu_bar.addMenu("打开")
        actionIfc = QAction(QIcon(":/Ifc.ico"), "打开IFC文件", self)
        actionIfc.setMenuRole(QtWidgets.QAction.NoRole)
        actionIfc.triggered.connect(self.parseIfc)
        actionStl = QAction(QIcon(":/Ifc.ico"), "打开STL文件", self)
        actionStl.setMenuRole(QtWidgets.QAction.NoRole)
        actionStl.triggered.connect(self.parseStl)
        actionIges = QAction(QIcon(":/Ifc.ico"), "打开IGES文件", self)
        actionIges.setMenuRole(QtWidgets.QAction.NoRole)
        actionIges.triggered.connect(self.parseIges)
        actionStep = QAction(QIcon(":/Ifc.ico"), "打开STEP文件", self)
        actionStep.setMenuRole(QtWidgets.QAction.NoRole)
        actionStep.triggered.connect(self.parseStep)
        self.menuOpen.addAction(actionIfc)
        self.menuOpen.addAction(actionStl)
        self.menuOpen.addAction(actionIges)
        self.menuOpen.addAction(actionStep)

    def parseStep(self)->None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开STEP文件", os.path.join(os.path.expanduser("~"), 'Desktop'),
            "STEP文件(*.step;*.stp)")
        if os.path.exists(file_path):
            shapes = read_step_file(file_path,False)
            if isinstance(shapes,Iterable):
                for shape in shapes:
                    self.canva._display.DisplayShape(shape)
            else:
                self.canva._display.DisplayShape(shapes)
            self.canva._display.FitAll()
            self.canva._display.Repaint()

    def parseIges(self)->None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开IGES文件", os.path.join(os.path.expanduser("~"), 'Desktop'),
            "IGES文件(*.iges;*.igs)")
        if os.path.exists(file_path):
            shapes = read_iges_file(file_path,True)
            for shape in shapes:
                self.canva._display.DisplayShape(shape)
            self.canva._display.FitAll()
            self.canva._display.Repaint()
        
    def parseStl(self)->None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开STL文件", os.path.join(os.path.expanduser("~"), 'Desktop'),
            "STL文件(*.stl)")
        if os.path.exists(file_path):
            shape = read_stl_file(file_path)
            self.canva._display.DisplayShape(shape)
            self.canva._display.FitAll()
            self.canva._display.Repaint()

    def parseIfc(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开IFC文件", os.path.join(os.path.expanduser("~"), 'Desktop'),
            "工业基础类(*.ifc)")
        if os.path.exists(file_path):
            self.canva._display.EraseAll()
            settings = geom.settings()
            settings.set(settings.USE_PYTHON_OPENCASCADE, True)
            ifc_file = ifcopenshell.open(file_path)
            products = ifc_file.by_type("IfcProduct")
            n = len(products)
            progress = QProgressDialog(minimum=0, maximum=n, parent=self)
            progress.setWindowFlags(
                Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
            progress.setWindowTitle("正在解析...")
            progress.setCancelButton(None)
            progress.setWindowModality(Qt.ApplicationModal)
            progress.show()
            try:
                for i, product in enumerate(products):
                    progress.setValue(i + 1)
                    if product.is_a("IfcOpeningElement") or product.is_a("IfcSpace") or product.is_a("IfcGrid"):
                        continue
                    QCoreApplication.processEvents()
                    if progress.wasCanceled():
                        break
                    if product.Representation is not None:
                        # These are methods of the TopoDS_Shape class from pythonOCC
                        shape = geom.create_shape(settings, product)
                        rgbColor = Quantity_Color()
                        transparency = 0.0
                        for style in shape.styles:
                            rgbColor = rgb_color(style[0], style[1], style[2])
                            transparency = style[3]
                            break
                        self.canva._display.DisplayShape(
                            shape.geometry, color=rgbColor, transparency=1-transparency)
            except Exception as e:
                print(e)
            finally:
                progress.close()
            self.canva._display.FitAll()
            self.canva._display.Repaint()

    def centerOnScreen(self) -> None:
        """Centers the window on the screen."""
        resolution = QtWidgets.QApplication.desktop().screenGeometry()
        x = (resolution.width() - self.frameSize().width()) // 2
        y = (resolution.height() - self.frameSize().height()) // 2
        self.move(x, y)


if __name__ == "__main__":
    # checks if QApplication already exists
    app = QtWidgets.QApplication.instance()
    if not app:  # create QApplication if it doesn't exist
        app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.resize(1024, 768)
    win.show()
    win.centerOnScreen()
    win.canva.InitDriver()
    win.canva.qApp = app
    display = win.canva._display
    display.display_triedron()
    display.set_bg_gradient_color([206, 215, 222], [128, 128, 128])
    win.raise_()
    app.exec_()

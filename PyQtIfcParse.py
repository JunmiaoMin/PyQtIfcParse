from PyQt5 import QtWidgets
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QFileDialog, QProgressDialog, QAction
from PyQt5.QtWinExtras import QWinTaskbarButton, QWinTaskbarProgress
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import sys
import os
import ifcopenshell
from ifcopenshell import geom
from OCC.Display.backend import load_any_qt_backend, get_qt_modules
from OCC.Display.OCCViewer import rgb_color
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
        action = QAction(QIcon(":/Ifc.ico"), "打开IFC文件", self)
        action.setMenuRole(QtWidgets.QAction.NoRole)
        action.triggered.connect(self.parseIfc)
        self.menuOpen.addAction(action)
        self.taskbar_button = QWinTaskbarButton(self)
        self.taskbar_button.setWindow(self.windowHandle())
        self._progress = self.taskbar_button.progress()
            

    def parseIfc(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开IFC文件", os.path.join(os.path.expanduser("~"), 'Desktop'),
            "工业基础类(*.ifc)")
        if os.path.exists(file_path):
            settings = geom.settings()
            settings.set(settings.USE_PYTHON_OPENCASCADE, True)
            ifc_file = ifcopenshell.open(file_path)
            products = ifc_file.by_type("IfcProduct")
            n = len(products)
            progress = QProgressDialog(minimum=0, maximum=n, parent=self)
            progress.setWindowFlags(
                Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
            self._progress.setVisible(True)
            self._progress.setRange(0,n)
            progress.setWindowTitle("正在解析...")
            progress.setCancelButton(None)
            progress.setWindowModality(Qt.ApplicationModal)
            progress.show()
            try:
                for i, product in enumerate(products):
                    progress.setValue(i + 1)
                    self._progress.setValue(i+1)
                    self._progress.show()
                    QCoreApplication.processEvents()
                    if progress.wasCanceled():
                        break
                    if product.Representation is not None:
                        rgbColor = rgb_color(
                            0.5704820156097412, 0.2835550010204315, 0.01233499962836504)
                        ifcTransparency = 0.0
                        for representation in product.Representation.Representations:
                            for item in representation.Items:
                                for styleItem in item.StyledByItem:
                                    for presentationStyle in styleItem.Styles:
                                        for style in presentationStyle.Styles:
                                            if style.is_a("IfcSurfaceStyle"):
                                                for styleRendering in style.Styles:
                                                    if styleRendering.is_a("IfcSurfaceStyleRendering"):
                                                        ifcColour = styleRendering.SurfaceColour
                                                        ifcTransparency = styleRendering.Transparency
                                                        rgbColor = rgb_color(
                                                            ifcColour.Red, ifcColour.Green, ifcColour.Blue)
                        # These are methods of the TopoDS_Shape class from pythonOCC
                        shape = geom.create_shape(settings, product).geometry
                        self.canva._display.DisplayShape(
                            shape, color=rgbColor, transparency=ifcTransparency)
            except Exception as e:
                print(e)
                progress.close()
            self._progress.reset()
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

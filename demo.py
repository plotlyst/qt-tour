import sys

from PyQt6.QtWidgets import QPushButton
from qthandy import vbox
from qtpy.QtWidgets import QMainWindow, QApplication, QWidget

from qttour import TourManager, TourStep, TourSequence


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)

        self._btn1 = QPushButton('Btn1')
        self._btn2 = QPushButton('Btn2')
        self._btn3 = QPushButton('Start tour')

        vbox(self.widget, 25)
        self.widget.layout().addWidget(self._btn1)
        self.widget.layout().addWidget(self._btn2)
        self.widget.layout().addWidget(self._btn3)

        self._btn1.clicked.connect(lambda: print('btn 1'))
        self._btn2.clicked.connect(lambda: print('btn 2'))
        self._btn3.clicked.connect(self._startTour)

        self._tour = TourManager.instance()
        self._tour.tourFinished.connect(lambda: self._btn3.setEnabled(True))

    def _startTour(self):
        sequence = TourSequence()
        step1 = TourStep(self._btn1)
        step3 = TourStep(self._btn3, delegateClick=False, message='Text bubble')
        step1.finished.connect(lambda: sequence.addStep(step3))
        sequence.addStep(step1)
        sequence.addStep(TourStep(self._btn2))
        self._tour.run(sequence)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()

    app.exec()

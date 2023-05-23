import threading
from typing import Optional, List, Union

import qtanim
from qthandy import vbox, pointy
from qtpy.QtCore import QObject, QPoint, QEvent, Signal, Qt
from qtpy.QtGui import QMouseEvent, QColor, QHideEvent, QKeyEvent
from qtpy.QtWidgets import QWidget, QApplication, QFrame, QAbstractButton


def global_pos(widget: QWidget) -> QPoint:
    return widget.parent().mapToGlobal(widget.pos())


class CoachmarkWidget(QWidget):
    clicked = Signal()

    def __init__(self, parent=None, color: str = 'darkBlue'):
        super(CoachmarkWidget, self).__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._color = color

        pointy(self)
        vbox(self)
        self._frame = QFrame()
        self.setStyleSheet(f'''
        QFrame {{
                padding-left: 2px;
                padding-right: 2px;
                border: 3px dashed {self._color};
                border-radius: 5px;
            }}
        ''')
        self.layout().addWidget(self._frame)
        self._anim = None

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        pass

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._frame.underMouse():
            self.close()
            self.clicked.emit()

    def show(self) -> None:
        super(CoachmarkWidget, self).show()
        self._anim = qtanim.glow(self._frame, loop=-1, duration=600, radius=20, color=QColor(self._color).darker())

    def hideEvent(self, event: QHideEvent) -> None:
        if self._anim:
            self._anim.stop()


class DisabledClickEventFilter(QObject):
    # clicked = Signal()

    def __init__(self, parent=None):
        super(DisabledClickEventFilter, self).__init__(parent)
        self._widget: Optional[QWidget] = None
        self._mark: Optional[CoachmarkWidget] = None

    def setWidget(self, widget: QWidget):
        self._widget = widget

    def setMark(self, mark: CoachmarkWidget):
        self._mark = mark

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(event, QMouseEvent) and event.type() == QEvent.Type.MouseButtonPress:
            if self._widget is None or self._mark is None:
                return True
            if self._mark.underMouse():
                return False
            elif self._widget.underMouse():
                # self.clicked.emit()
                return False
            return True
        return super(DisabledClickEventFilter, self).eventFilter(watched, event)


class TourStep(QObject):
    finished = Signal()

    def __init__(self, widget: QWidget, delegateClick: bool = True):
        super(TourStep, self).__init__()
        self._widget = widget
        self._delegateClick = delegateClick

    def widget(self) -> QWidget:
        return self._widget

    def delegateClick(self) -> bool:
        return self._delegateClick


class TourSequence(QObject):

    def __init__(self):
        super(TourSequence, self).__init__()
        self._steps: List[TourStep] = []

    def addStep(self, step: TourStep):
        self._steps.append(step)

    def addSteps(self, *steps: TourStep):
        for step in steps:
            self._steps.append(step)

    def clear(self):
        self._steps.clear()

    def steps(self) -> List[TourStep]:
        return self._steps


class TourManager(QObject):
    tourStarted = Signal()
    tourFinished = Signal()

    __instance = None
    __lock = threading.Lock()

    def __init__(self):
        super(TourManager, self).__init__()
        self._coachColor: str = 'darkBlue'
        self._disabledEventFilter = DisabledClickEventFilter()
        self._stepIndex: int = 0
        self._started: bool = False
        self._finishNext: bool = False
        self._sequence: Optional[TourSequence] = None
        self._mark: Optional[CoachmarkWidget] = None
        self._currentStep: Optional[TourStep] = None

    @classmethod
    def instance(cls):
        if not cls.__instance:
            with cls.__lock:
                if not cls.__instance:
                    cls.__instance = TourManager()
        return cls.__instance

    def setCoachColor(self, color: Union[str, QColor, Qt.GlobalColor]):
        if isinstance(color, QColor):
            color = color.name()
        self._coachColor = color

    def start(self):
        self._started = True
        QApplication.instance().installEventFilter(self._disabledEventFilter)
        self.tourStarted.emit()

    def run(self, sequence: TourSequence, finishTour: bool = True):
        if not self._started:
            self.start()
        self._finishNext = finishTour
        self._sequence = sequence
        if not sequence.steps():
            return
        self._stepIndex = 0

        self._activate(self._sequence.steps()[self._stepIndex])

    def finish(self):
        QApplication.instance().removeEventFilter(self._disabledEventFilter)
        self._mark = None
        self._started = False
        self.tourFinished.emit()

    def _activate(self, step: TourStep):
        self._currentStep = step
        self._disabledEventFilter.setWidget(step.widget())

        pos = global_pos(step.widget())
        self._mark = CoachmarkWidget(step.widget(), color=self._coachColor)
        padding = 10
        self._mark.setGeometry(pos.x() - padding, pos.y() - padding, step.widget().width() + padding * 2,
                               step.widget().height() + padding * 2)

        self._mark.clicked.connect(self._next)
        self._disabledEventFilter.setMark(self._mark)
        self._mark.show()

    def _next(self):
        if self._currentStep.delegateClick():
            wdg = self._currentStep.widget()
            if isinstance(wdg, QAbstractButton):
                wdg.click()
        self._currentStep.finished.emit()

        self._stepIndex += 1
        if self._finishNext and self._stepIndex >= len(self._sequence.steps()):
            self.finish()
        else:
            self._activate(self._sequence.steps()[self._stepIndex])

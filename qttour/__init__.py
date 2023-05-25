import threading
from typing import Optional, List, Union

import qtanim
import qtawesome
from qthandy import pointy, transparent, gc, ask_confirmation, vbox
from qtpy.QtCore import QObject, QPoint, QEvent, Signal, Qt, QSize, QRect
from qtpy.QtGui import QMouseEvent, QColor, QHideEvent, QKeyEvent, QPaintEvent, QPainter, QPolygon, QPen, QRegion, \
    QCloseEvent
from qtpy.QtWidgets import QWidget, QApplication, QAbstractButton, QToolButton, QFrame, QTextBrowser, QPushButton


def global_pos(widget: QWidget) -> QPoint:
    return widget.mapToGlobal(QPoint(0, 0))


def global_rect(widget: QWidget) -> QRect:
    return QRect(global_pos(widget), widget.rect().size())


def map_from_global_rect(global_rect: QRect, widget: QWidget) -> QRect:
    top_left = widget.mapFromGlobal(global_rect.topLeft())
    local_rect = QRect(top_left, global_rect.size())
    return local_rect


class Arrow(QWidget):
    def __init__(self, color: str, parent):
        super(Arrow, self).__init__(parent)
        self._color = color
        self._penWidth: int = 2

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(self._color), self._penWidth))
        painter.setBrush(QColor('#f8f9fa'))

        top_point = self.rect().topRight()
        bottom_point = self.rect().bottomRight()
        left_point = QPoint(self._penWidth, self.height() / 2)

        arrow_polygon = QPolygon([top_point, bottom_point, left_point])
        painter.drawPolygon(arrow_polygon)


class BubbleText(QFrame):
    def __init__(self, text: str, action: str = '', parent=None):
        super(BubbleText, self).__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.text = QTextBrowser()
        transparent(self.text)
        self.text.setText(text)

        self.btn = QPushButton()
        pointy(self.btn)
        self.btn.setProperty('coachmark-message-action', True)
        if action:
            self.btn.setText(action)
        else:
            self.btn.setHidden(True)

        vbox(self, 5, 0).addWidget(self.text)
        self.layout().addWidget(self.btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)


class CoachmarkWidget(QWidget):
    clicked = Signal()
    terminate = Signal()

    def __init__(self, step: 'TourStep', color: str = 'darkBlue'):
        super(CoachmarkWidget, self).__init__(step.widget())
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._color = color
        self._closeAllowed = False

        pos = global_pos(step.widget())
        padding = 10
        self.move(pos.x() - padding, pos.y() - padding)

        self.frame = QFrame(self)
        self.frame.setFixedSize(QSize(step.widget().width() + padding * 2, step.widget().height() + padding * 2))
        pointy(self.frame)
        self.frame.setStyleSheet(f'''
            QFrame {{
                    padding-left: 2px;
                    padding-right: 2px;
                    border: 4px dashed {self._color};
                    border-radius: 12px;
                }}
            ''')

        self.setFixedWidth(self.frame.width() + 220)
        self.setFixedHeight(self.frame.height() + 200)

        if step.message():
            self._bubble = BubbleText(step.message(), step.action(), self)
            self._bubble.setStyleSheet(f'''
                QFrame {{
                        padding: 2px;
                        border: 4px solid {self._color};
                        background: #f8f9fa;
                        border-radius: 12px;
                    }}
                ''')
            self._bubble.setFixedSize(200, 200)
            self._bubble.move(self.frame.rect().topRight() + QPoint(20, 0))
            self._bubble.btn.clicked.connect(self._click)

            self._arrow = Arrow(self._color, self)
            self._arrow.setFixedSize(20, 25)
            self._arrow.move(self.frame.rect().topRight() + QPoint(1, 10))
        else:
            self._cursor = QToolButton(self)
            transparent(self._cursor)
            self._cursor.setIcon(qtawesome.icon('mdi.cursor-default-click', color=self._color))
            self._cursor.setIconSize(QSize(45, 45))
            self._cursor.move(self.frame.rect().bottomRight() - QPoint(20, 20))

        self._anim = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._closeAllowed = True
            if ask_confirmation('Terminate tour?', self):
                self.terminate.emit()
            else:
                self.show()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.frame.underMouse():
            self._click()

    def show(self) -> None:
        super(CoachmarkWidget, self).show()
        self._anim = qtanim.glow(self.frame, loop=-1, duration=300, radius=15, color=QColor(self._color).darker(10))
        self._closeAllowed = False

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closeAllowed:
            event.accept()
        else:
            event.ignore()

    def hideEvent(self, event: QHideEvent) -> None:
        if self._anim:
            self._anim.stop()

    def _click(self):
        self._closeAllowed = True

        self.close()
        self.clicked.emit()


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

    def __init__(self, widget: QWidget, message: str = '', delegateClick: bool = True, action: str = ''):
        super(TourStep, self).__init__()
        self._widget = widget
        self._delegateClick = delegateClick
        self._message = message
        self._action = action

    def widget(self) -> QWidget:
        return self._widget

    def delegateClick(self) -> bool:
        return self._delegateClick

    def message(self) -> str:
        return self._message

    def action(self) -> str:
        return self._action


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
        self._overlay: Optional[QWidget] = None

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

        if self._overlay:
            self._overlay.setHidden(True)
            gc(self._overlay)
            self._overlay = None

    def _activate(self, step: TourStep):
        self._currentStep = step
        self._disabledEventFilter.setWidget(step.widget())

        self._mark = CoachmarkWidget(step, color=self._coachColor)

        if self._overlay is None:
            self._overlay = QWidget(step.widget().window())
            self._overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self._overlay.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
            self._overlay.setFixedSize(step.widget().window().size())
            self._overlay.show()

        region = QRegion(step.widget().window().rect())
        target_rect = global_rect(step.widget())
        region = region.subtracted(QRegion(map_from_global_rect(target_rect, self._overlay)))
        self._overlay.setMask(region)

        self._mark.clicked.connect(self._next)
        self._mark.terminate.connect(self.finish)
        self._disabledEventFilter.setMark(self._mark)
        self._mark.show()

    def _next(self):
        if self._currentStep.delegateClick():
            wdg = self._currentStep.widget()
            if isinstance(wdg, QAbstractButton):
                wdg.click()
        self._currentStep.finished.emit()

        self._stepIndex += 1
        if self._stepIndex >= len(self._sequence.steps()):
            if self._finishNext:
                self.finish()
        else:
            self._activate(self._sequence.steps()[self._stepIndex])

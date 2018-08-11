import logging
import sys
import time
from datetime import datetime, timedelta

from PyQt5.QtCore import QCoreApplication, QPoint, Qt, QTimer
from PyQt5.QtWidgets import QApplication, QDesktopWidget, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QPushButton, QStyle


class TimeMonitor(object):
    def __init__(self, warn_seconds):
        self._max_seconds = warn_seconds
        self._last_status = get_time_status()

    def monitor(self, callback):
        status = get_time_status()
        last_status = self._last_status
        self._last_status = status

        if abs(status['diff'] - last_status['diff']) > self._max_seconds:
            callback(status, last_status)


def get_time_status():
    timestamp = time.time()
    monotonic_seconds = time.monotonic()
    return {
        'timestamp': timestamp,
        'monotonic_seconds': monotonic_seconds,
        'diff': timestamp - monotonic_seconds,
    }


def get_time_warning(status, last_status):
    m_key = 'monotonic_seconds'
    m_key = status[m_key] - last_status[m_key]
    t_key = 'timestamp'
    t_change = abs(status[t_key] - last_status[t_key])
    return '过去{}内，系统时间变化达到{}'.format(
        format_timedelta(timedelta(seconds=m_key)),
        format_timedelta(timedelta(seconds=t_change)))


class ToolWindow(QWidget):
    def __init__(self):
        # flags: no frame | always on top | do not show in taskbar
        super(ToolWindow, self).__init__(flags=Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)

    def set_background_color(self, color):
        p = self.palette()
        p.setColor(self.backgroundRole(), color)
        self.setPalette(p)


class MainWindow(ToolWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self._local_time_display = None
        self._utc_time_display = None
        self._drag_start = None
        self._warning_window = None

        self.create_widgets()

        self.set_background_color(Qt.yellow)

        self._fresh_timer = q_delay(self.update_time_label, 0, 100)

        self._time_monitor = TimeMonitor(warn_seconds=300)
        interval = 2000
        self._monitor_timer = q_delay(self.monitor_time_change, interval, interval)

    def create_widgets(self):
        root = QVBoxLayout()
        self.setLayout(root)

        self._local_time_display = self.create_time_label(root, '北京时间：')
        self._utc_time_display = self.create_time_label(root, '世界时间：')

    @staticmethod
    def create_time_label(root, text):
        time_display = QTimeDisplay(text, format_time)
        root.addLayout(time_display.root_layout)
        return time_display

    def monitor_time_change(self):
        self._time_monitor.monitor(self.show_time_jump)

    def show_time_jump(self, status, last_status):
        self._warning_window = WarningWindow('检测到时间突变', get_time_warning(status, last_status))
        self._warning_window.showFullScreen()

    def update_time_label(self):
        utc_time = datetime.utcnow()
        self._utc_time_display.set_content(utc_time)

        local_time = get_local_time(utc_time)
        self._local_time_display.set_content(local_time)

    def position_to_bottom_right(self, margin=20):
        desktop = QDesktopWidget()
        ag = desktop.availableGeometry()
        x = ag.width() - self.width() - margin
        y = ag.height() - self.height() - margin
        self.move(x, y)

    def resizeEvent(self, event):
        super(MainWindow, self).resizeEvent(event)
        self.position_to_bottom_right()

    def mousePressEvent(self, event):
        self._drag_start = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self._drag_start)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self._drag_start = event.globalPos()

    def closeEvent(self, event):
        super(MainWindow, self).closeEvent(event)
        # noinspection PyArgumentList
        QCoreApplication.quit()


class WarningWindow(ToolWindow):
    def __init__(self, title, content, opacity=0.8):
        super(WarningWindow, self).__init__()

        self.setWindowOpacity(opacity)

        root = QVBoxLayout()
        self.setLayout(root)
        root.setAlignment(Qt.AlignCenter)

        title_style = ' '.join([
            'color: blue;',
            'font-weight: bold;',
            'font-size: 24px;',
            'font-family: Microsoft YaHei, SimHei, sans-serif;'
        ])

        lb_title = QLabel(title)
        lb_title.setStyleSheet(title_style)
        # noinspection PyArgumentList
        root.addWidget(lb_title)

        hbox = QHBoxLayout()
        root.addLayout(hbox)

        lb_icon = QLabel()
        icon_size = 40
        lb_icon.setPixmap(self.style().standardPixmap(QStyle.SP_MessageBoxWarning).scaled(icon_size, icon_size))
        # noinspection PyArgumentList
        hbox.addWidget(lb_icon)

        content_style = ' '.join([
            'color: red;',
            'font-weight: bold;',
            'font-size: 18px;',
            'font-family: Microsoft YaHei, SimHei, sans-serif;'
        ])

        lb_content = QLabel(content)
        lb_content.setMaximumWidth(400)
        lb_content.setWordWrap(True)
        lb_content.setStyleSheet(content_style)
        # noinspection PyArgumentList
        hbox.addWidget(lb_content)

        button_style = ' '.join([
            'color: black;',
            'font-weight: bold;',
            'font-size: 18px;',
            'font-family: Microsoft YaHei, SimHei, sans-serif;'
        ])

        confirm_button = QPushButton('确认')
        confirm_button.clicked.connect(self.close)
        confirm_button.setStyleSheet(button_style)
        root.addWidget(confirm_button, alignment=Qt.AlignLeft)


class QTimeDisplay(object):
    def __init__(self, title, formatter):
        self._root = root = QHBoxLayout()

        style_sheet = ' '.join([
            'color: blue;',
            'font-weight: bold;',
            'font-size: 24px;',
            'font-family: Verdana, Arial, Helvetica, Microsoft YaHei, SimHei, sans-serif;'
        ])

        lb_name = QLabel(title)
        lb_name.setStyleSheet(style_sheet)
        # noinspection PyArgumentList
        root.addWidget(lb_name)

        self._lb_time = lb_time = QLabel()
        lb_time.setStyleSheet(style_sheet)
        # noinspection PyArgumentList
        root.addWidget(lb_time)

        self._formatter = formatter

    @property
    def root_layout(self):
        return self._root

    def set_content(self, t):
        self._lb_time.setText(self._formatter(t))


def q_delay(action, delay_millis, repeat_millis, *args, **kwargs):
    def action_wrapper():
        action(*args, **kwargs)

    def repeat_wrapper():
        action_wrapper()
        if repeat_millis > 0:
            timer.timeout.connect(action_wrapper)
            timer.setSingleShot(False)
            timer.start(repeat_millis)

    timer = QTimer()
    timer.timeout.connect(repeat_wrapper)
    timer.setSingleShot(True)
    timer.start(delay_millis)
    return timer


# convert utc_time to local time in GMT+8 timezone
def get_local_time(utc_time):
    return utc_time + timedelta(hours=8)


def format_time(t):
    return t.strftime('%Y-%m-%d %H:%M:%S')


def format_timedelta(td):
    days = td.days
    remain_seconds = td.seconds
    hours, remain_seconds = divmod(remain_seconds, 3600)
    minutes, remain_seconds = divmod(remain_seconds, 60)
    seconds = remain_seconds

    if days == hours == minutes == seconds == 0:
        return '0秒'
    else:
        result = ''
        result += '{}天'.format(days) if days > 0 else ''
        result += '{}小时'.format(hours) if hours > 0 else ''
        result += '{}分钟'.format(minutes) if minutes > 0 else ''
        result += '{}秒'.format(seconds) if seconds > 0 else ''
        return result


def main():
    logging.basicConfig(level=logging.DEBUG)

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

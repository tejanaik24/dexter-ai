from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from config import EVENT_LOG_PATH, FIX_QUEUE_PATH, MAX_LOG_LINES, POLL_INTERVAL_MS
from event_reader import EventReader
from fix_request_writer import FixRequestWriter
from ui_main import DashboardWindow


def _set_text_lines(widget, lines):
    widget.setPlainText("\n".join(lines))
    scrollbar = widget.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())


def run() -> int:
    app = QApplication(sys.argv)

    reader = EventReader(EVENT_LOG_PATH, max_log_lines=MAX_LOG_LINES)
    writer = FixRequestWriter(FIX_QUEUE_PATH)
    window = DashboardWindow()

    def refresh() -> None:
        state = reader.poll()
        window.status_value.setText(state.dexter_status)
        window.user_speech_value.setText(state.user_speech)
        window.dexter_speech_value.setText(state.dexter_speech)
        window.current_task_value.setText(state.current_task)
        _set_text_lines(window.operation_log, state.operation_log)
        _set_text_lines(window.web_search_log, state.web_search_activity)

    def queue_fix_request() -> None:
        raw_text = window.fix_input.text().strip()
        if not raw_text:
            window.fix_status.setText("Status: enter a request before queueing")
            return

        payload = writer.enqueue(raw_text)
        window.fix_status.setText(f"Status: queued ({payload['timestamp']})")
        window.fix_input.clear()

    window.fix_button.clicked.connect(queue_fix_request)

    timer = QTimer()
    timer.timeout.connect(refresh)
    timer.start(POLL_INTERVAL_MS)

    refresh()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class DashboardWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Dexter Dashboard (v1)")
        self.resize(1000, 700)

        root = QWidget()
        layout = QVBoxLayout(root)

        top_grid = QGridLayout()
        self.status_value = QLabel("unknown")
        self.user_speech_value = QLabel("")
        self.dexter_speech_value = QLabel("")
        self.current_task_value = QLabel("")

        top_grid.addWidget(QLabel("Dexter status:"), 0, 0)
        top_grid.addWidget(self.status_value, 0, 1)
        top_grid.addWidget(QLabel("User speech:"), 1, 0)
        top_grid.addWidget(self.user_speech_value, 1, 1)
        top_grid.addWidget(QLabel("Dexter speech:"), 2, 0)
        top_grid.addWidget(self.dexter_speech_value, 2, 1)
        top_grid.addWidget(QLabel("Current task:"), 3, 0)
        top_grid.addWidget(self.current_task_value, 3, 1)
        layout.addLayout(top_grid)

        logs_row = QHBoxLayout()

        self.operation_log = QPlainTextEdit()
        self.operation_log.setReadOnly(True)
        op_group = QGroupBox("Operation log")
        op_layout = QVBoxLayout(op_group)
        op_layout.addWidget(self.operation_log)

        self.web_search_log = QPlainTextEdit()
        self.web_search_log.setReadOnly(True)
        ws_group = QGroupBox("Web search activity")
        ws_layout = QVBoxLayout(ws_group)
        ws_layout.addWidget(self.web_search_log)

        logs_row.addWidget(op_group)
        logs_row.addWidget(ws_group)
        layout.addLayout(logs_row)

        fix_group = QGroupBox("Fix Dexter")
        fix_layout = QHBoxLayout(fix_group)
        self.fix_input = QLineEdit()
        self.fix_input.setPlaceholderText("Describe what Dexter should fix...")
        self.fix_button = QPushButton("Queue Request")
        self.fix_status = QLabel("Status: idle")
        fix_layout.addWidget(self.fix_input)
        fix_layout.addWidget(self.fix_button)
        fix_layout.addWidget(self.fix_status)
        layout.addWidget(fix_group)

        self.setCentralWidget(root)

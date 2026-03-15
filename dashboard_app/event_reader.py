from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class DashboardState:
    dexter_status: str = "unknown"
    user_speech: str = ""
    dexter_speech: str = ""
    current_task: str = ""
    operation_log: List[str] = field(default_factory=list)
    web_search_activity: List[str] = field(default_factory=list)


class EventReader:
    """Reads Dexter event updates from a JSONL file.

    Expected event format (one JSON object per line):
    {
      "type": "status|user_speech|dexter_speech|current_task|operation_log|web_search",
      "value": "text or serializable payload"
    }
    """

    def __init__(self, event_file: Path, max_log_lines: int = 200) -> None:
        self.event_file = event_file
        self.max_log_lines = max_log_lines
        self._position = 0
        self.state = DashboardState()

    def poll(self) -> DashboardState:
        if not self.event_file.exists():
            return self.state

        with self.event_file.open("r", encoding="utf-8") as f:
            f.seek(self._position)
            for line in f:
                self._apply_event_line(line)
            self._position = f.tell()
        return self.state

    def _apply_event_line(self, line: str) -> None:
        line = line.strip()
        if not line:
            return

        try:
            event: Dict = json.loads(line)
        except json.JSONDecodeError:
            self._append_log(f"[invalid-event] {line}")
            return

        event_type = event.get("type")
        value = event.get("value", "")

        if event_type == "status":
            self.state.dexter_status = str(value)
        elif event_type == "user_speech":
            self.state.user_speech = str(value)
        elif event_type == "dexter_speech":
            self.state.dexter_speech = str(value)
        elif event_type == "current_task":
            self.state.current_task = str(value)
        elif event_type == "operation_log":
            self._append_log(str(value))
        elif event_type == "web_search":
            self._append_web_search(str(value))
        else:
            self._append_log(f"[unknown-event:{event_type}] {value}")

    def _append_log(self, message: str) -> None:
        self.state.operation_log.append(message)
        self.state.operation_log = self.state.operation_log[-self.max_log_lines :]

    def _append_web_search(self, message: str) -> None:
        self.state.web_search_activity.append(message)
        self.state.web_search_activity = self.state.web_search_activity[-self.max_log_lines :]

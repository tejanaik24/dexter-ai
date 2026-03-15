from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class FixRequestWriter:
    def __init__(self, queue_file: Path) -> None:
        self.queue_file = queue_file
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)

    def enqueue(self, text: str) -> dict:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": text.strip(),
            "status": "queued",
        }
        with self.queue_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return payload

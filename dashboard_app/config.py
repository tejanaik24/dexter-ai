from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DEXTER_DASHBOARD_DATA_DIR", BASE_DIR / "data"))
EVENT_LOG_PATH = Path(os.getenv("DEXTER_EVENT_LOG_PATH", DATA_DIR / "events.jsonl"))
FIX_QUEUE_PATH = Path(os.getenv("DEXTER_FIX_QUEUE_PATH", DATA_DIR / "fix_requests.jsonl"))
POLL_INTERVAL_MS = int(os.getenv("DEXTER_DASHBOARD_POLL_MS", "1000"))
MAX_LOG_LINES = int(os.getenv("DEXTER_DASHBOARD_MAX_LOG_LINES", "200"))

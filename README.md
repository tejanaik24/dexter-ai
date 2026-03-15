# dexter-ai
Dexter AI assistant dashboard and control system.

## Standalone dashboard app (v1)
A small, standalone PySide6 dashboard now lives in `dashboard_app/`.

### Files
- `dashboard_app/main.py`
- `dashboard_app/ui_main.py`
- `dashboard_app/event_reader.py`
- `dashboard_app/fix_request_writer.py`
- `dashboard_app/config.py`
- `docs/dashboard_architecture.md`

### Install
```bash
pip install PySide6
```

### Run
```bash
cd dashboard_app
python main.py
```

### What it shows
- Dexter status
- User speech
- Dexter speech
- Current task
- Operation log
- Web search activity
- Fix Dexter input box

### Fix Dexter behavior in v1
The "Fix Dexter" box only queues requests to a file and marks them queued in the UI.

Default queue file path:
- `dashboard_app/data/fix_requests.jsonl`

### Event input file
The dashboard polls this file by default:
- `dashboard_app/data/events.jsonl`

You can override paths with environment variables:
- `DEXTER_DASHBOARD_DATA_DIR`
- `DEXTER_EVENT_LOG_PATH`
- `DEXTER_FIX_QUEUE_PATH`
- `DEXTER_DASHBOARD_POLL_MS`
- `DEXTER_DASHBOARD_MAX_LOG_LINES`

## Project handoff notes
- Session 28 handoff summary: `docs/session_28_handoff.md`

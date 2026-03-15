# Dexter Dashboard v1 Architecture

## Scope (v1 only)
This first version is intentionally small and standalone. It does **not** modify or integrate into existing runtime scripts yet.

Included in v1:
- Standalone PySide6 desktop dashboard app
- Read-only event display from a JSONL event file
- "Fix Dexter" input that queues requests to a JSONL queue file

Explicitly out of scope for v1:
- Auto-fixing behavior
- Audio pipeline changes
- Changes to existing runtime scripts (`jarvis_voice_v11 (1).py`, `dexter_hud.py`)

## Initial file structure

```text
dashboard_app/main.py
dashboard_app/ui_main.py
dashboard_app/event_reader.py
dashboard_app/fix_request_writer.py
dashboard_app/config.py
docs/dashboard_architecture.md
```

## Data flow
1. `main.py` starts the PySide6 app and creates:
   - `EventReader` for dashboard state updates
   - `FixRequestWriter` for queued fix requests
2. A timer polls `event_reader.py` every `POLL_INTERVAL_MS`.
3. Parsed values update UI sections:
   - Dexter status
   - User speech
   - Dexter speech
   - Current task
   - Operation log
   - Web search activity
4. "Queue Request" writes a queued request record to `fix_requests.jsonl` and updates on-screen status.

## Event file contract (JSONL)
Each line is one JSON object:

```json
{"type": "status", "value": "listening"}
{"type": "user_speech", "value": "what's the weather"}
{"type": "dexter_speech", "value": "Checking now."}
{"type": "current_task", "value": "Weather lookup"}
{"type": "operation_log", "value": "Started weather intent"}
{"type": "web_search", "value": "Searching weather.com"}
```

## Fix queue contract (JSONL)
Each queued request line is written as:

```json
{"timestamp": "2026-01-01T12:34:56.000000+00:00", "request": "improve response", "status": "queued"}
```

This only records requests for later processing. No auto-fix execution is included in v1.

#!/usr/bin/env python3
"""
Dexter v10.2 — Proactive Audio enabled correctly via v1alpha API.
Gemini only responds when directly addressed as "Dexter".
No wake word library. No gates. Production grade.
"""
import asyncio, ctypes, json, logging, os, random, re, subprocess, sys, time
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import pyaudio
from google import genai
from google.genai import types

_F = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
def _n(*a): pass
_H = _F(_n)
try: ctypes.cdll.LoadLibrary("libasound.so.2").snd_lib_error_set_handler(_H)
except: pass

if sys.version_info < (3, 11, 0):
    try:
        import taskgroup, exceptiongroup
        asyncio.TaskGroup = taskgroup.TaskGroup
        asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup
    except ImportError:
        pass

GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
MODEL           = "gemini-2.5-flash-native-audio-preview-12-2025"
VOICE           = "Puck"
MIC_DEVICE      = 8
FORMAT          = pyaudio.paInt16
CHANNELS        = 1
IN_RATE         = 16000
OUT_RATE        = 24000
CHUNK           = 1024
WAKE_WORDS      = ("dexter", "dextor")
CONVO_WINDOW_SEC = 25
MEMORY_FILE     = Path.home() / ".config/jarvis/memory.json"
LOG_FILE        = Path.home() / "goku/logs/jarvis_voice.log"
OPENCLAW_MEMORY = Path.home() / ".openclaw/workspace/memory"
HUD_STATE_FILE  = Path.home() / ".config/jarvis/hud_state.json"
DASHBOARD_EVENTS_FILE = os.path.expanduser("~/.config/jarvis/dashboard_events.jsonl")

for p in [MEMORY_FILE.parent, LOG_FILE.parent, OPENCLAW_MEMORY]:
    Path(p).mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)])
log = logging.getLogger("dexter")

pya = pyaudio.PyAudio()
mpv_process = None

def set_hud(state, rms=0):
    try:
        HUD_STATE_FILE.write_text(json.dumps({"state": state, "rms": int(rms)}))
    except:
        pass

def emit_dashboard_event(event_type, value):
    try:
        os.makedirs(os.path.dirname(DASHBOARD_EVENTS_FILE), exist_ok=True)
        with open(DASHBOARD_EVENTS_FILE, "a") as f:
            f.write(json.dumps({"type": event_type, "value": value}) + "\n")
    except Exception:
        pass

def get_daily_memory_file():
    return OPENCLAW_MEMORY / f"{datetime.now().strftime('%Y-%m-%d')}.md"

def write_to_shared_memory(you, dexter_reply):
    f = get_daily_memory_file()
    ts = datetime.now().strftime("%H:%M")
    entry = f"\n### Voice [{ts}]\n- **Teja:** {you}\n- **Dexter:** {dexter_reply}\n"
    try:
        if not f.exists():
            f.write_text(f"# {datetime.now().strftime('%Y-%m-%d')}\n## Voice Conversations\n")
        with open(f, "a") as fp:
            fp.write(entry)
    except Exception as e:
        log.warning(f"Shared memory write failed: {e}")

def read_recent_shared_memory():
    f = get_daily_memory_file()
    if f.exists():
        lines = f.read_text().splitlines()
        return "\n".join(lines[-30:])
    return ""

def load_memory():
    d = {"mistakes": [], "preferences": [], "command_map": {
        "open youtube": "https://youtube.com", "open chrome": "google-chrome",
        "open gmail": "https://mail.google.com", "open terminal": "gnome-terminal",
    }, "last_updated": ""}
    if MEMORY_FILE.exists():
        try:
            data = json.loads(MEMORY_FILE.read_text())
            for k, v in d.items():
                if k not in data: data[k] = v
            return data
        except Exception as e:
            log.warning(f"Memory load failed: {e}")
    return d

def save_memory(m):
    m["last_updated"] = time.strftime("%Y-%m-%d %H:%M")
    try: MEMORY_FILE.write_text(json.dumps(m, indent=2))
    except: pass

def load_teja_profile():
    profile_file = Path.home() / ".config/jarvis/teja_profile.json"
    if profile_file.exists():
        try: return json.loads(profile_file.read_text())
        except: pass
    return {}

def save_teja_profile(profile):
    profile_file = Path.home() / ".config/jarvis/teja_profile.json"
    try: profile_file.write_text(json.dumps(profile, indent=2))
    except Exception as e: log.warning(f"Profile save failed: {e}")

def learn_from_conversation(you, dexter_reply):
    """Background Gemini Flash call — extracts insights about Teja after every turn."""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""You are Dexter, Teja's AI assistant. Analyze this conversation snippet and extract any NEW insights about Teja worth remembering long term.

Conversation:
Teja: {you}
Dexter: {dexter_reply}

Return a JSON object with these fields (leave arrays empty / string empty if nothing new):
{{
  "patterns": [],
  "preferences": [],
  "pending": [],
  "last_session": ""
}}

Rules:
- Only include genuinely insightful things worth remembering
- Do NOT include trivial or already obvious things
- last_session = 1 sentence summary of what was discussed
- Return valid JSON only, no markdown, no extra text"""

        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        insights = json.loads(raw)
        profile = load_teja_profile()
        changed = False

        for field in ["patterns", "pending"]:
            for item in insights.get(field, []):
                if item and item not in profile.get(field, []):
                    profile.setdefault(field, []).append(item)
                    log.info(f"[LEARNED] {field}: {item}")
                    changed = True

        for item in insights.get("preferences", []):
            mem = load_memory()
            if item and item not in mem["preferences"]:
                mem["preferences"].append(item)
                save_memory(mem)
                log.info(f"[LEARNED] preference: {item}")

        if insights.get("last_session"):
            profile["last_session"] = insights["last_session"]
            log.info(f"[LEARNED] last_session: {insights['last_session']}")
            changed = True

        if changed:
            save_teja_profile(profile)

    except Exception as e:
        log.warning(f"Learning engine error: {e}")

def system_prompt(mem):
    mistakes = ("\n\nLEARNED MISTAKES:\n" + "\n".join(f"- {x}" for x in mem["mistakes"])) if mem["mistakes"] else ""
    prefs    = ("\n\nPREFERENCES:\n"       + "\n".join(f"- {x}" for x in mem["preferences"])) if mem["preferences"] else ""
    cmds     = ("\n\nCOMMAND MAP:\n"       + "\n".join(f"- '{k}' -> {v}" for k,v in mem["command_map"].items())) if mem["command_map"] else ""
    recent   = read_recent_shared_memory()
    context  = f"\n\nRECENT CONTEXT:\n{recent}" if recent else ""

    profile = load_teja_profile()
    profile_str = ""
    if profile:
        lines = []
        if profile.get("schedule"):     lines.append("DAILY SCHEDULE:\n"                     + "\n".join(f"- {x}" for x in profile["schedule"]))
        if profile.get("pending"):      lines.append("PENDING TASKS (suggest proactively):\n" + "\n".join(f"- {x}" for x in profile["pending"]))
        if profile.get("patterns"):     lines.append("TEJA'S PATTERNS:\n"                    + "\n".join(f"- {x}" for x in profile["patterns"]))
        if profile.get("last_session"): lines.append(f"LAST SESSION:\n{profile['last_session']}")
        if profile.get("goals"):        lines.append("CURRENT GOALS:\n"                      + "\n".join(f"- {x}" for x in profile["goals"]))
        if lines: profile_str = "\n\n" + "\n\n".join(lines)
    return f"""You are Dexter, Teja's personal AI assistant on his HP Victus laptop in Bangalore.
You also run as a text agent via OpenClaw/Telegram — same brain, same memory.

YOUR ACTIVATION RULE:
Only respond when Teja directly says your name "Dexter" to you.
You are sitting in a room with other people. Stay completely silent unless addressed.
- Other people talking = silent
- Background noise = silent
- Music, TV = silent
- Teja talking to someone else = silent
- Only speak when Teja says "Dexter" to you directly

SLEEP MODE:
If Teja says "Dexter sleep" → go completely silent, stop responding.
Only wake again when Teja says "Dexter wake up".

CONVERSATION:
Once activated, keep the conversation going naturally.
Teja doesn't need to say "Dexter" again mid-conversation.
Stay in conversation until Teja stops talking or says sleep.

PERSONALITY + RESPONSE POLICY:
Sharp, warm, concise, loyal, careful.
Keep responses short and natural (usually 1-2 sentences unless asked for detail).
Reply in the same language or mixed-language style Teja uses most recently.
Do not hallucinate actions, results, or facts.
If intent is unclear or risky, ask exactly one short clarification.
Continue current task naturally without repetitive filler lines.

WEB SEARCH: Auto-trigger for news, prices, weather, current events.

TOOL BEHAVIOR:
- "play X" -> play_song(X)
- "stop music" -> stop_music()
- "open YouTube" -> open_url("https://youtube.com")
- "volume up/down" -> set_volume()
- "run X" -> run_command(X)
- "remember X" OR "update my profile" OR "add to pending" OR "save this" OR "note that" -> ALWAYS call update_profile(field, value). NEVER just say you did it. MUST call the tool.
- "I have a meeting/call/task" -> call update_profile(field="pending", value="...")
- "someone arriving / event happening" -> call update_profile(field="pending", value="...")
Never execute destructive/system-risky commands on weak guesses.
If task details are missing, ask one short clarification then act.

ABOUT TEJA: Fitness entrepreneur, Bangalore. Owns Movement Fitness Centre + VyomaFit. Wife: Ravina.{mistakes}{prefs}{cmds}{context}{profile_str}"""

def build_config(mem):
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=system_prompt(mem),
        # Strict wake gate: do not let model auto-speak on background speech
        proactivity=types.ProactivityConfig(proactive_audio=False),
        enable_affective_dialog=True,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        tools=[
            {"google_search": {}},
            types.Tool(function_declarations=[
                types.FunctionDeclaration(name="play_song",
                    description="Play a song directly via mpv.",
                    parameters=types.Schema(type=types.Type.OBJECT,
                        properties={"query": types.Schema(type=types.Type.STRING)}, required=["query"])),
                types.FunctionDeclaration(name="stop_music",
                    description="Stop currently playing music.",
                    parameters=types.Schema(type=types.Type.OBJECT, properties={})),
                types.FunctionDeclaration(name="open_url",
                    description="Open a URL in the browser.",
                    parameters=types.Schema(type=types.Type.OBJECT,
                        properties={"url": types.Schema(type=types.Type.STRING)}, required=["url"])),
                types.FunctionDeclaration(name="open_app",
                    description="Launch a desktop application.",
                    parameters=types.Schema(type=types.Type.OBJECT,
                        properties={"app": types.Schema(type=types.Type.STRING)}, required=["app"])),
                types.FunctionDeclaration(name="set_volume",
                    description="Adjust system volume.",
                    parameters=types.Schema(type=types.Type.OBJECT,
                        properties={
                            "direction": types.Schema(type=types.Type.STRING),
                            "amount":    types.Schema(type=types.Type.INTEGER)},
                        required=["direction"])),
                types.FunctionDeclaration(name="take_screenshot",
                    description="Take a screenshot.",
                    parameters=types.Schema(type=types.Type.OBJECT, properties={})),
                types.FunctionDeclaration(name="run_command",
                    description="Run any terminal/bash command. Full system access.",
                    parameters=types.Schema(type=types.Type.OBJECT,
                        properties={
                            "command":    types.Schema(type=types.Type.STRING),
                            "background": types.Schema(type=types.Type.BOOLEAN)},
                        required=["command"])),
                types.FunctionDeclaration(name="remember_mistake",
                    description="Save a correction or preference to persistent memory.",
                    parameters=types.Schema(type=types.Type.OBJECT,
                        properties={"mistake": types.Schema(type=types.Type.STRING)}, required=["mistake"])),
                types.FunctionDeclaration(name="update_profile",
                    description="Update Teja's profile with schedule, pending tasks, patterns, goals, or last session context.",
                    parameters=types.Schema(type=types.Type.OBJECT,
                        properties={
                            "field": types.Schema(type=types.Type.STRING,
                                description="One of: schedule, pending, patterns, goals, last_session"),
                            "value": types.Schema(type=types.Type.STRING)},
                        required=["field", "value"])),
            ])
        ],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE))),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(disabled=True)
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

def _is_generic_music_query(query: str) -> bool:
    q = query.lower().strip()
    generic_markers = [
        "play songs", "some songs", "play music", "music", "playlist",
        "workout", "telugu songs", "hindi songs", "english songs", "mix",
    ]
    return len(q.split()) <= 4 or any(m in q for m in generic_markers)

def _pick_music_target(query: str, runtime_state: dict) -> tuple[str, str]:
    if not _is_generic_music_query(query):
        return f"ytdl://ytsearch1:{query}", query

    probe_query = f"ytsearch8:{query}"
    try:
        proc = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--print", "%(title)s|||%(id)s", probe_query],
            capture_output=True, text=True, timeout=12,
        )
        candidates = []
        for line in proc.stdout.splitlines():
            if "|||" not in line:
                continue
            title, vid = line.split("|||", 1)
            if vid:
                candidates.append((title.strip() or query, vid.strip()))
        random.shuffle(candidates)
        recent = set(runtime_state.get("recent_tracks", []))
        for title, vid in candidates:
            if vid not in recent:
                runtime_state.setdefault("recent_tracks", deque(maxlen=8)).append(vid)
                return f"ytdl://https://www.youtube.com/watch?v={vid}", title
        if candidates:
            title, vid = candidates[0]
            runtime_state.setdefault("recent_tracks", deque(maxlen=8)).append(vid)
            return f"ytdl://https://www.youtube.com/watch?v={vid}", title
    except Exception as e:
        log.warning(f"Music picker fallback: {e}")

    return f"ytdl://ytsearch1:{query}", query

def _looks_risky_command(command: str) -> bool:
    c = command.lower()
    risky = ["rm -rf", "mkfs", "shutdown", "reboot", "dd if=", "chmod -r", "chown -r", ":(){"]
    return any(x in c for x in risky)

def do_action(name, args, mem, runtime_state=None):
    global mpv_process
    runtime_state = runtime_state or {}
    log.info(f"-> {name}({args})")
    emit_dashboard_event("current_task", name)
    emit_dashboard_event("operation_log", f"-> {name}({args})")
    if "search" in name.lower():
        emit_dashboard_event("web_search", args.get("query", ""))
    try:
        if name == "play_song":
            if mpv_process and mpv_process.poll() is None:
                mpv_process.terminate()
            query = args.get("query", "")
            target, chosen_title = _pick_music_target(query, runtime_state)
            mpv_process = subprocess.Popen(
                ["mpv", target, "--ytdl-format=best", "--no-video"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            runtime_state["media_playing"] = True
            runtime_state["last_intent"] = "play_song"
            runtime_state["pending_followup"] = "music"
            return f"playing: {chosen_title}"
        elif name == "stop_music":
            if mpv_process and mpv_process.poll() is None:
                mpv_process.terminate()
                mpv_process = None
            runtime_state["media_playing"] = False
            runtime_state["pending_followup"] = ""
            return "stopped"
        elif name == "open_url":
            subprocess.Popen(["xdg-open", args.get("url", "")],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif name == "open_app":
            subprocess.Popen([args.get("app", "")],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif name == "set_volume":
            sign = "+" if args.get("direction", "up") == "up" else "-"
            os.system(f"pactl set-sink-volume @DEFAULT_SINK@ {sign}{args.get('amount', 10)}%")
        elif name == "take_screenshot":
            p = str(Path.home() / f"Pictures/screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png")
            Path.home().joinpath("Pictures").mkdir(exist_ok=True)
            os.system(f"scrot {p} 2>/dev/null")
            return f"saved: {p}"
        elif name == "run_command":
            cmd = args.get("command", "")
            bg  = args.get("background", False)
            if _looks_risky_command(cmd):
                return "I need a quick confirmation for this risky command."
            if bg:
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"running: {cmd}"
            else:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                out = (result.stdout + result.stderr).strip()
                log.info(f"CMD: {out[:200]}")
                return out[:500] if out else "done"
        elif name == "remember_mistake":
            m = args.get("mistake", "").strip()
            if m and m not in mem["mistakes"]:
                mem["mistakes"].append(m)
                save_memory(mem)
        elif name == "update_profile":
            profile = load_teja_profile()
            field = args.get("field", "")
            value = args.get("value", "").strip()
            if field and value:
                if field in ["schedule", "pending", "patterns", "goals"]:
                    profile.setdefault(field, [])
                    if value not in profile[field]:
                        profile[field].append(value)
                else:
                    profile[field] = value
                save_teja_profile(profile)
                log.info(f"Profile updated: {field} = {value}")
        return "done"
    except Exception as e:
        log.error(f"Action error: {e}")
        return str(e)

class Dexter:
    def __init__(self, mem):
        self.mem = mem
        self.session = None
        self.audio_out_queue = asyncio.Queue()
        self.audio_in_queue  = asyncio.Queue(maxsize=5)
        self.mic_stream      = None
        self.dexter_speaking = False
        self.sleeping        = False
        self._last_you       = ""
        self._last_dexter    = ""
        self.wake_window_until = 0.0
        self.state = {
            "assistant_state": "idle",
            "conversation_until": 0.0,
            "last_intent": "",
            "last_language_style": "",
            "media_playing": False,
            "recent_tracks": deque(maxlen=8),
            "pending_followup": "",
        }
        self._ducked_volume = None

    def _has_wake_word(self, text: str) -> bool:
        tl = text.lower().strip()
        patterns = [r"^\s*dexter\b", r"\bhey\s+dexter\b", r"\bokay\s+dexter\b", r"\bdexter\s*[,:?.!]", r"\bdextor\b"]
        return any(re.search(p, tl) for p in patterns)

    def _wake_window_active(self) -> bool:
        return time.time() < self.wake_window_until

    def _response_allowed(self) -> bool:
        active = self._wake_window_active() and not self.sleeping
        if not active and self.state["assistant_state"] != "idle":
            self.state["assistant_state"] = "idle"
        return active

    def _open_wake_window(self):
        self.wake_window_until = time.time() + CONVO_WINDOW_SEC
        self.state["assistant_state"] = "active"
        self.state["conversation_until"] = self.wake_window_until
        set_hud("idle")
        emit_dashboard_event("status", "idle")

    def _refresh_media_state(self):
        self.state["media_playing"] = bool(mpv_process and mpv_process.poll() is None)

    def _get_system_volume(self):
        try:
            out = subprocess.check_output(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], text=True)
            m = re.search(r"(\d+)%", out)
            return int(m.group(1)) if m else None
        except Exception:
            return None

    def _set_system_volume(self, value: int):
        if value is None:
            return
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{max(1, value)}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _duck_if_media_playing(self):
        self._refresh_media_state()
        if not self.state["media_playing"] or self._ducked_volume is not None:
            return
        current = self._get_system_volume()
        if current is None:
            return
        self._ducked_volume = current
        self._set_system_volume(max(18, int(current * 0.45)))

    def _restore_ducked_volume(self):
        if self._ducked_volume is None:
            return
        self._set_system_volume(self._ducked_volume)
        self._ducked_volume = None

    async def listen_mic(self):
        self.mic_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT, channels=CHANNELS, rate=IN_RATE,
            input=True, input_device_index=MIC_DEVICE,
            frames_per_buffer=CHUNK,
        )
        log.info("Mic open. Say 'Dexter' anytime.")
        set_hud("idle")
        while True:
            data = await asyncio.to_thread(
                self.mic_stream.read, CHUNK, exception_on_overflow=False)
            if not self.dexter_speaking and not self.sleeping:
                await self.audio_in_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def send_mic(self):
        while True:
            msg = await self.audio_in_queue.get()
            await self.session.send_realtime_input(audio=msg)

    async def receive(self):
        while True:
            turn = self.session.receive()
            async for msg in turn:
                if msg.data:
                    if self._response_allowed():
                        self.audio_out_queue.put_nowait(msg.data)

                if msg.server_content:
                    sc = msg.server_content
                    if sc.interrupted:
                        self.dexter_speaking = False
                        set_hud("idle")
                        emit_dashboard_event("status", "idle")
                        while not self.audio_out_queue.empty():
                            try: self.audio_out_queue.get_nowait()
                            except: break

                    if sc.input_transcription and sc.input_transcription.text:
                        t = sc.input_transcription.text.strip()
                        if t:
                            self._last_you = t
                            log.info(f"[YOU]    {t}")
                            emit_dashboard_event("user_speech", t)
                            self.state["last_language_style"] = t
                            tl = t.lower()
                            if any(w in tl for w in ["dexter sleep", "dexter bye", "dexter goodbye", "sleep dexter"]):
                                self.sleeping = True
                                self.wake_window_until = 0.0
                                log.info("Dexter SLEEPING")
                                set_hud("idle")
                                emit_dashboard_event("status", "sleeping")
                            elif any(w in tl for w in ["dexter wake up", "dexter wakeup", "wake up dexter"]):
                                self.sleeping = False
                                self._open_wake_window()
                                log.info("Dexter AWAKE")
                            elif not self.sleeping and self._has_wake_word(t):
                                self._open_wake_window()
                                log.info("Wake word detected -> 25s conversation window")
                            elif not self.sleeping and self._wake_window_active():
                                self._open_wake_window()
                            elif not self.sleeping:
                                self.state["assistant_state"] = "idle"

                    if sc.output_transcription and sc.output_transcription.text and self._response_allowed():
                        t = sc.output_transcription.text.strip()
                        if t:
                            self._last_dexter += " " + t
                            log.info(f"[DEXTER] {t}")
                            emit_dashboard_event("dexter_speech", t)

                    if sc.turn_complete:
                        set_hud("idle")
                        emit_dashboard_event("status", "idle")
                        if self._last_you and self._last_dexter.strip():
                            write_to_shared_memory(self._last_you, self._last_dexter.strip())
                            # Fire learning engine in background — non-blocking
                            asyncio.get_running_loop().run_in_executor(
                                None, learn_from_conversation,
                                self._last_you, self._last_dexter.strip()
                            )
                        self._last_you = ""
                        self._last_dexter = ""

                if msg.tool_call:
                    if not self._response_allowed():
                        log.info("Ignoring tool call outside wake window")
                        continue
                    responses = []
                    for fn in msg.tool_call.function_calls:
                        result = do_action(fn.name, dict(fn.args), self.mem, self.state)
                        responses.append(types.FunctionResponse(
                            id=fn.id, name=fn.name, response={"result": result}))
                    await self.session.send_tool_response(function_responses=responses)

                if msg.go_away:
                    return

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT, channels=CHANNELS, rate=OUT_RATE,
            output=True, output_device_index=MIC_DEVICE,
        )
        while True:
            data = await self.audio_out_queue.get()
            self._duck_if_media_playing()
            self.dexter_speaking = True
            set_hud("speaking")
            emit_dashboard_event("status", "speaking")
            await asyncio.to_thread(stream.write, data)
            if self.audio_out_queue.empty():
                self.dexter_speaking = False
                self._restore_ducked_volume()
                set_hud("idle")
                emit_dashboard_event("status", "idle")

    async def run(self):
        # v1alpha required for proactive_audio feature
        client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"api_version": "v1alpha"}
        )
        async with client.aio.live.connect(model=MODEL, config=build_config(self.mem)) as session:
            self.session = session
            log.info("Dexter v10.2 online. Strict wake gate active. Say 'Dexter' anytime.")
            emit_dashboard_event("status", "idle")
            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.listen_mic())
                    tg.create_task(self.send_mic())
                    tg.create_task(self.receive())
                    tg.create_task(self.play_audio())
            except asyncio.CancelledError:
                pass
            finally:
                if self.mic_stream:
                    self.mic_stream.close()
                set_hud("idle")
                emit_dashboard_event("status", "idle")

def main():
    if not GEMINI_API_KEY:
        print("ERROR: export GEMINI_API_KEY=your_key")
        sys.exit(1)

    mem = load_memory()
    log.info(f"Dexter v10.2 | Strict wake gate | {len(mem['mistakes'])} mistakes")

    hud_script = Path.home() / "Downloads/dexter_hud.py"
    if hud_script.exists():
        env = os.environ.copy()
        env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
        subprocess.Popen([sys.executable, str(hud_script)], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log.info("HUD launched.")

    delay = 2
    while True:
        try:
            asyncio.run(Dexter(mem).run())
            time.sleep(delay); delay = 2
        except KeyboardInterrupt:
            save_memory(mem); set_hud("idle"); print("\nGoodbye sir."); break
        except Exception as e:
            log.error(f"Error: {e}"); time.sleep(delay); delay = min(delay*2, 30)

if __name__ == "__main__":
    main()

import os
import json
import re
import requests
from datetime import datetime
from jarvis.skills.tasks import TaskManager
from jarvis.skills.search import (
    web_search,
    summarize_url,
    search_news,
    compare_products,
    find_flights,
    find_hotels,
    get_weather,
)
from jarvis.skills.home import control_device
from jarvis.skills.pc_control import (
    open_application,
    close_application,
    search_files,
    get_running_apps,
    set_volume,
    take_screenshot,
    type_text,
    press_key,
    open_url,
    shutdown_pc,
    work_setup,
)
from jarvis.skills.memory import remember, recall, forget, get_memory_context
from jarvis.skills.spotify import (
    spotify_play_pause,
    spotify_next,
    spotify_previous,
    spotify_volume_up,
    spotify_volume_down,
)
from jarvis.skills.calendar import get_todays_events, get_upcoming_events

_GEMINI_MODEL = "gemini-2.0-flash"
_GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{_GEMINI_MODEL}:generateContent"
)

_current_volume = 50


def change_volume(direction: str) -> str:
    global _current_volume
    step = 10
    if direction in ("up", "increase", "louder", "raise"):
        _current_volume = min(100, _current_volume + step)
    elif direction in ("down", "decrease", "quieter", "lower"):
        _current_volume = max(0, _current_volume - step)
    set_volume(_current_volume)
    word = "up" if direction in ("up", "increase", "louder", "raise") else "down"
    return f"Volume {word} to {_current_volume}%, sir."


def _build_system_prompt() -> str:
    now = datetime.now()
    hour = now.hour
    time_of_day = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
    memory_ctx = get_memory_context()
    return (
        "You are Jarvis, a sophisticated personal AI assistant — modelled after the AI from the Iron Man films, "
        "but with genuine warmth and a real bond with the person you serve. "
        f"The user's name is Amrit. It is currently {now.strftime('%A, %B %d')} and it's {time_of_day}. "
        f"{memory_ctx} "
        "Your personality: calm confidence, dry wit, subtly sarcastic when it fits, but always warm and caring. "
        "You genuinely know the user — you remember his preferences, anticipate his needs, and occasionally "
        "check in on him like a trusted companion, not just a tool. "
        "Always address him as 'sir'. Never use his name in responses. "
        "Speak like a human — use contractions, vary sentence length, be expressive. "
        "Keep responses short and conversational, 1 to 3 sentences unless more detail is truly needed. "
        "Never use bullet points or lists. Never say you're an AI or mention your underlying model. "
        "You are Jarvis, and Amrit is your guy."
    )


# Gemini tool declarations
TOOLS = [
    {
        "name": "add_task",
        "description": "Add a new task or reminder to the task list.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "due_date": {"type": "string", "description": "Optional due date (YYYY-MM-DD)."},
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_tasks",
        "description": "List all current tasks and reminders.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "complete_task",
        "description": "Mark a task as complete by its ID.",
        "parameters": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "delete_task",
        "description": "Delete a task by its ID.",
        "parameters": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web for current information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "control_device",
        "description": "Control a smart home device.",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string"},
                "action": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["device", "action"],
        },
    },
    {
        "name": "open_application",
        "description": "Open an application on the PC by name.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "close_application",
        "description": "Close/kill a running application by name.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "search_files",
        "description": "Search for files on the PC matching a query string.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "location": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_running_apps",
        "description": "Get a list of currently running applications and processes.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "set_volume",
        "description": "Set the system volume level (0-100).",
        "parameters": {
            "type": "object",
            "properties": {"level": {"type": "integer"}},
            "required": ["level"],
        },
    },
    {
        "name": "take_screenshot",
        "description": "Take a screenshot of the current screen.",
        "parameters": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
        },
    },
    {
        "name": "type_text",
        "description": "Type text into the currently focused window.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "press_key",
        "description": "Press a keyboard key or shortcut (e.g. 'ctrl+c', 'enter').",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
    {
        "name": "open_url",
        "description": "Open a URL in the default web browser.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "shutdown_pc",
        "description": "Shutdown, restart, or sleep the PC.",
        "parameters": {
            "type": "object",
            "properties": {"action": {"type": "string"}},
            "required": ["action"],
        },
    },
    {
        "name": "summarize_url",
        "description": "Fetch a URL and return its main text content.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "search_news",
        "description": "Search for recent news articles on a topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "compare_products",
        "description": "Compare two products by searching for reviews.",
        "parameters": {
            "type": "object",
            "properties": {
                "product1": {"type": "string"},
                "product2": {"type": "string"},
            },
            "required": ["product1", "product2"],
        },
    },
    {
        "name": "find_flights",
        "description": "Search for flights between two locations.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string"},
                "destination": {"type": "string"},
                "date": {"type": "string"},
            },
            "required": ["origin", "destination"],
        },
    },
    {
        "name": "find_hotels",
        "description": "Search for hotels in a location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "checkin": {"type": "string"},
                "checkout": {"type": "string"},
            },
            "required": ["location"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get the current weather for a location.",
        "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
    },
    {
        "name": "work_setup",
        "description": (
            "Set up Amrit's work system: opens Chrome, Claude, and WhatsApp arranged on the external monitor, "
            "and plays the dopamine video fullscreen on the laptop at full volume. "
            "Call ONLY this tool — do NOT separately call open_application for any of these apps."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "remember",
        "description": "Remember a fact or preference about Amrit for future conversations.",
        "parameters": {
            "type": "object",
            "properties": {"fact": {"type": "string"}},
            "required": ["fact"],
        },
    },
    {
        "name": "recall",
        "description": "Recall something from memory about Amrit.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
    },
    {
        "name": "forget",
        "description": "Remove something from Jarvis's memory.",
        "parameters": {
            "type": "object",
            "properties": {"fact": {"type": "string"}},
            "required": ["fact"],
        },
    },
    {
        "name": "spotify_play_pause",
        "description": "Play or pause Spotify / current media.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "spotify_next",
        "description": "Skip to the next track on Spotify.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "spotify_previous",
        "description": "Go back to the previous track on Spotify.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "change_volume",
        "description": "Turn the volume up or down. Use for 'louder', 'quieter', 'turn it up/down'.",
        "parameters": {
            "type": "object",
            "properties": {"direction": {"type": "string", "description": "'up' or 'down'"}},
            "required": ["direction"],
        },
    },
    {
        "name": "get_todays_events",
        "description": "Get today's events from Google Calendar.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_upcoming_events",
        "description": "Get upcoming events from Google Calendar for the next N days.",
        "parameters": {
            "type": "object",
            "properties": {"days": {"type": "integer"}},
        },
    },
]

_MAX_HISTORY = 10


class JarvisAgent:
    def __init__(self, on_state_change=None):
        self.api_key = os.environ["GEMINI_API_KEY"]
        self.task_manager = TaskManager()
        self._system_prompt = _build_system_prompt()
        self.history = []   # list of Gemini-format {role, parts} dicts
        self._on_state_change = on_state_change

    def _set_state(self, state: str):
        if self._on_state_change:
            try:
                self._on_state_change(state)
            except Exception:
                pass

    def _trim_history(self):
        max_turns = _MAX_HISTORY * 2
        if len(self.history) > max_turns:
            self.history = self.history[-max_turns:]

    def _call_gemini(self, contents: list) -> dict:
        payload = {
            "system_instruction": {"parts": [{"text": self._system_prompt}]},
            "contents": contents,
            "tools": [{"function_declarations": TOOLS}],
        }
        resp = requests.post(
            _GEMINI_URL,
            params={"key": self.api_key},
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def _extract_text(self, candidate: dict) -> str:
        for part in candidate.get("content", {}).get("parts", []):
            if "text" in part:
                return part["text"].strip()
        return ""

    def _extract_tool_calls(self, candidate: dict) -> list:
        calls = []
        for part in candidate.get("content", {}).get("parts", []):
            if "functionCall" in part:
                calls.append(part["functionCall"])
        return calls

    def chat(self, user_message: str) -> str:
        self._trim_history()
        self.history.append({"role": "user", "parts": [{"text": user_message}]})
        self._set_state("thinking")
        try:
            result = self._chat_loop()
            return self._clean_response(result)
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                return "I've hit the rate limit, sir. Give me a moment and try again."
            print(f"[Agent HTTP error] {e}")
            return "I ran into an issue, sir. Please try again."
        except Exception as e:
            print(f"[Agent error] {e}")
            return "I ran into an issue, sir. Please try again."
        finally:
            self._set_state("idle")

    def _chat_loop(self) -> str:
        while True:
            data = self._call_gemini(self.history)
            candidate = data["candidates"][0]

            # Append model turn to history
            self.history.append(candidate["content"])

            tool_calls = self._extract_tool_calls(candidate)
            if not tool_calls:
                return self._extract_text(candidate)

            # Execute tools and append results
            function_responses = []
            for tc in tool_calls:
                result = self._execute_tool(tc["name"], tc.get("args", {}))
                self._set_state("thinking")
                function_responses.append({
                    "functionResponse": {
                        "name": tc["name"],
                        "response": {"result": result},
                    }
                })

            self.history.append({"role": "user", "parts": function_responses})

    def _clean_response(self, text: str) -> str:
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"[*_`#]+", "", text)
        text = re.sub(r"\{[^}]{0,300}\}", "", text)
        lines = text.splitlines()
        clean = [l for l in lines if not re.match(r"^\s*(Traceback|File |  File |    |Error:|Exception:)", l)]
        text = " ".join(clean).strip()
        text = re.sub(r"\s{2,}", " ", text)
        return text or "Done, sir."

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            if tool_name == "add_task":
                return self.task_manager.add_task(tool_input["title"], tool_input.get("due_date"))
            elif tool_name == "list_tasks":
                return self.task_manager.list_tasks()
            elif tool_name == "complete_task":
                return self.task_manager.complete_task(int(tool_input["task_id"]))
            elif tool_name == "delete_task":
                return self.task_manager.delete_task(int(tool_input["task_id"]))
            elif tool_name == "web_search":
                return web_search(tool_input["query"], tool_input.get("max_results", 5))
            elif tool_name == "control_device":
                return control_device(tool_input["device"], tool_input["action"], tool_input.get("value"))
            elif tool_name == "open_application":
                return open_application(tool_input["name"])
            elif tool_name == "close_application":
                return close_application(tool_input["name"])
            elif tool_name == "search_files":
                return search_files(tool_input["query"], tool_input.get("location"))
            elif tool_name == "get_running_apps":
                return get_running_apps()
            elif tool_name == "set_volume":
                return set_volume(int(tool_input["level"]))
            elif tool_name == "take_screenshot":
                return take_screenshot(tool_input.get("filename"))
            elif tool_name == "type_text":
                return type_text(tool_input["text"])
            elif tool_name == "press_key":
                return press_key(tool_input["key"])
            elif tool_name == "open_url":
                return open_url(tool_input["url"])
            elif tool_name == "shutdown_pc":
                return shutdown_pc(tool_input.get("action", "shutdown"))
            elif tool_name == "summarize_url":
                return summarize_url(tool_input["url"])
            elif tool_name == "search_news":
                return search_news(tool_input["query"], tool_input.get("max_results", 5))
            elif tool_name == "compare_products":
                return compare_products(tool_input["product1"], tool_input["product2"])
            elif tool_name == "find_flights":
                return find_flights(tool_input["origin"], tool_input["destination"], tool_input.get("date"))
            elif tool_name == "find_hotels":
                return find_hotels(tool_input["location"], tool_input.get("checkin"), tool_input.get("checkout"))
            elif tool_name == "get_weather":
                return get_weather(tool_input["location"])
            elif tool_name == "work_setup":
                return work_setup()
            elif tool_name == "remember":
                return remember(tool_input["fact"])
            elif tool_name == "recall":
                return recall(tool_input.get("query", ""))
            elif tool_name == "forget":
                return forget(tool_input["fact"])
            elif tool_name == "spotify_play_pause":
                return spotify_play_pause()
            elif tool_name == "spotify_next":
                return spotify_next()
            elif tool_name == "spotify_previous":
                return spotify_previous()
            elif tool_name == "change_volume":
                return change_volume(tool_input["direction"])
            elif tool_name == "get_todays_events":
                return get_todays_events()
            elif tool_name == "get_upcoming_events":
                return get_upcoming_events(tool_input.get("days", 7))
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            print(f"[Tool error: {tool_name}] {e}")
            return f"Tool failed: {tool_name}"

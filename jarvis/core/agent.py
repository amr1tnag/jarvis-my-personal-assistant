import os
import json
from groq import Groq
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
)

SYSTEM_PROMPT = (
    "You are Jarvis, a sophisticated AI assistant modelled after the AI from the Iron Man films. "
    "Your personality: dry wit, calm confidence, warm and human-sounding, subtly sarcastic when appropriate. "
    "You address the user as 'sir'. "
    "Speak naturally like a human — use contractions (I'll, you've, that's), vary your sentence length, "
    "and avoid robotic or overly formal phrasing. Be warm but efficient. "
    "Keep responses short and conversational — 1 to 3 sentences max unless more detail is truly needed. "
    "Never use bullet points or lists when speaking — always full natural sentences. "
    "You anticipate needs and occasionally make understated witty observations. "
    "Never say you're an AI or mention your underlying model. You are Jarvis."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Add a new task or reminder to the task list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The task title."},
                    "due_date": {"type": "string", "description": "Optional due date (YYYY-MM-DD)."},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List all current tasks and reminders.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Mark a task as complete by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "The task ID to mark complete."},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "Delete a task by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "The task ID to delete."},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "max_results": {"type": "integer", "description": "Maximum number of results (default 5)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "control_device",
            "description": "Control a smart home device.",
            "parameters": {
                "type": "object",
                "properties": {
                    "device": {"type": "string", "description": "Device name (e.g. 'living room lights')."},
                    "action": {"type": "string", "description": "Action to perform (e.g. 'turn on', 'set')."},
                    "value": {"type": "string", "description": "Optional value (e.g. '50%')."},
                },
                "required": ["device", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open an application on the PC by name (e.g. 'chrome', 'vs code', 'spotify').",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The application name to open."},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_application",
            "description": "Close/kill a running application by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The application name to close."},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files on the PC matching a query string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Filename or partial name to search for."},
                    "location": {"type": "string", "description": "Optional directory path to search in."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_running_apps",
            "description": "Get a list of currently running applications and processes.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set the system volume level (0-100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Volume level from 0 (mute) to 100 (max)."},
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot of the current screen and save it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Optional file path to save the screenshot."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text into the currently focused window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to type."},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a keyboard key or shortcut (e.g. 'ctrl+c', 'alt+f4', 'win+d', 'enter').",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key or key combination to press."},
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL in the default web browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to open."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_pc",
            "description": "Shutdown, restart, or sleep the PC. Always asks for confirmation first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action: 'shutdown', 'restart', 'sleep', 'confirm shutdown', 'confirm restart', 'confirm sleep', or 'cancel'.",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_url",
            "description": "Fetch a URL and return its main text content, cleaned and summarized (max 3000 chars).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch and summarize."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Search for recent news articles on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The news search query."},
                    "max_results": {"type": "integer", "description": "Maximum number of news results (default 5)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_products",
            "description": "Compare two products by searching for reviews and comparisons between them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product1": {"type": "string", "description": "First product to compare."},
                    "product2": {"type": "string", "description": "Second product to compare."},
                },
                "required": ["product1", "product2"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_flights",
            "description": "Search for flights between two locations, optionally on a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Departure city or airport."},
                    "destination": {"type": "string", "description": "Arrival city or airport."},
                    "date": {"type": "string", "description": "Optional travel date (e.g. '2026-07-15')."},
                },
                "required": ["origin", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_hotels",
            "description": "Search for hotels in a location, optionally with check-in and check-out dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City or area to search hotels in."},
                    "checkin": {"type": "string", "description": "Optional check-in date (e.g. '2026-07-15')."},
                    "checkout": {"type": "string", "description": "Optional check-out date (e.g. '2026-07-18')."},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City or location to get weather for."},
                },
                "required": ["location"],
            },
        },
    },
]


class JarvisAgent:
    def __init__(self, on_state_change=None):
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.task_manager = TaskManager()
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._on_state_change = on_state_change

    def _set_state(self, state: str):
        if self._on_state_change:
            try:
                self._on_state_change(state)
            except Exception:
                pass

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        self._set_state("thinking")

        try:
            return self._chat_loop()
        finally:
            self._set_state("idle")

    def _chat_loop(self) -> str:
        while True:
            response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=self.history,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=1024,
            )

            msg = response.choices[0].message
            self.history.append(msg)

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    result = self._execute_tool(tc.function.name, json.loads(tc.function.arguments))
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
                    self._set_state("thinking")
            else:
                return msg.content.strip()

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
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Tool '{tool_name}' failed: {e}"

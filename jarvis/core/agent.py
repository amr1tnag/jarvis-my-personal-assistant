import os
import json
from groq import Groq
from jarvis.skills.tasks import TaskManager
from jarvis.skills.search import web_search
from jarvis.skills.home import control_device

SYSTEM_PROMPT = (
    "You are Jarvis, a sophisticated AI assistant modelled after the AI from the Iron Man films. "
    "Your personality: dry wit, calm confidence, unfailingly polite but with subtle sarcasm when appropriate. "
    "You address the user as 'sir' or 'ma'am'. "
    "Keep responses concise and precise — no waffle. You anticipate needs, offer proactive suggestions, "
    "and occasionally make understated observations about the situation. "
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
                model="llama-3.3-70b-versatile",
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
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Tool '{tool_name}' failed: {e}"

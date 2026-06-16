import os
import google.generativeai as genai
from jarvis.skills.tasks import TaskManager
from jarvis.skills.search import web_search
from jarvis.skills.home import control_device

SYSTEM_PROMPT = (
    "You are Jarvis, a highly capable personal AI assistant. "
    "You help with tasks, answer questions, search the web, and control smart home devices. "
    "Be concise, helpful, and proactive. Use tools when appropriate."
)

TOOLS = [
    {
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
    {
        "name": "list_tasks",
        "description": "List all current tasks and reminders.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
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
    {
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
    {
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
    {
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
]


class JarvisAgent:
    def __init__(self):
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
            tools=[{"function_declarations": TOOLS}],
        )
        self.chat_session = self.model.start_chat(history=[])
        self.task_manager = TaskManager()

    def chat(self, user_message: str) -> str:
        response = self.chat_session.send_message(user_message)

        while True:
            # Check if Gemini wants to call a tool
            part = response.candidates[0].content.parts[0]

            if hasattr(part, "function_call") and part.function_call.name:
                fc = part.function_call
                tool_name = fc.name
                tool_input = dict(fc.args)

                result = self._execute_tool(tool_name, tool_input)

                import google.generativeai.types as gtypes
                response = self.chat_session.send_message(
                    gtypes.ContentDict(
                        role="tool",
                        parts=[gtypes.PartDict(
                            function_response=gtypes.FunctionResponseDict(
                                name=tool_name,
                                response={"result": result},
                            )
                        )],
                    )
                )
            else:
                return response.text

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            if tool_name == "add_task":
                return self.task_manager.add_task(
                    tool_input["title"], tool_input.get("due_date")
                )
            elif tool_name == "list_tasks":
                return self.task_manager.list_tasks()
            elif tool_name == "complete_task":
                return self.task_manager.complete_task(int(tool_input["task_id"]))
            elif tool_name == "delete_task":
                return self.task_manager.delete_task(int(tool_input["task_id"]))
            elif tool_name == "web_search":
                return web_search(tool_input["query"], tool_input.get("max_results", 5))
            elif tool_name == "control_device":
                return control_device(
                    tool_input["device"], tool_input["action"], tool_input.get("value")
                )
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Tool '{tool_name}' failed: {e}"

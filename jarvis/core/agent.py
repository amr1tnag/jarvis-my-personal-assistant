import anthropic
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
        "description": "Add a new task to the task list.",
        "input_schema": {
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
        "description": "List all tasks.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as complete by its ID.",
        "input_schema": {
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
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "The task ID to delete."},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo.",
        "input_schema": {
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
        "input_schema": {
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
        self.client = anthropic.Anthropic()
        self.history: list[dict] = []
        self.task_manager = TaskManager()

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})

        while True:
            response = self.client.messages.create(
                model="claude-opus-4-8",
                max_tokens=8096,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                messages=self.history,
                tools=TOOLS,
            )

            if response.stop_reason == "tool_use":
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                self.history.append({"role": "assistant", "content": response.content})

                tool_results = []
                for tool_use in tool_uses:
                    result = self._execute_tool(tool_use.name, tool_use.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    })

                self.history.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                reply = "\n".join(text_blocks).strip()
                self.history.append({"role": "assistant", "content": response.content})
                return reply

            else:
                return f"Unexpected stop reason: {response.stop_reason}"

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            if tool_name == "add_task":
                return self.task_manager.add_task(
                    tool_input["title"], tool_input.get("due_date")
                )
            elif tool_name == "list_tasks":
                return self.task_manager.list_tasks()
            elif tool_name == "complete_task":
                return self.task_manager.complete_task(tool_input["task_id"])
            elif tool_name == "delete_task":
                return self.task_manager.delete_task(tool_input["task_id"])
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

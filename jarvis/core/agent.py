import os
from google import genai
from google.genai import types
from jarvis.skills.tasks import TaskManager
from jarvis.skills.search import web_search
from jarvis.skills.home import control_device

SYSTEM_PROMPT = (
    "You are Jarvis, a sophisticated AI assistant "
    "modelled after the AI from the Iron Man films. Your personality: dry wit, calm confidence, "
    "unfailingly polite but with subtle sarcasm when appropriate. You address the user as 'sir' or 'ma'am'. "
    "Keep responses concise and precise — no waffle. You anticipate needs, offer proactive suggestions, "
    "and occasionally make understated observations about the situation. "
    "Never say you're an AI or mention Google. You are Jarvis. Use tools whenever they'd help."
)

TOOLS = [
    types.FunctionDeclaration(
        name="add_task",
        description="Add a new task or reminder to the task list.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "title": types.Schema(type="STRING", description="The task title."),
                "due_date": types.Schema(type="STRING", description="Optional due date (YYYY-MM-DD)."),
            },
            required=["title"],
        ),
    ),
    types.FunctionDeclaration(
        name="list_tasks",
        description="List all current tasks and reminders.",
        parameters=types.Schema(type="OBJECT", properties={}),
    ),
    types.FunctionDeclaration(
        name="complete_task",
        description="Mark a task as complete by its ID.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "task_id": types.Schema(type="INTEGER", description="The task ID to mark complete."),
            },
            required=["task_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="delete_task",
        description="Delete a task by its ID.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "task_id": types.Schema(type="INTEGER", description="The task ID to delete."),
            },
            required=["task_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="web_search",
        description="Search the web for current information.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(type="STRING", description="The search query."),
                "max_results": types.Schema(type="INTEGER", description="Maximum number of results (default 5)."),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="control_device",
        description="Control a smart home device.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "device": types.Schema(type="STRING", description="Device name (e.g. 'living room lights')."),
                "action": types.Schema(type="STRING", description="Action to perform (e.g. 'turn on', 'set')."),
                "value": types.Schema(type="STRING", description="Optional value (e.g. '50%')."),
            },
            required=["device", "action"],
        ),
    ),
]


class JarvisAgent:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.task_manager = TaskManager()
        self.history: list[types.Content] = []
        self.tools = types.Tool(function_declarations=TOOLS)
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[self.tools],
        )

    def chat(self, user_message: str) -> str:
        self.history.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

        while True:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=self.history,
                config=self.config,
            )

            candidate = response.candidates[0].content
            self.history.append(candidate)

            # Check for function calls
            function_calls = [p for p in candidate.parts if p.function_call is not None]

            if function_calls:
                tool_results = []
                for part in function_calls:
                    fc = part.function_call
                    result = self._execute_tool(fc.name, dict(fc.args))
                    tool_results.append(types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result},
                        )
                    ))
                self.history.append(types.Content(role="tool", parts=tool_results))
            else:
                text_parts = [p.text for p in candidate.parts if p.text]
                return "\n".join(text_parts).strip()

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

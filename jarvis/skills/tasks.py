import sqlite3
from pathlib import Path


class TaskManager:
    def __init__(self):
        db_dir = Path.home() / ".jarvis"
        db_dir.mkdir(exist_ok=True)
        self.db_path = db_dir / "tasks.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due_date TEXT,
                    completed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def add_task(self, title: str, due_date: str = None) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (title, due_date) VALUES (?, ?)",
                (title, due_date),
            )
            return f"Task added with ID {cursor.lastrowid}: '{title}'"

    def list_tasks(self) -> str:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, title, due_date, completed FROM tasks ORDER BY id"
            ).fetchall()
        if not rows:
            return "No tasks found."
        lines = []
        for row in rows:
            task_id, title, due_date, completed = row
            status = "done" if completed else "pending"
            due = f" (due: {due_date})" if due_date else ""
            lines.append(f"[{task_id}] [{status}] {title}{due}")
        return "\n".join(lines)

    def complete_task(self, task_id: int) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,)
            )
            if cursor.rowcount == 0:
                return f"No task found with ID {task_id}."
            return f"Task {task_id} marked as complete."

    def delete_task(self, task_id: int) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cursor.rowcount == 0:
                return f"No task found with ID {task_id}."
            return f"Task {task_id} deleted."

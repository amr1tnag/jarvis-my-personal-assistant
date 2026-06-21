import json
import os

_MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "jarvis_memory.json")
_MEMORY_FILE = os.path.abspath(_MEMORY_FILE)

_DEFAULT = {
    "user_name": "Amrit",
    "facts": [],
    "preferences": {},
}


def _load() -> dict:
    if os.path.exists(_MEMORY_FILE):
        try:
            with open(_MEMORY_FILE, "r") as f:
                data = json.load(f)
                return {**_DEFAULT, **data}
        except Exception:
            pass
    return dict(_DEFAULT)


def _save(data: dict):
    with open(_MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def remember(fact: str) -> str:
    data = _load()
    if fact not in data["facts"]:
        data["facts"].append(fact)
        _save(data)
    return f"Got it, I'll remember that."


def recall(query: str = "") -> str:
    data = _load()
    facts = data.get("facts", [])
    if not facts:
        return "I don't have anything stored in memory yet."
    if query:
        q = query.lower()
        matches = [f for f in facts if q in f.lower()]
        if matches:
            return "Here's what I remember: " + "; ".join(matches)
        return "I don't have anything specific about that in memory."
    return "Here's everything I remember: " + "; ".join(facts)


def forget(fact: str) -> str:
    data = _load()
    before = len(data["facts"])
    data["facts"] = [f for f in data["facts"] if fact.lower() not in f.lower()]
    _save(data)
    removed = before - len(data["facts"])
    return f"Done, removed {removed} item(s) from memory." if removed else "I couldn't find that in memory."


def get_user_name() -> str:
    return _load().get("user_name", "Amrit")


def get_memory_context() -> str:
    data = _load()
    facts = data.get("facts", [])
    name = data.get("user_name", "Amrit")
    lines = [f"The user's name is {name}."]
    if facts:
        lines.append("Things Jarvis remembers about the user: " + "; ".join(facts))
    return " ".join(lines)

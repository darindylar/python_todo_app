from flask import Flask, render_template, request, redirect, url_for
import os, json
import datetime as dt
import re

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

DATA_FILE = "tasks.json"

DEFAULT_COLOR = "#6c757d" 

def _valid_hex(s: str | None) -> bool:
    if not s:
        return False
    return bool(re.fullmatch(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})", s))


def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_tasks():
    with open(DATA_FILE, "w") as f:
        json.dump(tasks, f, indent=4)

tasks = load_tasks()

def parse_due_iso(raw: str | None):
    """Parse browser datetime-local string like '2025-10-14T18:30' -> datetime (local)."""
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw)
    except ValueError:
        return None

def humanise_delta(delta: dt.timedelta) -> str:
    secs = int(abs(delta.total_seconds()))
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if mins or not parts: parts.append(f"{mins}m")
    return " ".join(parts)

def augment_for_view(t: dict) -> dict:
    out = dict(t)  # shallow copy
    due_iso = t.get("due")
    out["due_text"] = ""
    out["overdue"] = False
    if due_iso:
        due_dt = parse_due_iso(due_iso)
        if due_dt:
            now = dt.datetime.now()
            delta = due_dt - now
            out["overdue"] = delta.total_seconds() < 0
            out["due_text"] = ("overdue by " if out["overdue"] else "due in ") + humanise_delta(delta)
    out["color"] = t.get("color") if _valid_hex(t.get("color")) else DEFAULT_COLOR
    return out

@app.get("/")
def index():
    # Provide a default min value for the datetime picker (now)
    now_str = dt.datetime.now().strftime("%Y-%m-%dT%H:%M")

    tasks_view = [augment_for_view(t) for t in tasks]

    def sort_key(t):
        return (t.get("done", False),
                t.get("due") is None,
                t.get("due") or "9999-12-31T23:59")
    tasks_view.sort(key=sort_key)

    return render_template(
    "index.html",
    tasks=tasks_view,
    now_str=now_str,
    default_color=DEFAULT_COLOR
    )


@app.post("/add")
def add():
    task_text = request.form.get("task", "").strip()
    due_iso = request.form.get("due", "").strip() or None  
    if task_text:
        color = request.form.get("color", "").strip()
        if not _valid_hex(color):
            color = DEFAULT_COLOR
        tasks.append({"task": task_text, "done": False, "due": due_iso, "color": color})
        save_tasks()
    return redirect(url_for("index"))

@app.get("/complete/<int:index>")
def complete(index):
    if 0 <= index < len(tasks):
        tasks[index]["done"] = True
        save_tasks()
    return redirect(url_for("index"))

@app.get("/delete/<int:index>")
def delete(index):
    if 0 <= index < len(tasks):
        tasks.pop(index)
        save_tasks()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)

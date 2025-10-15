from flask import Flask, render_template, request, redirect, url_for
import os, json
import datetime as dt
import re

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

DATA_FILE = "tasks.json"
CATEGORIES_FILE = "categories.json"
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

def load_categories():
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, "r") as f:
                cats = json.load(f)
                if not isinstance(cats, list):
                    cats = []
        except json.JSONDecodeError:
            cats = []
    else:
        cats = []
    if "General" not in cats:
        cats.append("General")
    seen = set()
    deduped = []
    for c in cats:
        key = c.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(c.strip())
    return deduped

def save_categories():
    with open(CATEGORIES_FILE, "w") as f:
        json.dump(categories, f, indent=4)

tasks = load_tasks()
categories = load_categories()

def parse_due_iso(raw: str | None):
    """Parse 'YYYY-MM-DDTHH:MM' from <input type=datetime-local> to datetime (local)."""
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
    out = dict(t)
    out["due_text"] = ""
    out["overdue"] = False
    due_iso = t.get("due")
    if due_iso:
        due_dt = parse_due_iso(due_iso)
        if due_dt:
            now = dt.datetime.now()
            delta = due_dt - now
            out["overdue"] = delta.total_seconds() < 0
            out["due_text"] = ("overdue by " if out["overdue"] else "due in ") + humanise_delta(delta)
    out["color"] = t.get("color") if _valid_hex(t.get("color")) else DEFAULT_COLOR
    out["category"] = (t.get("category") or "General").strip() or "General"
    return out

@app.get("/")
def index():
    now = dt.datetime.now()
    now_str = now.strftime("%Y-%m-%dT%H:%M")
    default_due_str = (now + dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")  

    def sort_key(t):
        return (
            t.get("done", False),
            t.get("due") is None,
            t.get("due") or "9999-12-31T23:59",
        )
    tasks.sort(key=sort_key)

    base_view = [dict(augment_for_view(t), _idx=i) for i, t in enumerate(tasks)]

    selected_filter = request.args.get("filter", "All").strip() or "All"
    if selected_filter != "All":
        tasks_view = [t for t in base_view if t.get("category") == selected_filter]
    else:
        tasks_view = base_view

    return render_template(
        "index.html",
        tasks=tasks_view,
        categories=categories,
        selected_filter=selected_filter,
        now_str=now_str,
        default_due_str=default_due_str,
        default_color=DEFAULT_COLOR,
    )

@app.post("/add")
def add():
    task_text = request.form.get("task", "").strip()
    due_iso = request.form.get("due", "").strip() or None
    if task_text:
        color = request.form.get("color", "").strip()
        if not _valid_hex(color):
            color = DEFAULT_COLOR
        category_sel = (request.form.get("category", "") or "").strip() or "General"
        if category_sel and category_sel not in categories:
            categories.append(category_sel)
            save_categories()
        tasks.append({
            "task": task_text,
            "done": False,
            "due": due_iso,
            "color": color,
            "category": category_sel
        })
        save_tasks()
    return redirect(url_for("index"))

@app.post("/add_category")
def add_category():
    new_cat = (request.form.get("new_category", "") or "").strip()
    if new_cat:
        key = new_cat.lower()
        if key not in {c.lower() for c in categories}:
            categories.append(new_cat)
            save_categories()
    current_filter = request.args.get("filter")
    if current_filter:
        return redirect(url_for("index", filter=current_filter))
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

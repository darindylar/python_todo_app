from flask import Flask, render_template, request, redirect, url_for
import os

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

tasks = [
    {"task": "Test", "done": False},
]

@app.get("/")
def index():
    print("Serving /  | templates in:", os.listdir("templates") if os.path.isdir("templates") else "NO templates dir")
    return render_template("index.html", tasks=tasks)

@app.post("/add")
def add():
    task = request.form.get("task", "").strip()
    if task:
        tasks.append({"task": task, "done": False})
    return redirect(url_for("index"))

@app.get("/complete/<int:index>")
def complete(index):
    if 0 <= index < len(tasks):
        tasks[index]["done"] = True
    return redirect(url_for("index"))

@app.get("/delete/<int:index>")
def delete(index):
    if 0 <= index < len(tasks):
        tasks.pop(index)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)

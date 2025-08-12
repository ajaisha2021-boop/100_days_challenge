"""
Flask + MongoDB (pymongo) 100 Days Challenge app.

Each task document structure:
{
  "_id": ObjectId,
  "name": str,
  "created_at": "YYYY-MM-DD",
  "completions": ["YYYY-MM-DD", ...]   # dates when user marked it completed
}
"""
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("DB_NAME", "100days")

if not MONGO_URI:
    raise RuntimeError("Please set MONGO_URI environment variable (or create .env).")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
tasks_col = db["tasks"]

app = Flask(__name__)

def today_iso():
    # Use user's timezone Asia/Kolkata (per project requirement)
    tz = ZoneInfo("Asia/Kolkata")
    return datetime.now(tz).date().isoformat()  # YYYY-MM-DD

@app.route("/")
def index():
    docs = list(tasks_col.find().sort("created_at", 1))
    tasks = []
    td = today_iso()
    for d in docs:
        tasks.append({
            "id": str(d["_id"]),
            "name": d.get("name", ""),
            "created_at": d.get("created_at"),
            "completions": d.get("completions", []),
            "completed_today": td in d.get("completions", []),
            "total_completions": len(d.get("completions", [])),
        })
    return render_template("index.html", tasks=tasks, today=td)

@app.route("/add", methods=["POST"])
def add_task():
    name = request.form.get("task_name", "").strip()
    if name:
        doc = {
            "name": name,
            "created_at": today_iso(),
            "completions": []
        }
        tasks_col.insert_one(doc)
    return redirect(url_for("index"))

@app.route("/complete/<task_id>", methods=["POST"])
def complete_task(task_id):
    """
    Toggle completion for today:
    - If today not in completions: append it (mark completed today)
    - If today already present: remove it (unmark)
    """
    td = today_iso()
    try:
        oid = ObjectId(task_id)
    except Exception:
        return "Invalid id", 400

    task = tasks_col.find_one({"_id": oid})
    if not task:
        return "Task not found", 404

    completions = task.get("completions", [])
    if td in completions:
        # unmark
        tasks_col.update_one({"_id": oid}, {"$pull": {"completions": td}})
    else:
        # mark
        tasks_col.update_one({"_id": oid}, {"$push": {"completions": td}})

    return redirect(url_for("index"))

@app.route("/delete/<task_id>", methods=["POST"])
def delete_task(task_id):
    try:
        oid = ObjectId(task_id)
    except Exception:
        return "Invalid id", 400
    tasks_col.delete_one({"_id": oid})
    return redirect(url_for("index"))

if __name__ == "__main__":
    # don't use debug mode on production
    app.run(debug=True, host="0.0.0.0", port=5051)

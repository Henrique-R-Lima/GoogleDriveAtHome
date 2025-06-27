import os
import json
import time
import base64
import threading
import requests
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# === CONFIGURATION ===
WORKING_DIR = os.getcwd()
WATCH_PATH = os.path.join(WORKING_DIR, "test_chamber")
CLOUD_PEERS = ["http://172.21.17.21:5000", "http://172.21.17.22:5000"]
MACHINE_ID = f"user-{os.uname().nodename}"

# === Flask setup ===
app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app)

# === Data State ===
pending_changes = []
current_state = []

def get_fastest_peer():
    for url in CLOUD_PEERS:
        try:
            start = time.time()
            r = requests.get(f"{url}/get_full_state", timeout=3)
            if r.status_code == 200:
                print(f"Selected peer: {url}")
                return url, r.json()
        except:
            continue
    return None, []

def apply_remote_state(remote_state):
    for root, dirs, files in os.walk(WATCH_PATH, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

    for item in remote_state:
        path = os.path.join(WORKING_DIR, item['path'])
        if item['is_directory']:
            os.makedirs(path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(base64.b64decode(item['content'].encode('utf-8')))
            os.utime(path, (item['last_modified'], item['last_modified']))

def push_changes():
    success = 0
    for peer in CLOUD_PEERS:
        for change in pending_changes:
            try:
                requests.post(f"{peer}/push_change", json=change, timeout=3)
                success += 1
            except:
                continue
    pending_changes.clear()
    return success

# === Watchdog File Monitor ===
class ChangeHandler(FileSystemEventHandler):
    def dispatch(self, event):
        if event.is_directory and not os.path.exists(event.src_path):
            return  # skip temporary directory events

        rel_src = os.path.relpath(event.src_path, WORKING_DIR)
        change = {
            'timestamp': datetime.now().isoformat(),
            'src': rel_src,
            'is_directory': event.is_directory,
            'origin': MACHINE_ID
        }

        if event.event_type == 'created':
            change['type'] = 'created'
        elif event.event_type == 'modified':
            change['type'] = 'modified'
        elif event.event_type == 'deleted':
            change['type'] = 'deleted'
        elif event.event_type == 'moved':
            change['type'] = 'moved'
            change['dest'] = os.path.relpath(event.dest_path, WORKING_DIR)

        if change['type'] in ['created', 'modified'] and not change['is_directory']:
            try:
                with open(event.src_path, 'rb') as f:
                    change['content'] = base64.b64encode(f.read()).decode('utf-8')
            except:
                return

        pending_changes.append(change)
        socketio.emit('change_detected', change)

# === Flask Web Routes ===
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/pull", methods=["POST"])
def api_pull():
    peer, data = get_fastest_peer()
    if peer:
        apply_remote_state(data)
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "No cloud responded"}), 500

@app.route("/api/push", methods=["POST"])
def api_push():
    count = push_changes()
    return jsonify({"status": "ok", "changes_pushed": count})

@app.route("/api/status")
def api_status():
    result = []
    for root, dirs, files in os.walk(WATCH_PATH):
        for name in files:
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, WORKING_DIR)
            result.append({
                'path': rel_path,
                'mtime': os.path.getmtime(abs_path),
                'status': 'modified' if any(c['src'] == rel_path for c in pending_changes) else 'synced'
            })
    return jsonify(result)

# === App Start ===
if __name__ == "__main__":
    os.makedirs(WATCH_PATH, exist_ok=True)
    print("Initial sync from cloud...")
    peer, data = get_fastest_peer()
    if data:
        apply_remote_state(data)

    observer = Observer()
    observer.schedule(ChangeHandler(), path=WATCH_PATH, recursive=True)
    observer.start()

    threading.Thread(target=socketio.run, args=(app,), kwargs={'host': '0.0.0.0', 'port': 7000}).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        print("Stopped")

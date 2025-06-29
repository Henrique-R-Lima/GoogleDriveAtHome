import os
import time
import json
import shutil
import socket
import base64
import threading
import requests
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# ========== CONFIGURATION ==========

CLOUD_PEERS = [
    "http://192.168.15.68:5000"
    "http://192.168.15.122:5000"
]

connected = False  # Tracks if a peer is currently reachable

WORKING_DIR = os.getcwd()
WATCH_PATH = os.path.join(WORKING_DIR, "test_chamber")
CHANGE_LOG = os.path.join(WORKING_DIR, "change_log.json")

MACHINE_ID = f"user-{socket.gethostname()}"

# ========== STATE ==========

pending_changes = []
current_peer = None
app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*")

# ========== LOGGING ==========

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ========== FILE I/O ==========

def write_file_content(path, content_b64):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(content_b64.encode('utf-8')))
    except Exception as e:
        log(f"Error writing file {path}: {e}")

def read_file_content(path):
    try:
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        log(f"Error reading {path}: {e}")
        return None

# ========== SYNC ENGINE ==========

def get_fastest_peer():
    global connected
    for url in CLOUD_PEERS:
        try:
            r = requests.get(f"{url}/get_full_state", timeout=3)
            if r.status_code == 200:
                if not connected:
                    connected = True
                    socketio.emit("peer_status", {"connected": True})
                log(f"Peer selected: {url}")
                return url, r.json()
        except Exception as e:
            log(f"Peer {url} unreachable")
    if connected:
        connected = False
        socketio.emit("peer_status", {"connected": False})
    return None, []


def apply_remote_state(data):
    for item in data:
        path = os.path.join(WORKING_DIR, item['path'])

        if item['is_directory']:
            os.makedirs(path, exist_ok=True)
            continue

        content = item.get('content', '')
        write_file_content(path, content)
        if 'last_modified' in item:
            os.utime(path, (item['last_modified'], item['last_modified']))

def initial_sync():
    global current_peer
    peer, data = get_fastest_peer()
    if peer and data:
        log("Initial sync from peer")
        current_peer = peer
        apply_remote_state(data)
    else:
        log("No cloud peer reachable at startup. Running in offline mode.")

def retry_peer_discovery():
    global current_peer
    while True:
        time.sleep(30)
        if current_peer is None:
            peer, data = get_fastest_peer()
            if peer and data:
                current_peer = peer
                apply_remote_state(data)
                log("Peer became available. State pulled.")

# ========== WATCHDOG ==========

class UserSyncHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last = {}

    def record_change(self, event_type, src_path, is_dir, dest_path=None):
        rel_src = os.path.relpath(src_path, WORKING_DIR)
        rel_dest = os.path.relpath(dest_path, WORKING_DIR) if dest_path else None
        if rel_src.startswith(os.path.basename(__file__)):
            return

        now = datetime.now().timestamp()
        key = (event_type, rel_src, rel_dest)
        if now - self.last.get(key, 0) < 0.5:
            return
        self.last[key] = now

        change = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "src": rel_src,
            "is_directory": is_dir,
            "origin": MACHINE_ID
        }
        if dest_path:
            change["dest"] = rel_dest
        if event_type in ["created", "modified"] and not is_dir:
            content = read_file_content(src_path)
            if content:
                change["content"] = content

        pending_changes.append(change)
        socketio.emit("change", change)

    def on_created(self, event):
        self.record_change("created", event.src_path, event.is_directory)

    def on_deleted(self, event):
        self.record_change("deleted", event.src_path, event.is_directory)

    def on_modified(self, event):
        self.record_change("modified", event.src_path, event.is_directory)

    def on_moved(self, event):
        self.record_change("moved", event.src_path, event.is_directory, event.dest_path)

# ========== API ROUTES ==========

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    file_state = []
    for root, dirs, files in os.walk(WATCH_PATH):
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, WORKING_DIR)
            try:
                mtime = os.path.getmtime(path)
                file_state.append({"path": rel, "mtime": mtime, "status": "synced"})
            except:
                pass
        for name in dirs:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, WORKING_DIR)
            file_state.append({"path": rel, "is_directory": True, "status": "synced"})
    return jsonify({
        "pending": pending_changes,
        "files": file_state,
        "peer_connected": connected
    })

@app.route("/api/pull", methods=["POST"])
def api_pull():
    global current_peer
    peer, data = get_fastest_peer()
    if not peer:
        return jsonify({"status": "error", "message": "No cloud peer reachable"}), 500
    current_peer = peer
    apply_remote_state(data)
    return jsonify({"status": "ok"})

@app.route("/api/push", methods=["POST"])
def api_push():
    if not pending_changes:
        return jsonify({"status": "ok", "message": "No changes to push"})

    success = 0
    for peer in CLOUD_PEERS:
        for change in pending_changes:
            try:
                r = requests.post(f"{peer}/push_change", json=change, timeout=5)
                if r.status_code == 200:
                    success += 1
            except Exception as e:
                log(f"Push to {peer} failed: {e}")

    if success:
        pending_changes.clear()
        return jsonify({"status": "ok", "message": "Changes pushed"})
    else:
        return jsonify({"status": "error", "message": "Push failed"}), 500

# ========== MAIN ==========

def start():
    os.makedirs(WATCH_PATH, exist_ok=True)
    initial_sync()
    threading.Thread(target=retry_peer_discovery, daemon=True).start()

    observer = Observer()
    observer.schedule(UserSyncHandler(), path=WATCH_PATH, recursive=True)
    observer.start()

    try:
        socketio.run(app, host="0.0.0.0", port=7000)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start()

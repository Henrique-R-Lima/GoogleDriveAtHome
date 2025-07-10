import os
import sys
import time
import json
import shutil
import socket
import base64
import threading
import requests
import webbrowser
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# ========== CONFIGURATION ==========

SERVERS = []

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

def clear_directory_contents(path):
    """
    Deletes all files and subdirectories in the specified directory.
    The directory itself is not deleted.
    """
    if not os.path.isdir(path):
        raise ValueError(f"{path} is not a valid directory")

    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")

# ========== SYNC ENGINE ==========

def get_fastest_peer():
    global connected
    for url in SERVERS:
        try:
            r = requests.get(f"http://{url}:5000/get_full_state", timeout=3)
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
    if data:
        for item in data:
            path = os.path.join(WORKING_DIR, item['path'])

            if item['is_directory']:
                os.makedirs(path, exist_ok=True)
                continue

            content = item.get('content', '')
            write_file_content(path, content)
            if 'last_modified' in item:
                os.utime(path, (item['last_modified'], item['last_modified']))
    else:
        clear_directory_contents(WATCH_PATH)

def initial_sync():
    global current_peer
    peer, data = get_fastest_peer()
    if peer:
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

# Push and pull now check for the fastest peer before action
@app.route("/api/pull", methods=["POST"])
def api_pull():
    global current_peer
    best_peer = None
    best_time = float("inf")
    best_data = None

    # Try all peers and select the fastest
    for peer in SERVERS:
        try:
            start = time.time()
            r = requests.get(f"http://{peer}:5000/get_full_state", timeout=5)
            if r.status_code == 200:
                elapsed = time.time() - start
                if elapsed < best_time:
                    best_time = elapsed
                    best_peer = peer
                    best_data = r.json()
        except Exception as e:
            log(f"Peer {peer} unreachable during pull selection: {e}")

    if not best_peer:
        return jsonify({"status": "error", "message": "No reachable peers"}), 502

    current_peer = best_peer
    apply_remote_state(best_data)
    log(f"Pulled from fastest peer: {best_peer}")
    return jsonify({"status": "ok", "message": f"Pulled from {best_peer}"})

@app.route("/api/push", methods=["POST"])
def api_push():
    global pending_changes

    if not pending_changes:
        return jsonify({"status": "ok", "message": "No changes to push"})

    best_peer = None
    best_time = float("inf")

    # Try all peers and find the fastest responder
    for peer in SERVERS:
        try:
            start = time.time()
            test = requests.get(f"http://{peer}:5000/get_full_state", timeout=3)
            if test.status_code == 200:
                elapsed = time.time() - start
                if elapsed < best_time:
                    best_time = elapsed
                    best_peer = peer
        except Exception as e:
            log(f"Peer {peer} unreachable during push selection: {e}")

    if not best_peer:
        return jsonify({"status": "error", "message": "No reachable peers"}), 502

    # Push all changes to the fastest peer
    success = True
    for change in pending_changes:
        try:
            r = requests.post(f"http://{best_peer}:5000/push_change", json=change, timeout=30)
            if r.status_code != 200:
                log(f"Push to {best_peer} failed with status {r.status_code}")
                success = False
                break
        except Exception as e:
            log(f"Push to {best_peer} failed: {e}")
            success = False
            break

    if success:
        pending_changes.clear()
        return jsonify({"status": "ok", "message": f"Pushed to {best_peer}"})
    else:
        return jsonify({"status": "error", "message": f"Push to {best_peer} failed"}), 502

# ========== MAIN ==========

def start():

    #webbrowser.open("http://localhost:7000")

    os.makedirs(WATCH_PATH, exist_ok=True)

    # Create change_log.json if it doesn't exist
    if not os.path.exists(CHANGE_LOG):
        with open(CHANGE_LOG, 'w') as f:
            json.dump([], f)
        log("Created missing change_log.json")

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

def collectPeers():
    if len(sys.argv) > 1:    
        for i, arg in enumerate(sys.argv):
            if i>0:
                SERVERS.append(arg)

def printConfiguration():
    print("\n---Client Start---")
    print("\n---Configuration---")
    print(f" Set servers: {SERVERS}")
    print(f" Working directory: {WORKING_DIR}")
    print(f" Watch path: {WATCH_PATH}")
    print(f" Change log file: {CHANGE_LOG}")
    print(f" Machine ID: {MACHINE_ID}")
    print("---\n")

if __name__ == "__main__":
    collectPeers()
    printConfiguration()
    start()

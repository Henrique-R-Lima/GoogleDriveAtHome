from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
from flask import Flask, request, jsonify
import threading
import time
import os
import json
import shutil
import socket
import requests
import base64

# ==================== CONFIG ====================

WORKING_DIR = os.getcwd()
WATCH_PATH = os.path.join(WORKING_DIR, "test_chamber")
CHANGE_LOG = os.path.join(WORKING_DIR, "change_log.json")

# Peer machine IP and port
PEER_ADDRESS = "http://<peer_ip>:5000"  # Example: http://192.168.1.2:5000

MACHINE_ID = socket.gethostname()
# May return localhost, which is not desirable
# MACHINE_IP = socket.gethostbyname(MACHINE_ID)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually connect, just determines the best local IP
        s.connect(("8.8.8.8", 80))  # Google's public DNS
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"  # Fallback to localhost
    finally:
        s.close()
    return local_ip

MACHINE_IP = get_local_ip()
print("Local IP:", MACHINE_IP)

# ==================== CHANGE LOG ====================

if not os.path.exists(CHANGE_LOG):
    with open(CHANGE_LOG, 'w') as f:
        json.dump([], f)

def load_log():
    with open(CHANGE_LOG, 'r') as f:
        return json.load(f)

def append_to_log(change):
    log = load_log()
    log.append(change)
    with open(CHANGE_LOG, 'w') as f:
        json.dump(log, f, indent=2)

# ==================== FILE WATCHER ====================

class SyncHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_events = {}

    def _read_file_content(self, path):
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"Error reading file {path}: {e}")
            return None

    def _record_change(self, event_type, src_path, is_directory=False, dest_path=None):
        rel_src = os.path.relpath(src_path, WORKING_DIR)
        rel_dest = os.path.relpath(dest_path, WORKING_DIR) if dest_path else None

        if rel_src == os.path.basename(CHANGE_LOG):
            return

        now = datetime.now().timestamp()
        key = (event_type, rel_src, rel_dest)
        last_time = self.last_events.get(key, 0)
        if now - last_time < 0.5:
            return

        self.last_events[key] = now

        change = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'src': rel_src,
            'is_directory': is_directory,
            'origin': MACHINE_ID
        }
        if dest_path:
            change['dest'] = rel_dest

        # For file creation or modification, include content
        if event_type in ['created', 'modified'] and not is_directory:
            content = self._read_file_content(src_path)
            if content:
                change['content'] = content

        append_to_log(change)

        print(f"{change['timestamp']} | {event_type}: {rel_src}" + (f" -> {rel_dest}" if rel_dest else ""))

    def on_moved(self, event):
        self._record_change('moved', event.src_path, event.is_directory, event.dest_path)

    def on_created(self, event):
        self._record_change('created', event.src_path, event.is_directory)

    def on_deleted(self, event):
        self._record_change('deleted', event.src_path, event.is_directory)

    def on_modified(self, event):
        self._record_change('modified', event.src_path, event.is_directory)

# ==================== APPLY CHANGES ====================

def write_file_content(path, content_b64):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(content_b64.encode('utf-8')))
    except Exception as e:
        print(f"Error writing file {path}: {e}")

def apply_changes(changes):
    for change in changes:
        src_path = os.path.join(WORKING_DIR, change['src'])
        dest_path = os.path.join(WORKING_DIR, change['dest']) if 'dest' in change else None

        if change['origin'] == MACHINE_ID:
            continue

        print(f"Applying {change['type']} {change['src']}" + (f" -> {change.get('dest')}" if dest_path else ""))

        try:
            if change['type'] == 'created':
                if change['is_directory']:
                    os.makedirs(src_path, exist_ok=True)
                else:
                    write_file_content(src_path, change.get('content', ''))

            elif change['type'] == 'deleted':
                if os.path.exists(src_path):
                    if change['is_directory']:
                        shutil.rmtree(src_path)
                    else:
                        os.remove(src_path)

            elif change['type'] == 'moved':
                if os.path.exists(src_path):
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.move(src_path, dest_path)

            elif change['type'] == 'modified':
                if not change['is_directory']:
                    write_file_content(src_path, change.get('content', ''))

        except Exception as e:
            print(f"Error applying {change['type']} {change['src']}: {e}")

# ==================== HTTP API ====================

app = Flask(__name__)

@app.route('/get_changes', methods=['GET'])
def get_changes():
    since = request.args.get('since')
    log = load_log()
    filtered = [entry for entry in log if entry['timestamp'] > since]
    return jsonify(filtered)

def run_server():
    app.run(host="0.0.0.0", port=5000)

# ==================== SYNC CLIENT ====================

def sync_with_peer():
    last_check = datetime.now().isoformat()
    while True:
        time.sleep(3)
        try:
            response = requests.get(f"{PEER_ADDRESS}/get_changes", params={'since': last_check}, timeout=5)
            if response.status_code == 200:
                remote_changes = response.json()
                if remote_changes:
                    apply_changes(remote_changes)
                    for change in remote_changes:
                        append_to_log(change)
                    last_check = max(c['timestamp'] for c in remote_changes)
        except Exception as e:
            print(f"Sync error: {e}")

# ==================== MAIN ====================

if __name__ == "__main__":
    os.makedirs(WATCH_PATH, exist_ok=True)

    observer = Observer()
    event_handler = SyncHandler()
    observer.schedule(event_handler, path=WATCH_PATH, recursive=True)
    observer.start()

    threading.Thread(target=run_server, daemon=True).start()

    print(f"Started file sync on {MACHINE_ID}. Watching {WATCH_PATH}")
    print("Serving API on port 5000")

    threading.Thread(target=sync_with_peer, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping sync...")
        observer.stop()

    observer.join()

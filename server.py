import os
import sys
import time
import json
import shutil
import socket
import base64
import threading
import requests
from flask import Flask, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# ========== CONFIGURATION ==========

WORKING_DIR = os.getcwd()
WATCH_PATH = os.path.join(WORKING_DIR, "test_chamber")
CHANGE_LOG = os.path.join(WORKING_DIR, "change_log.json")

# Peer machine's IP address
PEER_ADDRESS = "http://"

MACHINE_ID = socket.gethostname()

log_lock = threading.Lock()  # Ensures thread-safe access

# ========== INIT SETUP ==========

if not os.path.exists(CHANGE_LOG):
    with open(CHANGE_LOG, 'w') as f:
        json.dump([], f)

def load_log():
    with open(CHANGE_LOG, 'r') as f:
        return json.load(f)

def append_to_log(change):
    with log_lock:
        try:
            if not os.path.exists(CHANGE_LOG):
                log = []
            else:
                with open(CHANGE_LOG, 'r', encoding='utf-8') as f:
                    try:
                        log = json.load(f)
                        if not isinstance(log, list):
                            log = []
                    except json.JSONDecodeError:
                        print("[append_to_log] Warning: Log file is invalid, resetting.")
                        log = []

            log.append(change)

            with open(CHANGE_LOG, 'w', encoding='utf-8') as f:
                json.dump(log, f, indent=2)

        except Exception as e:
            print(f"[append_to_log] Error: {e}")

# ========== FILE I/O ==========

def write_file_content(path, content_b64):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(content_b64.encode('utf-8')))
    except Exception as e:
        print(f"Error writing file {path}: {e}")

# ========== FILE WATCHER ==========

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
        if now - self.last_events.get(key, 0) < 0.5:
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

# ========== APPLY REMOTE CHANGES ==========

def apply_changes(changes):
    for change in changes:
        src_path = os.path.join(WORKING_DIR, change['src'])
        dest_path = os.path.join(WORKING_DIR, change['dest']) if 'dest' in change else None

        if change['origin'] == MACHINE_ID:
            continue

        print(f"[Sync] Applying {change['type']} {change['src']}" + (f" -> {change.get('dest')}" if dest_path else ""))

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

# ========== STARTUP BOOTSTRAP SYNC ==========

def initial_sync_from_peer():
    try:
        response = requests.get(f"{PEER_ADDRESS}/get_full_state", timeout=10)
        if response.status_code != 200:
            print("Peer did not return a valid state.")
            return

        remote_state = response.json()

        for item in remote_state:
            local_path = os.path.join(WORKING_DIR, item['path'])

            if item['is_directory']:
                os.makedirs(local_path, exist_ok=True)
                continue

            remote_mtime = item.get('last_modified')
            remote_content = item.get('content')

            if not os.path.exists(local_path):
                print(f"[Init Sync] Creating missing file: {item['path']}")
                write_file_content(local_path, remote_content)
                os.utime(local_path, (remote_mtime, remote_mtime))
                continue

            local_mtime = os.path.getmtime(local_path)
            if abs(local_mtime - remote_mtime) < 0.01:
                continue

            if remote_mtime > local_mtime:
                print(f"[Conflict] Remote file newer: Replacing {item['path']}")
                write_file_content(local_path, remote_content)
                os.utime(local_path, (remote_mtime, remote_mtime))
            else:
                print(f"[Conflict] Local file newer: Keeping {item['path']}")

    except Exception as e:
        print(f"[Init Sync] Failed: {e}")

# ========== HTTP API SERVER ==========

app = Flask(__name__)

@app.route('/get_changes', methods=['GET'])
def get_changes():
    since = request.args.get('since')
    return jsonify([e for e in load_log() if e['timestamp'] > since])

@app.route('/get_full_state', methods=['GET'])
def get_full_state():
    state = []
    for root, dirs, files in os.walk(WATCH_PATH):
        for name in files:
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, WORKING_DIR)
            try:
                with open(abs_path, 'rb') as f:
                    content = base64.b64encode(f.read()).decode('utf-8')
                mtime = os.path.getmtime(abs_path)
                state.append({
                    'path': rel_path,
                    'content': content,
                    'last_modified': mtime,
                    'is_directory': False
                })
            except Exception as e:
                print(f"Could not read {rel_path}: {e}")
        for name in dirs:
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, WORKING_DIR)
            state.append({
                'path': rel_path,
                'is_directory': True
            })
    return jsonify(state)

@app.route('/push_change', methods=['POST'])
def push_change():
    change = request.get_json()
    if not change:
        return jsonify({'status': 'error', 'message': 'No change payload'}), 400

    if 'origin' not in change:
        change['origin'] = f"user-{request.remote_addr}"

    try:
        print(f"[Push from User] {change['type']} {change['src']} (origin: {change['origin']})")
        apply_changes([change])
        append_to_log(change)
        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def run_server():
    app.run(host="0.0.0.0", port=5000)

# ========== SYNC CLIENT ===========

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
            print(f"[Sync Client] Error: {e}")

# ========== MAIN RUN ==========

def collectPeer():
    if len(sys.argv) > 1: 
        global PEER_ADDRESS
        for i, arg in enumerate(sys.argv):
            if i == 1:
                PEER_ADDRESS += arg + ":5000"

def printConfiguration():
    print("\n---Server Start---")
    print("\n---Configuration---")
    print(f" Peer server: {PEER_ADDRESS}")
    print(f" Working directory: {WORKING_DIR}")
    print(f" Watch path: {WATCH_PATH}")
    print(f" Change log file: {CHANGE_LOG}")
    print(f" Machine ID: {MACHINE_ID}")
    print("---\n")

if __name__ == "__main__":

    collectPeer()
    printConfiguration()

    os.makedirs(WATCH_PATH, exist_ok=True)

    print("Performing initial synchronization with peer...")
    initial_sync_from_peer()

    print(f"Starting sync on {MACHINE_ID}")
    observer = Observer()
    observer.schedule(SyncHandler(), path=WATCH_PATH, recursive=True)
    observer.start()

    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=sync_with_peer, daemon=True).start()


    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("Stopping sync...")

    observer.join()
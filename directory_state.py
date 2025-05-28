from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import time, os
import json

# Program working directory
WORKING_DIR = os.getcwd()

# Directory to be watched
WATCH_PATH = os.path.join(WORKING_DIR, "test_chamber")

# File to store the change log
CHANGE_LOG = os.path.join(WORKING_DIR, "change_log.json")

class SyncHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        # Create or load the change log
        if not os.path.exists(CHANGE_LOG):
            with open(CHANGE_LOG, 'w') as f:
                json.dump([], f)
    
    def _record_change(self, event_type, src_path, is_directory=False, dest_path=None):
        # Get relative paths
        rel_src = os.path.relpath(src_path, WORKING_DIR)
        rel_dest = os.path.relpath(dest_path, WORKING_DIR) if dest_path else None
        
        # Ignore changes to the log file itself
        if rel_src == os.path.basename(CHANGE_LOG):
            return
        
        # Create change record
        change = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'src': rel_src,
            'is_directory': is_directory
        }
        
        if dest_path:
            change['dest'] = rel_dest
        
        # Load existing log, append new change, and save
        with open(CHANGE_LOG, 'r+') as f:
            log = json.load(f)
            log.append(change)
            f.seek(0)
            json.dump(log, f, indent=2)
        
        # Print the change (optional)
        print(f"{change['timestamp']} - {event_type}: {rel_src}" + 
              (f" -> {rel_dest}" if rel_dest else ""))

    def on_moved(self, event):
        self._record_change('moved', event.src_path, 
                           event.is_directory, event.dest_path)

    def on_created(self, event):
        self._record_change('created', event.src_path, event.is_directory)

    def on_deleted(self, event):
        self._record_change('deleted', event.src_path, event.is_directory)

    def on_modified(self, event):
        self._record_change('modified', event.src_path, event.is_directory)

observer = Observer()
observer.schedule(SyncHandler(), path=WATCH_PATH, recursive=True)
observer.start()

try:
    while True:
        time.sleep(3)
except KeyboardInterrupt:
    observer.stop()
observer.join()
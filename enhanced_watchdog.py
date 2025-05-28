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
        # Skip folder modification events
        if event_type == 'modified' and is_directory:
            return
            
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
        # This will now only record file modifications
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

"""
Code for the other machine TO BE TESTED:

import os
import json
import shutil
from datetime import datetime

def replicate_changes(log_file, target_dir):
    with open(log_file, 'r') as f:
        changes = json.load(f)
    
    for change in changes:
        print(f"Replicating: {change['type']} {change['src']}")
        
        src_path = os.path.join(target_dir, change['src'])
        dest_path = os.path.join(target_dir, change['dest']) if 'dest' in change else None
        
        try:
            if change['type'] == 'created':
                if change['is_directory']:
                    os.makedirs(src_path, exist_ok=True)
                else:
                    open(src_path, 'a').close()  # Create empty file
            
            elif change['type'] == 'deleted':
                if os.path.exists(src_path):
                    if change['is_directory']:
                        shutil.rmtree(src_path)
                    else:
                        os.remove(src_path)
            
            elif change['type'] == 'moved':
                if os.path.exists(src_path):
                    shutil.move(src_path, dest_path)
            
            elif change['type'] == 'modified':
                if not change['is_directory'] and os.path.exists(src_path):
                    # For files, touch them to update modified time
                    os.utime(src_path, None)
        
        except Exception as e:
            print(f"Failed to replicate {change['type']} {change['src']}: {str(e)}")

if __name__ == "__main__":
    # Example usage
    replicate_changes("change_log.json", "test_chamber")

"""
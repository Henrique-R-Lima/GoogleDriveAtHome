from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import requests

class SyncHandler(FileSystemEventHandler):
    def on_modified(self, event):
        print(f"File changed: {event.src_path}")
        # Sync logic here (upload to server or peer)

observer = Observer()
observer.schedule(SyncHandler(), path="/path/to/watch", recursive=True)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
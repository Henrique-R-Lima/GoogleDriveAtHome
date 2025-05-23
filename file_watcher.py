from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import time, os

# Program working directory
WORKING_DIR = os.getcwd()

# Directory to be watched
WATCH_PATH = os.path.join(WORKING_DIR, "test_chamber")

class SyncHandler(FileSystemEventHandler):
    def on_any_event(self, event):

        # Element that caused the event
        element_str = event.src_path.removeprefix(os.path.join(WORKING_DIR,""))

        # Event type
        event_str = event.event_type

        # Ignore changes to observed directory
        if element_str == "test_chamber":
            return
        
        # Simplify element path
        element_str = element_str.removeprefix("test_chamber/")

        # Current time
        timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')

        # Log changes
        print(f"\'{element_str}\' {event_str} at {timestamp}")

observer = Observer()
observer.schedule(SyncHandler(), path=WATCH_PATH, recursive=True)
observer.start()

try:
    while True:
        time.sleep(3)
except KeyboardInterrupt:
    observer.stop()
observer.join()
# /opt/chappie-organizer/chappie-organizer.py

import time
import shutil
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Directory to watch
WATCH_DIR = '/home/boba/Mainframe/psydekik/drop-box'

# Define target directories
TARGETS = {
    # TEXT type format file extensions & locations
    '.txt': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.pdf': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.doc': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.docx': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.xls': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.xlsx': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.ppt': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.pptx': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.odt': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.ods': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.odp': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    '.pages': '/home/boba/Mainframe/psydekik/chappie/assets/documents',
    # CODE type format file extensions & locations
    '.py': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.js': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.html': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.css': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.java': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.cpp': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.c': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.cs': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.php': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.rb': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.go': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.swift': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.ts': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.sh': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.bat': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.ps1': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.sql': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.json': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.xml': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.yaml': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.yml': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.toml': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.md': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    '.csv': '/home/boba/Mainframe/psydekik/chappie/assets/code',
    # IMAGE type format file extensions & locations
    '.mpg': '/home/boba/Mainframe/psydekik/chappie/assets/media/video',
    '.png': '/home/boba/Mainframe/psydekik/chappie/assets/media/images',
    '.jpg': '/home/boba/Mainframe/psydekik/chappie/assets/media/images',
    # ANIMATION type format file extensions & locations
    '.gif': '/home/boba/Mainframe/psydekik/chappie/assets/media/gif',
    # VIDEO type format file extensions & locations
    '.mp4': '/home/boba/Mainframe/psydekik/chappie/assets/media/video',
    '.avi': '/home/boba/Mainframe/psydekik/chappie/assets/media/video',
    '.mov': '/home/boba/Mainframe/psydekik/chappie/assets/media/video',
    '.mkv': '/home/boba/Mainframe/psydekik/chappie/assets/media/video',
    # SOUND type format file extensions & locations
    '.mp3': '/home/boba/Mainframe/psydekik/chappie/assets/media/audio',
    '.wav': '/home/boba/Mainframe/psydekik/chappie/assets/media/audio',
    '.flac': '/home/boba/Mainframe/psydekik/chappie/assets/media/audio',
    # COMPRESSED type format file extensions & locations
    '.zip': '/home/boba/Mainframe/psydekik/chappie/assets/compressed',
}

# Make sure that the target folders exist
for path in TARGETS.values():
    os.makedirs(path, exist_ok=True)


class chappieHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            filepath = event.src_path
            _, ext = os.path.splitext(filepath)
            ext = ext.lower()
            target_dir = TARGETS.get(ext)
            if target_dir:
                print(f"Detected {ext} file. Moving {filepath} -> {target_dir}")
                shutil.move(filepath, os.path.join(target_dir, os.path.basename(filepath)))
            else:
                print(f"Unknown file type: {filepath}. Ignoring.")


if __name__ == "__main__":
    print(f"Starting chappie-Organizer! Watching: {WATCH_DIR}")
    event_handler = chappieHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

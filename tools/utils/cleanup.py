import os
import time
import shutil
from django.conf import settings


def cleanup_old_files():
    folder = settings.MEDIA_ROOT
    os.makedirs(folder, exist_ok=True)

    now = time.time()

    for filename in os.listdir(folder):
        # Skip gitignore if it exists in media for any reason
        if filename == ".gitignore":
            continue

        file_path = os.path.join(folder, filename)

        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            # File or folder may have been removed concurrently
            continue

        file_age = now - mtime

        # 30 mins = 1800 sec
        if file_age > 1800:
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path, ignore_errors=True)
            except (PermissionError, OSError):
                # Ignore files/folders currently in use
                pass


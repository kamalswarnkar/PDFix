import os
import time
from django.conf import settings


def cleanup_old_files():
    folder = settings.MEDIA_ROOT
    os.makedirs(folder, exist_ok=True)

    now = time.time()

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)

        if os.path.isfile(file_path):
            try:
                file_age = now - os.path.getmtime(file_path)
            except OSError:
                # File may be deleted or moved while iterating.
                continue

            # 30 mins = 1800 sec
            if file_age > 1800:
                try:
                    os.remove(file_path)
                except (PermissionError, OSError):
                    # Ignore files currently in use or concurrently modified.
                    pass

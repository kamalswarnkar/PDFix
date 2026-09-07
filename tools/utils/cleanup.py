import logging
import os
import shutil
import time

from django.conf import settings

logger = logging.getLogger(__name__)


def cleanup_old_files():
    """Delete anything left in MEDIA_ROOT past the retention window.

    On POSIX the download is unlinked as soon as it is streamed, so in normal
    operation this only sweeps up after a crash or a killed worker.
    """
    folder = settings.MEDIA_ROOT
    os.makedirs(folder, exist_ok=True)

    cutoff = time.time() - settings.MEDIA_RETENTION_SECONDS

    try:
        entries = os.scandir(folder)
    except OSError:
        logger.warning("cleanup: cannot read %s", folder)
        return

    with entries:
        for entry in entries:
            if entry.name == ".gitignore":
                continue
            try:
                if entry.stat().st_mtime > cutoff:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    shutil.rmtree(entry.path, ignore_errors=True)
                else:
                    os.remove(entry.path)
            except OSError:
                # Removed concurrently, or still open by another worker.
                continue

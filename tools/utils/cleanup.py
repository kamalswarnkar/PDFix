import os
import time
from django.conf import settings

def cleanup_old_files():
    #print("chal raha hai")
    folder = settings.MEDIA_ROOT

    now = time.time()

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)

        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)

            #30 mins = 1800 sec
            if file_age > 1800:
                try:
                    os.remove(file_path)
                    print("file deleted")
                except PermissionError:
                    print("file still in use: ", filename)
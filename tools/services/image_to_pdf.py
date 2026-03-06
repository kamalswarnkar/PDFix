from PIL import Image
import os
import uuid
from django.conf import settings

def img_to_pdf(files):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    images = []

    for file in files:
        img = Image.open(file).convert("RGB")
        images.append(img)
    
    filename = f"{uuid.uuid4()}_images.pdf"
    output_path = os.path.join(settings.MEDIA_ROOT, filename)

    if len(images) == 1:
        images[0].save(output_path)
    else:
        images[0].save(output_path, save_all = True, append_images=images[1:])
    
    return filename

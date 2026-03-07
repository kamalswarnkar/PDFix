from pdf2image import convert_from_path
import os
import uuid
import zipfile
from django.conf import settings


def pdf_to_images(files):

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    zip_filename = f"{uuid.uuid4()}_images.zip"
    zip_path = os.path.join(settings.MEDIA_ROOT, zip_filename)

    with zipfile.ZipFile(zip_path, "w") as zipf:

        for file in files:

            input_filename = f"{uuid.uuid4()}_input.pdf"
            input_path = os.path.join(settings.MEDIA_ROOT, input_filename)

            with open(input_path, "wb+") as f:
                if hasattr(file, "chunks"):
                    for chunk in file.chunks():
                        f.write(chunk)
                else:
                    f.write(file)

            try:
                images = convert_from_path(input_path, dpi=300)
            except Exception as e:
                os.remove(input_path)
                raise Exception("PDF conversion failed")

            for i, image in enumerate(images):

                base_name = os.path.splitext(os.path.basename(file.name))[0]
                img_name = f"{base_name}_page_{i+1}.png"
                img_path = os.path.join(settings.MEDIA_ROOT, img_name)

                image.save(img_path, "PNG")

                zipf.write(img_path, img_name)

                os.remove(img_path)

            os.remove(input_path)

    return zip_filename
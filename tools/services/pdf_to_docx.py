from pdf2docx import Converter
import os
import uuid
from django.conf import settings

def pdf_to_docx(file):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    input_name = f"{uuid.uuid4()}.pdf"
    input_path = os.path.join(settings.MEDIA_ROOT, input_name)

    with open(input_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)
    
    output_name = f"{uuid.uuid4()}.docx"
    output_path = os.path.join(settings.MEDIA_ROOT, output_name)

    cv = Converter(input_path)
    cv.convert(output_path)
    cv.close()

    return output_name
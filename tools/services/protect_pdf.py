from pypdf import PdfReader, PdfWriter
import os
import uuid
from django.conf import settings

def protect_pdf(file, pwd):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    input_name = f"{uuid.uuid4()}.pdf"
    input_path = os.path.join(settings.MEDIA_ROOT, input_name)

    with open(input_path, "wb") as f:
        for chunk in file.chunks():
            f.write(chunk)
    
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)
    
    writer.encrypt(pwd)

    output_name = f"{uuid.uuid4()}_protected.pdf"
    output_path = os.path.join(settings.MEDIA_ROOT, output_name)

    with open(output_path, "wb") as f:
        writer.write(f)
    
    return output_name
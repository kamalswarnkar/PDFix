from pypdf import PdfReader, PdfWriter
import os
import uuid
from django.conf import settings

def rotate_pdf(file, angle):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    input_file = f"{uuid.uuid4()}.pdf"
    input_path = os.path.join(settings.MEDIA_ROOT, input_file)

    with open(input_path, "wb") as f:
        for chunk in file.chunks():
            f.write(chunk)
    
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)
    
    output_name = f"{uuid.uuid4()}_rotated.pdf"
    output_path = os.path.join(settings.MEDIA_ROOT, output_name)

    with open(output_path, "wb") as f:
        writer.write(f)
    
    return output_name
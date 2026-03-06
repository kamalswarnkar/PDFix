from pypdf import PdfReader, PdfWriter
import os
import uuid
from django.conf import settings

def extract_pages(file, start_page, end_page):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    reader = PdfReader(file)
    writer = PdfWriter()

    for i in range(start_page - 1, end_page):
        writer.add_page(reader.pages[i])
    
    filename = f"{uuid.uuid4()}_extracted.pdf"
    output_path = os.path.join(settings.MEDIA_ROOT, filename)

    with open(output_path, "wb") as f:
        writer.write(f)
    
    return filename

from pypdf import PdfReader, PdfWriter
import os
import uuid
from django.conf import settings

def split_pdf(file):
    reader = PdfReader(file)
    output_files = []

    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        filename = f"{uuid.uuid4()}_page_{i+1}.pdf"
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        output_path = os.path.join(settings.MEDIA_ROOT, filename)

        with open(output_path, "wb") as f:
            writer.write(f)
        
        output_files.append(filename)
    
    return output_files
from pypdf import PdfReader, PdfWriter
import os
import uuid
from django.conf import settings

def merge_pdfs(files):
    writer = PdfWriter()

    for file in files:
        reader = PdfReader(file)
        for page in reader.pages:
            writer.add_page(page)
    
    filename = f"{uuid.uuid4()}.pdf"
    output_path = os.path.join(settings.MEDIA_ROOT, filename)

    with open(output_path, "wb") as f:
        writer.write(f)
    
    return filename
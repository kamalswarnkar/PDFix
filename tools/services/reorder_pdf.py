from pypdf import PdfReader, PdfWriter
import os
import uuid
from django.conf import settings

def reorder_pdf(file, order):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    input_name = f"{uuid.uuid4()}.pdf"
    input_path = os.path.join(settings.MEDIA_ROOT, input_name)

    try:
        with open(input_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)
        
        reader = PdfReader(input_path)
        writer = PdfWriter()

        if not order:
            raise ValueError("Invalid page order")

        parts = [part.strip() for part in order.split(",")]

        if not parts or any(not part for part in parts):
            raise ValueError("Invalid page order")

        pages = list(map(int, parts))
        total_pages = len(reader.pages)

        if len(pages) != total_pages or sorted(pages) != list(range(1, total_pages + 1)):
            raise ValueError("Invalid page order")

        for p in pages:
            writer.add_page(reader.pages[p-1])
        
        output_name = f"{uuid.uuid4()}_reordered.pdf"
        output_path = os.path.join(settings.MEDIA_ROOT, output_name)

        with open(output_path, "wb") as f:
            writer.write(f)
        
        return output_name
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

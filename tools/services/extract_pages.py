from pypdf import PdfReader, PdfWriter
import os
import uuid
from django.conf import settings

def extract_pages(file, start_page, end_page):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    reader = PdfReader(file)
    total = len(reader.pages)

    # ponytail: validate before touching pages — this was the root cause of the 500
    if start_page < 1 or end_page < start_page or end_page > total:
        raise ValueError(
            f"Invalid page range {start_page}–{end_page} for a {total}-page PDF."
        )

    writer = PdfWriter()
    for i in range(start_page - 1, end_page):
        writer.add_page(reader.pages[i])

    filename = f"{uuid.uuid4()}_extracted.pdf"
    output_path = os.path.join(settings.MEDIA_ROOT, filename)

    with open(output_path, "wb") as f:
        writer.write(f)

    return filename

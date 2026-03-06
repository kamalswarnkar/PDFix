from pypdf import PdfReader, PdfWriter
import os
import uuid
import zipfile
from django.conf import settings

def split_pdf(file):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    reader = PdfReader(file)
    zipfilename = f"{uuid.uuid4()}_split_pdf.zip"
    zip_path = os.path.join(settings.MEDIA_ROOT, zipfilename)

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for i, page in enumerate(reader.pages):
            writer = PdfWriter()
            writer.add_page(page)

            pdf_filename = f"page_{i + 1}.pdf"
            pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_filename)

            with open(pdf_path, "wb") as f:
                writer.write(f)
            
            zipf.write(pdf_path, pdf_filename)

            os.remove(pdf_path)
    return zipfilename
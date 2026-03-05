from pypdf import PdfReader, PdfWriter
import os
import uuid
import subprocess
from django.conf import settings

# def compress_pdf(file):
#     reader = PdfReader(file)
#     writer = PdfWriter()

#     for page in reader.pages:
#         writer.add_page(page)
    
#     for page in writer.pages:
#         page.compress_content_streams()
    
#     filename = f"{uuid.uuid4()}_compressed.pdf"
#     os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
#     output_path = os.path.join(settings.MEDIA_ROOT, filename)

#     with open(output_path, "wb") as f:
#         writer.write(f)

#     return filename

def compress_pdf(file):

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    input_filename = f"{uuid.uuid4()}_input.pdf"
    output_filename = f"{uuid.uuid4()}_compressed.pdf"

    input_path = os.path.join(settings.MEDIA_ROOT, input_filename)
    output_path = os.path.join(settings.MEDIA_ROOT, output_filename)

    # save uploaded file
    with open(input_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)

    gs_path = r"C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe"

    command = [
        gs_path,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/screen",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ]

    subprocess.run(command, check=True)

    os.remove(input_path)

    return output_filename
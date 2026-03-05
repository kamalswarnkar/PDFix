import os
import uuid
import subprocess
from django.conf import settings


def compress_pdf_to_size(file, target_kb=100):

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    input_filename = f"{uuid.uuid4()}_input.pdf"
    input_path = os.path.join(settings.MEDIA_ROOT, input_filename)

    with open(input_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)

    gs_path = r"C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe"

    current_input = input_path

    for i in range(5):

        output_filename = f"{uuid.uuid4()}_compressed.pdf"
        output_path = os.path.join(settings.MEDIA_ROOT, output_filename)

        command = [
            gs_path,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/screen",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={output_path}",
            current_input
        ]

        subprocess.run(command)

        size_kb = os.path.getsize(output_path) / 1024

        if size_kb <= target_kb:
            os.remove(current_input)
            return output_filename

        current_input = output_path

    return output_filename
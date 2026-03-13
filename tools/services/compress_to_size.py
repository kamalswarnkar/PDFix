import os
import uuid
import subprocess
from django.conf import settings


def save_best_output(output_filename, output_path, size_kb, best_output_filename, best_output_path, best_size_kb):

    if best_size_kb is None or size_kb < best_size_kb:
        if best_output_path and os.path.exists(best_output_path):
            os.remove(best_output_path)
        return output_filename, output_path, size_kb

    if os.path.exists(output_path):
        os.remove(output_path)

    return best_output_filename, best_output_path, best_size_kb


def compress_pdf_to_size(file, target_kb=100):

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    input_filename = f"{uuid.uuid4()}_input.pdf"
    input_path = os.path.join(settings.MEDIA_ROOT, input_filename)

    with open(input_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)

    gs_path = r"C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe"

    best_output_filename = None
    best_output_path = None
    best_size_kb = None

    attempts = [
        {"pdfsettings": "/ebook", "resolution": 110, "jpegq": 55},
        {"pdfsettings": "/ebook", "resolution": 96, "jpegq": 50},
        {"pdfsettings": "/screen", "resolution": 90, "jpegq": 45},
        {"pdfsettings": "/screen", "resolution": 84, "jpegq": 40},
        {"pdfsettings": "/screen", "resolution": 72, "jpegq": 35},
    ]

    for attempt in attempts:

        output_filename = f"{uuid.uuid4()}_compressed.pdf"
        output_path = os.path.join(settings.MEDIA_ROOT, output_filename)

        command = [
            gs_path,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={attempt['pdfsettings']}",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dAutoFilterColorImages=false",
            "-dAutoFilterGrayImages=false",
            "-dColorImageFilter=/DCTEncode",
            "-dGrayImageFilter=/DCTEncode",
            f"-dJPEGQ={attempt['jpegq']}",
            "-dDownsampleColorImages=true",
            "-dDownsampleGrayImages=true",
            "-dDownsampleMonoImages=true",
            "-dColorImageDownsampleType=/Bicubic",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dMonoImageDownsampleType=/Subsample",
            f"-dColorImageResolution={attempt['resolution']}",
            f"-dGrayImageResolution={attempt['resolution']}",
            f"-dMonoImageResolution={attempt['resolution']}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={output_path}",
            input_path
        ]

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            if os.path.exists(output_path):
                os.remove(output_path)
            continue

        size_kb = os.path.getsize(output_path) / 1024

        best_output_filename, best_output_path, best_size_kb = save_best_output(
            output_filename,
            output_path,
            size_kb,
            best_output_filename,
            best_output_path,
            best_size_kb
        )

        if size_kb <= target_kb:
            if os.path.exists(input_path):
                os.remove(input_path)
            return output_filename

    if os.path.exists(input_path):
        os.remove(input_path)

    return best_output_filename

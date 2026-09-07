import logging
import os

from ..uploads import ToolError, new_media_path, read_pdf, save_upload
from .compress_pdf import resolve_ghostscript, run_ghostscript

logger = logging.getLogger(__name__)

# ponytail: fixed ladder of five passes, stopping at the first that hits target.
# A binary search over JPEG quality would land closer to the target, but each
# probe costs a full Ghostscript run - not worth it until users complain.
ATTEMPTS = (
    {"pdfsettings": "/ebook", "resolution": 110, "jpegq": 55},
    {"pdfsettings": "/ebook", "resolution": 96, "jpegq": 50},
    {"pdfsettings": "/screen", "resolution": 90, "jpegq": 45},
    {"pdfsettings": "/screen", "resolution": 84, "jpegq": 40},
    {"pdfsettings": "/screen", "resolution": 72, "jpegq": 35},
)


def _command(gs, attempt, output_path, input_path):
    return [
        gs,
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
        "-dSAFER",
        f"-sOutputFile={output_path}",
        input_path,
    ]


def compress_pdf_to_size(file, target_kb=100):
    """Compress towards `target_kb`, keeping the smallest result achieved.

    Returns the best filename even when the target is missed - the old version
    could return None here, which the view then fed to os.path.join().
    """
    read_pdf(file, file.name)          # reject corrupt/encrypted input up front
    file.seek(0)
    input_path = save_upload(file, "_input.pdf")

    best_filename = None
    best_path = None
    best_kb = None

    try:
        if os.path.getsize(input_path) / 1024 <= target_kb:
            # Already small enough; running Ghostscript could only make it worse.
            filename, output_path = new_media_path("_compressed.pdf")
            os.replace(input_path, output_path)
            return filename

        gs = resolve_ghostscript()

        for attempt in ATTEMPTS:
            filename, output_path = new_media_path("_compressed.pdf")

            if not run_ghostscript(_command(gs, attempt, output_path, input_path)):
                if os.path.exists(output_path):
                    os.remove(output_path)
                continue

            size_kb = os.path.getsize(output_path) / 1024

            if best_kb is None or size_kb < best_kb:
                if best_path and os.path.exists(best_path):
                    os.remove(best_path)
                best_filename, best_path, best_kb = filename, output_path, size_kb
            elif os.path.exists(output_path):
                os.remove(output_path)

            if size_kb <= target_kb:
                break

        if best_filename is None:
            raise ToolError(
                "This PDF could not be compressed. It may use unusual fonts or images."
            )

        if best_kb > target_kb:
            logger.info("compress_to_size: best %.0f KB, target %s KB", best_kb, target_kb)

        return best_filename
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

import logging
import os
import shutil
import subprocess

from django.conf import settings

from ..uploads import ToolError, new_media_path, read_pdf, save_upload

logger = logging.getLogger(__name__)

# Ghostscript presets, worst-to-best quality. "balanced" matches the old
# hard-coded /ebook behaviour.
LEVELS = {
    "small": "/screen",
    "balanced": "/ebook",
    "quality": "/printer",
}


def resolve_ghostscript():
    """Locate the Ghostscript binary, or raise a message the user can act on."""
    for candidate in ("gs", "gswin64c", "gswin32c"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    # Windows installers do not always add themselves to PATH.
    for root in (r"C:\Program Files\gs", r"C:\Program Files (x86)\gs"):
        if os.path.isdir(root):
            for version in sorted(os.listdir(root), reverse=True):
                exe = os.path.join(root, version, "bin", "gswin64c.exe")
                if os.path.exists(exe):
                    return exe

    logger.error("Ghostscript not found on PATH; PDF compression is unavailable")
    raise ToolError("PDF compression is temporarily unavailable. Please try again later.")


def run_ghostscript(args, timeout=None):
    """Run Ghostscript, returning True on success. Never raises for a bad PDF."""
    try:
        result = subprocess.run(
            args,
            timeout=timeout or settings.CONVERT_TIMEOUT_SECONDS,
            capture_output=True,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Ghostscript timed out after %ss", timeout)
        raise ToolError(
            "This PDF took too long to compress. Try a smaller file."
        ) from None

    if result.returncode != 0:
        logger.warning("Ghostscript failed (%s): %s", result.returncode, result.stderr[-500:])
        return False
    return True


def compress_pdf(file, level="balanced"):
    """Shrink a PDF with Ghostscript.

    If Ghostscript cannot beat the original size - common for already-optimised
    PDFs - the original is returned rather than a larger "compressed" file.
    """
    preset = LEVELS.get(level, LEVELS["balanced"])

    read_pdf(file, file.name)          # reject corrupt/encrypted input up front
    file.seek(0)
    input_path = save_upload(file, "_input.pdf")

    try:
        filename, output_path = new_media_path("_compressed.pdf")
        gs = resolve_ghostscript()

        ok = run_ghostscript([
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={preset}",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dSAFER",
            f"-sOutputFile={output_path}",
            input_path,
        ])

        original_size = os.path.getsize(input_path)
        if not ok or not os.path.exists(output_path):
            raise ToolError(
                "This PDF could not be compressed. It may use unusual fonts or images."
            )

        if os.path.getsize(output_path) >= original_size:
            # Already optimised - hand back the original instead of a bigger file.
            shutil.copyfile(input_path, output_path)

        return filename
    finally:
        # The old version leaked this file whenever Ghostscript failed.
        if os.path.exists(input_path):
            os.remove(input_path)

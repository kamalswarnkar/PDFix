import logging
import os
import shutil
import subprocess

from django.conf import settings

from ..uploads import ToolError, save_upload

logger = logging.getLogger(__name__)


def _convert_with_libreoffice(input_path, output_dir, output_path, uid):
    """LibreOffice headless DOCX -> PDF, with a per-request user profile.

    The previous version shared one profile directory in the system temp dir,
    so two simultaneous conversions collided on LibreOffice's profile lock.
    """
    profile_dir = os.path.join(output_dir, f"lo_profile_{uid}")
    os.makedirs(profile_dir, exist_ok=True)

    try:
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--norestore",
                "--nofirststartwizard",
                "--convert-to", "pdf:writer_pdf_Export",
                f"-env:UserInstallation=file:///{profile_dir.replace(os.sep, '/')}",
                "--outdir", output_dir,
                input_path,
            ],
            check=True,
            timeout=settings.CONVERT_TIMEOUT_SECONDS,
            capture_output=True,
        )
    except Exception as exc:
        logger.info("LibreOffice DOCX->PDF failed: %s", exc)

    return os.path.exists(output_path)


def docx_to_pdf(file):
    """Convert a Word document to PDF with LibreOffice."""
    input_path = save_upload(file, ".docx")
    uid = os.path.splitext(os.path.basename(input_path))[0]
    output_name = f"{uid}.pdf"
    output_path = os.path.join(settings.MEDIA_ROOT, output_name)

    try:
        if _convert_with_libreoffice(input_path, settings.MEDIA_ROOT, output_path, uid):
            return output_name

        logger.warning("docx_to_pdf: no engine produced output for %s", file.name)
        raise ToolError(
            "This document could not be converted. It may be corrupt, "
            "password-protected, or use features the converter does not support."
        )
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        # LibreOffice occasionally leaves a stray profile behind after a kill.
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT, f"lo_profile_{uid}"), ignore_errors=True)

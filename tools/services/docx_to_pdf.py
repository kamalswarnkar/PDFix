import os
import uuid
import subprocess
import shutil
from django.conf import settings


def _convert_with_word_com(input_path, output_path):
    """
    Use win32com to drive Microsoft Word directly from Python.
    No PowerShell subprocess spawn → much faster conversion.
    Returns True if the conversion succeeded.
    """
    try:
        import win32com.client
        import pythoncom
    except ImportError:
        return False

    try:
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone — suppress all dialogs

        doc = word.Documents.Open(os.path.abspath(input_path))
        # SaveAs2 format 17 = wdFormatPDF
        doc.SaveAs2(os.path.abspath(output_path), FileFormat=17)
        doc.Close(0)  # wdDoNotSaveChanges
        word.Quit()

        return os.path.exists(output_path)
    except Exception:
        try:
            word.Quit()
        except Exception:
            pass
        return False
    finally:
        pythoncom.CoUninitialize()


def docx_to_pdf(file):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    uid = str(uuid.uuid4())
    input_name = f"{uid}.docx"
    input_path = os.path.join(settings.MEDIA_ROOT, input_name)

    try:
        with open(input_path, "wb+") as f:
            for chunk in file.chunks():
                f.write(chunk)

        output_name = f"{uid}.pdf"
        output_path = os.path.join(settings.MEDIA_ROOT, output_name)

        # ── Tier 1: Direct Python COM via pywin32 (Windows only) ──────────────
        if os.name == "nt":
            if _convert_with_word_com(input_path, output_path):
                return output_name

        # ── Tier 2: docx2pdf library (Windows fallback, wraps COM efficiently) ─
        try:
            from docx2pdf import convert
            convert(input_path, output_path)
            if os.path.exists(output_path):
                return output_name
        except Exception:
            pass

        # ── Tier 3: LibreOffice headless (cross-platform, non-Windows) ────────
        profile_dir = os.path.join(settings.MEDIA_ROOT, "lo_shared_profile")
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
                    "--outdir", settings.MEDIA_ROOT,
                    input_path,
                ],
                check=True,
                timeout=120,
            )
        except Exception:
            pass

        if not os.path.exists(output_path):
            raise RuntimeError(
                "Conversion failed. Microsoft Word or LibreOffice is required to convert DOCX files."
            )

        return output_name
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)


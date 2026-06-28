import os
import uuid
import subprocess
import shutil
import multiprocessing
from django.conf import settings

WORD_TIMEOUT_SECONDS = 75
LIBREOFFICE_TIMEOUT_SECONDS = 75
PDF2DOCX_TIMEOUT_SECONDS = 120
PDF2DOCX_MAX_MB = 8
PDF2DOCX_MAX_PAGES = 10


def word_engine_available():
    if os.name != "nt":
        return False
    try:
        import win32com.client  # noqa: F401
        return True
    except Exception:
        pass

    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$word=$null; try { $word=New-Object -ComObject Word.Application; 'ok' } finally { if($word -ne $null){$word.Quit()} }",
            ],
            check=True,
            timeout=6,
            capture_output=True,
            text=True,
        )
        return True
    except Exception:
        return False


def _word_com_worker(input_path, output_path, result_queue):
    """
    Run Word COM conversion in an isolated process so we can enforce timeout.
    """
    word = None
    doc = None

    try:
        import win32com.client
        import pythoncom
    except ImportError:
        result_queue.put(False)
        return

    try:
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone: suppress all dialogs

        doc = word.Documents.Open(
            FileName=os.path.abspath(input_path),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
            Revert=False,
            NoEncodingDialog=True,
        )
        # SaveAs2 format 16 = wdFormatXMLDocument (DOCX)
        doc.SaveAs2(os.path.abspath(output_path), FileFormat=16)
        result_queue.put(os.path.exists(output_path))
    except Exception:
        result_queue.put(False)
    finally:
        try:
            if doc is not None:
                doc.Close(0)  # wdDoNotSaveChanges
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def _convert_with_word_com(input_path, output_path):
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_word_com_worker,
        args=(input_path, output_path, result_queue),
    )
    process.start()
    process.join(WORD_TIMEOUT_SECONDS)

    if process.is_alive():
        process.terminate()
        process.join()
        return False

    if result_queue.empty():
        return False

    return bool(result_queue.get())


def _convert_with_word_powershell(input_path, output_path):
    """
    Fallback Word automation path that does not require pywin32.
    Uses PowerShell COM automation if Microsoft Word is installed.
    """
    if os.name != "nt":
        return False

    # Use single quotes for literal Windows paths in PowerShell script.
    in_ps = os.path.abspath(input_path).replace("'", "''")
    out_ps = os.path.abspath(output_path).replace("'", "''")
    script = (
        "$ErrorActionPreference='Stop';"
        "$word=$null;$doc=$null;"
        "try {"
        "$word=New-Object -ComObject Word.Application;"
        "$word.Visible=$false;$word.DisplayAlerts=0;"
        "$doc=$word.Documents.Open('" + in_ps + "',$false,$true);"
        "$doc.SaveAs2('" + out_ps + "',16);"
        "} finally {"
        "if($doc -ne $null){$doc.Close(0)};"
        "if($word -ne $null){$word.Quit()}"
        "}"
    )

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True,
            timeout=WORD_TIMEOUT_SECONDS,
        )
        return os.path.exists(output_path)
    except Exception:
        return False


def _convert_with_libreoffice(input_path, output_dir, output_path, uid):
    """
    Use LibreOffice headless to convert PDF -> DOCX.
    Returns True if the conversion succeeded.
    """
    profile_dir = os.path.join(output_dir, f"lo_profile_{uid}")
    os.makedirs(profile_dir, exist_ok=True)

    base_cmd = [
        "soffice",
        "--headless",
        "--norestore",
        "--nofirststartwizard",
        "--convert-to",
        "docx:MS Word 2007 XML",
        f"-env:UserInstallation=file:///{profile_dir.replace(os.sep, '/')}",
        "--outdir",
        output_dir,
    ]

    # Try Writer import first because Impress import often yields textbox-heavy output.
    attempts = [
        ["--infilter=writer_pdf_import"],
        [],
    ]

    try:
        for infilter in attempts:
            try:
                subprocess.run(
                    [*base_cmd, *infilter, input_path],
                    check=True,
                    timeout=LIBREOFFICE_TIMEOUT_SECONDS,
                )
                if os.path.exists(output_path):
                    return True
            except Exception:
                continue
        return False
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)


def _pdf2docx_worker(input_path, output_path, result_queue):
    try:
        from pdf2docx import Converter

        cv = Converter(input_path)
        try:
            cv.convert(
                output_path,
                multi_processing=True,
                parse_lattice_table=False,
                parse_stream_table=False,
            )
        finally:
            cv.close()

        result_queue.put(os.path.exists(output_path))
    except Exception:
        result_queue.put(False)


def _convert_with_pdf2docx(input_path, output_path):
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_pdf2docx_worker,
        args=(input_path, output_path, result_queue),
    )
    process.start()
    process.join(PDF2DOCX_TIMEOUT_SECONDS)

    if process.is_alive():
        process.terminate()
        process.join()
        return False

    if result_queue.empty():
        return False

    return bool(result_queue.get())


def _should_try_pdf2docx(input_path):
    try:
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        if file_size_mb > PDF2DOCX_MAX_MB:
            return False

        from pypdf import PdfReader

        page_count = len(PdfReader(input_path).pages)
        return page_count <= PDF2DOCX_MAX_PAGES
    except Exception:
        # If we cannot inspect the file, allow fallback attempt.
        return True


def pdf_to_docx(file):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    uid = str(uuid.uuid4())
    input_name = f"{uid}.pdf"
    input_path = os.path.join(settings.MEDIA_ROOT, input_name)

    try:
        with open(input_path, "wb+") as f:
            for chunk in file.chunks():
                f.write(chunk)

        output_name = f"{uid}.docx"
        output_path = os.path.join(settings.MEDIA_ROOT, output_name)

        # Tier 1: Word COM (Windows only): best layout fidelity when available.
        if os.name == "nt":
            if _convert_with_word_com(input_path, output_path):
                return output_name
            if _convert_with_word_powershell(input_path, output_path):
                return output_name

        # Tier 2: LibreOffice fallback, usually faster on complex PDFs.
        if _convert_with_libreoffice(input_path, settings.MEDIA_ROOT, output_path, uid):
            return output_name

        # Tier 3: pdf2docx for smaller files where an editable structure is feasible.
        if _should_try_pdf2docx(input_path):
            if _convert_with_pdf2docx(input_path, output_path):
                return output_name

        raise RuntimeError("PDF to DOCX conversion failed across all available engines.")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

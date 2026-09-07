import logging
import multiprocessing
import os
import shutil
import subprocess
import time
from functools import lru_cache

from django.conf import settings

from ..uploads import ToolError, read_pdf, save_upload

logger = logging.getLogger(__name__)

# Each engine gets CONVERT_TIMEOUT_SECONDS, and the whole request gets
# TOTAL_BUDGET_SECONDS. Both must stay under gunicorn's --timeout or the worker
# is killed mid-conversion and the user sees a 502 instead of an error page.
TOTAL_BUDGET_SECONDS = 240
PDF2DOCX_MAX_MB = 8
PDF2DOCX_MAX_PAGES = 10


def _timeout():
    return settings.CONVERT_TIMEOUT_SECONDS


@lru_cache(maxsize=1)
def word_engine_available():
    """Whether Microsoft Word can be driven for high-fidelity conversion.

    Cached: the PowerShell probe below costs seconds, and this is called on
    every GET of the tool page.
    """
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
                "$word=$null; try { $word=New-Object -ComObject Word.Application; 'ok' } "
                "finally { if($word -ne $null){$word.Quit()} }",
            ],
            check=True,
            timeout=6,
            capture_output=True,
            text=True,
        )
        return True
    except Exception:
        return False


def _mp_context():
    """Pick a start method that is safe inside a WSGI worker.

    "spawn" re-imports __main__, which under gunicorn means re-running the
    gunicorn entry point. Python 3.14 switched the Linux default away from
    "fork", so pin it explicitly rather than inherit whatever the runtime picks.
    The worker functions are module-level so they stay picklable either way.
    """
    try:
        return multiprocessing.get_context("fork")
    except ValueError:          # Windows has no fork
        return multiprocessing.get_context("spawn")


def _run_in_process(target, args, timeout):
    """Run `target` in a child process so a hung engine can be killed."""
    ctx = _mp_context()
    queue = ctx.Queue()
    process = ctx.Process(target=target, args=(*args, queue))
    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join(5)
        if process.is_alive():
            process.kill()
        return False

    return bool(not queue.empty() and queue.get())


def _word_com_worker(input_path, output_path, result_queue):
    word = None
    doc = None
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        result_queue.put(False)
        return

    try:
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(
            FileName=os.path.abspath(input_path),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
            Revert=False,
            NoEncodingDialog=True,
        )
        doc.SaveAs2(os.path.abspath(output_path), FileFormat=16)  # wdFormatXMLDocument
        result_queue.put(os.path.exists(output_path))
    except Exception:
        result_queue.put(False)
    finally:
        for close in (lambda: doc and doc.Close(0), lambda: word and word.Quit(),
                      pythoncom.CoUninitialize):
            try:
                close()
            except Exception:
                pass


def _convert_with_word_powershell(input_path, output_path, timeout):
    """Word automation without pywin32 - the path that works on a bare Windows box."""
    if os.name != "nt":
        return False

    in_ps = os.path.abspath(input_path).replace("'", "''")
    out_ps = os.path.abspath(output_path).replace("'", "''")
    script = (
        "$ErrorActionPreference='Stop';"
        "$word=$null;$doc=$null;"
        "try {"
        "$word=New-Object -ComObject Word.Application;"
        "$word.Visible=$false;$word.DisplayAlerts=0;"
        f"$doc=$word.Documents.Open('{in_ps}',$false,$true);"
        f"$doc.SaveAs2('{out_ps}',16);"
        "} finally {"
        "if($doc -ne $null){$doc.Close(0)};"
        "if($word -ne $null){$word.Quit()}"
        "}"
    )

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True,
            timeout=timeout,
            capture_output=True,
        )
        return os.path.exists(output_path)
    except Exception as exc:
        logger.info("Word (PowerShell) PDF->DOCX failed: %s", exc)
        return False


def _pdf2docx_worker(input_path, output_path, result_queue):
    try:
        from pdf2docx import Converter

        converter = Converter(input_path)
        try:
            converter.convert(
                output_path,
                multi_processing=False,   # we already run in a child process
                parse_lattice_table=False,
                parse_stream_table=False,
            )
        finally:
            converter.close()
        result_queue.put(os.path.exists(output_path))
    except Exception:
        result_queue.put(False)


def _convert_with_libreoffice(input_path, output_dir, output_path, uid, timeout):
    """LibreOffice headless PDF -> DOCX, with a per-request user profile.

    A shared profile directory makes concurrent conversions fail on the
    profile lock, so every request gets its own and deletes it afterwards.
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

    try:
        # Writer import first: the Impress importer yields textbox-heavy output.
        for infilter in (["--infilter=writer_pdf_import"], []):
            try:
                subprocess.run(
                    [*base_cmd, *infilter, input_path],
                    check=True,
                    timeout=timeout,
                    capture_output=True,
                )
                if os.path.exists(output_path):
                    return True
            except Exception as exc:
                logger.info("LibreOffice PDF->DOCX attempt failed: %s", exc)
        return False
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)


def _should_try_pdf2docx(input_path):
    try:
        if os.path.getsize(input_path) / (1024 * 1024) > PDF2DOCX_MAX_MB:
            return False
        from pypdf import PdfReader

        return len(PdfReader(input_path).pages) <= PDF2DOCX_MAX_PAGES
    except Exception:
        return True


def pdf_to_docx(file):
    """Convert a PDF to DOCX using the best engine available on this host."""
    read_pdf(file, file.name)          # reject corrupt/encrypted input up front
    file.seek(0)

    input_path = save_upload(file, ".pdf")
    uid = os.path.splitext(os.path.basename(input_path))[0]
    output_name = f"{uid}.docx"
    output_path = os.path.join(settings.MEDIA_ROOT, output_name)
    deadline = time.monotonic() + TOTAL_BUDGET_SECONDS

    def remaining():
        return min(_timeout(), deadline - time.monotonic())

    try:
        # Tier 1: Microsoft Word - best fidelity, Windows only.
        if os.name == "nt" and word_engine_available() and remaining() > 5:
            if _run_in_process(_word_com_worker, (input_path, output_path), remaining()):
                return output_name
            if _convert_with_word_powershell(input_path, output_path, remaining()):
                return output_name

        # Tier 2: pdf2docx - good text/layout fidelity for ordinary PDFs.
        if remaining() > 5 and _should_try_pdf2docx(input_path):
            if _run_in_process(_pdf2docx_worker, (input_path, output_path), remaining()):
                return output_name

        # Tier 3: LibreOffice - copes with large or complex documents.
        if remaining() > 5 and _convert_with_libreoffice(
            input_path, settings.MEDIA_ROOT, output_path, uid, remaining()
        ):
            return output_name

        logger.warning("pdf_to_docx: all engines failed for a %s-byte PDF", file.size)
        raise ToolError(
            "This PDF could not be converted. Scanned or image-only PDFs are not "
            "supported yet - try a smaller, text-based PDF."
        )
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

"""Tool views.

All thirteen tools share one request flow: validate the upload, run a service
function, stream the result back as a download. `TOOLS` below is the only thing
that differs between them, so the validation, error handling, logging and
cleanup are written once rather than thirteen times.
"""
import logging
import os
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from django.conf import settings
from django.core.mail import send_mail
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import Feedback, Suggestion
from .seo import PAGES
from .services.compress_pdf import LEVELS, compress_pdf
from .services.compress_to_size import compress_pdf_to_size
from .services.docx_to_pdf import docx_to_pdf
from .services.extract_pages import extract_pages
from .services.image_to_pdf import PAGE_SIZES, img_to_pdf
from .services.merge_pdf import merge_pdfs
from .services.pdf_to_docx import pdf_to_docx
from .services.pdf_to_image import DPI_CHOICES, FORMATS, pdf_to_images
from .services.protect_pdf import protect_pdf
from .services.reorder_pdf import reorder_pdf
from .services.rotate_pdf import rotate_pdf
from .services.split_pdf import split_pdf
from .services.unlock_pdf import unlock_pdf
from .throttle import throttled
from .uploads import (
    ToolError,
    cleanup_old_files,
    validate_upload,
    validate_uploads,
)

logger = logging.getLogger(__name__)

PDF = (".pdf",)
IMAGES = (".png", ".jpg", ".jpeg", ".webp")
WORD = (".doc", ".docx")

GENERIC_ERROR = (
    "Something went wrong while processing your file. "
    "Please try again, or report the problem using the bug button."
)


@dataclass(frozen=True)
class Tool:
    """Everything that differs between one tool and the next."""

    template: str
    service: Callable
    suffix: str
    output_ext: str
    accepts: tuple = PDF
    field_name: str = "file"
    multiple: bool = False
    #  request -> extra keyword arguments for the service; may raise ToolError
    options: Optional[Callable] = None


def _int_option(request, name, choices, default):
    """Read a whitelisted integer from POST, falling back to `default`."""
    try:
        value = int(request.POST.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value in choices else default


def _protect_options(request):
    """Catch a mistyped confirmation before the file is locked with it."""
    pwd = request.POST.get("pwd", "")
    confirm = request.POST.get("pwd_confirm", "")
    if confirm and pwd != confirm:
        raise ToolError("The two passwords do not match.")
    return {"pwd": pwd}


TOOLS = {
    "merge_pdf": Tool(
        template="tools/merge_pdf.html", service=merge_pdfs,
        suffix="_merged", output_ext=".pdf",
        field_name="files", multiple=True,
    ),
    "split_pdf": Tool(
        template="tools/split_pdf.html", service=split_pdf,
        suffix="_split", output_ext=".zip",
    ),
    "compress_pdf": Tool(
        template="tools/compress_pdf.html", service=compress_pdf,
        suffix="_compressed", output_ext=".pdf",
        options=lambda r: {
            "level": r.POST.get("level") if r.POST.get("level") in LEVELS else "balanced"
        },
    ),
    "compress_100kb": Tool(
        template="tools/compress_100kb.html", service=compress_pdf_to_size,
        suffix="_compressed", output_ext=".pdf",
        options=lambda r: {"target_kb": _int_option(r, "target_kb", (100, 200, 500), 100)},
    ),
    "extract_pages": Tool(
        template="tools/extract_pages.html", service=extract_pages,
        suffix="_extracted", output_ext=".pdf",
        options=lambda r: {"selection": r.POST.get("pages", "")},
    ),
    "image_to_pdf": Tool(
        template="tools/image_to_pdf.html", service=img_to_pdf,
        suffix="_images", output_ext=".pdf",
        accepts=IMAGES, field_name="images", multiple=True,
        options=lambda r: {
            "page_size": r.POST.get("page_size") if r.POST.get("page_size") in PAGE_SIZES else "a4"
        },
    ),
    "pdf_to_image": Tool(
        template="tools/pdf_to_image.html", service=pdf_to_images,
        suffix="_images", output_ext=".zip",
        field_name="files", multiple=True,
        options=lambda r: {
            "dpi": _int_option(r, "dpi", DPI_CHOICES, 150),
            "image_format": r.POST.get("format") if r.POST.get("format") in FORMATS else "png",
        },
    ),
    "pdf_to_docx": Tool(
        template="tools/pdf_to_docx.html", service=pdf_to_docx,
        suffix="", output_ext=".docx",
    ),
    "docx_to_pdf": Tool(
        template="tools/docx_to_pdf.html", service=docx_to_pdf,
        suffix="", output_ext=".pdf", accepts=WORD,
    ),
    "rotate_pdf": Tool(
        template="tools/rotate_pdf.html", service=rotate_pdf,
        suffix="_rotated", output_ext=".pdf",
        options=lambda r: {"angle": r.POST.get("angle")},
    ),
    "protect_pdf": Tool(
        template="tools/protect_pdf.html", service=protect_pdf,
        suffix="_protected", output_ext=".pdf",
        options=_protect_options,
    ),
    "unlock_pdf": Tool(
        template="tools/unlock_pdf.html", service=unlock_pdf,
        suffix="_unlocked", output_ext=".pdf",
        options=lambda r: {"pwd": r.POST.get("pwd", "")},
    ),
    "reorder_pdf": Tool(
        template="tools/reorder_pdf.html", service=reorder_pdf,
        suffix="_reordered", output_ext=".pdf",
        options=lambda r: {"order": r.POST.get("order", "")},
    ),
}


def build_download_name(original_name, suffix, extension):
    base_name = os.path.splitext(os.path.basename(original_name or "file"))[0]
    return f"{base_name}{suffix}{extension}"


def _download(path, download_name):
    """Stream a generated file, then delete it.

    On POSIX the file is unlinked while still open, so it is gone from disk the
    moment the response is built - which is what the privacy page promises.
    Windows cannot unlink an open file, so there the sweeper handles it.
    """
    handle = open(path, "rb")
    if os.name != "nt":
        try:
            os.remove(path)
        except OSError:
            pass

    response = FileResponse(handle, as_attachment=True, filename=download_name)
    # The spinner script watches for this cookie to know the download started.
    response.set_cookie("fileDownload", "true", max_age=60, samesite="Lax")
    return response


def _run(request, name):
    """Shared GET/POST handling for every tool."""
    tool = TOOLS[name]
    # Sweep on every tool hit, not only successful POSTs. _download unlinks the
    # file as it streams, but that cannot happen on Windows or after a killed
    # worker, so on a quiet site leftovers outlived the retention window while
    # waiting for the next upload to trigger a sweep.
    # ponytail: a scandir per request; move to a cron/beat job if media grows big.
    cleanup_old_files()
    extra_context = {
        "seo": PAGES[name],
        "max_upload_mb": settings.MAX_UPLOAD_MB,
        "max_upload_files": settings.MAX_UPLOAD_FILES,
    }

    if request.method != "POST":
        return render(request, tool.template, extra_context)

    # A conversion can hold this worker for CONVERT_TIMEOUT_SECONDS, and there
    # are only a handful of workers. Cap how many one address can start.
    if throttled(request, "tool", settings.TOOL_RATE_LIMIT,
                 settings.TOOL_RATE_WINDOW_SECONDS):
        return render(request, tool.template, {
            "error_message": (
                "You have run a lot of conversions in the last few minutes. "
                "Please wait a moment and try again."
            ),
            **extra_context,
        }, status=429)

    try:
        if tool.multiple:
            uploads = request.FILES.getlist(tool.field_name)
            validate_uploads(uploads, tool.accepts)
            payload = uploads
            first_name = uploads[0].name
        else:
            upload = request.FILES.get(tool.field_name)
            validate_upload(upload, tool.accepts)
            payload = upload
            first_name = upload.name

        options = tool.options(request) if tool.options else {}
        output_name = tool.service(payload, **options)

    except ToolError as exc:
        return render(request, tool.template, {"error_message": str(exc), **extra_context})
    except Exception:
        # Never surface the exception text: it leaks server paths.
        logger.exception("%s failed", name)
        return render(request, tool.template, {"error_message": GENERIC_ERROR, **extra_context})

    output_path = os.path.join(settings.MEDIA_ROOT, output_name)
    if not os.path.exists(output_path):
        logger.error("%s: service returned a missing file %r", name, output_name)
        return render(request, tool.template, {"error_message": GENERIC_ERROR, **extra_context})

    return _download(output_path, build_download_name(first_name, tool.suffix, tool.output_ext))


# Thin named wrappers so urls.py and {% url %} tags stay readable.
def merge_pdf(request):          return _run(request, "merge_pdf")
def split_pdf_view(request):     return _run(request, "split_pdf")
def compress_pdf_view(request):  return _run(request, "compress_pdf")
def compress_100kb_view(request): return _run(request, "compress_100kb")
def extract_pages_view(request): return _run(request, "extract_pages")
def image_to_pdf_view(request):  return _run(request, "image_to_pdf")
def pdf_to_image_view(request):  return _run(request, "pdf_to_image")
def pdf_to_docx_view(request):   return _run(request, "pdf_to_docx")
def docx_to_pdf_view(request):   return _run(request, "docx_to_pdf")
def rotate_pdf_view(request):    return _run(request, "rotate_pdf")
def protect_pdf_view(request):   return _run(request, "protect_pdf")
def unlock_pdf_view(request):    return _run(request, "unlock_pdf")
def reorder_pdf_view(request):   return _run(request, "reorder_pdf")


# ---------------------------------------------------------------------------
# Static pages
# ---------------------------------------------------------------------------
@ensure_csrf_cookie
def home(request):
    return render(request, "tools/home.html", {"seo": PAGES["home"]})


def privacy_view(request):
    return render(request, "tools/privacy.html", {"seo": PAGES["privacy"]})


def terms_view(request):
    return render(request, "tools/terms.html", {"seo": PAGES["terms"]})


def about_view(request):
    return render(request, "tools/about.html", {"seo": PAGES["about"]})


def healthz(request):
    """Liveness probe for the platform's health check."""
    return HttpResponse("ok", content_type="text/plain")


# ---------------------------------------------------------------------------
# Feedback and suggestions
# ---------------------------------------------------------------------------
def _rate_limited(request):
    """Per-IP cap on submissions, so the forms cannot burn the email quota."""
    return throttled(request, "feedback", settings.FEEDBACK_RATE_LIMIT,
                     settings.FEEDBACK_RATE_WINDOW_SECONDS)


def _send_email(subject, message):
    """Notify the admin over Gmail SMTP.

    Never raises: the submission is already in the database by this point, so a
    dead mail server must not turn a saved report into a 500 for the user.
    """
    recipient = getattr(settings, "FEEDBACK_EMAIL", "")
    if not recipient:
        logger.warning("tryPDF! email: FEEDBACK_EMAIL not set, skipping notification")
        return

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
        logger.info("tryPDF! email: sent %r to %s", subject, recipient)
    except Exception:
        # Common causes: an account password used instead of a Gmail App
        # Password, 2-Step Verification off, or the host blocking outbound
        # port 587. The full exception goes to the platform log.
        logger.exception("tryPDF! email: SMTP send failed")


def _queue_email(subject, body):
    """Send off the request thread - Gmail can take seconds to respond."""
    if getattr(settings, "TESTING", False):
        _send_email(subject, body)      # deterministic under the test runner
        return

    threading.Thread(target=_send_email, args=(subject, body), daemon=True).start()


def _collect(request, *fields, max_length=3000):
    """Pull and validate required text fields; raises ToolError on bad input."""
    values = []
    for name in fields:
        value = request.POST.get(name, "").strip()
        if not value:
            raise ToolError("Please fill in all fields.")
        if len(value) > max_length:
            raise ToolError(f"That is too long (max {max_length} characters).")
        values.append(value)
    return values


@require_POST
def submit_feedback(request):
    try:
        feature, issue = _collect(request, "feature", "issue")
    except ToolError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    if _rate_limited(request):
        return JsonResponse(
            {"ok": False, "error": "You have sent several reports already. Please try again later."},
            status=429,
        )

    try:
        Feedback.objects.create(feature=feature[:150], issue=issue)
    except Exception:
        logger.exception("submit_feedback: DB save failed")

    _queue_email(
        f"[tryPDF! Bug] {feature}",
        f"Bug Report - tryPDF!\n{'=' * 40}\nFeature : {feature}\nIssue   : {issue}\n",
    )
    return JsonResponse({"ok": True})


@require_POST
def submit_suggestion(request):
    try:
        description, why_needed = _collect(request, "description", "why_needed")
    except ToolError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    if _rate_limited(request):
        return JsonResponse(
            {"ok": False, "error": "You have sent several suggestions already. Please try again later."},
            status=429,
        )

    try:
        Suggestion.objects.create(description=description, why_needed=why_needed)
    except Exception:
        logger.exception("submit_suggestion: DB save failed")

    _queue_email(
        "[tryPDF! Suggestion]",
        f"Suggestion - tryPDF!\n{'=' * 40}\nDescription : {description}\nWhy needed  : {why_needed}\n",
    )
    return JsonResponse({"ok": True})

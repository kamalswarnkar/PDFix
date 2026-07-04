from django.shortcuts import render
from django.http import HttpResponse, FileResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.mail import send_mail
from django.conf import settings
from .services.merge_pdf import merge_pdfs
from .services.split_pdf import split_pdf
from .services.compress_pdf import compress_pdf
from .services.compress_to_size import compress_pdf_to_size
from .services.extract_pages import extract_pages
from .services.image_to_pdf import img_to_pdf
from .services.pdf_to_image import pdf_to_images
from .services.pdf_to_docx import pdf_to_docx, word_engine_available
from .services.docx_to_pdf import docx_to_pdf
from .services.rotate_pdf import rotate_pdf
from .services.protect_pdf import protect_pdf
from .services.unlock_pdf import unlock_pdf
from .services.reorder_pdf import reorder_pdf
from .utils.cleanup import cleanup_old_files
from .models import Feedback, Suggestion
import os
import json
import logging
import threading
import urllib.request

logger = logging.getLogger(__name__)


def _send_email_bg(subject, message, from_email, recipient):
    """Send via Brevo HTTP API — avoids SMTP ports blocked by Render/Railway."""
    from django.conf import settings as _s
    api_key = getattr(_s, "BREVO_API_KEY", "")
    if not api_key:
        logger.warning("PDFix email: BREVO_API_KEY not set, skipping email")
        return
    payload = json.dumps({
        "sender": {"name": "PDFix", "email": from_email},
        "to": [{"email": recipient}],
        "subject": subject,
        "textContent": message,
    }).encode()
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={"Content-Type": "application/json", "api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("PDFix email: sent OK (HTTP %s) to %s", resp.status, recipient)
    except Exception:
        logger.exception("PDFix email: Brevo API call FAILED")


# Create your views here.

def build_download_name(original_name, suffix, extension):
    base_name = os.path.splitext(os.path.basename(original_name))[0]
    return f"{base_name}{suffix}{extension}"

@ensure_csrf_cookie
def home(request):
    return render(request, "tools/home.html")

def merge_pdf(request):
    cleanup_old_files()

    if request.method == "POST":
        files = request.FILES.getlist("files")
        if not files:
            return render(request, "tools/merge_pdf.html", {
                "error_message": "No files selected. Please upload at least one PDF.",
            })
        try:
            merged_filename = merge_pdfs(files)
            filepath = os.path.join(settings.MEDIA_ROOT, merged_filename)
            download_name = build_download_name(files[0].name, "_merged", ".pdf")
            response = FileResponse(open(filepath, "rb"), as_attachment=True, filename=download_name)
            response.set_cookie("fileDownload", "true")
            return response
        except Exception as e:
            return render(request, "tools/merge_pdf.html", {
                "error_message": f"Failed to merge PDFs. Details: {e}",
            })
    
    return render(request, "tools/merge_pdf.html")

def split_pdf_view(request):
    cleanup_old_files()

    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            return render(request, "tools/split_pdf.html", {
                "error_message": "No file selected. Please upload a PDF.",
            })
        try:
            zipfilename = split_pdf(file)
            file_path = os.path.join(settings.MEDIA_ROOT, zipfilename)
            download_name = build_download_name(file.name, "_split_pdf", ".zip")
            response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)
            response.set_cookie("fileDownload", "true")
            return response
        except Exception as e:
            return render(request, "tools/split_pdf.html", {
                "error_message": f"Failed to split PDF. Details: {e}",
            })
    
    return render(request, "tools/split_pdf.html")

def compress_pdf_view(request):
    cleanup_old_files()

    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            return render(request, "tools/compress_pdf.html", {
                "error_message": "No file selected. Please upload a PDF.",
            })
        try:
            compressed_filename = compress_pdf(file)
            file_path = os.path.join(settings.MEDIA_ROOT, compressed_filename)
            download_name = build_download_name(file.name, "_compressed", ".pdf")
            response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)
            response.set_cookie("fileDownload", "true")
            return response
        except Exception as e:
            return render(request, "tools/compress_pdf.html", {
                "error_message": f"Compression failed. Details: {e}",
            })
    return render(request, "tools/compress_pdf.html")

def compress_100kb_view(request):
    cleanup_old_files()

    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            return render(request, "tools/compress_100kb.html", {
                "error_message": "No file selected. Please upload a PDF.",
            })
        try:
            compressed_filename = compress_pdf_to_size(file, 100)
            file_path = os.path.join(settings.MEDIA_ROOT, compressed_filename)
            download_name = build_download_name(file.name, "_compressed_100kb", ".pdf")
            response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)
            response.set_cookie("fileDownload", "true")
            return response
        except Exception as e:
            return render(request, "tools/compress_100kb.html", {
                "error_message": f"Compression failed. Details: {e}",
            })

    return render(request, "tools/compress_100kb.html")

def extract_pages_view(request):
    cleanup_old_files()

    if request.method == "POST":
        file = request.FILES.get("file")
        try:
            start_str = request.POST.get("start", "")
            end_str = request.POST.get("end", "")
            if not start_str or not end_str:
                raise ValueError("Please provide both start and end page numbers.")
            start = int(start_str)
            end = int(end_str)
            filename = extract_pages(file, start, end)
        except (ValueError, TypeError, Exception) as e:
            return render(request, "tools/extract_pages.html", {
                "error_message": str(e) if isinstance(e, (ValueError, TypeError)) else "Failed to extract pages. Please check the file and try again.",
            })

        file_path = os.path.join(settings.MEDIA_ROOT, filename)
        download_name = build_download_name(file.name, "_extracted", ".pdf")

        response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)

        response.set_cookie("fileDownload", "true")

        return response
    
    return render(request, "tools/extract_pages.html")

def image_to_pdf_view(request):
    cleanup_old_files()

    if request.method == "POST":
        files = request.FILES.getlist("images")
        if not files:
            return render(request, "tools/image_to_pdf.html", {
                "error_message": "No images selected. Please upload at least one image.",
            })
        try:
            filename = img_to_pdf(files)
            filepath = os.path.join(settings.MEDIA_ROOT, filename)
            download_name = build_download_name(files[0].name, "_images", ".pdf")
            response = FileResponse(open(filepath, "rb"), as_attachment=True, filename=download_name)
            response.set_cookie("fileDownload", "true")
            return response
        except Exception as e:
            return render(request, "tools/image_to_pdf.html", {
                "error_message": f"Failed to convert images to PDF. Details: {e}",
            })
    
    return render(request, "tools/image_to_pdf.html")

def pdf_to_image_view(request):
    cleanup_old_files()

    if request.method == "POST":
        files = request.FILES.getlist("files")
        if not files:
            return render(request, "tools/pdf_to_image.html", {
                "error_message": "No files selected. Please upload at least one PDF.",
            })
        try:
            zip_filename = pdf_to_images(files)
            file_path = os.path.join(settings.MEDIA_ROOT, zip_filename)
            download_name = build_download_name(files[0].name, "_images", ".zip")
            response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)
            response.set_cookie("fileDownload", "true")
            return response
        except Exception as e:
            return render(request, "tools/pdf_to_image.html", {
                "error_message": f"Failed to convert PDF to images. Details: {e}",
            })
    
    return render(request, "tools/pdf_to_image.html")

def pdf_to_docx_view(request):
    cleanup_old_files()

    if request.method == "POST":
        file = request.FILES.get("file")
        try:
            file_name = pdf_to_docx(file)
            file_path = os.path.join(settings.MEDIA_ROOT, file_name)
            download_name = build_download_name(file.name, "", ".docx")

            response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)

            response.set_cookie("fileDownload", "true")

            return response
        except Exception:
            return render(request, "tools/pdf_to_docx.html", {
                "error_message": "Conversion failed or timed out. Try a smaller file, or retry with a clearer text-based PDF.",
                "word_engine_available": word_engine_available(),
            })
    
    return render(request, "tools/pdf_to_docx.html", {
        "word_engine_available": word_engine_available(),
    })

def docx_to_pdf_view(request):
    cleanup_old_files()

    if request.method == "POST":
        file = request.FILES.get("file")
        try:
            filename = docx_to_pdf(file)
        except Exception as e:
            return render(request, "tools/docx_to_pdf.html", {
                "error_message": str(e),
            })
        file_path = os.path.join(settings.MEDIA_ROOT, filename)
        download_name = build_download_name(file.name, "", ".pdf")

        response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)

        response.set_cookie("fileDownload", "true")

        return response
    
    return render(request, "tools/docx_to_pdf.html")

def rotate_pdf_view(request):
    cleanup_old_files()

    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            return render(request, "tools/rotate_pdf.html", {
                "error_message": "No file selected. Please upload a PDF.",
            })
        try:
            angle = int(request.POST.get("angle"))
            filename = rotate_pdf(file, angle)
            file_path = os.path.join(settings.MEDIA_ROOT, filename)
            download_name = build_download_name(file.name, "_rotated", ".pdf")
            response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)
            response.set_cookie("fileDownload", "true")
            return response
        except Exception as e:
            return render(request, "tools/rotate_pdf.html", {
                "error_message": f"Failed to rotate PDF. Details: {e}",
            })
    
    return render(request, "tools/rotate_pdf.html")

def protect_pdf_view(request):
    cleanup_old_files()

    if request.method == "POST":
        file = request.FILES.get("file")
        pwd = request.POST.get("pwd")
        if not file or not pwd:
            return render(request, "tools/protect_pdf.html", {
                "error_message": "Invalid form submission. Please provide both a PDF file and a password.",
            })
        try:
            filename = protect_pdf(file, pwd)
            file_path = os.path.join(settings.MEDIA_ROOT, filename)
            download_name = build_download_name(file.name, "_protected", ".pdf")
            response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)
            response.set_cookie("fileDownload", "true")
            return response
        except Exception as e:
            return render(request, "tools/protect_pdf.html", {
                "error_message": f"Failed to protect PDF. Details: {e}",
            })
    
    return render(request, "tools/protect_pdf.html")

def unlock_pdf_view(request):
    cleanup_old_files()

    if request.method == "POST":
        file = request.FILES.get("file")
        pwd = request.POST.get("pwd")
        try:
            filename = unlock_pdf(file, pwd)
        except Exception:
            return render(request, "tools/unlock_pdf.html", {
                "error_message": "Incorrect password or the PDF could not be unlocked. Please check your password and try again.",
            })
        file_path = os.path.join(settings.MEDIA_ROOT, filename)
        download_name = build_download_name(file.name, "_unlocked", ".pdf")

        response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)

        response.set_cookie("fileDownload", "true")

        return response
    
    return render(request, "tools/unlock_pdf.html")


def reorder_pdf_view(request):
    cleanup_old_files()

    if request.method == "POST":
        file = request.FILES.get("file")
        order = request.POST.get("order")
        if not file or not order:
            return render(request, "tools/reorder_pdf.html", {
                "error": "Upload a PDF and wait for the page previews before submitting."
            })

        try:
            filename = reorder_pdf(file, order)
        except (ValueError, Exception) as e:
            return render(request, "tools/reorder_pdf.html", {
                "error": str(e) if isinstance(e, ValueError) else "Failed to reorder PDF. Please verify that the file is not corrupt."
            })
        file_path = os.path.join(settings.MEDIA_ROOT, filename)
        download_name = build_download_name(file.name, "_reordered", ".pdf")

        response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=download_name)
        response.set_cookie("fileDownload", "true")
        return response
    return render(request, "tools/reorder_pdf.html")

def privacy_view(request):
    return render(request, "tools/privacy.html")

def terms_view(request):
    return render(request, "tools/terms.html")

def about_view(request):
    return render(request, "tools/about.html")


@require_POST
def submit_feedback(request):
    feature = request.POST.get("feature", "").strip()
    issue   = request.POST.get("issue", "").strip()
    if not feature or not issue:
        return JsonResponse({"ok": False, "error": "Please fill in all fields."}, status=400)
    if len(issue) > 3000:
        return JsonResponse({"ok": False, "error": "Issue description is too long (max 3000 characters)."}, status=400)

    try:
        Feedback.objects.create(feature=feature, issue=issue)
    except Exception:
        logger.exception("submit_feedback: DB save failed")

    body = (
        f"Bug Report \u2014 PDFix\n"
        f"{'='*40}\n"
        f"Feature : {feature}\n"
        f"Issue   : {issue}\n"
    )
    threading.Thread(
        target=_send_email_bg,
        args=(f"[PDFix Bug] {feature}", body, settings.DEFAULT_FROM_EMAIL, settings.FEEDBACK_EMAIL),
        daemon=True,
    ).start()

    return JsonResponse({"ok": True})


@require_POST
def submit_suggestion(request):
    description = request.POST.get("description", "").strip()
    why_needed  = request.POST.get("why_needed", "").strip()
    if not description or not why_needed:
        return JsonResponse({"ok": False, "error": "Please fill in all fields."}, status=400)
    if len(description) > 3000 or len(why_needed) > 3000:
        return JsonResponse({"ok": False, "error": "Text is too long (max 3000 characters per field)."}, status=400)

    try:
        Suggestion.objects.create(description=description, why_needed=why_needed)
    except Exception:
        logger.exception("submit_suggestion: DB save failed")

    body = (
        f"Suggestion \u2014 PDFix\n"
        f"{'='*40}\n"
        f"Description : {description}\n"
        f"Why needed  : {why_needed}\n"
    )
    threading.Thread(
        target=_send_email_bg,
        args=("[PDFix Suggestion]", body, settings.DEFAULT_FROM_EMAIL, settings.FEEDBACK_EMAIL),
        daemon=True,
    ).start()

    return JsonResponse({"ok": True})

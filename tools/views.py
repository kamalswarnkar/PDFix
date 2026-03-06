from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from .services.merge_pdf import merge_pdfs
from .services.split_pdf import split_pdf
from .services.compress_pdf import compress_pdf
from .services.compress_to_size import compress_pdf_to_size
from .services.extract_pages import extract_pages
import os
from django.conf import settings
# Create your views here.

def home(request):
    return render(request, "tools/home.html")

def merge_pdf(request):
    if request.method == "POST":
        files = request.FILES.getlist("files")
        merged_filename = merge_pdfs(files)
        filepath = os.path.join(settings.MEDIA_ROOT, merged_filename)

        return FileResponse(open(filepath, "rb"), as_attachment=True)
    
    return render(request, "tools/merge_pdf.html")

def split_pdf_view(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        zipfilename = split_pdf(file)
        file_path = os.path.join(settings.MEDIA_ROOT, zipfilename)

        return FileResponse(open(file_path, "rb"), as_attachment=True, filename=zipfilename)
    
    return render(request, "tools/split_pdf.html")

def compress_pdf_view(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        compressed_filename = compress_pdf(file)
        file_path = os.path.join(settings.MEDIA_ROOT, compressed_filename)

        return FileResponse(open(file_path, "rb"), as_attachment=True)
    return render(request, "tools/compress_pdf.html")

def compress_100kb_view(request):

    if request.method == "POST":

        file = request.FILES.get("file")

        compressed_filename = compress_pdf_to_size(file, 100)

        file_path = os.path.join(settings.MEDIA_ROOT, compressed_filename)

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=compressed_filename
        )

    return render(request, "tools/compress_100kb.html")

def extract_pages_view(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        start = int(request.POST.get("start"))
        end = int(request.POST.get("end"))

        filename = extract_pages(file, start, end)

        file_path = os.path.join(settings.MEDIA_ROOT, filename)

        return FileResponse(open(file_path, "rb"), as_attachment=True, filename=filename)
    
    return render(request, "tools/extract_pages.html")
from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from .services.merge_pdf import merge_pdfs
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

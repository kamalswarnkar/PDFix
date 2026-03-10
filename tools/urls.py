from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("merge-pdf/", views.merge_pdf, name="merge_pdf"),
    path("split-pdf/", views.split_pdf_view, name = "split_pdf"),
    path("compress-pdf/", views.compress_pdf_view, name="compress_pdf"),
    path("compress-pdf-100kb/", views.compress_100kb_view, name="compress_100kb"),
    path("extract-pages/", views.extract_pages_view, name="extract_pages"),
    path("image-to-pdf/", views.image_to_pdf_view, name="image_to_pdf"),
    path("pdf-to-image/", views.pdf_to_image_view, name="pdf_to_image"),
    path("pdf-to-docx/", views.pdf_to_docx_view, name="pdf_to_docx"),
    path("docx-to-pdf/", views.docx_to_pdf_view, name="docx_to_pdf"),
    path("rotate-pdf/", views.rotate_pdf_view, name="rotate_pdf"),
    path("protect-pdf/", views.protect_pdf_view, name="protect_pdf"),
    path("unlock-pdf/", views.unlock_pdf_view, name="unlock_pdf"),
]
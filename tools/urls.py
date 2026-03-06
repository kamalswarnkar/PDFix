from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("merge-pdf/", views.merge_pdf, name="merge_pdf"),
    path("split-pdf/", views.split_pdf_view, name = "split_pdf"),
    path("compress-pdf/", views.compress_pdf_view, name="compress_pdf"),
    path("compress-pdf-100kb/", views.compress_100kb_view, name="compress_100kb"),
    path("extract-pages/", views.extract_pages_view, name="extract_pages"),
]
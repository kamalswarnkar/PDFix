from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("merge-pdf/", views.merge_pdf, name="merge_pdf"),
]
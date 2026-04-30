from django.urls import path
from dashboard.views import dashboard_view, download_sample

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('samples/<str:filename>', download_sample, name='download_sample'),
]

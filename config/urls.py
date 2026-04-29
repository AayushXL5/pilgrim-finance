from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('health/', lambda r: JsonResponse({'status': 'ok'}), name='health'),
    path('admin/', admin.site.urls),
    path('api/', include('finance.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('', include('dashboard.urls')),
]

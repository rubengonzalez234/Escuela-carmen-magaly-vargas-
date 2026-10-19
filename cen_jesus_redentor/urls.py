"""
URL configuration for cen_jesus_redentor project.
"""
from django.contrib import admin
from django.urls import path, include  # ✅ Agregar "include"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('escuela.urls')),  # ✅ Agregar esta línea
]

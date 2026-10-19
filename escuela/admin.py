from django.contrib import admin
from .models import Estudiante, Docente, Materia, Calificacion, Asistencia

@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'cedula', 'edad', 'activo')
    search_fields = ('nombres', 'apellidos', 'cedula')
    list_filter = ('activo', 'genero')

@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'cedula', 'especialidad', 'activo')
    search_fields = ('nombres', 'apellidos', 'cedula')
    list_filter = ('activo', 'genero', 'especialidad')

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'docente')
    search_fields = ('nombre', 'codigo')

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'materia', 'nota', 'periodo')
    list_filter = ('periodo', 'materia')
    search_fields = ('estudiante__nombres', 'estudiante__apellidos')

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'fecha', 'presente')
    list_filter = ('presente', 'fecha')
    search_fields = ('estudiante__nombres', 'estudiante__apellidos')

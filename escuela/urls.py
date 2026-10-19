from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('gestion-estudiantes/',
         views.gestion_estudiantes,
         name='gestion_estudiantes'),

    path('admin-panel/estudiantes/retirar/<int:pk>/',
         views.admin_estudiante_retirar,
         name='admin_estudiante_retirar'),

    path('admin-panel/estudiantes/<str:nivel>/',
         views.admin_estudiantes_json,
         name='admin_estudiantes_json'),

    # Educación Inicial
    path('inicial/', views.inicial, name='inicial'),
    path('inicial/registrar/', views.registrar_estudiante, name='registrar_estudiante'),
    path('inicial/ver/<int:pk>/', views.ver_estudiante, name='ver_estudiante'),
    path('inicial/exportar-pdf/', views.exportar_inicial_pdf, name='exportar_inicial_pdf'),
    path('exportar/inicial/general/pdf/', views.exportar_inicial_general_pdf, name='exportar_inicial_general_pdf'),

    # Educación Primaria
    path('primaria/', views.primaria, name='primaria'),
    path('primaria/exportar-pdf/', views.exportar_primaria_pdf, name='exportar_primaria_pdf'),
    path('exportar/primaria/general/pdf/', views.exportar_primaria_general_pdf, name='exportar_primaria_general_pdf'),

    # Personal
    path('personal/', views.personal, name='personal'),
    path('personal/registrar/', views.registrar_personal, name='registrar_personal'),
    path('personal/ver/<str:tipo>/<int:pk>/', views.ver_personal, name='ver_personal'),
    path('admin-panel/personal/<str:tipo>/', views.admin_personal_json, name='admin_personal_json'),
    path('admin-panel/personal/eliminar/<str:tipo>/<int:pk>/',
         views.admin_personal_eliminar, name='admin_personal_eliminar'),
    path('personal/exportar-pdf/', views.exportar_personal_pdf, name='exportar_personal_pdf'),

    # Asistencias de Personal
    path('asistencias/', views.asistencias_personal, name='asistencias_personal'),
    path('asistencias/guardar/', views.guardar_asistencias_personal, name='guardar_asistencias_personal'),

    # Admin
    path('admin-panel/', views.menu_admin, name='menu_admin'),

    # PDF Asistencias
    path('exportar/asistencias/pdf/', views.exportar_asistencias_pdf, name='exportar_asistencias_pdf'),

    # Calendario Escolar
    path('calendario-escolar/', views.calendario_escolar, name='calendario_escolar'),
    path('calendario-escolar/guardar/', views.guardar_calendario_escolar, name='guardar_calendario_escolar'),
    path('calendario-escolar/configuracion/guardar/', views.guardar_configuracion_anual, name='guardar_configuracion_anual'),
    path('calendario-escolar/vacaciones/guardar/', views.guardar_vacaciones, name='guardar_vacaciones'),
    path('calendario-escolar/vacaciones/eliminar/<int:pk>/', views.eliminar_vacaciones, name='eliminar_vacaciones'),
    path('exportar/calendario/pdf/', views.exportar_calendario_pdf, name='exportar_calendario_pdf'),

    # ✅ CIERRE ANUAL (desde el Calendario)
    path('cierre-anual/json/', views.cierre_anual_json, name='cierre_anual_json'),
    path('cierre-anual/ejecutar/', views.ejecutar_cierre_anual, name='ejecutar_cierre_anual'),

    # actualizar encabezado
    path('actualizar-encabezado/', views.actualizar_encabezado, name='actualizar_encabezado'),

    # ================================================================
    # CONSTANCIA DE ESTUDIO
    # ================================================================
    path('constancia-estudio/<int:pk>/',
         views.constancia_estudio_pdf,
         name='constancia_estudio_pdf'),

    # ================================================================
    # UTILIDADES DE FECHAS (mes en texto)
    # ================================================================
    path('mes-en-texto/',
         views.mes_en_texto,
         name='mes_en_texto'),

    path('meses-en-texto/',
         views.meses_en_texto,
         name='meses_en_texto'),

    # ================================================================
    # CONSTANCIA DE TRABAJO
    # ================================================================
    path('constancia-trabajo/<int:pk>/',
         views.constancia_trabajo_pdf,
         name='constancia_trabajo_pdf'),

    # ================================================================
    # AULA ANEXA — DASHBOARD Y CONSTANCIAS
    # ================================================================
    path('dashboard-anexa/', views.dashboard_anexa, name='dashboard_anexa'),
    path('anexa/constancia-estudio/',
         views.constancia_estudio_anexa_pdf,
         name='constancia_estudio_anexa_pdf'),
    path('anexa/constancia-trabajo/',
         views.constancia_trabajo_anexa_pdf,
         name='constancia_trabajo_anexa_pdf'),

    # ================================================================
    # FIRMANTES
    # ================================================================
    path('firmantes/', views.gestion_firmantes, name='gestion_firmantes'),
    path('admin-panel/firmantes/json/', views.admin_firmantes_json, name='admin_firmantes_json'),
    path('admin-panel/firmantes/guardar/', views.guardar_firmante, name='guardar_firmante'),
    path('admin-panel/firmantes/eliminar/<int:pk>/', views.eliminar_firmante, name='eliminar_firmante'),

    # ================================================================
    # CERTIFICADO DE EDUCACIÓN PRIMARIA
    # ================================================================
    path('certificado-primaria/<int:pk>/',
         views.certificado_primaria_pdf,
         name='certificado_primaria_pdf'),

    # ================================================================
    # EGRESADOS
    # ================================================================
    path('egresados/', views.lista_egresados, name='lista_egresados'),
    path('admin-panel/egresados/json/', views.admin_egresados_json, name='admin_egresados_json'),
    # ================================================================
    # CONSTANCIA / BOLETA DE RETIRO
    # ================================================================
    path('constancia-retiro/<int:pk>/', views.constancia_retiro_pdf, name='constancia_retiro_pdf'),
    path('verificar-cierre-anual/json/', views.verificar_cierre_anual_json, name='verificar_cierre_anual_json'),
    # ================================================================
    # HISTORIAL DE RETIROS Y EGRESOS
    # ================================================================
    path('historial-retiros-egresos/', views.historial_retiros_egresos, name='historial_retiros_egresos'),
    path('admin-panel/historial-retiros/json/', views.admin_historial_retiros_json, name='admin_historial_retiros_json'),
    path('admin-panel/historial-egresados/json/', views.admin_historial_egresados_json, name='admin_historial_egresados_json'),
    path('admin-panel/historial/eliminar/<str:tipo>/<int:pk>/', views.eliminar_historial, name='eliminar_historial'),

    # ================================================================
    # CONSTANCIA DE PROSECUCIÓN DE ESTUDIOS
    # ================================================================
    path('constancia-prosecucion/<int:pk>/', views.constancia_prosecucion_pdf, name='constancia_prosecucion_pdf'),
        # ================================================================
    # CONSTANCIA DE CUPO
    # ================================================================
    path('constancia-cupo/<int:pk>/', views.constancia_cupo_pdf, name='constancia_cupo_pdf'),
        # ================================================================
    # INSCRIPCIÓN / CIERRE DE AÑO ESCOLAR
    # ================================================================
    path('inscripcion-escolar/', views.inscripcion_escolar, name='inscripcion_escolar'),
    path('admin-panel/inscripcion/json/', views.admin_inscripcion_json, name='admin_inscripcion_json'),
]

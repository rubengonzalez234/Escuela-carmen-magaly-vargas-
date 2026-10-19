from urllib.parse import urlparse
import json
import os
import io
import shutil
from django.core.files.storage import FileSystemStorage
import fitz  # PyMuPDF
from PIL import Image
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.urls import reverse
from xhtml2pdf import pisa
from .models import (
    Estudiante,
    Docente,
    PersonalAdministrativo,
    PersonalApoyo,
    PersonalCocina,
    Materia,
    Calificacion,
    AsistenciaPersonal,
    Feriado,
    ConfiguracionAnual,
    PeriodoVacaciones,
    Firmante,
    HistorialEstudiante,
    Egresado,
)
from .forms import (
    EstudianteForm,
    DocenteForm,
    PersonalAdministrativoForm,
    PersonalApoyoForm,
    PersonalCocinaForm,
)
import calendar
from datetime import date, timedelta, datetime
from django.utils import timezone


# ================================================================
# CONSTANTES
# ================================================================
NIVELES_INICIAL = ['1er_Nivel', '2do_Nivel', '3er_Nivel']
NIVELES_PRIMARIA = ['1er_Grado', '2do_Grado', '3er_Grado', '4to_Grado', '5to_Grado', '6to_Grado']

GRADOS_CON_CEDULA_IDENTIDAD = ['3er_Grado', '4to_Grado', '5to_Grado', '6to_Grado']

MESES_NOMBRES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

MAPA_NIVEL_A_DOCENTE = {
    '1er_Nivel': '1er Nivel',
    '2do_Nivel': '2do Nivel',
    '3er_Nivel': '3er Nivel',
    '1er_Grado': '1er Grado',
    '2do_Grado': '2do Grado',
    '3er_Grado': '3er Grado',
    '4to_Grado': '4to Grado',
    '5to_Grado': '5to Grado',
    '6to_Grado': '6to Grado',
}

SIGUIENTE_NIVEL = {
    '1er_Nivel': '2do_Nivel',
    '2do_Nivel': '3er_Nivel',
    '3er_Nivel': '1er_Grado',
    '1er_Grado': '2do_Grado',
    '2do_Grado': '3er_Grado',
    '3er_Grado': '4to_Grado',
    '4to_Grado': '5to_Grado',
    '5to_Grado': '6to_Grado',
    '6to_Grado': None,
}


# ================================================================
# ✅ NUEVO — HELPER: ¿SE PUEDEN EMITIR CONSTANCIAS?
# ================================================================
def _puede_emitir_constancias():
    """
    Determina si el sistema puede emitir constancias (estudio o trabajo).

    Reglas:
      1. Debe existir una ConfiguracionAnual con activo=True y cerrado=False.
      2. Si esa configuración tiene fecha_fin y la fecha actual ya la superó,
         tampoco se puede emitir (el año escolar finalizó).
      3. Si no hay fecha_fin configurada, se permite mientras esté activa y no cerrada.

    Retorna:
        (puede: bool, motivo: str, config: ConfiguracionAnual | None)
    """
    hoy = timezone.localdate()

    config = ConfiguracionAnual.objects.filter(
        activo=True, cerrado=False
    ).order_by('-anio_escolar').first()

    if not config:
        return (
            False,
            "No hay un Año Escolar activo. El año escolar fue cerrado o aún no "
            "ha sido configurado. No se pueden emitir constancias.",
            None,
        )

    if config.fecha_fin and hoy > config.fecha_fin:
        return (
            False,
            (
                f"El Año Escolar {config.anio_escolar} finalizó el "
                f"{config.fecha_fin.strftime('%d/%m/%Y')}. Ya no se pueden emitir "
                f"constancias de estudio ni de trabajo. Realice el cierre anual "
                f"para habilitar el nuevo período."
            ),
            config,
        )

    return (True, "", config)


# ================================================================
# AUTENTICACIÓN
# ================================================================
def login_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, 'escuela/login.html')


def logout_usuario(request):
    logout(request)
    messages.info(request, "Ha cerrado sesión de forma segura.")
    return redirect('login')


# ================================================================
# DASHBOARD
# ================================================================
@login_required
def dashboard(request):
    director_plantel = PersonalAdministrativo.objects.filter(
        cargo='Director', activo=True
    ).first()

    director_anexa = Firmante.objects.filter(
        tipo='director_anexa', activo=True
    ).first()

    director_cdce = Firmante.objects.filter(
        tipo='centro_desarrollo', activo=True
    ).first()

    contexto = {
        'total_estudiantes': Estudiante.objects.filter(activo=True).count(),
        'total_docentes': Docente.objects.filter(activo=True).count(),
        'total_apoyo': PersonalApoyo.objects.filter(activo=True).count(),
        'total_asistencias': AsistenciaPersonal.objects.count(),
        'director_plantel': director_plantel,
        'director_anexa': director_anexa,
        'director_cdce': director_cdce,
    }
    return render(request, 'escuela/dashboard.html', contexto)


# ================================================================
# EDUCACIÓN INICIAL
# ================================================================
@login_required
def inicial(request):
    qs = Estudiante.objects.filter(activo=True, nivel__in=NIVELES_INICIAL)

    busqueda = request.GET.get('buscar', '').strip()
    if busqueda:
        qs = qs.filter(
            Q(nombres__icontains=busqueda) |
            Q(apellidos__icontains=busqueda) |
            Q(cedula__icontains=busqueda) |
            Q(cedula_identidad__icontains=busqueda) |
            Q(rep_nombres__icontains=busqueda) |
            Q(rep_apellidos__icontains=busqueda)
        )

    primer_nivel = qs.filter(nivel='1er_Nivel').order_by('apellidos', 'nombres')
    segundo_nivel = qs.filter(nivel='2do_Nivel').order_by('apellidos', 'nombres')
    tercer_nivel = qs.filter(nivel='3er_Nivel').order_by('apellidos', 'nombres')

    total_registrados = qs.count()
    total_ninos = qs.filter(genero='M').count()
    total_ninas = qs.filter(genero='F').count()

    contexto = {
        'primer_nivel': primer_nivel,
        'segundo_nivel': segundo_nivel,
        'tercer_nivel': tercer_nivel,
        'total_registrados': total_registrados,
        'total_ninos': total_ninos,
        'total_ninas': total_ninas,
        'busqueda': busqueda,
    }
    return render(request, 'escuela/inicial.html', contexto)


# ================================================================
# EDUCACIÓN PRIMARIA
# ================================================================
@login_required
def primaria(request):
    qs = Estudiante.objects.filter(activo=True, nivel__in=NIVELES_PRIMARIA)

    busqueda = request.GET.get('buscar', '').strip()
    if busqueda:
        qs = qs.filter(
            Q(nombres__icontains=busqueda) |
            Q(apellidos__icontains=busqueda) |
            Q(cedula__icontains=busqueda) |
            Q(cedula_identidad__icontains=busqueda) |
            Q(rep_nombres__icontains=busqueda) |
            Q(rep_apellidos__icontains=busqueda)
        )

    primer_grado = qs.filter(nivel='1er_Grado').order_by('apellidos', 'nombres')
    segundo_grado = qs.filter(nivel='2do_Grado').order_by('apellidos', 'nombres')
    tercer_grado = qs.filter(nivel='3er_Grado').order_by('apellidos', 'nombres')
    cuarto_grado = qs.filter(nivel='4to_Grado').order_by('apellidos', 'nombres')
    quinto_grado = qs.filter(nivel='5to_Grado').order_by('apellidos', 'nombres')
    sexto_grado = qs.filter(nivel='6to_Grado').order_by('apellidos', 'nombres')

    total_registrados = qs.count()
    total_ninos = qs.filter(genero='M').count()
    total_ninas = qs.filter(genero='F').count()

    contexto = {
        'primer_grado': primer_grado,
        'segundo_grado': segundo_grado,
        'tercer_grado': tercer_grado,
        'cuarto_grado': cuarto_grado,
        'quinto_grado': quinto_grado,
        'sexto_grado': sexto_grado,
        'total_registrados': total_registrados,
        'total_ninos': total_ninos,
        'total_ninas': total_ninas,
        'busqueda': busqueda,
    }
    return render(request, 'escuela/primaria.html', contexto)


# ================================================================
# HELPER: CÉDULAS REGISTRADAS
# ================================================================
def _obtener_cedulas_registradas(excluir_pk=None):
    qs = Estudiante.objects.all()
    if excluir_pk:
        qs = qs.exclude(pk=excluir_pk)

    cedulas = list(
        qs.exclude(cedula__isnull=True).exclude(cedula='').values_list('cedula', flat=True)
    )
    cedulas_identidad = list(
        qs.exclude(cedula_identidad__isnull=True).exclude(cedula_identidad='')
        .values_list('cedula_identidad', flat=True)
    )
    return cedulas + cedulas_identidad


# ================================================================
# REGISTRAR / EDITAR ESTUDIANTE
# ================================================================
# ================================================================
# REGISTRAR / EDITAR ESTUDIANTE
# ================================================================
@login_required
def registrar_estudiante(request):
    referer = request.META.get('HTTP_REFERER', '')
    origen = request.GET.get('origen', '')
    url_origen_raw = origen or referer or ''

    url_origen = ''
    if url_origen_raw:
        parsed = urlparse(url_origen_raw)
        if parsed.netloc and parsed.netloc != request.get_host():
            url_origen = ''
        else:
            url_origen = parsed.path or ''

    if not url_origen or url_origen == request.path:
        url_origen = '/inicial/'

    pk_editar = request.GET.get('pk') or request.POST.get('pk_editar') or ''
    es_edicion = False
    instancia_existente = None

    if pk_editar:
        try:
            instancia_existente = Estudiante.objects.get(pk=pk_editar)
            es_edicion = True
        except Estudiante.DoesNotExist:
            messages.error(request, "El estudiante que intentas editar no existe.")
            return redirect('inicial')

    cedulas_registradas = _obtener_cedulas_registradas(
        excluir_pk=instancia_existente.pk if es_edicion and instancia_existente else None
    )

    if request.method == 'POST':
        if es_edicion:
            form = EstudianteForm(request.POST, instance=instancia_existente)
        else:
            form = EstudianteForm(request.POST)

        if form.is_valid():
            estudiante = form.save(commit=False)
            tipo_doc = request.POST.get('tipo_documento', 'escolar')
            estudiante.tipo_documento = tipo_doc

            if tipo_doc == 'identidad':
                cedula_identidad = request.POST.get('cedula_identidad', '').strip()
                if cedula_identidad:
                    qs_cedula_id = Estudiante.objects.filter(cedula_identidad=cedula_identidad)
                    if es_edicion:
                        qs_cedula_id = qs_cedula_id.exclude(pk=instancia_existente.pk)
                    if qs_cedula_id.exists():
                        messages.error(request, f"La Cédula de Identidad {cedula_identidad} ya está registrada.")
                        return render(request, 'escuela/registrar_estudiante.html', {
                            'form': form,
                            'cedulas_registradas': cedulas_registradas,
                            'url_origen': url_origen,
                            'es_edicion': es_edicion,
                            'pk_editar': pk_editar,
                        })
                    estudiante.cedula_identidad = cedula_identidad
                    if not estudiante.cedula:
                        estudiante.cedula = None
                else:
                    messages.error(request, "La Cédula de Identidad es obligatoria cuando se selecciona ese tipo de documento.")
                    return render(request, 'escuela/registrar_estudiante.html', {
                        'form': form,
                        'cedulas_registradas': cedulas_registradas,
                        'url_origen': url_origen,
                        'es_edicion': es_edicion,
                        'pk_editar': pk_editar,
                    })
            else:
                if not estudiante.cedula:
                    messages.error(request, "La Cédula Escolar es obligatoria cuando se selecciona ese tipo de documento.")
                    return render(request, 'escuela/registrar_estudiante.html', {
                        'form': form,
                        'cedulas_registradas': cedulas_registradas,
                        'url_origen': url_origen,
                        'es_edicion': es_edicion,
                        'pk_editar': pk_editar,
                    })
                estudiante.cedula_identidad = None

            estudiante.pais_nacimiento = request.POST.get('pais_nacimiento', 'Venezuela')
            estudiante.estado_nacimiento = request.POST.get('estado_nacimiento', '').strip()
            estudiante.ciudad_nacimiento = request.POST.get('ciudad_nacimiento', '').strip()

            if tipo_doc == 'escolar' and estudiante.cedula:
                qs_cedula = Estudiante.objects.filter(cedula=estudiante.cedula)
                if es_edicion:
                    qs_cedula = qs_cedula.exclude(pk=instancia_existente.pk)
                if qs_cedula.exists():
                    messages.error(request, f"La Cédula Escolar {estudiante.cedula} ya está registrada.")
                    return render(request, 'escuela/registrar_estudiante.html', {
                        'form': form,
                        'cedulas_registradas': cedulas_registradas,
                        'url_origen': url_origen,
                        'es_edicion': es_edicion,
                        'pk_editar': pk_editar,
                    })

            estudiante.save()

            if es_edicion:
                messages.success(request, f"Estudiante {estudiante.nombres} {estudiante.apellidos} actualizado exitosamente.")
                if estudiante.nivel in NIVELES_PRIMARIA:
                    return redirect('primaria')
                return redirect('inicial')
            else:
                messages.success(request, f"Estudiante {estudiante.nombres} {estudiante.apellidos} registrado exitosamente.")
                messages.info(request, "Generando Constancia de Cupo...")
                
                # ✅ NUEVO: Redirigir al listado con los parámetros para que el JS sepa qué PDF abrir
                if estudiante.nivel in NIVELES_PRIMARIA:
                    return redirect(f'/primaria/?pdf_cupo={estudiante.pk}')
                return redirect(f'/inicial/?pdf_cupo={estudiante.pk}')

        else:
            print("=" * 60)
            print("⚠️  ERRORES DEL FORMULARIO DE ESTUDIANTE:")
            for campo, errores in form.errors.items():
                for error in errores:
                    print(f"   - {campo}: {error}")
            print("=" * 60)

            for campo, errores in form.errors.items():
                for error in errores:
                    messages.error(request, f"{campo}: {error}")
    else:
        if es_edicion:
            form = EstudianteForm(instance=instancia_existente)
        else:
            form = EstudianteForm()

    return render(request, 'escuela/registrar_estudiante.html', {
        'form': form,
        'cedulas_registradas': cedulas_registradas,
        'url_origen': url_origen,
        'es_edicion': es_edicion,
        'pk_editar': pk_editar,
    })
# ================================================================
# VER DETALLE DEL ESTUDIANTE
# ================================================================
@login_required
def ver_estudiante(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)
    
    # ✅ Verificar si el estudiante es de primaria o inicial para el botón de regreso
    es_primaria = estudiante.nivel in NIVELES_PRIMARIA
    
    contexto = {
        'estudiante': estudiante,
        'es_primaria': es_primaria,
    }
    return render(request, 'escuela/ver_estudiante.html', contexto)
# ================================================================
# GESTIÓN DE ESTUDIANTES
# ================================================================
@login_required
def gestion_estudiantes(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para gestionar estudiantes.")
        return redirect('dashboard')
    return render(request, 'escuela/gestion_estudiantes.html')


# ================================================================
# ADMIN PANEL — ESTUDIANTES (JSON por nivel)
# ================================================================
@login_required
def admin_estudiantes_json(request, nivel):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    nivel = (nivel or '').strip()

    MAPA_NIVELES = {
        'inicial': {
            'filtro': ['1er_Nivel', '2do_Nivel', '3er_Nivel'],
            'etiqueta': 'Inicial',
        },
        'primaria': {
            'filtro': ['1er_Grado', '2do_Grado', '3er_Grado',
                       '4to_Grado', '5to_Grado', '6to_Grado'],
            'etiqueta': 'Primaria',
        },
        'todos': {
            'filtro': None,
            'etiqueta': 'Todos',
        },
    }

    if nivel not in MAPA_NIVELES:
        return JsonResponse({'ok': False, 'error': 'Nivel no válido'}, status=400)

    qs = Estudiante.objects.filter(activo=True)
    if MAPA_NIVELES[nivel]['filtro']:
        qs = qs.filter(nivel__in=MAPA_NIVELES[nivel]['filtro'])

    busqueda = request.GET.get('buscar', '').strip()
    if busqueda:
        qs = qs.filter(
            Q(nombres__icontains=busqueda) |
            Q(apellidos__icontains=busqueda) |
            Q(cedula__icontains=busqueda) |
            Q(cedula_identidad__icontains=busqueda)
        )

    qs = qs.order_by('apellidos', 'nombres')

    datos = []
    for e in qs:
        if e.tipo_documento == 'identidad' and e.cedula_identidad:
            cedula_mostrar = f"{e.nacionalidad}-{e.cedula_identidad}"
        else:
            cedula_mostrar = e.cedula or '—'

        datos.append({
            'id': e.pk,
            'nombres': e.nombres,
            'apellidos': e.apellidos,
            'cedula': cedula_mostrar,
            'nivel': e.get_nivel_display(),
            'genero': e.get_genero_display() if hasattr(e, 'get_genero_display') else e.genero,
            'edad': e.edad,
            'rep_nombre': f"{e.rep_nombres} {e.rep_apellidos}".strip(),
            'rep_telefono': e.rep_telefono or '—',
            'nombre_completo': f"{e.nombres} {e.apellidos}",
            'url_editar': f"{reverse('registrar_estudiante')}?pk={e.pk}",
            'url_retirar': f"/admin-panel/estudiantes/retirar/{e.pk}/",
        })

    return JsonResponse({'ok': True, 'estudiantes': datos})


# ================================================================
# ADMIN PANEL — RETIRAR ESTUDIANTE
# ================================================================
# ================================================================
# ADMIN PANEL — RETIRAR ESTUDIANTE (AHORA GUARDA MOTIVO Y DEVUELVE URL DEL PDF)
# ================================================================
@login_required
@require_POST
def admin_estudiante_retirar(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    try:
        data = json.loads(request.body)
        motivo = data.get('motivo', '').strip()
        observacion = data.get('observacion', '').strip()

        if not motivo:
            return JsonResponse({'ok': False, 'error': 'El motivo del retiro es obligatorio.'}, status=400)

        estudiante = get_object_or_404(Estudiante, pk=pk)
        nombre = f"{estudiante.nombres} {estudiante.apellidos}"

        # 1. Marcar como retirado
        estudiante.activo = False
        estudiante.estado = 'retirado'
        estudiante.save()

        # 2. Obtener año escolar activo
        config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
        anio_escolar = config.anio_escolar if config else "N/A"

        # 3. Guardar en el historial
        obs_final = f"Motivo: {motivo}"
        if observacion:
            obs_final += f" | Obs: {observacion}"

        HistorialEstudiante.objects.create(
            estudiante=estudiante,
            anio_escolar=anio_escolar,
            nivel_anterior=estudiante.nivel,
            nivel_nuevo='',
            accion='retirado',
            observacion=obs_final
        )

        # 4. Devolver la URL para generar el PDF
        url_pdf = reverse('constancia_retiro_pdf', args=[estudiante.pk]) + f"?motivo={motivo}&observacion={observacion}"
        
        return JsonResponse({
            'ok': True,
            'mensaje': f"{nombre} ha sido retirado(a) del sistema.",
            'url_pdf': url_pdf
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

# ================================================================
# BOLETA DE RETIRO — PDF
# ================================================================
@login_required
def constancia_retiro_pdf(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "No tiene permisos para generar boletas de retiro.")
        return redirect('gestion_estudiantes')

    estudiante = get_object_or_404(Estudiante, pk=pk)

    # Obtener motivo y observación por GET
    motivo = request.GET.get('motivo', 'No especificado').strip()
    observacion = request.GET.get('observacion', '').strip()

    # Director (desde PersonalAdministrativo)
    director = PersonalAdministrativo.objects.filter(cargo='Director', activo=True).first()
    if not director:
        messages.error(request, "No se puede emitir la boleta porque no hay un Director activo registrado.")
        return redirect('gestion_estudiantes')

    director_nombres = f"{director.nombres} {director.apellidos}"
    director_cedula = f"{director.nacionalidad}-{director.cedula}"
    director_telefono = director.telefono or '—'

    # Año escolar
    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    anio_escolar = config.anio_escolar if config else "2025-2026"

    # Datos del estudiante
    nivel_display = estudiante.get_nivel_display()
    
    # ✅ NUEVO: Calcular tipo de documento y artículo según género
    if estudiante.tipo_documento == 'identidad' and estudiante.cedula_identidad:
        cedula_estudiante = f"{estudiante.nacionalidad}-{estudiante.cedula_identidad}"
        tipo_documento_display = "Cédula de Identidad"
    else:
        cedula_estudiante = estudiante.cedula or '—'
        tipo_documento_display = "Cédula Escolar"

    articulo = "la" if estudiante.genero == 'F' else "el"

    # Datos del representante (desde el modelo)
    rep_nombre_completo = f"{estudiante.rep_nombres} {estudiante.rep_apellidos}"
    rep_cedula_completa = f"{estudiante.rep_nacionalidad}-{estudiante.rep_cedula}" if estudiante.rep_cedula else '—'

    # Fecha de expedición
    hoy = timezone.localdate()
    dia_expedicion = hoy.day
    mes_expedicion = MESES_TEXTO.get(hoy.month, '')
    anio_expedicion = hoy.year

    ahora = timezone.localtime(timezone.now())

    contexto = {
        'estudiante': estudiante,
        'director_nombres': director_nombres,
        'director_cedula': director_cedula,
        'director_telefono': director_telefono,
        'anio_escolar': anio_escolar,
        'cedula_estudiante': cedula_estudiante,
        'tipo_documento_display': tipo_documento_display, # ✅ Pasamos el tipo exacto
        'articulo': articulo,                             # ✅ Pasamos el/la
        'nivel_display': nivel_display,
        'motivo': motivo,
        'observacion': observacion,
        'rep_nombre_completo': rep_nombre_completo,
        'rep_cedula_completa': rep_cedula_completa,
        'dia_expedicion': dia_expedicion,
        'mes_expedicion': mes_expedicion,
        'anio_expedicion': anio_expedicion,
        'fecha': hoy,
        'hora': ahora.strftime('%I:%M %p'),
    }

    template = get_template('escuela/constancia_retiro_pdf.html')
    html = template.render(contexto)
    
    return generar_pdf_con_marca(
        html,
        f"boleta_retiro_{estudiante.cedula or estudiante.pk}",
        mostrar_en_navegador=True
    )
# ================================================================
# PANEL ADMIN
# ================================================================
@login_required
def menu_admin(request):
    return render(request, 'escuela/menu_admin.html')


# ================================================================
# ADMIN PANEL — PERSONAL (JSON por tipo)
# ================================================================
@login_required
def admin_personal_json(request, tipo):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    tipo = (tipo or '').lower()
    datos = []

    if tipo == 'docentes':
        for p in Docente.objects.filter(activo=True).order_by('apellidos', 'nombres'):
            datos.append({
                'id': p.pk, 'nombres': p.nombres, 'apellidos': p.apellidos,
                'cedula': f"{p.nacionalidad}-{p.cedula}",
                'extra': p.nivel_grado or '—',
                'nombre_completo': f"{p.nombres} {p.apellidos}",
                'url_editar': f"/admin/escuela/docente/{p.pk}/change/",
                'url_eliminar': f"/admin-panel/personal/eliminar/docente/{p.pk}/",
            })
    elif tipo == 'administrativos':
        for p in PersonalAdministrativo.objects.filter(activo=True).order_by('apellidos', 'nombres'):
            datos.append({
                'id': p.pk, 'nombres': p.nombres, 'apellidos': p.apellidos,
                'cedula': f"{p.nacionalidad}-{p.cedula}",
                'extra': p.get_cargo_display() or '—',
                'nombre_completo': f"{p.nombres} {p.apellidos}",
                'url_editar': f"/admin/escuela/personaladministrativo/{p.pk}/change/",
                'url_eliminar': f"/admin-panel/personal/eliminar/administrativo/{p.pk}/",
            })
    elif tipo == 'apoyo':
        for p in PersonalApoyo.objects.filter(activo=True).order_by('apellidos', 'nombres'):
            datos.append({
                'id': p.pk, 'nombres': p.nombres, 'apellidos': p.apellidos,
                'cedula': f"{p.nacionalidad}-{p.cedula}",
                'extra': p.get_cargo_display() or '—',
                'nombre_completo': f"{p.nombres} {p.apellidos}",
                'url_editar': f"/admin/escuela/personalapoyo/{p.pk}/change/",
                'url_eliminar': f"/admin-panel/personal/eliminar/apoyo/{p.pk}/",
            })
    elif tipo == 'cocina':
        for p in PersonalCocina.objects.filter(activo=True).order_by('apellidos', 'nombres'):
            datos.append({
                'id': p.pk, 'nombres': p.nombres, 'apellidos': p.apellidos,
                'cedula': f"{p.nacionalidad}-{p.cedula}",
                'extra': p.get_cargo_display() or '—',
                'nombre_completo': f"{p.nombres} {p.apellidos}",
                'url_editar': f"/admin/escuela/personalcocina/{p.pk}/change/",
                'url_eliminar': f"/admin-panel/personal/eliminar/cocina/{p.pk}/",
            })
    else:
        return JsonResponse({'ok': False, 'error': 'Tipo no válido'}, status=400)

    return JsonResponse({'ok': True, 'personal': datos})


# ================================================================
# ADMIN PANEL — ELIMINAR PERSONAL
# ================================================================
@login_required
@require_POST
def admin_personal_eliminar(request, tipo, pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    tipo = (tipo or '').lower()
    try:
        if tipo == 'docente':
            persona = get_object_or_404(Docente, pk=pk)
        elif tipo == 'administrativo':
            persona = get_object_or_404(PersonalAdministrativo, pk=pk)
        elif tipo == 'apoyo':
            persona = get_object_or_404(PersonalApoyo, pk=pk)
        elif tipo == 'cocina':
            persona = get_object_or_404(PersonalCocina, pk=pk)
        else:
            return JsonResponse({'ok': False, 'error': 'Tipo no válido'}, status=400)

        nombre = f"{persona.nombres} {persona.apellidos}"
        persona.delete()
        return JsonResponse({'ok': True, 'mensaje': f"{nombre} eliminado(a) correctamente."})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ================================================================
# PERSONAL (listado)
# ================================================================
@login_required
def personal(request):
    busqueda = request.GET.get('buscar', '').strip()

    def filtrar(qs):
        if not busqueda:
            return qs
        return qs.filter(
            Q(nombres__icontains=busqueda) |
            Q(apellidos__icontains=busqueda) |
            Q(cedula__icontains=busqueda)
        )

    docentes = filtrar(Docente.objects.filter(activo=True)).order_by('apellidos', 'nombres')
    administrativos = filtrar(PersonalAdministrativo.objects.filter(activo=True)).order_by('apellidos', 'nombres')
    apoyo = filtrar(PersonalApoyo.objects.filter(activo=True)).order_by('apellidos', 'nombres')
    cocina = filtrar(PersonalCocina.objects.filter(activo=True)).order_by('apellidos', 'nombres')

    contexto = {
        'docentes': docentes,
        'administrativos': administrativos,
        'apoyo': apoyo,
        'cocina': cocina,
        'total_personal': docentes.count() + administrativos.count() + apoyo.count() + cocina.count(),
        'total_docentes': docentes.count(),
        'total_administrativos': administrativos.count(),
        'total_apoyo': apoyo.count(),
        'total_cocina': cocina.count(),
        'busqueda': busqueda,
    }
    return render(request, 'escuela/personal.html', contexto)


# ================================================================
# REGISTRAR PERSONAL
# ================================================================
@login_required
def registrar_personal(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para registrar personal.")
        return redirect('personal')

    tipo = request.POST.get('tipo') or request.GET.get('tipo') or 'Docente'
    pk_editar = request.POST.get('pk_editar') or request.GET.get('pk') or ''
    es_edicion = False
    instancia_existente = None

    if tipo == 'Administrativo':
        FormClass = PersonalAdministrativoForm
        etiqueta = 'Personal Administrativo'
        ModelClass = PersonalAdministrativo
    elif tipo == 'Apoyo':
        FormClass = PersonalApoyoForm
        etiqueta = 'Personal de Apoyo'
        ModelClass = PersonalApoyo
    elif tipo == 'Cocina':
        FormClass = PersonalCocinaForm
        etiqueta = 'Personal de Cocina'
        ModelClass = PersonalCocina
    else:
        tipo = 'Docente'
        FormClass = DocenteForm
        etiqueta = 'Docente'
        ModelClass = Docente

    if pk_editar:
        try:
            instancia_existente = ModelClass.objects.get(pk=pk_editar)
            es_edicion = True
        except ModelClass.DoesNotExist:
            messages.error(request, "El registro que intentas editar no existe.")
            return redirect('personal')

    if request.method == 'POST':
        if es_edicion:
            form = FormClass(request.POST, instance=instancia_existente)
        else:
            form = FormClass(request.POST)

        if form.is_valid():
            persona = form.save(commit=False)
            persona.nacionalidad = request.POST.get('nacionalidad', 'V')
            persona.save()

            if es_edicion:
                messages.success(request, f"{etiqueta} {persona.nombres} {persona.apellidos} actualizado(a) exitosamente.")
            else:
                messages.success(request, f"{etiqueta} {persona.nombres} {persona.apellidos} registrado(a) exitosamente.")
            return redirect('personal')
        else:
            print("=" * 60)
            print(f"⚠️  ERRORES DEL FORMULARIO DE {etiqueta.upper()}:")
            for campo, errores in form.errors.items():
                for error in errores:
                    print(f"   - {campo}: {error}")
            print("=" * 60)

            for campo, errores in form.errors.items():
                for error in errores:
                    messages.error(request, f"{campo}: {error}")

            if es_edicion:
                form_docente = DocenteForm(request.POST, instance=instancia_existente) if tipo == 'Docente' else DocenteForm()
                form_admin = PersonalAdministrativoForm(request.POST, instance=instancia_existente) if tipo == 'Administrativo' else PersonalAdministrativoForm()
                form_apoyo = PersonalApoyoForm(request.POST, instance=instancia_existente) if tipo == 'Apoyo' else PersonalApoyoForm()
                form_cocina = PersonalCocinaForm(request.POST, instance=instancia_existente) if tipo == 'Cocina' else PersonalCocinaForm()
            else:
                form_docente = DocenteForm(request.POST) if tipo == 'Docente' else DocenteForm()
                form_admin = PersonalAdministrativoForm(request.POST) if tipo == 'Administrativo' else PersonalAdministrativoForm()
                form_apoyo = PersonalApoyoForm(request.POST) if tipo == 'Apoyo' else PersonalApoyoForm()
                form_cocina = PersonalCocinaForm(request.POST) if tipo == 'Cocina' else PersonalCocinaForm()
    else:
        if es_edicion:
            form_docente = DocenteForm(instance=instancia_existente) if tipo == 'Docente' else DocenteForm()
            form_admin = PersonalAdministrativoForm(instance=instancia_existente) if tipo == 'Administrativo' else PersonalAdministrativoForm()
            form_apoyo = PersonalApoyoForm(instance=instancia_existente) if tipo == 'Apoyo' else PersonalApoyoForm()
            form_cocina = PersonalCocinaForm(instance=instancia_existente) if tipo == 'Cocina' else PersonalCocinaForm()
        else:
            form_docente = DocenteForm()
            form_admin = PersonalAdministrativoForm()
            form_apoyo = PersonalApoyoForm()
            form_cocina = PersonalCocinaForm()

    qs_doc = Docente.objects.all()
    qs_admin = PersonalAdministrativo.objects.all()
    qs_apo = PersonalApoyo.objects.all()
    qs_cocina = PersonalCocina.objects.all()

    if es_edicion and instancia_existente:
        if tipo == 'Docente':
            qs_doc = qs_doc.exclude(pk=instancia_existente.pk)
        elif tipo == 'Administrativo':
            qs_admin = qs_admin.exclude(pk=instancia_existente.pk)
        elif tipo == 'Apoyo':
            qs_apo = qs_apo.exclude(pk=instancia_existente.pk)
        elif tipo == 'Cocina':
            qs_cocina = qs_cocina.exclude(pk=instancia_existente.pk)

    if tipo == 'Docente':
        cedulas = list(qs_doc.values_list('cedula', flat=True))
    elif tipo == 'Administrativo':
        cedulas = list(qs_admin.values_list('cedula', flat=True))
    elif tipo == 'Apoyo':
        cedulas = list(qs_apo.values_list('cedula', flat=True))
    elif tipo == 'Cocina':
        cedulas = list(qs_cocina.values_list('cedula', flat=True))
    else:
        cedulas = []

    niveles_ocupados_qs = Docente.objects.filter(activo=True).exclude(nivel_grado='')
    if es_edicion and tipo == 'Docente' and instancia_existente:
        niveles_ocupados_qs = niveles_ocupados_qs.exclude(pk=instancia_existente.pk)
    niveles_ocupados = list(niveles_ocupados_qs.values_list('nivel_grado', flat=True))

    cargos_ocupados_qs = PersonalAdministrativo.objects.filter(activo=True).exclude(cargo='Otro')
    if es_edicion and tipo == 'Administrativo' and instancia_existente:
        cargos_ocupados_qs = cargos_ocupados_qs.exclude(pk=instancia_existente.pk)
    cargos_ocupados = list(cargos_ocupados_qs.values_list('cargo', flat=True))

    docentes_disponibles = Docente.objects.filter(activo=True).order_by('apellidos', 'nombres')
    if es_edicion and tipo == 'Docente' and instancia_existente:
        docentes_disponibles = docentes_disponibles.exclude(pk=instancia_existente.pk)

    return render(request, 'escuela/registrar_personal.html', {
        'form_docente': form_docente,
        'form_admin': form_admin,
        'form_apoyo': form_apoyo,
        'form_cocina': form_cocina,
        'tipo': tipo,
        'etiqueta': etiqueta,
        'cedulas_registradas': cedulas,
        'niveles_ocupados': niveles_ocupados,
        'cargos_ocupados': cargos_ocupados,
        'es_edicion': es_edicion,
        'pk_editar': pk_editar,
        'docentes_disponibles': docentes_disponibles,
    })


# ================================================================
# VER DETALLE DEL PERSONAL
# ================================================================
@login_required
def ver_personal(request, tipo, pk):
    tipo_norm = (tipo or '').lower().strip()

    if tipo_norm == 'docente':
        persona = get_object_or_404(Docente, pk=pk)
        tipo_etiqueta = 'Docente'
        icono = 'bi-person-workspace'
        color = 'primary'
        campos_laborales = [
            ('Nivel / Grado', persona.nivel_grado or '—'),
            ('Especialidad', persona.especialidad or '—'),
        ]
    elif tipo_norm == 'administrativo':
        persona = get_object_or_404(PersonalAdministrativo, pk=pk)
        tipo_etiqueta = 'Personal Administrativo'
        icono = 'bi-briefcase-fill'
        color = 'success'
        cargo_mostrar = persona.get_cargo_display() if persona.cargo else '—'
        if persona.cargo == 'Otro' and persona.cargo_detalle:
            cargo_mostrar = persona.cargo_detalle
        campos_laborales = [('Cargo', cargo_mostrar)]
    elif tipo_norm == 'apoyo':
        persona = get_object_or_404(PersonalApoyo, pk=pk)
        tipo_etiqueta = 'Personal de Apoyo'
        icono = 'bi-people-fill'
        color = 'warning'
        cargo_mostrar = persona.get_cargo_display() if persona.cargo else '—'
        if persona.cargo == 'Otro' and persona.cargo_detalle:
            cargo_mostrar = persona.cargo_detalle
        campos_laborales = [('Cargo', cargo_mostrar)]
    elif tipo_norm == 'cocina':
        persona = get_object_or_404(PersonalCocina, pk=pk)
        tipo_etiqueta = 'Personal de Cocina'
        icono = 'bi-egg-fried'
        color = 'info'
        cargo_mostrar = persona.get_cargo_display() if persona.cargo else '—'
        campos_laborales = [('Cargo', cargo_mostrar)]
    else:
        messages.error(request, "Tipo de personal no válido.")
        return redirect('personal')

    return render(request, 'escuela/ver_personal.html', {
        'persona': persona,
        'tipo': tipo_norm,
        'tipo_etiqueta': tipo_etiqueta,
        'icono': icono,
        'color': color,
        'campos_laborales': campos_laborales,
    })


# ================================================================
# HELPERS ASISTENCIAS
# ================================================================
def _calcular_meses_disponibles(hoy):
    meses = []
    for i in range(3):
        mes_ref = hoy.replace(day=1)
        anio = mes_ref.year
        mes = mes_ref.month - i
        while mes <= 0:
            mes += 12
            anio -= 1
        meses.append({
            'valor': f"{anio}-{mes:02d}",
            'nombre': MESES_NOMBRES[mes],
            'anio': anio,
            'mes': mes,
            'es_actual': (i == 0),
            'etiqueta': 'Mes en curso' if i == 0 else f"Hace {i} mes{'es' if i > 1 else ''}",
        })
    return meses


def _dias_laborables(anio, mes):
    primer_dia = date(anio, mes, 1)
    if mes == 12:
        ultimo_dia = date(anio + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(anio, mes + 1, 1) - timedelta(days=1)

    dias = []
    d = primer_dia
    while d <= ultimo_dia:
        if d.weekday() < 5:
            dias.append(d)
        d += timedelta(days=1)
    return dias


def _obtener_fecha_inicio_anio_escolar():
    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    if config and config.fecha_inicio:
        return config.fecha_inicio
    return None


# ================================================================
# ASISTENCIAS DE PERSONAL
# ================================================================
@login_required
def asistencias_personal(request):
    hoy = timezone.localdate()
    meses_disponibles = _calcular_meses_disponibles(hoy)
    mes_default = meses_disponibles[0]['valor']
    mes_sel_str = request.GET.get('mes', mes_default)

    valores_validos = [m['valor'] for m in meses_disponibles]
    if mes_sel_str not in valores_validos:
        mes_sel_str = mes_default

    anio_sel, mes_sel_num = map(int, mes_sel_str.split('-'))
    es_mes_actual = (mes_sel_str == mes_default)

    dias = _dias_laborables(anio_sel, mes_sel_num)

    if mes_sel_num == 12:
        ultimo_dia_mes = date(anio_sel + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia_mes = date(anio_sel, mes_sel_num + 1, 1) - timedelta(days=1)

    personal = []
    for p in Docente.objects.filter(activo=True, fecha_ingreso__lte=ultimo_dia_mes).order_by('apellidos', 'nombres'):
        personal.append({'obj': p, 'tipo': 'Docente'})
    for p in PersonalAdministrativo.objects.filter(activo=True, fecha_ingreso__lte=ultimo_dia_mes).order_by('apellidos', 'nombres'):
        personal.append({'obj': p, 'tipo': 'Administrativo'})
    for p in PersonalApoyo.objects.filter(activo=True, fecha_ingreso__lte=ultimo_dia_mes).order_by('apellidos', 'nombres'):
        personal.append({'obj': p, 'tipo': 'Apoyo'})
    for p in PersonalCocina.objects.filter(activo=True, fecha_ingreso__lte=ultimo_dia_mes).order_by('apellidos', 'nombres'):
        personal.append({'obj': p, 'tipo': 'Cocina'})

    asistencias_qs = AsistenciaPersonal.objects.filter(fecha__year=anio_sel, fecha__month=mes_sel_num)
    asistencias_map = {}
    for a in asistencias_qs:
        clave = f"{a.tipo_personal}-{a.personal_id}-{a.fecha.strftime('%Y-%m-%d')}"
        asistencias_map[clave] = "presente" if a.presente else "ausente"

    feriados_qs = Feriado.objects.filter(fecha__year=anio_sel, fecha__month=mes_sel_num)
    eventos_map = {}
    for f in feriados_qs:
        clave = f.fecha.strftime('%Y-%m-%d')
        eventos_map[clave] = {
            'tipo': f.tipo_evento or 'feriado',
            'descripcion': f.descripcion or ''
        }

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    vacaciones_map = {}
    if config:
        vacaciones_qs = PeriodoVacaciones.objects.filter(
            configuracion=config,
            fecha_inicio__lte=ultimo_dia_mes,
            fecha_fin__gte=date(anio_sel, mes_sel_num, 1),
        )
        for v in vacaciones_qs:
            d = max(v.fecha_inicio, date(anio_sel, mes_sel_num, 1))
            fin = min(v.fecha_fin, ultimo_dia_mes)
            while d <= fin:
                vacaciones_map[d.strftime('%Y-%m-%d')] = v.descripcion
                d += timedelta(days=1)

    fecha_inicio_anio = _obtener_fecha_inicio_anio_escolar()

    contexto = {
        'dias': dias,
        'personal': personal,
        'meses_disponibles': meses_disponibles,
        'mes_sel_str': mes_sel_str,
        'mes': mes_sel_num,
        'anio': anio_sel,
        'mes_nombre': MESES_NOMBRES[mes_sel_num],
        'es_mes_actual': es_mes_actual,
        'asistencias_map': asistencias_map,
        'eventos_map': eventos_map,
        'vacaciones_map': vacaciones_map,
        'hoy': hoy,
        'fecha_inicio_anio': fecha_inicio_anio,
    }
    return render(request, 'escuela/asistencias_personal.html', contexto)


@login_required
@require_POST
def guardar_asistencias_personal(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    mes = data.get('mes', '')
    marcas = data.get('marcas', [])
    eliminar = data.get('eliminar', [])

    hoy = timezone.localdate()
    mes_actual_str = f"{hoy.year}-{hoy.month:02d}"
    if mes != mes_actual_str:
        return JsonResponse({'ok': False, 'error': 'Solo se pueden modificar asistencias del mes actual.'}, status=403)

    guardadas = 0
    for m in marcas:
        tipo = m.get('tipo')
        pid = m.get('personal_id')
        fecha_str = m.get('fecha')
        estado = m.get('estado', 'presente')

        if not (tipo and pid and fecha_str):
            continue
        try:
            fecha = date.fromisoformat(fecha_str)
        except ValueError:
            continue

        AsistenciaPersonal.objects.update_or_create(
            tipo_personal=tipo, personal_id=pid, fecha=fecha,
            defaults={'presente': (estado == 'presente')}
        )
        guardadas += 1

    eliminadas = 0
    for e in eliminar:
        tipo = e.get('tipo')
        pid = e.get('personal_id')
        fecha_str = e.get('fecha')

        if not (tipo and pid and fecha_str):
            continue
        try:
            fecha = date.fromisoformat(fecha_str)
        except ValueError:
            continue

        deleted, _ = AsistenciaPersonal.objects.filter(
            tipo_personal=tipo, personal_id=pid, fecha=fecha,
        ).delete()
        if deleted:
            eliminadas += 1

    return JsonResponse({
        'ok': True, 'guardadas': guardadas, 'eliminadas': eliminadas,
        'mensaje': f"{guardadas} asistencia(s) guardada(s) y {eliminadas} eliminada(s)."
    })


# ================================================================
# PDF CON MARCA DE AGUA (BLINDADA)
# ================================================================
def link_callback(uri, rel):
    result = finders.find(uri.replace(settings.STATIC_URL, ""))
    if result:
        return result
    return uri


def generar_pdf_con_marca(html_content, filename,
                          mostrar_en_navegador=True,
                          tamaño_marca=0.6,
                          opacidad_marca=0.3):
    try:
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_content.encode("utf-8")),
            dest=pdf_buffer,
            link_callback=link_callback
        )

        if pisa_status.err:
            return HttpResponse(f"Error al generar el PDF: {pisa_status.err}", status=500)

        pdf_buffer.seek(0)
        pdf_document = fitz.open(stream=pdf_buffer, filetype="pdf")

        if len(pdf_document) == 0:
            pdf_document.close()
            return HttpResponse(
                "Error: El PDF generado no contiene páginas. Revisa el template HTML.",
                status=500
            )

        primera_pagina = pdf_document[0]
        rect = primera_pagina.rect
        if rect is None or rect.width is None or rect.height is None or rect.width <= 0 or rect.height <= 0:
            pdf_document.close()
            return HttpResponse(
                "Error: El PDF generado tiene dimensiones inválidas. Revisa el template HTML.",
                status=500
            )

        marca_path = finders.find('img/logo.png')
        if not marca_path:
            marca_path = os.path.join(settings.STATIC_ROOT or '', 'img', 'logo.png')
            if not os.path.exists(marca_path):
                for static_dir in getattr(settings, 'STATICFILES_DIRS', []):
                    test_path = os.path.join(str(static_dir), 'img', 'logo.png')
                    if os.path.exists(test_path):
                        marca_path = test_path
                        break

        if marca_path and os.path.exists(marca_path):
            try:
                img = Image.open(marca_path)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')

                try:
                    data = list(img.getdata())
                except (TypeError, NotImplementedError) as conv_err:
                    print(f"⚠️ Advertencia: No se pudo leer getdata(): {conv_err}")
                    data = None

                if data and all(isinstance(p, tuple) and len(p) == 4 for p in data):
                    new_data = [(r, g, b, int(a * opacidad_marca)) for r, g, b, a in data]
                    img.putdata(new_data)

                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format='PNG')
                    img_data = img_buffer.getvalue()

                    for pagina_num in range(len(pdf_document)):
                        pagina = pdf_document[pagina_num]
                        page_rect = pagina.rect
                        if page_rect is None or page_rect.width is None or page_rect.height is None:
                            continue

                        ancho_imagen = page_rect.width * tamaño_marca
                        alto_imagen = page_rect.height * tamaño_marca
                        x = (page_rect.width - ancho_imagen) / 2
                        y = (page_rect.height - alto_imagen) / 2
                        rect_imagen = fitz.Rect(x, y, x + ancho_imagen, y + alto_imagen)
                        pagina.insert_image(rect_imagen, stream=img_data, keep_proportion=True)
                else:
                    print("⚠️ Advertencia: El logo no se pudo procesar como RGBA. Se omite la marca de agua.")
            except Exception as img_err:
                print(f"⚠️ Advertencia: No se pudo aplicar la marca de agua: {img_err}")

        output_buffer = io.BytesIO()
        pdf_document.save(output_buffer)
        pdf_document.close()

        response = HttpResponse(output_buffer.getvalue(), content_type='application/pdf')
        if mostrar_en_navegador:
            response['Content-Disposition'] = f'inline; filename="{filename}.pdf"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return response

    except ImportError as e:
        return HttpResponse(f"Error: Falta una dependencia. Instala PyMuPDF y Pillow. {str(e)}", status=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Error al generar el PDF con marca de agua: {str(e)}", status=500)


# ================================================================
# EXPORTAR PDF — EDUCACIÓN INICIAL
# ================================================================
@login_required
def exportar_inicial_pdf(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar PDFs.")
        return redirect('inicial')

    nivel = request.GET.get('nivel', '1er_Nivel')
    niveles_validos = {'1er_Nivel': 'Primer Nivel', '2do_Nivel': 'Segundo Nivel', '3er_Nivel': 'Tercer Nivel'}

    if nivel not in niveles_validos:
        messages.error(request, "Nivel no válido.")
        return redirect('inicial')

    estudiantes = Estudiante.objects.filter(activo=True, nivel=nivel).order_by('apellidos', 'nombres')
    nivel_docente = MAPA_NIVEL_A_DOCENTE.get(nivel, '')
    docente = Docente.objects.filter(activo=True, nivel_grado=nivel_docente).first()

    ahora = timezone.localtime(timezone.now())
    contexto = {
        'nivel': nivel,
        'nivel_display': niveles_validos[nivel],
        'estudiantes': estudiantes,
        'total': estudiantes.count(),
        'total_ninas': estudiantes.filter(genero='F').count(),
        'total_ninos': estudiantes.filter(genero='M').count(),
        'fecha': timezone.localdate(),
        'hora': ahora.strftime('%I:%M %p'),
        'usuario': request.user.get_full_name() or request.user.username,
        'docente': docente,
    }

    template = get_template('escuela/reporte_inicial_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(html, f"listado_inicial_{nivel}", mostrar_en_navegador=True)


# ================================================================
# EXPORTAR PDF — EDUCACIÓN INICIAL (GENERAL)
# ================================================================
@login_required
def exportar_inicial_general_pdf(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar PDFs.")
        return redirect('inicial')

    estudiantes = Estudiante.objects.filter(activo=True, nivel__in=NIVELES_INICIAL).order_by('nivel', 'apellidos', 'nombres')

    niveles_data = []
    for nivel_key, nivel_nombre in [('1er_Nivel', 'Primer Nivel'), ('2do_Nivel', 'Segundo Nivel'), ('3er_Nivel', 'Tercer Nivel')]:
        qs_nivel = estudiantes.filter(nivel=nivel_key)
        nivel_docente = MAPA_NIVEL_A_DOCENTE.get(nivel_key, '')
        docente = Docente.objects.filter(activo=True, nivel_grado=nivel_docente).first()
        niveles_data.append({
            'key': nivel_key, 'nombre': nivel_nombre,
            'estudiantes': qs_nivel, 'total': qs_nivel.count(), 'docente': docente,
        })

    ahora = timezone.localtime(timezone.now())
    contexto = {
        'niveles_data': niveles_data,
        'estudiantes': estudiantes,
        'total': estudiantes.count(),
        'total_ninas': estudiantes.filter(genero='F').count(),
        'total_ninos': estudiantes.filter(genero='M').count(),
        'fecha': timezone.localdate(),
        'hora': ahora.strftime('%I:%M %p'),
        'usuario': request.user.get_full_name() or request.user.username,
    }

    template = get_template('escuela/reporte_inicial_general_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(html, "listado_general_inicial", mostrar_en_navegador=True)


# ================================================================
# EXPORTAR PDF — EDUCACIÓN PRIMARIA
# ================================================================
@login_required
def exportar_primaria_pdf(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar PDFs.")
        return redirect('primaria')

    grado = request.GET.get('grado', '1er_Grado')
    grados_validos = {
        '1er_Grado': 'Primer Grado', '2do_Grado': 'Segundo Grado', '3er_Grado': 'Tercer Grado',
        '4to_Grado': 'Cuarto Grado', '5to_Grado': 'Quinto Grado', '6to_Grado': 'Sexto Grado',
    }

    if grado not in grados_validos:
        messages.error(request, "Grado no válido.")
        return redirect('primaria')

    estudiantes = Estudiante.objects.filter(activo=True, nivel=grado).order_by('apellidos', 'nombres')
    nivel_docente = MAPA_NIVEL_A_DOCENTE.get(grado, '')
    docente = Docente.objects.filter(activo=True, nivel_grado=nivel_docente).first()

    ahora = timezone.localtime(timezone.now())
    contexto = {
        'grado': grado,
        'grado_display': grados_validos[grado],
        'estudiantes': estudiantes,
        'total': estudiantes.count(),
        'fecha': timezone.localdate(),
        'hora': ahora.strftime('%I:%M %p'),
        'usuario': request.user.get_full_name() or request.user.username,
        'docente': docente,
    }

    template = get_template('escuela/reporte_primaria_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(html, f"listado_primaria_{grado}", mostrar_en_navegador=True)


# ================================================================
# EXPORTAR PDF — EDUCACIÓN PRIMARIA (GENERAL)
# ================================================================
@login_required
def exportar_primaria_general_pdf(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar PDFs.")
        return redirect('primaria')

    estudiantes = Estudiante.objects.filter(activo=True, nivel__in=NIVELES_PRIMARIA).order_by('nivel', 'apellidos', 'nombres')

    niveles_data = []
    for grado_key, grado_nombre in [
        ('1er_Grado', 'Primer Grado'), ('2do_Grado', 'Segundo Grado'), ('3er_Grado', 'Tercer Grado'),
        ('4to_Grado', 'Cuarto Grado'), ('5to_Grado', 'Quinto Grado'), ('6to_Grado', 'Sexto Grado'),
    ]:
        qs_grado = estudiantes.filter(nivel=grado_key)
        nivel_docente = MAPA_NIVEL_A_DOCENTE.get(grado_key, '')
        docente = Docente.objects.filter(activo=True, nivel_grado=nivel_docente).first()
        niveles_data.append({
            'key': grado_key, 'nombre': grado_nombre,
            'estudiantes': qs_grado, 'total': qs_grado.count(), 'docente': docente,
        })

    ahora = timezone.localtime(timezone.now())
    contexto = {
        'niveles_data': niveles_data,
        'estudiantes': estudiantes,
        'total': estudiantes.count(),
        'total_ninas': estudiantes.filter(genero='F').count(),
        'total_ninos': estudiantes.filter(genero='M').count(),
        'fecha': timezone.localdate(),
        'hora': ahora.strftime('%I:%M %p'),
        'usuario': request.user.get_full_name() or request.user.username,
    }

    template = get_template('escuela/reporte_primaria_general_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(html, "listado_general_primaria", mostrar_en_navegador=True)


# ================================================================
# EXPORTAR PDF — ASISTENCIAS DEL PERSONAL
# ================================================================
@login_required
def exportar_asistencias_pdf(request):
    if request.method != 'POST':
        return redirect('asistencias_personal')

    try:
        datos = json.loads(request.POST.get('datos', '{}'))
    except (json.JSONDecodeError, TypeError):
        datos = {}

    mes_str = datos.get('mes', '')
    try:
        anio_sel, mes_sel_num = map(int, mes_str.split('-'))
    except (ValueError, AttributeError):
        hoy = timezone.localdate()
        anio_sel, mes_sel_num = hoy.year, hoy.month

    dias = _dias_laborables(anio_sel, mes_sel_num)

    if mes_sel_num == 12:
        ultimo_dia_mes = date(anio_sel + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia_mes = date(anio_sel, mes_sel_num + 1, 1) - timedelta(days=1)

    personal = []
    for p in Docente.objects.filter(activo=True, fecha_ingreso__lte=ultimo_dia_mes).order_by('apellidos', 'nombres'):
        personal.append({'obj': p, 'tipo': 'Docente'})
    for p in PersonalAdministrativo.objects.filter(activo=True, fecha_ingreso__lte=ultimo_dia_mes).order_by('apellidos', 'nombres'):
        personal.append({'obj': p, 'tipo': 'Administrativo'})
    for p in PersonalApoyo.objects.filter(activo=True, fecha_ingreso__lte=ultimo_dia_mes).order_by('apellidos', 'nombres'):
        personal.append({'obj': p, 'tipo': 'Apoyo'})
    for p in PersonalCocina.objects.filter(activo=True, fecha_ingreso__lte=ultimo_dia_mes).order_by('apellidos', 'nombres'):
        personal.append({'obj': p, 'tipo': 'Cocina'})

    asistencias_qs = AsistenciaPersonal.objects.filter(fecha__year=anio_sel, fecha__month=mes_sel_num)
    asistencias_map = {}
    for a in asistencias_qs:
        clave = f"{a.tipo_personal}-{a.personal_id}-{a.fecha.strftime('%Y-%m-%d')}"
        asistencias_map[clave] = "presente" if a.presente else "ausente"

    feriados_qs = Feriado.objects.filter(fecha__year=anio_sel, fecha__month=mes_sel_num)
    feriados_map = {}
    eventos_map = {}
    for f in feriados_qs:
        fecha_str = f.fecha.strftime('%Y-%m-%d')
        tipo = f.tipo_evento or 'feriado'
        eventos_map[fecha_str] = tipo
        if tipo == 'feriado':
            feriados_map[fecha_str] = True

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    vacaciones_map = {}
    if config:
        vacaciones_qs = PeriodoVacaciones.objects.filter(
            configuracion=config,
            fecha_inicio__lte=ultimo_dia_mes,
            fecha_fin__gte=date(anio_sel, mes_sel_num, 1),
        )
        for v in vacaciones_qs:
            d = max(v.fecha_inicio, date(anio_sel, mes_sel_num, 1))
            fin = min(v.fecha_fin, ultimo_dia_mes)
            while d <= fin:
                vacaciones_map[d.strftime('%Y-%m-%d')] = v.descripcion
                d += timedelta(days=1)

    hoy = timezone.localdate()
    fecha_inicio_anio = _obtener_fecha_inicio_anio_escolar()

    filas = []
    for p in personal:
        celdas = []
        total_presente = 0
        total_ausente = 0

        for d in dias:
            fecha_str = d.strftime('%Y-%m-%d')
            clave = f"{p['tipo']}-{p['obj'].pk}-{fecha_str}"

            es_feriado = fecha_str in feriados_map
            es_vacaciones = fecha_str in vacaciones_map

            esta_bloqueado = False
            if fecha_inicio_anio and d < fecha_inicio_anio:
                esta_bloqueado = True
            elif d > hoy:
                esta_bloqueado = True

            estado = asistencias_map.get(clave, '')
            if estado == 'presente':
                total_presente += 1
            elif estado == 'ausente':
                total_ausente += 1

            celdas.append({
                'dia': d.day,
                'estado': estado,
                'es_feriado': es_feriado,
                'es_vacaciones': es_vacaciones,
                'bloqueado': esta_bloqueado,
            })

        filas.append({
            'nombre': f"{p['obj'].apellidos}, {p['obj'].nombres}",
            'tipo': p['tipo'],
            'celdas': celdas,
            'total_presente': total_presente,
            'total_ausente': total_ausente,
        })

    fechas_no_laborables = set(feriados_map.keys()) | set(vacaciones_map.keys())

    ahora = timezone.localtime(timezone.now())
    contexto = {
        'mes_nombre': MESES_NOMBRES[mes_sel_num],
        'anio': anio_sel,
        'dias': dias,
        'filas': filas,
        'total_presente': sum(f['total_presente'] for f in filas),
        'total_ausente': sum(f['total_ausente'] for f in filas),
        'total_feriados': len(fechas_no_laborables),
        'feriados_map': feriados_map,
        'eventos_map': eventos_map,
        'vacaciones_map': vacaciones_map,
        'fecha': timezone.localdate(),
        'hora': ahora.strftime('%I:%M %p'),
        'usuario': request.user.get_full_name() or request.user.username,
    }

    template = get_template('escuela/reporte_asistencias_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(html, f"reporte_asistencias_{mes_str}", mostrar_en_navegador=True)


# ================================================================
# CALENDARIO ESCOLAR — VERSIÓN CON CIERRE AUTOMÁTICO
# ================================================================
def _copiar_recurrentes(config_origen, config_destino):
    """Copia feriados y vacaciones recurrentes al nuevo año escolar."""
    try:
        anio_ini_origen = config_origen.anio_inicio
        anio_ini_destino = config_destino.anio_inicio
        if not (anio_ini_origen and anio_ini_destino):
            return
        delta_anios = anio_ini_destino - anio_ini_origen

        for f in Feriado.objects.filter(configuracion=config_origen, recurrente=True):
            try:
                nueva_fecha = f.fecha.replace(year=f.fecha.year + delta_anios)
            except ValueError:
                nueva_fecha = f.fecha.replace(year=f.fecha.year + delta_anios, day=28)
            Feriado.objects.create(
                configuracion=config_destino,
                fecha=nueva_fecha,
                tipo_evento=f.tipo_evento,
                descripcion=f.descripcion,
                recurrente=True,
            )

        for v in PeriodoVacaciones.objects.filter(configuracion=config_origen, recurrente=True):
            try:
                nuevo_ini = v.fecha_inicio.replace(year=v.fecha_inicio.year + delta_anios)
            except ValueError:
                nuevo_ini = v.fecha_inicio.replace(year=v.fecha_inicio.year + delta_anios, day=28)
            try:
                nuevo_fin = v.fecha_fin.replace(year=v.fecha_fin.year + delta_anios)
            except ValueError:
                nuevo_fin = v.fecha_fin.replace(year=v.fecha_fin.year + delta_anios, day=28)
            PeriodoVacaciones.objects.create(
                configuracion=config_destino,
                fecha_inicio=nuevo_ini,
                fecha_fin=nuevo_fin,
                descripcion=v.descripcion,
                recurrente=True,
            )
    except Exception as e:
        print(f"⚠️ Error copiando recurrentes: {e}")


@login_required
def calendario_escolar(request):
    hoy = timezone.localdate()

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()

    ultimo_cerrado = ConfiguracionAnual.objects.filter(
        cerrado=True
    ).order_by('-fecha_cierre').first()

    if not config and not ultimo_cerrado:
        anio_base = hoy.year if hoy.month >= 9 else hoy.year - 1
        anio_escolar_inicial = f"{anio_base}-{anio_base + 1}"
        config = ConfiguracionAnual.objects.create(
            anio_escolar=anio_escolar_inicial,
            activo=True,
            cerrado=False,
        )

    if not config and ultimo_cerrado:
        anio_fin_ultimo = ultimo_cerrado.anio_fin
        if anio_fin_ultimo:
            nuevo_anio = f"{anio_fin_ultimo}-{anio_fin_ultimo + 1}"
            config, created = ConfiguracionAnual.objects.get_or_create(
                anio_escolar=nuevo_anio,
                defaults={
                    'activo': True,
                    'cerrado': False,
                }
            )
            if created:
                _copiar_recurrentes(ultimo_cerrado, config)

    if not config:
        messages.error(request, "No se pudo determinar el año escolar activo.")
        return redirect('dashboard')

    mes_param = request.GET.get('mes')
    if mes_param:
        try:
            anio, mes = map(int, mes_param.split('-'))
        except ValueError:
            anio, mes = hoy.year, hoy.month
    else:
        anio, mes = hoy.year, hoy.month

    cal = calendar.monthcalendar(anio, mes)
    dias = []
    for semana in cal:
        for dia in semana:
            if dia != 0:
                dias.append(date(anio, mes, dia))

    mes_nombre = MESES_NOMBRES[mes]
    mes_sel_str = f"{anio}-{mes:02d}"

    meses_disponibles = []
    if config.fecha_inicio:
        anio_ini = config.fecha_inicio.year
        mes_ini = config.fecha_inicio.month
    else:
        anio_ini = config.anio_inicio or hoy.year
        mes_ini = 9

    if config.fecha_fin:
        anio_fin = config.fecha_fin.year
        mes_fin = config.fecha_fin.month
    else:
        anio_fin = (config.anio_fin or (anio_ini + 1))
        mes_fin = 7

    m_actual, a_actual = mes_ini, anio_ini
    for _ in range(24):
        meses_disponibles.append({
            'valor': f"{a_actual}-{m_actual:02d}",
            'nombre': MESES_NOMBRES[m_actual],
            'anio': a_actual,
            'etiqueta': f"{m_actual:02d}/{a_actual}"
        })
        if a_actual == anio_fin and m_actual == mes_fin:
            break
        m_actual += 1
        if m_actual > 12:
            m_actual = 1
            a_actual += 1

    es_temporada_vacaciones = False
    if config.fecha_inicio and config.fecha_fin:
        fecha_actual_mes = date(anio, mes, 1)
        inicio_ok = fecha_actual_mes >= config.fecha_inicio.replace(day=1)
        fin_ok = fecha_actual_mes <= config.fecha_fin.replace(day=1)
        es_temporada_vacaciones = not (inicio_ok and fin_ok)

    feriados_qs = Feriado.objects.filter(
        configuracion=config,
        fecha__year=anio,
        fecha__month=mes
    ).exclude(tipo_evento__in=['inicio', 'fin', 'vacaciones'])

    eventos_map = {}
    descripciones_map = {}
    for f in feriados_qs:
        tipo = f.tipo_evento or 'feriado'
        clave = f.fecha.strftime('%Y-%m-%d')
        eventos_map[clave] = tipo
        if f.descripcion:
            descripciones_map[clave] = f.descripcion

    vacaciones_map = {}
    if config:
        primer_dia = date(anio, mes, 1)
        ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1])
        vqs = PeriodoVacaciones.objects.filter(
            configuracion=config,
            fecha_inicio__lte=ultimo_dia,
            fecha_fin__gte=primer_dia,
        )
        for v in vqs:
            d = max(v.fecha_inicio, primer_dia)
            fin = min(v.fecha_fin, ultimo_dia)
            while d <= fin:
                vacaciones_map[d.strftime('%Y-%m-%d')] = v.descripcion
                d += timedelta(days=1)

    puede_cerrar_anio = False
    if config and config.fecha_fin and hoy >= config.fecha_fin:
        puede_cerrar_anio = True

    contexto = {
        'dias': dias,
        'mes': mes,
        'anio': anio,
        'mes_nombre': mes_nombre,
        'mes_sel_str': mes_sel_str,
        'meses_disponibles': meses_disponibles,
        'eventos_map': eventos_map,
        'descripciones_map': descripciones_map,
        'vacaciones_map': vacaciones_map,
        'config': config,
        'es_temporada_vacaciones': es_temporada_vacaciones,
        'puede_cerrar_anio': puede_cerrar_anio,
        'hoy': hoy,
    }
    return render(request, 'escuela/calendario_escolar.html', contexto)


@login_required
@require_POST
def guardar_calendario_escolar(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    mes = data.get('mes', '')
    eventos = data.get('eventos', [])
    recurrentes = data.get('recurrentes', [])

    try:
        anio_sel, mes_sel_num = map(int, mes.split('-'))
    except (ValueError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'Mes inválido'}, status=400)

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    if not config:
        return JsonResponse({'ok': False, 'error': 'No hay año escolar activo'}, status=400)

    Feriado.objects.filter(
        configuracion=config,
        fecha__year=anio_sel,
        fecha__month=mes_sel_num,
    ).exclude(tipo_evento__in=['inicio', 'fin', 'vacaciones']).delete()

    guardados = 0
    for ev in eventos:
        try:
            fecha = date.fromisoformat(ev['fecha'])
            tipo = ev.get('evento', 'feriado')
            if tipo not in ('feriado', 'eventos'):
                continue
            descripcion = ev.get('descripcion', '')
            es_recurrente = fecha.strftime('%Y-%m-%d') in recurrentes

            Feriado.objects.create(
                configuracion=config,
                fecha=fecha,
                tipo_evento=tipo,
                descripcion=descripcion,
                recurrente=es_recurrente,
            )
            guardados += 1
        except (ValueError, KeyError):
            continue

    return JsonResponse({
        'ok': True,
        'mensaje': f"Se guardaron {guardados} evento(s) del calendario.",
        'guardados': guardados,
    })


@login_required
@require_POST
def guardar_configuracion_anual(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    fecha_inicio_str = data.get('fecha_inicio', '').strip()
    fecha_fin_str = data.get('fecha_fin', '').strip()

    if not fecha_inicio_str:
        return JsonResponse({'ok': False, 'error': 'La fecha de inicio es obligatoria'}, status=400)

    try:
        fecha_inicio = date.fromisoformat(fecha_inicio_str)
        fecha_fin = date.fromisoformat(fecha_fin_str) if fecha_fin_str else None
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Formato de fecha inválido'}, status=400)

    if fecha_fin and fecha_fin < fecha_inicio:
        return JsonResponse({'ok': False, 'error': 'La fecha de fin no puede ser anterior a la de inicio'}, status=400)

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    if not config:
        return JsonResponse({'ok': False, 'error': 'No hay un año escolar activo'}, status=400)

    anio_esperado_ini = config.anio_inicio
    if fecha_inicio.year != anio_esperado_ini:
        return JsonResponse({
            'ok': False,
            'error': f'La fecha de inicio debe ser del año {anio_esperado_ini}'
        }, status=400)

    if fecha_inicio.month not in (9, 10):
        return JsonResponse({
            'ok': False,
            'error': 'La fecha de inicio debe ser en Septiembre u Octubre'
        }, status=400)

    if fecha_fin:
        anio_esperado_fin = config.anio_fin
        if fecha_fin.year != anio_esperado_fin:
            return JsonResponse({
                'ok': False,
                'error': f'La fecha de fin debe ser del año {anio_esperado_fin}'
            }, status=400)
        if fecha_fin.month != 7:
            return JsonResponse({
                'ok': False,
                'error': 'La fecha de fin debe ser en Julio'
            }, status=400)

    config.fecha_inicio = fecha_inicio
    config.fecha_fin = fecha_fin
    config.save()

    return JsonResponse({
        'ok': True,
        'mensaje': f'Configuración del año {config.anio_escolar} guardada correctamente.',
        'anio_escolar': config.anio_escolar,
    })


@login_required
@require_POST
def guardar_vacaciones(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    fecha_inicio_str = data.get('fecha_inicio', '').strip()
    fecha_fin_str = data.get('fecha_fin', '').strip()
    descripcion = data.get('descripcion', '').strip()
    recurrente = data.get('recurrente', True)

    if not (fecha_inicio_str and fecha_fin_str and descripcion):
        return JsonResponse({'ok': False, 'error': 'Todos los campos son obligatorios'}, status=400)

    try:
        fecha_inicio = date.fromisoformat(fecha_inicio_str)
        fecha_fin = date.fromisoformat(fecha_fin_str)
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Formato de fecha inválido'}, status=400)

    if fecha_fin < fecha_inicio:
        return JsonResponse({'ok': False, 'error': 'La fecha de fin no puede ser anterior a la de inicio'}, status=400)

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    if not config:
        return JsonResponse({'ok': False, 'error': 'No hay año escolar activo'}, status=400)

    if config.fecha_inicio and fecha_inicio < config.fecha_inicio:
        return JsonResponse({
            'ok': False,
            'error': f'La fecha de inicio no puede ser anterior al inicio del año escolar ({config.fecha_inicio.strftime("%d/%m/%Y")})'
        }, status=400)

    if config.fecha_fin and fecha_fin > config.fecha_fin:
        return JsonResponse({
            'ok': False,
            'error': f'La fecha de fin no puede ser posterior al fin del año escolar ({config.fecha_fin.strftime("%d/%m/%Y")})'
        }, status=400)

    vac = PeriodoVacaciones.objects.create(
        configuracion=config,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        descripcion=descripcion,
        recurrente=recurrente,
    )

    return JsonResponse({
        'ok': True,
        'mensaje': f'Vacaciones "{descripcion}" guardadas correctamente.',
        'id': vac.pk,
    })


@login_required
@require_POST
def eliminar_vacaciones(request, pk):
    try:
        vac = PeriodoVacaciones.objects.get(pk=pk)
        vac.delete()
        return JsonResponse({'ok': True, 'mensaje': 'Vacaciones eliminadas correctamente.'})
    except PeriodoVacaciones.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'No existe'}, status=404)


@login_required
def exportar_calendario_pdf(request):
    if request.method != 'POST':
        return redirect('calendario_escolar')

    try:
        datos = json.loads(request.POST.get('datos', '{}'))
    except (json.JSONDecodeError, TypeError):
        datos = {}

    mes_str = datos.get('mes', '')
    try:
        anio_sel, mes_sel_num = map(int, mes_str.split('-'))
    except (ValueError, AttributeError):
        hoy = timezone.localdate()
        anio_sel, mes_sel_num = hoy.year, hoy.month

    cal = calendar.monthcalendar(anio_sel, mes_sel_num)
    dias = []
    semanas = []
    for semana in cal:
        fila = []
        for dia in semana:
            if dia != 0:
                d = date(anio_sel, mes_sel_num, dia)
                dias.append(d)
                fila.append(d)
            else:
                fila.append(None)
        semanas.append(fila)

    feriados_qs = Feriado.objects.filter(fecha__year=anio_sel, fecha__month=mes_sel_num)
    eventos_map = {}
    descripciones_map = {}
    for f in feriados_qs:
        clave = f.fecha.strftime('%Y-%m-%d')
        eventos_map[clave] = f.tipo_evento or 'feriado'
        if f.descripcion:
            descripciones_map[clave] = f.descripcion

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    vacaciones_mes = []
    vacaciones_map = {}
    if config:
        ultimo_dia = date(anio_sel, mes_sel_num, calendar.monthrange(anio_sel, mes_sel_num)[1])
        primer_dia = date(anio_sel, mes_sel_num, 1)
        vqs = PeriodoVacaciones.objects.filter(
            configuracion=config,
            fecha_inicio__lte=ultimo_dia,
            fecha_fin__gte=primer_dia,
        )
        for v in vqs:
            vacaciones_mes.append(v)
            d = max(v.fecha_inicio, primer_dia)
            fin = min(v.fecha_fin, ultimo_dia)
            while d <= fin:
                vacaciones_map[d.strftime('%Y-%m-%d')] = v.descripcion
                d += timedelta(days=1)

    NOMBRES_EVENTOS = {
        'feriado': 'Feriado',
        'vacaciones': 'Vacaciones',
        'eventos': 'Evento Especial',
        'inicio': 'Inicio de Año Escolar',
        'fin': 'Fin de Año Escolar',
    }

    total_habiles = 0
    total_feriados = 0
    total_vacaciones = 0

    for semana in semanas:
        for d in semana:
            if d is None:
                continue
            if d.weekday() >= 5:
                continue

            fecha_str = d.strftime('%Y-%m-%d')

            if fecha_str in vacaciones_map:
                total_vacaciones += 1
            elif fecha_str in eventos_map:
                total_feriados += 1
            else:
                total_habiles += 1

    ahora = timezone.localtime(timezone.now())
    contexto = {
        'mes_nombre': MESES_NOMBRES[mes_sel_num],
        'anio': anio_sel,
        'dias': dias,
        'semanas': semanas,
        'eventos_map': eventos_map,
        'descripciones_map': descripciones_map,
        'nombres_eventos': NOMBRES_EVENTOS,
        'vacaciones_mes': vacaciones_mes,
        'vacaciones_map': vacaciones_map,
        'config': config,
        'fecha': timezone.localdate(),
        'hora': ahora.strftime('%I:%M %p'),
        'usuario': request.user.get_full_name() or request.user.username,
        'total_habiles': total_habiles,
        'total_feriados': total_feriados,
        'total_vacaciones': total_vacaciones,
    }

    template = get_template('escuela/reporte_calendario_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(html, f"calendario_escolar_{mes_str}", mostrar_en_navegador=True)


# ================================================================
# CIERRE DE AÑO ESCOLAR (integración con Calendario)
# ================================================================
@login_required
def cierre_anual_json(request):
    """Devuelve la lista de estudiantes activos para el cierre."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    if not config:
        return JsonResponse({
            'ok': False,
            'error': 'No hay un Año Escolar activo configurado.'
        }, status=400)

    estudiantes = Estudiante.objects.filter(
        activo=True
    ).exclude(
        estado='egresado'
    ).order_by('nivel', 'apellidos', 'nombres')

    datos = []
    for e in estudiantes:
        siguiente = SIGUIENTE_NIVEL.get(e.nivel)
        siguiente_display = dict(Estudiante.NIVEL_CHOICES).get(siguiente, '') if siguiente else '🎓 Egresado'

        datos.append({
            'id': e.pk,
            'nombres': e.nombres,
            'apellidos': e.apellidos,
            'cedula': e.cedula_activa,
            'nivel': e.nivel,
            'nivel_display': e.get_nivel_display(),
            'siguiente_nivel': siguiente or '',
            'siguiente_nivel_display': siguiente_display,
        })

    return JsonResponse({
        'ok': True,
        'estudiantes': datos,
        'anio_escolar': config.anio_escolar,
    })


@login_required
@require_POST
def ejecutar_cierre_anual(request):
    """Ejecuta el cierre anual. Se llama desde el Calendario Escolar."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    acciones = data.get('acciones', [])
    observacion_general = data.get('observacion', '').strip()

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    if not config:
        return JsonResponse({
            'ok': False,
            'error': 'No hay un Año Escolar activo configurado.'
        }, status=400)

    if config.cerrado:
        return JsonResponse({
            'ok': False,
            'error': f'El año escolar {config.anio_escolar} ya fue cerrado.'
        }, status=400)

    anio_escolar_actual = config.anio_escolar
    fecha_fin = config.fecha_fin
    hoy = timezone.localdate()

    if fecha_fin and hoy < fecha_fin:
        return JsonResponse({
            'ok': False,
            'error': (
                f'No se puede cerrar el año escolar antes de su fecha de fin. '
                f'La fecha de fin es {fecha_fin.strftime("%d/%m/%Y")} y hoy es {hoy.strftime("%d/%m/%Y")}.'
            )
        }, status=400)

    if not acciones:
        return JsonResponse({'ok': False, 'error': 'No hay acciones para aplicar.'}, status=400)

    stats = {'inscritos': 0, 'repitientes': 0, 'retirados': 0, 'egresados': 0, 'errores': 0}
    errores_detalle = []

    for accion_data in acciones:
        try:
            estudiante_id = accion_data.get('id')
            accion = accion_data.get('accion')

            if not estudiante_id or accion not in ['inscribir', 'repitiente', 'retirar']:
                stats['errores'] += 1
                continue

            try:
                estudiante = Estudiante.objects.get(pk=estudiante_id)
            except Estudiante.DoesNotExist:
                stats['errores'] += 1
                errores_detalle.append(f"Estudiante ID {estudiante_id} no existe")
                continue

            nivel_anterior = estudiante.nivel

            if accion == 'retirar':
                estudiante.activo = False
                estudiante.estado = 'retirado'
                estudiante.save()
                HistorialEstudiante.objects.create(
                    estudiante=estudiante,
                    anio_escolar=anio_escolar_actual,
                    nivel_anterior=nivel_anterior,
                    nivel_nuevo='',
                    accion='retirado',
                    observacion=observacion_general or 'Retirado en cierre anual'
                )
                stats['retirados'] += 1

            elif accion == 'repitiente':
                HistorialEstudiante.objects.create(
                    estudiante=estudiante,
                    anio_escolar=anio_escolar_actual,
                    nivel_anterior=nivel_anterior,
                    nivel_nuevo=nivel_anterior,
                    accion='repitiente',
                    observacion=observacion_general or 'Repitiente del año escolar'
                )
                stats['repitientes'] += 1

            elif accion == 'inscribir':
                siguiente = SIGUIENTE_NIVEL.get(nivel_anterior)
                if siguiente is None:
                    estudiante.estado = 'egresado'
                    estudiante.activo = False
                    estudiante.save()
                    Egresado.objects.create(
                        estudiante=estudiante,
                        anio_egreso=anio_escolar_actual,
                        cedula_escolar=estudiante.cedula or '',
                        cedula_identidad=estudiante.cedula_identidad or '',
                        nombres=estudiante.nombres,
                        apellidos=estudiante.apellidos,
                        genero=estudiante.genero,
                        fecha_nacimiento=estudiante.fecha_nacimiento,
                        nivel_egreso='6to Grado',
                        observacion=observacion_general or 'Egresado al culminar 6to Grado'
                    )
                    HistorialEstudiante.objects.create(
                        estudiante=estudiante,
                        anio_escolar=anio_escolar_actual,
                        nivel_anterior=nivel_anterior,
                        nivel_nuevo='',
                        accion='egresado',
                        observacion=observacion_general or 'Egresado de 6to Grado'
                    )
                    stats['egresados'] += 1
                else:
                    estudiante.nivel = siguiente
                    estudiante.save()
                    HistorialEstudiante.objects.create(
                        estudiante=estudiante,
                        anio_escolar=anio_escolar_actual,
                        nivel_anterior=nivel_anterior,
                        nivel_nuevo=siguiente,
                        accion='inscrito',
                        observacion=observacion_general or 'Inscrito al siguiente nivel'
                    )
                    stats['inscritos'] += 1

        except Exception as ex:
            stats['errores'] += 1
            errores_detalle.append(str(ex))

    config.activo = False
    config.cerrado = True
    config.fecha_cierre = timezone.now()
    config.save()

    nuevo_anio_escolar = None
    try:
        partes = anio_escolar_actual.split('-')
        if len(partes) == 2:
            anio_fin_actual = int(partes[1])
            nuevo_anio_escolar = f"{anio_fin_actual}-{anio_fin_actual + 1}"
            nuevo_config, created = ConfiguracionAnual.objects.get_or_create(
                anio_escolar=nuevo_anio_escolar,
                defaults={
                    'fecha_inicio': None,
                    'fecha_fin': None,
                    'activo': True,
                    'cerrado': False,
                }
            )
            if created:
                _copiar_recurrentes(config, nuevo_config)
    except (ValueError, IndexError):
        pass

    return JsonResponse({
        'ok': True,
        'mensaje': (
            f'Cierre anual completado. '
            f'{stats["inscritos"]} inscritos, '
            f'{stats["repitientes"]} repitientes, '
            f'{stats["retirados"]} retirados, '
            f'{stats["egresados"]} egresados.'
            + (f' Se creó y activó el año escolar {nuevo_anio_escolar}.' if nuevo_anio_escolar else '')
        ),
        'stats': stats,
        'errores': errores_detalle,
        'nuevo_anio_escolar': nuevo_anio_escolar,
    })


# ================================================================
# EGRESADOS
# ================================================================
@login_required
def lista_egresados(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos.")
        return redirect('dashboard')

    egresados = Egresado.objects.all().order_by('-anio_egreso', 'apellidos', 'nombres')
    anios = egresados.values_list('anio_egreso', flat=True).distinct().order_by('-anio_egreso')

    contexto = {
        'egresados': egresados,
        'anios': list(anios),
        'total': egresados.count(),
    }
    return render(request, 'escuela/lista_egresados.html', contexto)


@login_required
def admin_egresados_json(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    qs = Egresado.objects.all()
    anio = request.GET.get('anio', '').strip()
    buscar = request.GET.get('buscar', '').strip()

    if anio:
        qs = qs.filter(anio_egreso=anio)
    if buscar:
        qs = qs.filter(
            Q(nombres__icontains=buscar) |
            Q(apellidos__icontains=buscar) |
            Q(cedula_escolar__icontains=buscar) |
            Q(cedula_identidad__icontains=buscar)
        )

    qs = qs.order_by('-anio_egreso', 'apellidos', 'nombres')

    datos = []
    for e in qs:
        datos.append({
            'id': e.pk,
            'nombres': e.nombres,
            'apellidos': e.apellidos,
            'nombre_completo': e.nombre_completo,
            'cedula_escolar': e.cedula_escolar or '—',
            'cedula_identidad': e.cedula_identidad or '—',
            'genero': 'Masculino' if e.genero == 'M' else 'Femenino',
            'genero_codigo': e.genero,
            'fecha_nacimiento': e.fecha_nacimiento.strftime('%d/%m/%Y'),
            'anio_egreso': e.anio_egreso,
            'nivel_egreso': e.nivel_egreso,
            'observacion': e.observacion or '',
        })

    return JsonResponse({'ok': True, 'egresados': datos, 'total': len(datos)})


# ================================================================
# ACTUALIZAR ENCABEZADO INSTITUCIONAL
# ================================================================
@login_required
def actualizar_encabezado(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para actualizar el encabezado.")
        return redirect('dashboard')

    posibles_rutas = [
        os.path.join(settings.BASE_DIR, 'escuela', 'static', 'img'),
        os.path.join(settings.BASE_DIR, 'static', 'img'),
    ]

    ruta_destino_dir = None
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            ruta_destino_dir = ruta
            break

    if not ruta_destino_dir:
        messages.error(request, "No se encontró la carpeta static/img en el proyecto.")
        return redirect('menu_admin')

    ruta_encabezado_actual = os.path.join(ruta_destino_dir, 'encabezado.png')

    if request.method == 'POST':
        archivo = request.FILES.get('encabezado')
        errores = []
        advertencias = []

        if not archivo:
            errores.append("Debes seleccionar un archivo.")
        else:
            if archivo.name.lower() != 'encabezado.png':
                errores.append("El archivo debe llamarse exactamente 'encabezado.png'.")
            if not archivo.name.lower().endswith('.png'):
                errores.append("El archivo debe tener extensión .png.")
            if archivo.content_type != 'image/png':
                errores.append("El tipo de archivo debe ser image/png.")
            if archivo.size > 5 * 1024 * 1024:
                errores.append("El archivo es demasiado grande (máx. 5 MB).")

            try:
                img = Image.open(archivo)
                ancho, alto = img.size

                if (ancho, alto) != (1408, 162):
                    advertencias.append(
                        f"La resolución recomendada es 1408 x 162 px. "
                        f"Tu imagen tiene {ancho} x {alto} px. "
                        f"Se guardará igualmente, pero puede verse deformada en los PDFs."
                    )
            except Exception as e:
                errores.append(f"El archivo no es una imagen válida: {str(e)}")

        if errores:
            for err in errores:
                messages.error(request, err)
            for adv in advertencias:
                messages.warning(request, adv)
        else:
            try:
                archivo.seek(0)
                with open(ruta_encabezado_actual, 'wb+') as destino:
                    for chunk in archivo.chunks():
                        destino.write(chunk)

                messages.success(request, "Encabezado actualizado correctamente.")
                return redirect('actualizar_encabezado')
            except Exception as e:
                messages.error(request, f"Error al guardar el archivo: {str(e)}")
                for adv in advertencias:
                    messages.warning(request, adv)

    encabezado_existe = os.path.exists(ruta_encabezado_actual)
    fecha_modificacion = None
    if encabezado_existe:
        timestamp = os.path.getmtime(ruta_encabezado_actual)
        fecha_modificacion = datetime.fromtimestamp(timestamp)

    contexto = {
        'encabezado_existe': encabezado_existe,
        'fecha_modificacion': fecha_modificacion,
        'resolucion_recomendada': '1408 x 162 px',
        'nombre_obligatorio': 'encabezado.png',
        'ruta_encabezado': '/static/img/encabezado.png',
    }
    return render(request, 'escuela/actualizar_encabezado.html', contexto)


# ================================================================
# EXPORTAR PDF — LISTADO DE PERSONAL
# ================================================================
@login_required
def exportar_personal_pdf(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar PDFs.")
        return redirect('personal')

    busqueda = request.GET.get('buscar', '').strip()

    def filtrar(qs):
        if not busqueda:
            return qs
        return qs.filter(
            Q(nombres__icontains=busqueda) |
            Q(apellidos__icontains=busqueda) |
            Q(cedula__icontains=busqueda)
        )

    docentes = filtrar(Docente.objects.filter(activo=True)).order_by('apellidos', 'nombres')
    administrativos = filtrar(PersonalAdministrativo.objects.filter(activo=True)).order_by('apellidos', 'nombres')
    apoyo = filtrar(PersonalApoyo.objects.filter(activo=True)).order_by('apellidos', 'nombres')
    cocina = filtrar(PersonalCocina.objects.filter(activo=True)).order_by('apellidos', 'nombres')

    ahora = timezone.localtime(timezone.now())
    contexto = {
        'docentes': docentes,
        'administrativos': administrativos,
        'apoyo': apoyo,
        'cocina': cocina,
        'total_personal': docentes.count() + administrativos.count() + apoyo.count() + cocina.count(),
        'total_docentes': docentes.count(),
        'total_administrativos': administrativos.count(),
        'total_apoyo': apoyo.count(),
        'total_cocina': cocina.count(),
        'busqueda': busqueda,
        'fecha': timezone.localdate(),
        'hora': ahora.strftime('%I:%M %p'),
        'usuario': request.user.get_full_name() or request.user.username,
    }

    template = get_template('escuela/reporte_personal_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(html, "listado_personal", mostrar_en_navegador=True)


# ================================================================
# HELPER: MES EN TEXTO (español)
# ================================================================
MESES_TEXTO = {
    1: 'enero',
    2: 'febrero',
    3: 'marzo',
    4: 'abril',
    5: 'mayo',
    6: 'junio',
    7: 'julio',
    8: 'agosto',
    9: 'septiembre',
    10: 'octubre',
    11: 'noviembre',
    12: 'diciembre',
}


# ================================================================
# ✅ CONSTANCIA DE ESTUDIO — PDF (con bloqueo por fin de año)
# ================================================================
@login_required
def constancia_estudio_pdf(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar constancias.")
        return redirect('inicial')

    # ✅ NUEVO: Validar que el año escolar esté vigente
    puede, motivo, config = _puede_emitir_constancias()
    if not puede:
        messages.error(request, motivo)
        return redirect('inicial')

    estudiante = get_object_or_404(Estudiante, pk=pk)

    director = PersonalAdministrativo.objects.filter(
        cargo='Director', activo=True
    ).first()

    if not director:
        messages.error(
            request,
            "No se puede emitir la constancia de estudio porque no hay un Director "
            "activo registrado en el sistema. Registre o active un Director primero."
        )
        return redirect('inicial')

    director_nombres = f"{director.nombres} {director.apellidos}"
    director_cedula = f"{director.nacionalidad}-{director.cedula}"
    director_telefono = director.telefono or '—'

    director_direccion = "Calle principal del Helechal, Parroquia Bramón, Municipio Junín, Estado Táchira"
    director_correo = "coord.helechal282@gmail.com"
    director_telefono_institucional = "0276-8088144"

    anio_escolar = config.anio_escolar if config else "2025 - 2026"

    if estudiante.tipo_documento == 'identidad' and estudiante.cedula_identidad:
        cedula_estudiante = estudiante.cedula_identidad
        tipo_documento_display = "Cédula de Identidad"
    else:
        cedula_estudiante = estudiante.cedula or '—'
        tipo_documento_display = "Cédula Escolar"

    nivel_display = estudiante.get_nivel_display()
    seccion = "A"

    if estudiante.genero == 'F':
        articulo = "la"
    else:
        articulo = "el"

    hoy = timezone.localdate()
    dia_expedicion = hoy.day
    mes_expedicion = MESES_TEXTO.get(hoy.month, '')
    anio_expedicion = hoy.year

    ahora = timezone.localtime(timezone.now())

    contexto = {
        'estudiante': estudiante,
        'director_nombres': director_nombres,
        'director_cedula': director_cedula,
        'director_telefono': director_telefono,
        'director_direccion': director_direccion,
        'director_correo': director_correo,
        'director_telefono_institucional': director_telefono_institucional,
        'anio_escolar': anio_escolar,
        'cedula_estudiante': cedula_estudiante,
        'tipo_documento_display': tipo_documento_display,
        'nivel_display': nivel_display,
        'seccion': seccion,
        'articulo': articulo,
        'dia_expedicion': dia_expedicion,
        'mes_expedicion': mes_expedicion,
        'anio_expedicion': anio_expedicion,
        'fecha': hoy,
        'hora': ahora.strftime('%I:%M %p'),
    }

    template = get_template('escuela/constancia_estudio_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(
        html,
        f"constancia_estudio_{estudiante.cedula or estudiante.pk}",
        mostrar_en_navegador=True
    )


# ================================================================
# HELPER: MES EN TEXTO PARA FORMULARIOS / OTRAS VISTAS
# ================================================================
@login_required
def mes_en_texto(request):
    mes_param = request.GET.get('mes')
    fecha_param = request.GET.get('fecha')

    if fecha_param:
        try:
            fecha = date.fromisoformat(fecha_param)
            mes_num = fecha.month
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)
    elif mes_param:
        try:
            mes_num = int(mes_param)
        except (ValueError, TypeError):
            return JsonResponse({'ok': False, 'error': 'Mes inválido'}, status=400)
    else:
        mes_num = timezone.localdate().month

    if mes_num < 1 or mes_num > 12:
        return JsonResponse({'ok': False, 'error': 'Mes fuera de rango'}, status=400)

    return JsonResponse({
        'ok': True,
        'mes_numero': mes_num,
        'mes_texto': MESES_TEXTO.get(mes_num, ''),
    })


# ================================================================
# LISTADO DE MESES EN TEXTO
# ================================================================
@login_required
def meses_en_texto(request):
    meses = [{'numero': n, 'texto': t} for n, t in MESES_TEXTO.items()]
    return JsonResponse({'ok': True, 'meses': meses})


# ================================================================
# ✅ CONSTANCIA DE TRABAJO — PDF (con bloqueo por fin de año)
# ================================================================
@login_required
def constancia_trabajo_pdf(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar constancias.")
        return redirect('personal')

    # ✅ NUEVO: Validar que el año escolar esté vigente
    puede, motivo, _config = _puede_emitir_constancias()
    if not puede:
        messages.error(request, motivo)
        return redirect('personal')

    tipo_raw = (request.GET.get('tipo') or 'Docente').strip().lower()

    MAPA_TIPOS = {
        'docente':        Docente,
        'administrativo': PersonalAdministrativo,
        'apoyo':          PersonalApoyo,
        'cocina':         PersonalCocina,
    }

    if tipo_raw not in MAPA_TIPOS:
        messages.error(request, f"Tipo de personal no válido: '{tipo_raw}'.")
        return redirect('personal')

    Modelo = MAPA_TIPOS[tipo_raw]
    persona = Modelo.objects.filter(pk=pk).first()

    if not persona:
        messages.error(
            request,
            f"No se encontró {tipo_raw} con ID {pk}. "
            f"Verifique que el registro exista y esté activo."
        )
        return redirect('personal')

    categoria_personal = ''
    cargo_personal = ''

    if tipo_raw == 'docente':
        categoria_personal = 'DOCENTE'
        cargo_personal = 'DOCENTE DE AULA'

    elif tipo_raw == 'administrativo':
        categoria_personal = 'ADMINISTRATIVO'
        if persona.cargo == 'Otro' and persona.cargo_detalle:
            cargo_personal = persona.cargo_detalle.upper()
        else:
            cargo_personal = (
                persona.get_cargo_display() if persona.cargo else 'ADMINISTRATIVO'
            ).upper()

    elif tipo_raw == 'apoyo':
        categoria_personal = 'DE APOYO'
        if persona.cargo == 'Otro' and persona.cargo_detalle:
            cargo_personal = persona.cargo_detalle.upper()
        else:
            cargo_personal = (
                persona.get_cargo_display() if persona.cargo else 'OBRERO'
            ).upper()

    elif tipo_raw == 'cocina':
        categoria_personal = 'DE APOYO'
        if persona.genero == 'F':
            cargo_personal = 'COCINERA'
        else:
            cargo_personal = 'COCINERO'

    director = PersonalAdministrativo.objects.filter(
        cargo='Director', activo=True
    ).first()

    if not director:
        messages.error(
            request,
            "No se puede emitir la constancia de trabajo porque no hay un Director "
            "activo registrado en el sistema. Registre o active un Director primero."
        )
        return redirect('personal')

    director_nombres = f"{director.nombres} {director.apellidos}"
    director_cedula = f"{director.nacionalidad}-{director.cedula}"
    director_telefono = director.telefono or '—'

    codigo_cargo = (request.GET.get('codigo_cargo') or '').strip()
    carga_horaria = (request.GET.get('carga_horaria') or '').strip()

    if not codigo_cargo or not carga_horaria:
        messages.error(request, "Debe ingresar el código de cargo y la carga horaria.")
        return redirect('personal')

    if persona.genero == 'F':
        articulo = "la"
        ciudadano_o_ciudadana = "ciudadana"
    else:
        articulo = "el"
        ciudadano_o_ciudadana = "ciudadano"

    hoy = timezone.localdate()
    dia_expedicion = hoy.day
    mes_expedicion = MESES_TEXTO.get(hoy.month, '')
    anio_expedicion = hoy.year

    ahora = timezone.localtime(timezone.now())

    contexto = {
        'persona': persona,
        'categoria_personal': categoria_personal,
        'cargo_personal': cargo_personal,
        'director_nombres': director_nombres,
        'director_cedula': director_cedula,
        'director_telefono': director_telefono,
        'codigo_cargo': codigo_cargo,
        'carga_horaria': carga_horaria,
        'articulo': articulo,
        'ciudadano_o_ciudadana': ciudadano_o_ciudadana,
        'dia_expedicion': dia_expedicion,
        'mes_expedicion': mes_expedicion,
        'anio_expedicion': anio_expedicion,
        'fecha': hoy,
        'hora': ahora.strftime('%I:%M %p'),
    }

    template = get_template('escuela/constancia_trabajo_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(
        html,
        f"constancia_trabajo_{persona.cedula or persona.pk}",
        mostrar_en_navegador=True
    )


# ================================================================
# DASHBOARD ANEXA
# ================================================================
@login_required
def dashboard_anexa(request):
    contexto = {
        'total_estudiantes': Estudiante.objects.filter(activo=True).count(),
        'total_docentes': Docente.objects.filter(activo=True).count(),
        'total_personal': (
            Docente.objects.filter(activo=True).count() +
            PersonalAdministrativo.objects.filter(activo=True).count() +
            PersonalApoyo.objects.filter(activo=True).count() +
            PersonalCocina.objects.filter(activo=True).count()
        ),
    }
    return render(request, 'escuela/dashboard_anexa.html', contexto)


# ================================================================
# GESTIÓN DE FIRMANTES
# ================================================================
@login_required
def gestion_firmantes(request):
    """Vista principal para el panel de firmantes"""
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para gestionar firmantes.")
        return redirect('dashboard')

    firmantes = Firmante.objects.filter(activo=True)
    return render(request, 'escuela/gestion_firmantes.html', {
        'firmantes': firmantes
    })


@login_required
def admin_firmantes_json(request):
    """Endpoint JSON para obtener la lista de firmantes"""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    firmantes = Firmante.objects.filter(activo=True).order_by('tipo', 'apellidos', 'nombres')
    datos = []

    for f in firmantes:
        datos.append({
            'id': f.pk,
            'tipo': f.tipo,
            'tipo_display': f.get_tipo_display(),
            'nombres': f.nombres,
            'apellidos': f.apellidos,
            'cedula': f.cedula or '',
            'telefono': f.telefono or '',
            'nombre_completo': f.nombre_completo,
            'cedula_completa': f.cedula_completa,
            'iniciales': f"{f.nombres[0]}{f.apellidos[0]}" if f.nombres and f.apellidos else "??"
        })

    return JsonResponse({'ok': True, 'firmantes': datos})


@login_required
@require_POST
def guardar_firmante(request):
    """Guarda o edita un firmante. Solo permite 1 firmante por tipo."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    firmante_id = data.get('id')
    tipo = data.get('tipo')
    nombres = data.get('nombres', '').strip()
    apellidos = data.get('apellidos', '').strip()
    cedula = data.get('cedula', '').strip()
    telefono = data.get('telefono', '').strip()

    if not tipo or not nombres or not apellidos:
        return JsonResponse(
            {'ok': False, 'error': 'Tipo, Nombres y Apellidos son obligatorios'},
            status=400
        )

    if tipo not in ['director_anexa', 'centro_desarrollo']:
        return JsonResponse(
            {'ok': False, 'error': 'Tipo de firmante no válido.'},
            status=400
        )

    qs_existente = Firmante.objects.filter(tipo=tipo, activo=True)
    if firmante_id:
        qs_existente = qs_existente.exclude(pk=firmante_id)

    if qs_existente.exists():
        existente = qs_existente.first()
        tipo_display = existente.get_tipo_display()
        return JsonResponse({
            'ok': False,
            'error': (
                f'Ya existe un firmante activo de tipo "{tipo_display}" '
                f'({existente.nombre_completo}). Solo se permite 1 por tipo. '
                f'Debe eliminar el actual antes de registrar uno nuevo.'
            )
        }, status=400)

    try:
        if firmante_id:
            firmante = Firmante.objects.get(pk=firmante_id)
            firmante.tipo = tipo
            firmante.nombres = nombres
            firmante.apellidos = apellidos
            firmante.cedula = cedula if cedula else None
            firmante.telefono = telefono if telefono else None
            firmante.save()
            mensaje = f"Firmante {firmante.nombre_completo} actualizado correctamente."
        else:
            firmante = Firmante.objects.create(
                tipo=tipo,
                nombres=nombres,
                apellidos=apellidos,
                cedula=cedula if cedula else None,
                telefono=telefono if telefono else None,
                activo=True
            )
            mensaje = f"Firmante {firmante.nombre_completo} registrado correctamente."

        return JsonResponse({'ok': True, 'mensaje': mensaje})

    except Firmante.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'El firmante no existe'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def eliminar_firmante(request, pk):
    """Elimina lógicamente un firmante (lo desactiva)"""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    try:
        firmante = get_object_or_404(Firmante, pk=pk)
        firmante.activo = False
        firmante.save()
        return JsonResponse({'ok': True, 'mensaje': 'Firmante eliminado correctamente.'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

# ================================================================
# CERTIFICADO DE EDUCACIÓN PRIMARIA — PDF (con literal dinámico)
# ================================================================
@login_required
def certificado_primaria_pdf(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar certificados.")
        return redirect('primaria')

    # ✅ Validar que el año escolar esté cerrado
    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    hoy = timezone.localdate()
    
    if config and (not config.fecha_fin or hoy <= config.fecha_fin):
        messages.error(request, "No se puede emitir el certificado porque el año escolar aún no ha culminado.")
        return redirect('primaria')

    estudiante = get_object_or_404(Estudiante, pk=pk)

    if estudiante.nivel != '6to_Grado':
        messages.error(request, "El Certificado de Educación Primaria solo aplica para estudiantes de 6to Grado.")
        return redirect('primaria')

    director = PersonalAdministrativo.objects.filter(
        cargo='Director', activo=True
    ).first()

    if not director:
        messages.error(
            request,
            "No se puede emitir el certificado porque no hay un Director "
            "activo registrado en el sistema. Registre o active un Director primero."
        )
        return redirect('primaria')

    centro_desarrollo_firmante = Firmante.objects.filter(
        tipo='centro_desarrollo', activo=True
    ).first()

    if not centro_desarrollo_firmante:
        messages.error(
            request,
            "No se puede emitir el certificado porque no hay un representante del "
            "Centro de Desarrollo de la Calidad Educativa Estadal registrado. "
            "Registre uno en la sección de Firmantes."
        )
        return redirect('primaria')

    director_nombres = f"{director.nombres} {director.apellidos}"
    director_cedula = f"{director.nacionalidad}-{director.cedula}"

    director_cdc_nombres = centro_desarrollo_firmante.nombre_completo
    director_cdc_cedula = centro_desarrollo_firmante.cedula_completa

    if estudiante.tipo_documento == 'identidad' and estudiante.cedula_identidad:
        cedula_estudiante = f"{estudiante.nacionalidad}-{estudiante.cedula_identidad}"
    else:
        cedula_estudiante = estudiante.cedula or '—'

    # Obtener el año escolar de la última configuración cerrada o activa
    config_para_pdf = ConfiguracionAnual.objects.filter(cerrado=True).order_by('-fecha_cierre').first()
    if not config_para_pdf:
        config_para_pdf = ConfiguracionAnual.objects.filter(activo=True).first()
    anio_escolar = config_para_pdf.anio_escolar if config_para_pdf else "2025 - 2026"

    # ✅ Obtener el literal desde la URL (A, B, C o D). Por defecto A.
    literal = request.GET.get('literal', 'A').strip().upper()
    if literal not in ['A', 'B', 'C', 'D']:
        literal = 'A'

    meses_texto = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    fecha_nac = estudiante.fecha_nacimiento
    fecha_nacimiento_texto = f"{fecha_nac.day} de {meses_texto[fecha_nac.month]} de {fecha_nac.year}"

    hoy = timezone.localdate()
    dia_expedicion = hoy.day
    mes_expedicion = meses_texto.get(hoy.month, '')
    anio_expedicion = hoy.year

    ahora = timezone.localtime(timezone.now())

    contexto = {
        'estudiante': estudiante,
        'director_nombres': director_nombres,
        'director_cedula': director_cedula,
        'director_cdc_nombres': director_cdc_nombres,
        'director_cdc_cedula': director_cdc_cedula,
        'cedula_estudiante': cedula_estudiante,
        'anio_escolar': anio_escolar,
        'literal': literal, # ✅ Pasamos el literal seleccionado
        'municipio': 'Junín',
        'parroquia': 'Bramón',
        'centro_desarrollo': 'Centro de Desarrollo de la Calidad Educativa Estadal',
        'municipio_nacimiento': estudiante.ciudad_nacimiento or '—',
        'estado_nacimiento': estudiante.estado_nacimiento or '—',
        'fecha_nacimiento': fecha_nacimiento_texto,
        'ciudad_expedicion': 'El Helechal',
        'dia_expedicion': dia_expedicion,
        'mes_expedicion': mes_expedicion,
        'anio_expedicion': anio_expedicion,
        'fecha': hoy,
        'hora': ahora.strftime('%I:%M %p'),
    }

    template = get_template('escuela/certificado_primaria.html')
    html = template.render(contexto)

    return generar_pdf_con_marca_personalizada(
        html,
        f"certificado_primaria_{estudiante.cedula or estudiante.pk}",
        marca_agua='img/logo.png',
        tamaño_marca=0.6,
        opacidad_marca=0.15,
        mostrar_en_navegador=True
    )
# ================================================================
# PDF CON MARCA DE AGUA PERSONALIZADA
# ================================================================
def generar_pdf_con_marca_personalizada(html_content, filename,
                                        marca_agua='img/logo.png',
                                        mostrar_en_navegador=True,
                                        tamaño_marca=0.6,
                                        opacidad_marca=0.3):
    try:
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_content.encode("utf-8")),
            dest=pdf_buffer,
            link_callback=link_callback
        )

        if pisa_status.err:
            return HttpResponse(f"Error al generar el PDF: {pisa_status.err}", status=500)

        pdf_buffer.seek(0)
        pdf_document = fitz.open(stream=pdf_buffer, filetype="pdf")

        if len(pdf_document) == 0:
            pdf_document.close()
            return HttpResponse(
                "Error: El PDF generado no contiene páginas. Revisa el template HTML.",
                status=500
            )

        primera_pagina = pdf_document[0]
        rect = primera_pagina.rect
        if rect is None or rect.width is None or rect.height is None or rect.width <= 0 or rect.height <= 0:
            pdf_document.close()
            return HttpResponse(
                "Error: El PDF generado tiene dimensiones inválidas. Revisa el template HTML.",
                status=500
            )

        marca_path = finders.find(marca_agua)
        if not marca_path:
            marca_path = os.path.join(settings.STATIC_ROOT or '', marca_agua)
            if not os.path.exists(marca_path):
                for static_dir in getattr(settings, 'STATICFILES_DIRS', []):
                    test_path = os.path.join(str(static_dir), marca_agua)
                    if os.path.exists(test_path):
                        marca_path = test_path
                        break

        if marca_path and os.path.exists(marca_path):
            try:
                img = Image.open(marca_path)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')

                try:
                    data = list(img.getdata())
                except (TypeError, NotImplementedError) as conv_err:
                    print(f"⚠️ Advertencia: No se pudo leer getdata(): {conv_err}")
                    data = None

                if data and all(isinstance(p, tuple) and len(p) == 4 for p in data):
                    new_data = [(r, g, b, int(a * opacidad_marca)) for r, g, b, a in data]
                    img.putdata(new_data)

                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format='PNG')
                    img_data = img_buffer.getvalue()

                    for pagina_num in range(len(pdf_document)):
                        pagina = pdf_document[pagina_num]
                        page_rect = pagina.rect
                        if page_rect is None or page_rect.width is None or page_rect.height is None:
                            continue

                        ancho_imagen = page_rect.width * tamaño_marca
                        alto_imagen = page_rect.height * tamaño_marca
                        x = (page_rect.width - ancho_imagen) / 2
                        y = (page_rect.height - alto_imagen) / 2
                        rect_imagen = fitz.Rect(x, y, x + ancho_imagen, y + alto_imagen)
                        pagina.insert_image(rect_imagen, stream=img_data, keep_proportion=True)
                else:
                    print("⚠️ Advertencia: El logo no se pudo procesar como RGBA. Se omite la marca de agua.")
            except Exception as img_err:
                print(f"⚠️ Advertencia: No se pudo aplicar la marca de agua: {img_err}")

        output_buffer = io.BytesIO()
        pdf_document.save(output_buffer)
        pdf_document.close()

        response = HttpResponse(output_buffer.getvalue(), content_type='application/pdf')
        if mostrar_en_navegador:
            response['Content-Disposition'] = f'inline; filename="{filename}.pdf"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return response

    except ImportError as e:
        return HttpResponse(f"Error: Falta una dependencia. Instala PyMuPDF y Pillow. {str(e)}", status=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Error al generar el PDF con marca de agua: {str(e)}", status=500)

# ================================================================
# AULA ANEXA — CONSTANCIA DE ESTUDIO (con validaciones y .title())
# ================================================================
@login_required
def constancia_estudio_anexa_pdf(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar constancias.")
        return redirect('dashboard_anexa')

    if request.method != 'POST':
        messages.error(request, "Método no permitido.")
        return redirect('dashboard_anexa')

    puede, motivo, config = _puede_emitir_constancias()
    if not puede:
        messages.error(request, motivo)
        return redirect('dashboard_anexa')

    # ✅ Limpieza y formateo de datos
    nombres = request.POST.get('nombres', '').strip().title()
    apellidos = request.POST.get('apellidos', '').strip().title()
    tipo_documento_raw = request.POST.get('tipo_documento', 'escolar').strip()
    nacionalidad = request.POST.get('nacionalidad', 'V').strip().upper() or 'V'

    # Limpiar cédulas: solo dígitos
    cedula_escolar = re.sub(r'\D', '', request.POST.get('cedula', ''))
    cedula_identidad = re.sub(r'\D', '', request.POST.get('cedula_identidad', ''))

    genero = request.POST.get('genero', 'M').strip()
    nivel = request.POST.get('nivel', '').strip()

    # Sección: 1 letra mayúscula
    seccion_raw = request.POST.get('seccion', 'A').strip().upper()
    seccion = seccion_raw[:1] if seccion_raw else 'A'

    # ✅ Validaciones backend
    if not nombres or len(nombres) < 2:
        messages.error(request, "El nombre debe tener al menos 2 caracteres.")
        return redirect('dashboard_anexa')

    if not apellidos or len(apellidos) < 2:
        messages.error(request, "El apellido debe tener al menos 2 caracteres.")
        return redirect('dashboard_anexa')

    if nacionalidad not in ('V', 'E'):
        nacionalidad = 'V'

    if genero not in ('M', 'F'):
        genero = 'M'

    if not nivel:
        messages.error(request, "Debe seleccionar el nivel o grado.")
        return redirect('dashboard_anexa')

    # ✅ Armar cédula según el tipo
    if tipo_documento_raw == 'identidad':
        if not cedula_identidad or len(cedula_identidad) < 5:
            messages.error(request, "La Cédula de Identidad debe tener al menos 5 dígitos.")
            return redirect('dashboard_anexa')
        tipo_documento_display = "Cédula de Identidad"
        cedula_estudiante = f"{nacionalidad}-{cedula_identidad}"
    else:
        if not cedula_escolar or len(cedula_escolar) < 5:
            messages.error(request, "La Cédula Escolar debe tener al menos 5 dígitos.")
            return redirect('dashboard_anexa')
        tipo_documento_display = "Cédula Escolar"
        cedula_estudiante = cedula_escolar

    anio_escolar = config.anio_escolar

    director_firmante = Firmante.objects.filter(
        tipo='director_anexa', activo=True
    ).first()

    if not director_firmante:
        messages.error(
            request,
            "No se puede emitir la constancia porque no hay un Director(a) "
            "del Aula Anexa registrado en el sistema. Regístrelo en la sección de Firmantes."
        )
        return redirect('dashboard_anexa')

    director_nombres = director_firmante.nombre_completo
    director_cedula = director_firmante.cedula_completa
    director_telefono = director_firmante.telefono or '—'

    articulo = "la" if genero == 'F' else "el"

    hoy = timezone.localdate()
    dia_expedicion = hoy.day
    mes_expedicion = MESES_TEXTO.get(hoy.month, '')
    anio_expedicion = hoy.year

    ahora = timezone.localtime(timezone.now())

    contexto = {
        'estudiante': {
            'nombres': nombres,
            'apellidos': apellidos,
        },
        'cedula_estudiante': cedula_estudiante,
        'tipo_documento_display': tipo_documento_display,
        'nivel_display': nivel,
        'seccion': seccion,
        'articulo': articulo,
        'anio_escolar': anio_escolar,
        'director_nombres': director_nombres,
        'director_cedula': director_cedula,
        'director_telefono': director_telefono,
        'dia_expedicion': dia_expedicion,
        'mes_expedicion': mes_expedicion,
        'anio_expedicion': anio_expedicion,
        'fecha': hoy,
        'hora': ahora.strftime('%I:%M %p'),
    }

    template = get_template('escuela/constancia_estudio_anexa_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(
        html,
        f"constancia_estudio_anexa_{cedula_estudiante}",
        mostrar_en_navegador=True
    )


# ================================================================
# AULA ANEXA — CONSTANCIA DE TRABAJO (con validaciones y .title())
# ================================================================
@login_required
def constancia_trabajo_anexa_pdf(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar constancias.")
        return redirect('dashboard_anexa')

    if request.method != 'POST':
        messages.error(request, "Método no permitido.")
        return redirect('dashboard_anexa')

    puede, motivo, _config = _puede_emitir_constancias()
    if not puede:
        messages.error(request, motivo)
        return redirect('dashboard_anexa')

    # ✅ Limpieza y formateo
    nombres = request.POST.get('nombres', '').strip().title()
    apellidos = request.POST.get('apellidos', '').strip().title()
    nacionalidad = request.POST.get('nacionalidad', 'V').strip().upper() or 'V'
    cedula = re.sub(r'\D', '', request.POST.get('cedula', ''))
    genero = request.POST.get('genero', 'M').strip()
    cargo = request.POST.get('cargo', '').strip().title()
    categoria_personal = request.POST.get('categoria_personal', '').strip()

    # ✅ Código de cargo: letras, números, guiones, guion bajo y espacios
    codigo_cargo = request.POST.get('codigo_cargo', '').strip().upper()
    codigo_cargo = re.sub(r'[^A-Z0-9\-_ ]', '', codigo_cargo)

    # ✅ Carga horaria: entero o decimal con . o ,
    carga_horaria_raw = request.POST.get('carga_horaria', '').strip()
    # Reemplazar coma por punto para normalizar
    carga_horaria_raw = carga_horaria_raw.replace(',', '.')
    # Dejar solo dígitos y un único punto
    carga_horaria_raw = re.sub(r'[^0-9.]', '', carga_horaria_raw)
    # Si hay más de un punto, quedarse solo con el primero
    if carga_horaria_raw.count('.') > 1:
        partes = carga_horaria_raw.split('.')
        carga_horaria_raw = partes[0] + '.' + ''.join(partes[1:])
    # Quitar punto final o inicial sueltos
    carga_horaria_raw = carga_horaria_raw.strip('.')

    # Formatear como entero si no tiene decimales, o con . si los tiene
    if carga_horaria_raw:
        if '.' in carga_horaria_raw:
            entero, decimales = carga_horaria_raw.split('.')
            entero = entero or '0'
            decimales = decimales or '0'
            carga_horaria = f"{entero}.{decimales}"
        else:
            carga_horaria = carga_horaria_raw
    else:
        carga_horaria = ''

    # ✅ Validaciones backend
    if not nombres or len(nombres) < 2:
        messages.error(request, "El nombre debe tener al menos 2 caracteres.")
        return redirect('dashboard_anexa')

    if not apellidos or len(apellidos) < 2:
        messages.error(request, "El apellido debe tener al menos 2 caracteres.")
        return redirect('dashboard_anexa')

    if nacionalidad not in ('V', 'E'):
        nacionalidad = 'V'

    if genero not in ('M', 'F'):
        genero = 'M'

    if not cedula or len(cedula) < 5:
        messages.error(request, "La cédula debe tener al menos 5 dígitos.")
        return redirect('dashboard_anexa')

    if not cargo or len(cargo) < 3:
        messages.error(request, "El cargo debe tener al menos 3 caracteres.")
        return redirect('dashboard_anexa')

    if categoria_personal not in ('DOCENTE', 'ADMINISTRATIVO', 'DE APOYO'):
        messages.error(request, "Categoría de personal no válida.")
        return redirect('dashboard_anexa')

    if not codigo_cargo or len(codigo_cargo) < 2:
        messages.error(request, "El código de cargo debe tener al menos 2 caracteres.")
        return redirect('dashboard_anexa')

    if not carga_horaria:
        messages.error(request, "La carga horaria es obligatoria.")
        return redirect('dashboard_anexa')

    director_firmante = Firmante.objects.filter(
        tipo='director_anexa', activo=True
    ).first()

    if not director_firmante:
        messages.error(
            request,
            "No se puede emitir la constancia porque no hay un Director(a) "
            "del Aula Anexa registrado en el sistema. Regístrelo en la sección de Firmantes."
        )
        return redirect('dashboard_anexa')

    director_nombres = director_firmante.nombre_completo
    director_cedula = director_firmante.cedula_completa
    director_telefono = director_firmante.telefono or '—'

    if genero == 'F':
        articulo = "la"
        ciudadano_o_ciudadana = "ciudadana"
    else:
        articulo = "el"
        ciudadano_o_ciudadana = "ciudadano"

    hoy = timezone.localdate()
    dia_expedicion = hoy.day
    mes_expedicion = MESES_TEXTO.get(hoy.month, '')
    anio_expedicion = hoy.year

    ahora = timezone.localtime(timezone.now())

    contexto = {
        'persona': {
            'nombres': nombres,
            'apellidos': apellidos,
            'nacionalidad': nacionalidad,
            'cedula': cedula,
            'genero': genero,
        },
        'categoria_personal': categoria_personal,
        'cargo_personal': cargo.upper(),
        'codigo_cargo': codigo_cargo,
        'carga_horaria': carga_horaria,
        'articulo': articulo,
        'ciudadano_o_ciudadana': ciudadano_o_ciudadana,
        'director_nombres': director_nombres,
        'director_cedula': director_cedula,
        'director_telefono': director_telefono,
        'dia_expedicion': dia_expedicion,
        'mes_expedicion': mes_expedicion,
        'anio_expedicion': anio_expedicion,
        'fecha': hoy,
        'hora': ahora.strftime('%I:%M %p'),
    }

    template = get_template('escuela/constancia_trabajo_anexa_pdf.html')
    html = template.render(contexto)
    return generar_pdf_con_marca(
        html,
        f"constancia_trabajo_anexa_{cedula}",
        mostrar_en_navegador=True
    )
# ================================================================
# ✅ NUEVA API: VERIFICAR SI EL AÑO ESCOLAR YA CULMINÓ
# ================================================================
@login_required
def verificar_cierre_anual_json(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    
    if not config:
        # No hay año activo (ya se cerró o no existe)
        return JsonResponse({'cerrado': True, 'mensaje': 'El año escolar ha finalizado.'})
    
    hoy = timezone.localdate()
    if config.fecha_fin and hoy > config.fecha_fin:
        # Ya pasó la fecha de fin
        return JsonResponse({'cerrado': True, 'mensaje': f'El año escolar {config.anio_escolar} finalizó el {config.fecha_fin.strftime("%d/%m/%Y")}.'})
    
    # Si está activo y no ha pasado la fecha de fin, NO está cerrado
    return JsonResponse({'cerrado': False, 'mensaje': 'El año escolar sigue en curso.'})

##4 funciones de egresos
# ================================================================
# HISTORIAL DE RETIROS Y EGRESOS — VISTAS
# ================================================================

@login_required
def historial_retiros_egresos(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para ver el historial.")
        return redirect('dashboard')
    return render(request, 'escuela/historial_retiros_egresos.html')


@login_required
def admin_historial_retiros_json(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    # Buscamos en el HistorialEstudiante los que tienen acción 'retirado'
    historial_qs = HistorialEstudiante.objects.filter(accion='retirado').order_by('-fecha_registro')

    datos = []
    for h in historial_qs:
        est = h.estudiante
        if not est:
            continue

        # Extraer el motivo de la observación (formato: "Motivo: [motivo] | Obs: [obs]")
        obs = h.observacion or ''
        motivo = obs.replace('Motivo: ', '').split(' | Obs:')[0]

        # Determinar cédula
        if est.tipo_documento == 'identidad' and est.cedula_identidad:
            cedula = f"{est.nacionalidad}-{est.cedula_identidad}"
        else:
            cedula = est.cedula or '—'

        datos.append({
            'id': h.pk, # ID del historial
            'estudiante_id': est.pk,
            'nombre_completo': f"{est.nombres} {est.apellidos}",
            'cedula': cedula,
            'nivel': est.get_nivel_display(),
            'anio_escolar': h.anio_escolar,
            'fecha_registro': h.fecha_registro.strftime('%d/%m/%Y %I:%M %p'),
            'motivo': motivo,
            'observacion': obs,
            'url_pdf': reverse('constancia_retiro_pdf', args=[est.pk]) + f"?motivo={motivo}&observacion={obs}",
        })

    return JsonResponse({'ok': True, 'retiros': datos})


@login_required
def admin_historial_egresados_json(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    egresados_qs = Egresado.objects.all().order_by('-fecha_registro')

    datos = []
    for e in egresados_qs:
        # Determinar cédula
        if e.cedula_identidad:
            cedula = f"V-{e.cedula_identidad}"
        else:
            cedula = e.cedula_escolar or '—'

        datos.append({
            'id': e.pk,
            'estudiante_id': e.estudiante.pk if e.estudiante else None,
            'nombre_completo': e.nombre_completo,
            'cedula': cedula,
            'nivel': e.nivel_egreso,
            'anio_escolar': e.anio_egreso,
            'fecha_registro': e.fecha_registro.strftime('%d/%m/%Y %I:%M %p'),
            'motivo': e.observacion or 'Egreso por culminación de 6to Grado',
            'url_pdf': reverse('certificado_primaria_pdf', args=[e.estudiante.pk]) + "?literal=A" if e.estudiante else '#',
        })

    return JsonResponse({'ok': True, 'egresados': datos})


@login_required
@require_POST
def eliminar_historial(request, tipo, pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    try:
        if tipo == 'retiro':
            historial = get_object_or_404(HistorialEstudiante, pk=pk, accion='retirado')
            estudiante = historial.estudiante
            
            # Al eliminar el historial, reactivamos al estudiante para que vuelva al listado general
            if estudiante:
                estudiante.activo = True
                estudiante.estado = 'activo'
                estudiante.save()
            
            historial.delete()
            return JsonResponse({'ok': True, 'mensaje': 'Registro de retiro eliminado. El estudiante vuelve a estar activo.'})

        elif tipo == 'egresado':
            egresado = get_object_or_404(Egresado, pk=pk)
            estudiante = egresado.estudiante
            
            # Al eliminar el egreso, el estudiante vuelve a estar en 6to Grado activo
            if estudiante:
                estudiante.activo = True
                estudiante.estado = 'activo'
                estudiante.nivel = '6to_Grado'
                estudiante.save()
            
            egresado.delete()
            return JsonResponse({'ok': True, 'mensaje': 'Registro de egreso eliminado. El estudiante vuelve a estar activo en 6to Grado.'})
            
        else:
            return JsonResponse({'ok': False, 'error': 'Tipo no válido'}, status=400)

    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

# ================================================================
# CONSTANCIA DE PROSECUCIÓN DE ESTUDIOS — PDF
# ================================================================
@login_required
def constancia_prosecucion_pdf(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar constancias.")
        return redirect('primaria')

    estudiante = get_object_or_404(Estudiante, pk=pk)

    # 1. Verificar que el año escolar esté cerrado
    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    hoy = timezone.localdate()
    
    if config and (not config.fecha_fin or hoy <= config.fecha_fin):
        messages.error(request, "No se puede emitir la constancia porque el año escolar aún no ha culminado.")
        return redirect('primaria')

    director = PersonalAdministrativo.objects.filter(cargo='Director', activo=True).first()
    if not director:
        messages.error(request, "No se puede emitir la constancia porque no hay un Director activo registrado.")
        return redirect('primaria')

    centro_desarrollo_firmante = Firmante.objects.filter(tipo='centro_desarrollo', activo=True).first()
    if not centro_desarrollo_firmante:
        messages.error(request, "No se puede emitir la constancia porque no hay un representante del Centro de Desarrollo registrado.")
        return redirect('primaria')

    # 2. Datos del Director y CDC
    director_nombres = f"{director.nombres} {director.apellidos}"
    director_cedula = f"{director.nacionalidad}-{director.cedula}"
    director_cdc_nombres = centro_desarrollo_firmante.nombre_completo
    director_cdc_cedula = centro_desarrollo_firmante.cedula_completa

    # 3. Datos del Año Escolar
    config_para_pdf = ConfiguracionAnual.objects.filter(cerrado=True).order_by('-fecha_cierre').first()
    if not config_para_pdf:
        config_para_pdf = ConfiguracionAnual.objects.filter(activo=True).first()
    anio_escolar = config_para_pdf.anio_escolar if config_para_pdf else "2025 - 2026"

    # 4. Determinar si es Inicial o Primaria
    es_inicial = estudiante.nivel in NIVELES_INICIAL
    nivel_display = estudiante.get_nivel_display()
    nivel_actual_display = nivel_display.upper()

    # Variables para el HTML
    if es_inicial:
        titulo_documento = "CONSTANCIA DE PROSECUCIÓN EN EL NIVEL DE EDUCACIÓN INICIAL"
        # Calcular el grupo (A, B, C) según el nivel actual
        # 1er_Nivel -> A, 2do_Nivel -> B, 3er_Nivel -> C
        mapa_grupos = {'1er_Nivel': 'A', '2do_Nivel': 'B', '3er_Nivel': 'C'}
        grupo_actual = mapa_grupos.get(estudiante.nivel, 'A')
        
        if grupo_actual == 'A':
            grupo_pasado = 'B'
        elif grupo_actual == 'B':
            grupo_pasado = 'C'
        else:
            grupo_pasado = 'C' # Fallback si ya está en 3ro, aunque debería pasar a 1er grado
            
        # Si es 3er nivel, el texto dirá "siendo promovido al 1er Grado de Educación Primaria"
        texto_promocion = f"siendo promovido al Grupo <strong>{grupo_pasado}</strong> del Nivel Educación Inicial"
        if grupo_actual == 'C':
            texto_promocion = "siendo promovido al <strong>Primer Grado de Educación Primaria</strong>"
            
        texto_cursa = f"cursó el Grupo <strong>{grupo_actual}</strong>"
    else:
        titulo_documento = "CONSTANCIA DE PROSECUCIÓN EN EL NIVEL DE EDUCACIÓN PRIMARIA"
        # Formatear el grado actual (ej: 1er_Grado -> PRIMER (1ER) GRADO)
        mapa_grados = {
            '1er_Grado': 'PRIMER (1ER)',
            '2do_Grado': 'SEGUNDO (2DO)',
            '3er_Grado': 'TERCERO (3RO)',
            '4to_Grado': 'CUARTO (4TO)',
            '5to_Grado': 'QUINTO (5TO)',
            '6to_Grado': 'SEXTO (6TO)'
        }
        grado_actual_texto = mapa_grados.get(estudiante.nivel, 'PRIMER (1ER)')
        
        # Calcular siguiente grado
        siguiente_nivel = SIGUIENTE_NIVEL.get(estudiante.nivel)
        if siguiente_nivel:
            grado_pasado_texto = mapa_grados.get(siguiente_nivel, 'SEGUNDO (2DO)')
            texto_promocion = f"siendo promovido al <strong>{grado_pasado_texto} GRADO</strong> de Educación Primaria"
        else:
            texto_promocion = "habiendo culminado el Nivel de Educación Primaria"
            
        texto_cursa = f"cursó el <strong>{grado_actual_texto} GRADO</strong>"

    # 5. Datos de Cédula
    if estudiante.tipo_documento == 'identidad' and estudiante.cedula_identidad:
        tipo_doc_str = "Cédula de Identidad"
        cedula_estudiante = f"{estudiante.nacionalidad}-{estudiante.cedula_identidad}"
    else:
        tipo_doc_str = "Cédula Escolar"
        cedula_estudiante = estudiante.cedula or '—'

    # 6. Fechas y lugares
    meses_texto = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    fecha_nac = estudiante.fecha_nacimiento
    fecha_nacimiento_texto = f"{fecha_nac.day} de {meses_texto[fecha_nac.month]} de {fecha_nac.year}"

    hoy = timezone.localdate()
    dia_expedicion = hoy.day
    mes_expedicion = meses_texto.get(hoy.month, '')
    anio_expedicion = hoy.year

    ahora = timezone.localtime(timezone.now())

    contexto = {
        'estudiante': estudiante,
        'titulo_documento': titulo_documento,
        'director_nombres': director_nombres,
        'director_cedula': director_cedula,
        'director_cdc_nombres': director_cdc_nombres,
        'director_cdc_cedula': director_cdc_cedula,
        'anio_escolar': anio_escolar,
        'cedula_estudiante': cedula_estudiante,
        'tipo_doc_str': tipo_doc_str,
        'nivel_actual_display': nivel_actual_display,
        'texto_cursa': texto_cursa,
        'texto_promocion': texto_promocion,
        'municipio': 'Junín',
        'parroquia': 'Bramón',
        'centro_desarrollo': 'Centro de Desarrollo de la Calidad Educativa Estadal',
        'municipio_nacimiento': estudiante.ciudad_nacimiento or '—',
        'estado_nacimiento': estudiante.estado_nacimiento or '—',
        'fecha_nacimiento': fecha_nacimiento_texto,
        'ciudad_expedicion': 'El Helechal',
        'dia_expedicion': dia_expedicion,
        'mes_expedicion': mes_expedicion,
        'anio_expedicion': anio_expedicion,
        'fecha': hoy,
        'hora': ahora.strftime('%I:%M %p'),
    }

    template = get_template('escuela/constancia_prosecucion_pdf.html')
    html = template.render(contexto)

    return generar_pdf_con_marca_personalizada(
        html,
        f"constancia_prosecucion_{estudiante.cedula or estudiante.pk}",
        marca_agua='img/logo.png',
        tamaño_marca=0.6,
        opacidad_marca=0.15,
        mostrar_en_navegador=True
    )
# ================================================================
# CONSTANCIA DE CUPO — PDF (Descarga automática)
# ================================================================
@login_required
def constancia_cupo_pdf(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para generar constancias.")
        return redirect('inicial')

    estudiante = get_object_or_404(Estudiante, pk=pk)

    # Director
    director = PersonalAdministrativo.objects.filter(cargo='Director', activo=True).first()
    if not director:
        messages.error(request, "No se puede emitir la constancia porque no hay un Director activo registrado.")
        return redirect('inicial')

    director_nombres = f"{director.nombres} {director.apellidos}"
    director_cedula = f"{director.nacionalidad}-{director.cedula}"

    # Año escolar
    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    anio_escolar = config.anio_escolar if config else "2025 - 2026"

    # Datos del estudiante para la constancia
    nivel_display = estudiante.get_nivel_display().upper()
    
    # Lugar de nacimiento
    ciudad_nacimiento = estudiante.ciudad_nacimiento or '—'
    estado_nacimiento = estudiante.estado_nacimiento or '—'

    if estudiante.tipo_documento == 'identidad' and estudiante.cedula_identidad:
        cedula_estudiante = f"{estudiante.nacionalidad}-{estudiante.cedula_identidad}"
    else:
        cedula_estudiante = estudiante.cedula or '—'

    # Representante
    rep_nombre_completo = f"{estudiante.rep_nombres} {estudiante.rep_apellidos}"
    rep_cedula_completa = f"{estudiante.rep_nacionalidad}-{estudiante.rep_cedula}" if estudiante.rep_cedula else '—'

    # Fecha de expedición
    hoy = timezone.localdate()
    meses_texto = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    dia_expedicion = hoy.day
    mes_expedicion = meses_texto.get(hoy.month, '')
    anio_expedicion = hoy.year

    ahora = timezone.localtime(timezone.now())

    contexto = {
        'estudiante': estudiante,
        'director_nombres': director_nombres,
        'director_cedula': director_cedula,
        'anio_escolar': anio_escolar,
        'cedula_estudiante': cedula_estudiante,
        'nivel_display': nivel_display,
        'ciudad_nacimiento': ciudad_nacimiento,
        'estado_nacimiento': estado_nacimiento,
        'rep_nombre_completo': rep_nombre_completo,
        'rep_cedula_completa': rep_cedula_completa,
        'dia_expedicion': dia_expedicion,
        'mes_expedicion': mes_expedicion,
        'anio_expedicion': anio_expedicion,
        'fecha': hoy,
        'hora': ahora.strftime('%I:%M %p'),
    }

    template = get_template('escuela/constancia_cupo_pdf.html')
    html = template.render(contexto)

    # ✅ Nombre del archivo: Constancia_Cupo_Nombre_Apellido.pdf
    nombre_archivo = f"Constancia_Cupo_{estudiante.nombres}_{estudiante.apellidos}".replace(" ", "_")

    return generar_pdf_con_marca(
        html,
        nombre_archivo,
        mostrar_en_navegador=False  # ✅ FORZAR DESCARGA
    )
# ================================================================
# INSCRIPCIÓN / CIERRE DE AÑO ESCOLAR (NUEVA VISTA)
# ================================================================
@login_required
def inscripcion_escolar(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para gestionar la inscripción escolar.")
        return redirect('dashboard')
    
    # Obtener el año escolar activo
    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    
    contexto = {
        'config': config,
        'anio_escolar': config.anio_escolar if config else 'No configurado',
        'puede_cerrar': False
    }
    
    if config and config.fecha_fin:
        hoy = timezone.localdate()
        contexto['puede_cerrar'] = hoy >= config.fecha_fin
        
    return render(request, 'escuela/inscripcion_escolar.html', contexto)


@login_required
def admin_inscripcion_json(request):
    """Devuelve la lista de estudiantes activos para el proceso de inscripción."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    config = ConfiguracionAnual.objects.filter(activo=True, cerrado=False).first()
    if not config:
        return JsonResponse({
            'ok': False,
            'error': 'No hay un Año Escolar activo configurado. Debe configurarlo en el Calendario Escolar.'
        }, status=400)

    estudiantes = Estudiante.objects.filter(
        activo=True
    ).exclude(
        estado='egresado'
    ).order_by('nivel', 'apellidos', 'nombres')

    datos = []
    for e in estudiantes:
        siguiente = SIGUIENTE_NIVEL.get(e.nivel)
        siguiente_display = dict(Estudiante.NIVEL_CHOICES).get(siguiente, '') if siguiente else '🎓 Egresado'

        datos.append({
            'id': e.pk,
            'nombres': e.nombres,
            'apellidos': e.apellidos,
            'cedula': e.cedula_activa,
            'nivel': e.nivel,
            'nivel_display': e.get_nivel_display(),
            'siguiente_nivel': siguiente or '',
            'siguiente_nivel_display': siguiente_display,
        })

    return JsonResponse({
        'ok': True,
        'estudiantes': datos,
        'anio_escolar': config.anio_escolar,
    })

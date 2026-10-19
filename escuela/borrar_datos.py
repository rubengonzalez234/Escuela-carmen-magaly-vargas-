# borrar_datos.py
# ============================================================
# SCRIPT DE LIMPIEZA DE DATOS DE PRUEBA
# ============================================================
# Uso desde la terminal (en la carpeta donde está manage.py):
#   python borrar_datos.py
#
# OJO: Se debe ejecutar con el entorno virtual activado (si aplica)
# ============================================================

import os
import sys
import django

# ---------- CONFIGURACIÓN DE DJANGO ----------
# ⚠️ Cambia 'cen_jesus_redentor.settings' si tu carpeta de settings tiene otro nombre.
# Según tus capturas anteriores, la carpeta de configuración se llama 'cen_jesus_redentor'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cen_jesus_redentor.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error al inicializar Django: {e}")
    print("   Verifica que DJANGO_SETTINGS_MODULE esté bien configurado.")
    sys.exit(1)


# ---------- IMPORTAR MODELOS ----------
try:
    from escuela.models import (
        AsistenciaPersonal,
        Feriado,
        ConfiguracionAnual,
        PeriodoVacaciones,
    )
except ImportError as e:
    print(f"❌ Error al importar modelos: {e}")
    print("   Verifica que la app 'escuela' exista y los modelos estén definidos.")
    sys.exit(1)


# ---------- FUNCIONES DE LIMPIEZA ----------
def limpiar_asistencias():
    total = AsistenciaPersonal.objects.count()
    AsistenciaPersonal.objects.all().delete()
    return total


def limpiar_feriados():
    total = Feriado.objects.count()
    Feriado.objects.all().delete()
    return total


def limpiar_vacaciones():
    total = PeriodoVacaciones.objects.count()
    PeriodoVacaciones.objects.all().delete()
    return total


def limpiar_configuracion():
    total = ConfiguracionAnual.objects.count()
    ConfiguracionAnual.objects.all().delete()
    return total


# ---------- MAIN ----------
def main():
    print("=" * 60)
    print("🧹 LIMPIEZA DE DATOS DE PRUEBA")
    print("=" * 60)
    print()
    print("⚠️  Este script borrará:")
    print("    • Asistencias del personal")
    print("    • Feriados y eventos del calendario")
    print("    • Vacaciones registradas")
    print("    • Configuración anual (inicio/fin de año)")
    print()

    respuesta = input("¿Estás seguro? Escribe 'SI' para continuar: ").strip().upper()
    if respuesta != 'SI':
        print("❌ Cancelado.")
        return

    print()
    print("Borrando datos...")

    n_asist = limpiar_asistencias()
    print(f"   🗑️  Asistencias eliminadas: {n_asist}")

    n_fer = limpiar_feriados()
    print(f"   🗑️  Feriados/Eventos eliminados: {n_fer}")

    n_vac = limpiar_vacaciones()
    print(f"   🗑️  Vacaciones eliminadas: {n_vac}")

    n_cfg = limpiar_configuracion()
    print(f"   🗑️  Configuraciones anuales eliminadas: {n_cfg}")

    print()
    print("=" * 60)
    print("✅ LIMPIEZA COMPLETADA")
    print("=" * 60)


if __name__ == '__main__':
    main()

from django.db import models
from django.contrib.auth.models import User


# ================================================================
# ESTUDIANTES
# ================================================================
class Estudiante(models.Model):
    NIVEL_CHOICES = [
        ('1er_Nivel', 'Primer Nivel'),
        ('2do_Nivel', 'Segundo Nivel'),
        ('3er_Nivel', 'Tercer Nivel'),
        ('1er_Grado', 'Primer Grado'),
        ('2do_Grado', 'Segundo Grado'),
        ('3er_Grado', 'Tercer Grado'),
        ('4to_Grado', 'Cuarto Grado'),
        ('5to_Grado', 'Quinto Grado'),
        ('6to_Grado', 'Sexto Grado'),
    ]
    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]
    PARENTESCO_CHOICES = [
        ('Madre', 'Madre'),
        ('Padre', 'Padre'),
        ('Abuelo/a', 'Abuelo/a'),
        ('Tío/a', 'Tío/a'),
        ('Hermano/a', 'Hermano/a'),
        ('Tutor Legal', 'Tutor Legal'),
        ('Otro', 'Otro'),
    ]
    TIPO_DOCUMENTO_CHOICES = [
        ('escolar', 'Cédula Escolar'),
        ('identidad', 'Cédula de Identidad'),
    ]
    NACIONALIDAD_CHOICES = [
        ('V', 'Venezolano/a (V)'),
        ('E', 'Extranjero/a (E)'),
    ]
    PAIS_CHOICES = [
        ('Venezuela', 'Venezuela'),
        ('Colombia', 'Colombia'),
    ]
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('egresado', 'Egresado'),
        ('retirado', 'Retirado'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.CharField(
        max_length=20, unique=True, blank=True, null=True,
        verbose_name="Cédula Escolar"
    )
    cedula_identidad = models.CharField(
        max_length=20, unique=True, blank=True, null=True,
        verbose_name="Cédula de Identidad"
    )
    nacionalidad = models.CharField(
        max_length=1,
        choices=NACIONALIDAD_CHOICES,
        default='V',
        verbose_name="Nacionalidad"
    )
    tipo_documento = models.CharField(
        max_length=20,
        choices=TIPO_DOCUMENTO_CHOICES,
        default='escolar',
        verbose_name="Tipo de Documento"
    )
    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=10, choices=GENERO_CHOICES)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='1er_Nivel')
    direccion = models.TextField(blank=True)

    pais_nacimiento = models.CharField(
        max_length=50, choices=PAIS_CHOICES, default='Venezuela',
        verbose_name="País de Nacimiento"
    )
    estado_nacimiento = models.CharField(
        max_length=100, blank=True,
        verbose_name="Estado / Departamento de Nacimiento"
    )
    ciudad_nacimiento = models.CharField(
        max_length=100, blank=True,
        verbose_name="Ciudad / Municipio de Nacimiento"
    )

    fecha_inscripcion = models.DateField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo',
        verbose_name="Estado"
    )

    rep_nombres = models.CharField(max_length=100)
    rep_apellidos = models.CharField(max_length=100)
    rep_cedula = models.CharField(max_length=20)
    rep_nacionalidad = models.CharField(
        max_length=1,
        choices=NACIONALIDAD_CHOICES,
        default='V',
        verbose_name="Nacionalidad del Representante"
    )
    rep_parentesco = models.CharField(max_length=20, choices=PARENTESCO_CHOICES, default='Madre')
    
    # ✅ CAMBIO: Teléfono del representante es OPCIONAL a nivel de base de datos
    rep_telefono = models.CharField(max_length=15, null=True, blank=True)
    
    rep_email = models.EmailField(blank=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    @property
    def edad(self):
        from datetime import date
        hoy = date.today()
        return hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )

    @property
    def primer_nombre(self):
        return self.nombres.split()[0] if self.nombres else ''

    @property
    def primer_apellido(self):
        return self.apellidos.split()[0] if self.apellidos else ''

    @property
    def nombre_corto(self):
        return f"{self.primer_nombre} {self.primer_apellido}".strip()

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    @property
    def rep_primer_nombre(self):
        return self.rep_nombres.split()[0] if self.rep_nombres else ''

    @property
    def rep_primer_apellido(self):
        return self.rep_apellidos.split()[0] if self.rep_apellidos else ''

    @property
    def rep_nombre_corto(self):
        return f"{self.rep_primer_nombre} {self.rep_primer_apellido}".strip()

    @property
    def cedula_activa(self):
        if self.tipo_documento == 'identidad' and self.cedula_identidad:
            return f"{self.nacionalidad}-{self.cedula_identidad}"
        return self.cedula or '—'

    @property
    def lugar_nacimiento_completo(self):
        partes = []
        if self.ciudad_nacimiento:
            partes.append(self.ciudad_nacimiento)
        if self.estado_nacimiento:
            partes.append(self.estado_nacimiento)
        if self.pais_nacimiento:
            partes.append(self.pais_nacimiento)
        return ', '.join(partes) if partes else '—'

    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"


# ================================================================
# PERSONAL — Clase base abstracta
# ================================================================
class PersonaBase(models.Model):
    NACIONALIDAD_CHOICES = [
        ('V', 'Venezolano/a (V)'),
        ('E', 'Extranjero/a (E)'),
    ]
    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.CharField(max_length=20, unique=True)
    nacionalidad = models.CharField(
        max_length=1,
        choices=NACIONALIDAD_CHOICES,
        default='V',
        verbose_name="Nacionalidad"
    )
    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=10, choices=GENERO_CHOICES)
    telefono = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    fecha_ingreso = models.DateField(
        verbose_name="Fecha de Ingreso a la Institución",
        help_text="Fecha en que ingresó a la institución"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    @property
    def edad(self):
        from datetime import date
        hoy = date.today()
        return hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )

    @property
    def primer_nombre(self):
        return self.nombres.split()[0] if self.nombres else ''

    @property
    def primer_apellido(self):
        return self.apellidos.split()[0] if self.apellidos else ''

    @property
    def nombre_corto(self):
        return f"{self.primer_nombre} {self.primer_apellido}".strip()

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    @property
    def cedula_completa(self):
        nacionalidad = self.nacionalidad or 'V'
        return f"{nacionalidad}-{self.cedula}"


# ================================================================
# DOCENTES
# ================================================================
class Docente(PersonaBase):
    NIVEL_GRADO_CHOICES = [
        ('1er Nivel', 'Primer Nivel'),
        ('2do Nivel', 'Segundo Nivel'),
        ('3er Nivel', 'Tercer Nivel'),
        ('1er Grado', 'Primer Grado'),
        ('2do Grado', 'Segundo Grado'),
        ('3er Grado', 'Tercer Grado'),
        ('4to Grado', 'Cuarto Grado'),
        ('5to Grado', 'Quinto Grado'),
        ('6to Grado', 'Sexto Grado'),
    ]
    nivel_grado = models.CharField(
        max_length=100,
        choices=NIVEL_GRADO_CHOICES,
        unique=True,
        verbose_name="Nivel / Grado",
        help_text="Solo un docente por nivel/grado"
    )
    especialidad = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Docente"
        verbose_name_plural = "Docentes"


# ================================================================
# PERSONAL ADMINISTRATIVO
# ================================================================
class PersonalAdministrativo(PersonaBase):
    CARGO_CHOICES = [
        ('Director', 'Director'),
        ('Subdirector', 'Subdirector'),
        ('Coordinador', 'Coordinador'),
        ('Secretaria', 'Secretaria'),
        ('Administrador', 'Administrador'),
        ('Contador', 'Contador'),
        ('Otro', 'Otro'),
    ]
    cargo = models.CharField(
        max_length=100,
        choices=CARGO_CHOICES,
        unique=True,
        verbose_name="Cargo",
        help_text="Solo un registro por cargo (excepto 'Otro')"
    )
    cargo_detalle = models.CharField(
        max_length=100, blank=True,
        verbose_name="Especifique el cargo",
        help_text="Solo si seleccionó 'Otro'"
    )

    class Meta:
        verbose_name = "Personal Administrativo"
        verbose_name_plural = "Personal Administrativo"


# ================================================================
# PERSONAL DE APOYO
# ================================================================
class PersonalApoyo(PersonaBase):
    CARGO_CHOICES = [
        ('Vigilante', 'Vigilante'),
        ('Obrero', 'Obrero'),
        ('Aseadora', 'Aseadora'),
        ('Madre Elaboradora', 'Madre Elaboradora'),
        ('Mantenimiento', 'Mantenimiento'),
        ('Otro', 'Otro'),
    ]
    cargo = models.CharField(
        max_length=100,
        choices=CARGO_CHOICES,
        default='Obrero',
        verbose_name="Cargo"
    )
    cargo_detalle = models.CharField(
        max_length=100, blank=True,
        verbose_name="Especifique el cargo",
        help_text="Solo si seleccionó 'Otro'"
    )

    class Meta:
        verbose_name = "Personal de Apoyo"
        verbose_name_plural = "Personal de Apoyo"


# ================================================================
# PERSONAL DE COCINA
# ================================================================
class PersonalCocina(PersonaBase):
    CARGO_CHOICES = [
        ('Cocinero(a)', 'Cocinero(a)'),
    ]
    cargo = models.CharField(
        max_length=100,
        choices=CARGO_CHOICES,
        default='Cocinero(a)',
        verbose_name="Cargo"
    )

    class Meta:
        verbose_name = "Personal de Cocina"
        verbose_name_plural = "Personal de Cocina"


# ================================================================
# ASISTENCIA DE PERSONAL
# ================================================================
class AsistenciaPersonal(models.Model):
    TIPO_PERSONAL_CHOICES = [
        ('Docente', 'Docente'),
        ('Administrativo', 'Administrativo'),
        ('Apoyo', 'Personal de Apoyo'),
        ('Cocina', 'Personal de Cocina'),
    ]

    tipo_personal = models.CharField(max_length=20, choices=TIPO_PERSONAL_CHOICES)
    personal_id = models.PositiveIntegerField(verbose_name="ID del Personal")
    fecha = models.DateField()
    presente = models.BooleanField(default=True)
    observacion = models.CharField(max_length=200, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo_personal} #{self.personal_id} - {self.fecha}"

    class Meta:
        verbose_name = "Asistencia de Personal"
        verbose_name_plural = "Asistencias de Personal"
        unique_together = ('tipo_personal', 'personal_id', 'fecha')
        ordering = ['-fecha']


# ================================================================
# MATERIAS, CALIFICACIONES, ASISTENCIAS DE ESTUDIANTES
# ================================================================
class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.TextField(blank=True)
    docente = models.ForeignKey(Docente, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Materia"
        verbose_name_plural = "Materias"


class Calificacion(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    nota = models.DecimalField(max_digits=4, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    periodo = models.CharField(max_length=20, choices=[
        ('1er_Lapso', '1er Lapso'),
        ('2do_Lapso', '2do Lapso'),
        ('3er_Lapso', '3er Lapso'),
        ('Final', 'Final'),
    ])

    def __str__(self):
        return f"{self.estudiante} - {self.materia}: {self.nota}"

    class Meta:
        verbose_name = "Calificación"
        verbose_name_plural = "Calificaciones"
        unique_together = ('estudiante', 'materia', 'periodo')


class Asistencia(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    presente = models.BooleanField(default=True)
    justificacion = models.TextField(blank=True)

    def __str__(self):
        return f"{self.estudiante} - {self.fecha} - {'Presente' if self.presente else 'Ausente'}"

    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        unique_together = ('estudiante', 'fecha')


# ================================================================
# CONFIGURACIÓN ANUAL DEL AÑO ESCOLAR
# ================================================================
class ConfiguracionAnual(models.Model):
    anio_escolar = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Año Escolar",
        help_text="Ej: 2025-2026 (se genera automáticamente)"
    )
    fecha_inicio = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha de Inicio de Año Escolar"
    )
    fecha_fin = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha de Fin de Año Escolar"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    cerrado = models.BooleanField(
        default=False,
        verbose_name="Cerrado",
        help_text="Indica si ya se aplicó el cierre anual de este año escolar"
    )
    fecha_cierre = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de Cierre"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.anio_escolar

    @property
    def anio_inicio(self):
        try:
            return int(self.anio_escolar.split('-')[0])
        except (ValueError, IndexError):
            return None

    @property
    def anio_fin(self):
        try:
            return int(self.anio_escolar.split('-')[1])
        except (ValueError, IndexError):
            return None

    class Meta:
        verbose_name = "Configuración Anual"
        verbose_name_plural = "Configuraciones Anuales"
        ordering = ['-anio_escolar']


# ================================================================
# CALENDARIO ESCOLAR — Feriados y Eventos Especiales
# ================================================================
class Feriado(models.Model):
    TIPO_EVENTO_CHOICES = [
        ('feriado', 'Feriado'),
        ('eventos', 'Evento Especial'),
    ]

    configuracion = models.ForeignKey(
        ConfiguracionAnual,
        on_delete=models.CASCADE,
        related_name='feriados',
        null=True, blank=True,
        verbose_name="Año Escolar"
    )
    fecha = models.DateField(verbose_name="Fecha del Evento")
    tipo_evento = models.CharField(
        max_length=20,
        choices=TIPO_EVENTO_CHOICES,
        default='feriado',
        verbose_name="Tipo de Evento"
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Descripción",
        help_text="Detalle opcional del evento (ej: 'Día de la Independencia')"
    )
    recurrente = models.BooleanField(
        default=True,
        verbose_name="Recurrente",
        help_text="Si es True, se copiará automáticamente al siguiente año escolar"
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Registro"
    )

    def __str__(self):
        return f"{self.fecha} - {self.get_tipo_evento_display()}"

    class Meta:
        verbose_name = "Feriado / Evento Especial"
        verbose_name_plural = "Feriados y Eventos Especiales"
        ordering = ['fecha']


# ================================================================
# PERÍODOS DE VACACIONES
# ================================================================
class PeriodoVacaciones(models.Model):
    configuracion = models.ForeignKey(
        ConfiguracionAnual,
        on_delete=models.CASCADE,
        related_name='vacaciones',
        verbose_name="Configuración Anual"
    )
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin")
    descripcion = models.CharField(
        max_length=200,
        verbose_name="Descripción",
        help_text="Ej: Vacaciones de Navidad, Carnaval, Semana Santa..."
    )
    recurrente = models.BooleanField(
        default=True,
        verbose_name="Recurrente",
        help_text="Si es True, se copiará automáticamente al siguiente año escolar"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.descripcion} ({self.fecha_inicio} - {self.fecha_fin})"

    class Meta:
        verbose_name = "Período de Vacaciones"
        verbose_name_plural = "Períodos de Vacaciones"
        ordering = ['fecha_inicio']


# ================================================================
# HISTORIAL DE ESTUDIANTES (transiciones por año escolar)
# ================================================================
class HistorialEstudiante(models.Model):
    ACCION_CHOICES = [
        ('inscrito', 'Inscrito'),
        ('repitiente', 'Repitiente'),
        ('retirado', 'Retirado'),
        ('egresado', 'Egresado'),
    ]

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='historial',
        verbose_name="Estudiante"
    )
    anio_escolar = models.CharField(
        max_length=20,
        verbose_name="Año Escolar"
    )
    nivel_anterior = models.CharField(max_length=20, blank=True, verbose_name="Nivel Anterior")
    nivel_nuevo = models.CharField(max_length=20, blank=True, verbose_name="Nivel Nuevo")
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES, verbose_name="Acción")
    observacion = models.CharField(max_length=300, blank=True, verbose_name="Observación")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.estudiante} - {self.accion} ({self.anio_escolar})"

    class Meta:
        verbose_name = "Historial de Estudiante"
        verbose_name_plural = "Historial de Estudiantes"
        ordering = ['-fecha_registro']


# ================================================================
# EGRESADOS
# ================================================================
class Egresado(models.Model):
    estudiante = models.OneToOneField(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='egresado',
        verbose_name="Estudiante"
    )
    anio_egreso = models.CharField(
        max_length=20,
        verbose_name="Año Escolar de Egreso"
    )
    cedula_escolar = models.CharField(max_length=20, blank=True, verbose_name="Cédula Escolar")
    cedula_identidad = models.CharField(max_length=20, blank=True, verbose_name="Cédula de Identidad")
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    genero = models.CharField(max_length=10)
    fecha_nacimiento = models.DateField()
    nivel_egreso = models.CharField(max_length=30, default='6to Grado')
    observacion = models.CharField(max_length=300, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.anio_egreso})"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    class Meta:
        verbose_name = "Egresado"
        verbose_name_plural = "Egresados"
        ordering = ['-anio_egreso', 'apellidos', 'nombres']


# ================================================================
# FIRMANTES (Director Aula Anexa y Centro de Desarrollo)
# ================================================================
class Firmante(models.Model):
    TIPO_FIRMANTE_CHOICES = [
        ('director_anexa', 'Director(a) Aula Anexa Juan Pablo Rojas Paul'),
        ('centro_desarrollo', 'Centro de Desarrollo de la Calidad Educativa Estadal'),
    ]

    tipo = models.CharField(
        max_length=30,
        choices=TIPO_FIRMANTE_CHOICES,
        verbose_name="Tipo de Firmante"
    )
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    cedula = models.CharField(
        max_length=20, blank=True, null=True,
        verbose_name="Cédula de Identidad",
        help_text="Opcional para el Director del Aula Anexa"
    )
    telefono = models.CharField(
        max_length=20, blank=True, null=True,
        verbose_name="Número Telefónico",
        help_text="Opcional para el Centro de Desarrollo"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombres} {self.apellidos}"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    @property
    def cedula_completa(self):
        if self.cedula:
            return f"V-{self.cedula}"
        return "—"

    class Meta:
        verbose_name = "Firmante"
        verbose_name_plural = "Firmantes"
        ordering = ['tipo', 'apellidos', 'nombres']

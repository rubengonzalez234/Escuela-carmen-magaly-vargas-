import re
from datetime import date
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Estudiante,
    Docente,
    PersonalAdministrativo,
    PersonalApoyo,
    PersonalCocina,
)


# ================================================================
# FORMULARIO DE ESTUDIANTE
# ================================================================
class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = [
            'nombres', 'apellidos', 'cedula', 'fecha_nacimiento',
            'genero', 'nivel', 'direccion',
            'nacionalidad',
            'rep_nombres', 'rep_apellidos', 'rep_cedula', 'rep_nacionalidad',
            'rep_parentesco', 'rep_telefono', 'rep_email',
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres del estudiante', 'autocomplete': 'off'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos del estudiante', 'autocomplete': 'off'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12345678', 'autocomplete': 'off'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dirección de habitación'}),
            'nacionalidad': forms.Select(attrs={'class': 'form-select'}),
            'rep_nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres del representante', 'autocomplete': 'off'}),
            'rep_apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos del representante', 'autocomplete': 'off'}),
            'rep_cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12345678', 'autocomplete': 'off'}),
            'rep_nacionalidad': forms.Select(attrs={'class': 'form-select'}),
            'rep_parentesco': forms.Select(attrs={'class': 'form-select'}),
            'rep_telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 04141234567', 'autocomplete': 'off'}),
            'rep_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com (opcional)', 'autocomplete': 'off'}),
        }
        labels = {
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'cedula': 'Cédula Escolar',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'genero': 'Género',
            'nivel': 'Nivel Educativo',
            'direccion': 'Dirección',
            'nacionalidad': 'Nacionalidad',
            'rep_nombres': 'Nombres',
            'rep_apellidos': 'Apellidos',
            'rep_cedula': 'Cédula',
            'rep_nacionalidad': 'Nacionalidad',
            'rep_parentesco': 'Parentesco',
            'rep_telefono': 'Teléfono',
            'rep_email': 'Correo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Hacer que cedula y cedula_identidad NO sean obligatorios a nivel de formulario.
        # La validación real se hace en la vista según el tipo_documento.
        self.fields['cedula'].required = False
        
        for field_name in ['genero', 'nivel', 'rep_parentesco', 'nacionalidad', 'rep_nacionalidad']:
            if field_name in self.fields:
                opciones = list(self.fields[field_name].choices)
                opciones_filtradas = [op for op in opciones if op[0] != '']
                self.fields[field_name].choices = [('', 'Seleccione')] + opciones_filtradas

    REGEX_SOLO_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s'.-]+$")
    REGEX_SOLO_NUMEROS = re.compile(r"^\d+$")
    REGEX_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    def _validar_nombre(self, valor, etiqueta):
        valor = (valor or '').strip()
        if not valor:
            raise ValidationError(f"El campo '{etiqueta}' es obligatorio.")
        if not self.REGEX_SOLO_LETRAS.match(valor):
            raise ValidationError(f"El campo '{etiqueta}' solo puede contener letras y espacios.")
        if len(valor) < 2:
            raise ValidationError(f"El campo '{etiqueta}' es demasiado corto.")
        return valor.title()

    def _validar_cedula(self, valor, etiqueta, minimo=6, maximo=10):
        valor = (valor or '').strip()
        if not valor:
            raise ValidationError(f"El campo '{etiqueta}' es obligatorio.")
        if not self.REGEX_SOLO_NUMEROS.match(valor):
            raise ValidationError(f"El campo '{etiqueta}' solo puede contener números.")
        if not (minimo <= len(valor) <= maximo):
            raise ValidationError(f"El campo '{etiqueta}' debe tener entre {minimo} y {maximo} dígitos.")
        return valor

    def _validar_telefono(self, valor, etiqueta, obligatorio=False):
        valor = (valor or '').strip()
        if not valor:
            if obligatorio:
                raise ValidationError(f"El campo '{etiqueta}' es obligatorio.")
            return ''
        if not self.REGEX_SOLO_NUMEROS.match(valor):
            raise ValidationError(f"El campo '{etiqueta}' solo puede contener números.")
        if not (10 <= len(valor) <= 11):
            raise ValidationError(f"El campo '{etiqueta}' debe tener entre 10 y 11 dígitos.")
        return valor

    def _validar_email(self, valor, etiqueta, obligatorio=False):
        valor = (valor or '').strip()
        if not valor:
            if obligatorio:
                raise ValidationError(f"El campo '{etiqueta}' es obligatorio.")
            return ''
        if not self.REGEX_EMAIL.match(valor):
            raise ValidationError(f"El campo '{etiqueta}' no tiene un formato válido.")
        return valor.lower()

    def clean_nombres(self):
        return self._validar_nombre(self.cleaned_data.get('nombres'), 'Nombres')

    def clean_apellidos(self):
        return self._validar_nombre(self.cleaned_data.get('apellidos'), 'Apellidos')

    def clean_cedula(self):
        """
        ✅ CORREGIDO: Si el campo está vacío, devolvemos None/'' sin lanzar error.
        La vista se encargará de validar si es requerido según el tipo_documento.
        """
        cedula = (self.cleaned_data.get('cedula') or '').strip()
        
        if not cedula:
            return ''  # No lanzar error aquí. La vista lo maneja.
        
        # Validar formato si viene con datos
        if not self.REGEX_SOLO_NUMEROS.match(cedula):
            raise ValidationError("La Cédula Escolar solo puede contener números.")
        if not (6 <= len(cedula) <= 10):
            raise ValidationError("La Cédula Escolar debe tener entre 6 y 10 dígitos.")
        
        # Validar duplicados
        qs = Estudiante.objects.filter(cedula=cedula)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un estudiante con esta Cédula Escolar.")
        
        return cedula

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if not fecha:
            raise ValidationError("La fecha de nacimiento es obligatoria.")
        if fecha > date.today():
            raise ValidationError("La fecha de nacimiento no puede ser en el futuro.")
        hoy = date.today()
        edad = hoy.year - fecha.year - (
            (hoy.month, hoy.day) < (fecha.month, fecha.day)
        )
        if edad < 2:
            raise ValidationError("El estudiante debe tener al menos 2 años cumplidos.")
        if edad > 13:
            raise ValidationError("El estudiante no puede tener más de 13 años.")
        return fecha

    def clean_direccion(self):
        direccion = (self.cleaned_data.get('direccion') or '').strip()
        if not direccion:
            raise ValidationError("La dirección es obligatoria.")
        if len(direccion) < 5:
            raise ValidationError("La dirección es demasiado corta.")
        return direccion

    def clean_rep_nombres(self):
        return self._validar_nombre(self.cleaned_data.get('rep_nombres'), 'Nombres')

    def clean_rep_apellidos(self):
        return self._validar_nombre(self.cleaned_data.get('rep_apellidos'), 'Apellidos')

    def clean_rep_cedula(self):
        return self._validar_cedula(self.cleaned_data.get('rep_cedula'), 'Cédula')

    def clean_rep_telefono(self):
        return self._validar_telefono(self.cleaned_data.get('rep_telefono'), 'Teléfono', obligatorio=True)

    def clean_rep_email(self):
        return self._validar_email(self.cleaned_data.get('rep_email'), 'Correo', obligatorio=False)


# ================================================================
# PERSONAL — Clase base compartida
# ================================================================
NIVEL_GRADO_CHOICES = [
    ('', 'Seleccione'),
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


class _PersonalBaseForm(forms.ModelForm):
    REGEX_SOLO_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s'.-]+$")
    REGEX_SOLO_NUMEROS = re.compile(r"^\d+$")
    REGEX_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['genero', 'cargo', 'nivel_grado', 'nacionalidad']:
            if field_name in self.fields:
                opciones = list(self.fields[field_name].choices)
                opciones_filtradas = [op for op in opciones if op[0] != '']
                self.fields[field_name].choices = [('', 'Seleccione')] + opciones_filtradas

    def _validar_nombre(self, valor, etiqueta):
        valor = (valor or '').strip()
        if not valor:
            raise ValidationError(f"El campo '{etiqueta}' es obligatorio.")
        if not self.REGEX_SOLO_LETRAS.match(valor):
            raise ValidationError(f"El campo '{etiqueta}' solo puede contener letras y espacios.")
        if len(valor) < 2:
            raise ValidationError(f"El campo '{etiqueta}' es demasiado corto.")
        return valor.title()

    def _validar_cedula(self, valor, etiqueta):
        valor = (valor or '').strip()
        if not valor:
            raise ValidationError(f"El campo '{etiqueta}' es obligatorio.")
        if not self.REGEX_SOLO_NUMEROS.match(valor):
            raise ValidationError(f"El campo '{etiqueta}' solo puede contener números.")
        if not (6 <= len(valor) <= 10):
            raise ValidationError(f"El campo '{etiqueta}' debe tener entre 6 y 10 dígitos.")
        return valor

    def _validar_telefono(self, valor, etiqueta):
        valor = (valor or '').strip()
        if not valor:
            return ''
        if not self.REGEX_SOLO_NUMEROS.match(valor):
            raise ValidationError(f"El campo '{etiqueta}' solo puede contener números.")
        if not (10 <= len(valor) <= 11):
            raise ValidationError(f"El campo '{etiqueta}' debe tener entre 10 y 11 dígitos.")
        return valor

    def _validar_email(self, valor, etiqueta):
        valor = (valor or '').strip()
        if not valor:
            return ''
        if not self.REGEX_EMAIL.match(valor):
            raise ValidationError(f"El campo '{etiqueta}' no tiene un formato válido.")
        return valor.lower()

    def clean_nombres(self):
        return self._validar_nombre(self.cleaned_data.get('nombres'), 'Nombres')

    def clean_apellidos(self):
        return self._validar_nombre(self.cleaned_data.get('apellidos'), 'Apellidos')

    def clean_cedula(self):
        cedula = self._validar_cedula(self.cleaned_data.get('cedula'), 'Cédula')
        qs = self._meta.model.objects.filter(cedula=cedula)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                f"Ya existe un registro con la cédula {cedula} en esta categoría."
            )
        return cedula

    def clean_telefono(self):
        return self._validar_telefono(self.cleaned_data.get('telefono'), 'Teléfono')

    def clean_email(self):
        return self._validar_email(self.cleaned_data.get('email'), 'Correo')

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if not fecha:
            raise ValidationError("La fecha de nacimiento es obligatoria.")
        if fecha > date.today():
            raise ValidationError("La fecha de nacimiento no puede ser en el futuro.")
        edad = date.today().year - fecha.year - (
            (date.today().month, date.today().day) < (fecha.month, fecha.day)
        )
        if edad < 18:
            raise ValidationError("El personal debe ser mayor de 18 años.")
        if edad > 80:
            raise ValidationError("La edad no parece válida (máx. 80 años).")
        return fecha

    def clean_fecha_ingreso(self):
        fecha = self.cleaned_data.get('fecha_ingreso')
        if not fecha:
            raise ValidationError("La fecha de ingreso es obligatoria.")
        if fecha > date.today():
            raise ValidationError("La fecha de ingreso no puede ser en el futuro.")
        return fecha


# ================================================================
# DOCENTE
# ================================================================
class DocenteForm(_PersonalBaseForm):
    nivel_grado = forms.ChoiceField(
        choices=NIVEL_GRADO_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Nivel / Grado',
    )

    class Meta:
        model = Docente
        fields = [
            'nombres', 'apellidos', 'cedula', 'nacionalidad',
            'fecha_nacimiento', 'genero',
            'fecha_ingreso',
            'nivel_grado', 'especialidad',
            'telefono', 'email', 'direccion',
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres', 'autocomplete': 'off'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos', 'autocomplete': 'off'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12345678', 'autocomplete': 'off'}),
            'nacionalidad': forms.Select(attrs={'class': 'form-select'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Matemáticas, Educación Física...'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 04141234567 (opcional)', 'autocomplete': 'off'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com (opcional)', 'autocomplete': 'off'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dirección (opcional)'}),
        }
        labels = {
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'cedula': 'Cédula',
            'nacionalidad': 'Nacionalidad',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'fecha_ingreso': 'Fecha de Ingreso a la Institución',
            'genero': 'Género',
            'nivel_grado': 'Nivel / Grado',
            'especialidad': 'Especialidad',
            'telefono': 'Teléfono',
            'email': 'Correo',
            'direccion': 'Dirección',
        }

    def clean_nivel_grado(self):
        nivel = self.cleaned_data.get('nivel_grado')
        if not nivel:
            raise ValidationError("Debe seleccionar un Nivel / Grado.")
        qs = Docente.objects.filter(nivel_grado=nivel, activo=True)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            docente_existente = qs.first()
            raise ValidationError(
                f"Ya existe un docente registrado para {nivel} "
                f"({docente_existente.nombres} {docente_existente.apellidos}). "
                f"Solo puede haber uno por nivel/grado."
            )
        return nivel


# ================================================================
# PERSONAL ADMINISTRATIVO
# ================================================================
class PersonalAdministrativoForm(_PersonalBaseForm):
    class Meta:
        model = PersonalAdministrativo
        fields = [
            'nombres', 'apellidos', 'cedula', 'nacionalidad',
            'fecha_nacimiento', 'genero',
            'fecha_ingreso',
            'cargo', 'cargo_detalle',
            'telefono', 'email', 'direccion',
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres', 'autocomplete': 'off'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos', 'autocomplete': 'off'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12345678', 'autocomplete': 'off'}),
            'nacionalidad': forms.Select(attrs={'class': 'form-select'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'cargo_detalle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Especifique el cargo'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 04141234567 (opcional)', 'autocomplete': 'off'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com (opcional)', 'autocomplete': 'off'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dirección (opcional)'}),
        }
        labels = {
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'cedula': 'Cédula',
            'nacionalidad': 'Nacionalidad',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'fecha_ingreso': 'Fecha de Ingreso a la Institución',
            'genero': 'Género',
            'cargo': 'Cargo',
            'cargo_detalle': 'Especifique el cargo',
            'telefono': 'Teléfono',
            'email': 'Correo',
            'direccion': 'Dirección',
        }

    def clean_cargo(self):
        cargo = self.cleaned_data.get('cargo')
        if not cargo:
            raise ValidationError("Debe seleccionar un Cargo.")
        if cargo == 'Otro':
            return cargo
        qs = PersonalAdministrativo.objects.filter(cargo=cargo, activo=True)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            admin_existente = qs.first()
            raise ValidationError(
                f"Ya existe un {cargo} registrado "
                f"({admin_existente.nombres} {admin_existente.apellidos}). "
                f"Solo puede haber uno por cargo."
            )
        return cargo

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('cargo') == 'Otro' and not (cleaned_data.get('cargo_detalle') or '').strip():
            self.add_error('cargo_detalle', "Debe especificar el cargo cuando selecciona 'Otro'.")
        return cleaned_data


# ================================================================
# PERSONAL DE APOYO
# ================================================================
class PersonalApoyoForm(_PersonalBaseForm):
    class Meta:
        model = PersonalApoyo
        fields = [
            'nombres', 'apellidos', 'cedula', 'nacionalidad',
            'fecha_nacimiento', 'genero',
            'fecha_ingreso',
            'cargo', 'cargo_detalle',
            'telefono', 'email', 'direccion',
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres', 'autocomplete': 'off'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos', 'autocomplete': 'off'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12345678', 'autocomplete': 'off'}),
            'nacionalidad': forms.Select(attrs={'class': 'form-select'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'cargo_detalle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Especifique el cargo'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 04141234567 (opcional)', 'autocomplete': 'off'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com (opcional)', 'autocomplete': 'off'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dirección (opcional)'}),
        }
        labels = {
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'cedula': 'Cédula',
            'nacionalidad': 'Nacionalidad',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'fecha_ingreso': 'Fecha de Ingreso a la Institución',
            'genero': 'Género',
            'cargo': 'Cargo',
            'cargo_detalle': 'Especifique el cargo',
            'telefono': 'Teléfono',
            'email': 'Correo',
            'direccion': 'Dirección',
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('cargo') == 'Otro' and not (cleaned_data.get('cargo_detalle') or '').strip():
            self.add_error('cargo_detalle', "Debe especificar el cargo cuando selecciona 'Otro'.")
        return cleaned_data


# ================================================================
# PERSONAL DE COCINA
# ================================================================
class PersonalCocinaForm(_PersonalBaseForm):
    class Meta:
        model = PersonalCocina
        fields = [
            'nombres', 'apellidos', 'cedula', 'nacionalidad',
            'fecha_nacimiento', 'genero',
            'fecha_ingreso',
            'cargo',
            'telefono', 'email', 'direccion',
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres', 'autocomplete': 'off'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos', 'autocomplete': 'off'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12345678', 'autocomplete': 'off'}),
            'nacionalidad': forms.Select(attrs={'class': 'form-select'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 04141234567 (opcional)', 'autocomplete': 'off'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com (opcional)', 'autocomplete': 'off'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dirección (opcional)'}),
        }
        labels = {
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'cedula': 'Cédula',
            'nacionalidad': 'Nacionalidad',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'fecha_ingreso': 'Fecha de Ingreso a la Institución',
            'genero': 'Género',
            'cargo': 'Cargo',
            'telefono': 'Teléfono',
            'email': 'Correo',
            'direccion': 'Dirección',
        }

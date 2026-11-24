from django import forms
from .models import Producto, ConsultaCliente


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'precio', 'stock', 'imagen', 'imagen_url']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la herramienta o producto'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Categoría (ej: Eléctricas, Fijaciones)'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Precio en CLP'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Unidades en stock'}),
            'imagen_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'URL de imagen externa (opcional)'}),
        }


class ConsultaClienteForm(forms.ModelForm):
    """
    ModelForm de Consulta de Clientes (Evaluación Sumativa 3 - ES3).
    Cumple con el criterio 2.1.4: validaciones operativas (campos obligatorios,
    correo válido, largo mínimo) y mensajes de rechazo claros.
    """
    class Meta:
        model = ConsultaCliente
        fields = ['nombre', 'correo', 'producto_interes', 'mensaje']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tu nombre y apellido',
                'autocomplete': 'name',
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'tu-correo@ejemplo.com',
                'autocomplete': 'email',
            }),
            'producto_interes': forms.Select(attrs={
                'class': 'form-select',
            }),
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Escribe tu consulta o requerimiento aquí (mínimo 10 caracteres)...',
            }),
        }
        labels = {
            'nombre': 'Nombre Completo',
            'correo': 'Correo Electrónico',
            'producto_interes': 'Producto de Interés (Opcional)',
            'mensaje': 'Mensaje de Consulta',
        }
        help_texts = {
            'nombre': 'Ingresa tu nombre (mínimo 3 caracteres).',
            'correo': 'Te responderemos a esta dirección de correo.',
            'producto_interes': 'Si tu consulta es sobre una herramienta específica, selecciónala aquí.',
            'mensaje': 'Detalla tu duda, cotización o consulta de stock.',
        }
        error_messages = {
            'nombre': {
                'required': 'El nombre del cliente es obligatorio.',
                'max_length': 'El nombre no puede superar los 120 caracteres.',
            },
            'correo': {
                'required': 'El correo electrónico es obligatorio.',
                'invalid': 'Por favor ingresa un correo electrónico válido con formato nombre@dominio.com.',
            },
            'mensaje': {
                'required': 'Debes ingresar un mensaje con tu consulta.',
            },
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return nombre

    def clean_correo(self):
        correo = (self.cleaned_data.get('correo') or '').strip().lower()
        if not correo or '@' not in correo or '.' not in correo:
            raise forms.ValidationError("Ingresa un correo electrónico válido (ejemplo: cliente@gmail.com).")
        return correo

    def clean_mensaje(self):
        mensaje = (self.cleaned_data.get('mensaje') or '').strip()
        if len(mensaje) < 10:
            raise forms.ValidationError("El mensaje debe contener al menos 10 caracteres explicando tu consulta.")
        return mensaje
